#!/usr/bin/env python3
"""Cloud Run HTTP Server for GitHub Roast & Rescue.

Implements the Cloud Run deployment contract:
- Binds to dynamic PORT environment variable (default: 8080)
- Handles POST requests with {"username": "github_handle"}
- Returns structured JSON and terminal-friendly Bento Style layout
- Serves an interactive Bento Style web dashboard at GET /
- Provides health check at GET /health
"""

import json
import os
import re
import sys
import traceback
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Optional, List
import sqlite3

# Initialize SQLite database for Tech Debt Leaderboard
def init_db():
    conn = sqlite3.connect("leaderboard.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS roasts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  archetype TEXT,
                  roast_preview TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_to_leaderboard(username, archetype, roast_preview):
    try:
        conn = sqlite3.connect("leaderboard.db")
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO roasts (username, archetype, roast_preview, timestamp)
                     VALUES (?, ?, ?, CURRENT_TIMESTAMP)''', (username, archetype, roast_preview))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_leaderboard():
    try:
        conn = sqlite3.connect("leaderboard.db")
        c = conn.cursor()
        c.execute('''SELECT username, archetype, roast_preview FROM roasts ORDER BY timestamp DESC LIMIT 10''')
        rows = c.fetchall()
        conn.close()
        return [{"username": r[0], "archetype": r[1], "roast_preview": r[2]} for r in rows]
    except Exception:
        return []


def _get_cached_badge(username: str):
    """Return (archetype, roast_preview) for a user from leaderboard.db, or None."""
    try:
        conn = sqlite3.connect("leaderboard.db")
        c = conn.cursor()
        c.execute(
            "SELECT archetype, roast_preview FROM roasts WHERE lower(username) = lower(?) LIMIT 1",
            (username,),
        )
        row = c.fetchone()
        conn.close()
        if row:
            return (row[0] or "Roasted Dev", row[1] or "")
        return None
    except Exception:
        return None


def _badge_context(username: str):
    """Resolve (archetype, preview, roasted) for the README badge.

    Prefers cached leaderboard data (zero API cost); falls back to one
    lightweight public-profile fetch. Never raises — degrades to UNROASTED.
    """
    cached = _get_cached_badge(username)
    if cached:
        return (cached[0], cached[1], True)
    try:
        client = get_github_client()
        profile = client.get_user_profile(username)
    except Exception:
        profile = None
    if not profile:
        return ("UNROASTED", "Run a roast to earn an archetype", False)
    followers = profile.get("followers", 0) or 0
    repos = profile.get("public_repos", 0) or 0
    return (
        "Fresh Meat (%d followers)" % followers,
        "@%s commands %d public repos — awaiting judgment" % (username, repos),
        False,
    )


def _build_badge_svg(username: str, archetype: str, preview: str, roasted: bool) -> str:
    """Build the 460x90 Neo-Brutalist README badge SVG (brag-slim micro-copy)."""
    from xml.sax.saxutils import escape as _esc
    user = _esc(username)
    arch = _esc((archetype or "Developer")[:26])
    status = "ROASTED" if roasted else "AWAITING ROAST"
    status_fill = "#00ffff" if roasted else "#ffffff"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="460" height="90" '
        'viewBox="0 0 460 90" role="img" aria-label="GitHub Roast badge for @' + user + '">'
        '<rect x="3" y="3" width="454" height="84" fill="#ffff00" stroke="#000000" stroke-width="5"/>'
        '<text x="18" y="30" font-family="monospace" font-size="14" font-weight="900" '
        'fill="#000000" textLength="420" lengthAdjust="spacingAndGlyphs">'
        '&#x1F525; ROAST &amp; RESCUE // @' + user + '</text>'
        '<rect x="15" y="42" width="272" height="32" fill="#000000"/>'
        '<text x="27" y="64" font-family="monospace" font-size="14" font-weight="900" '
        'fill="#ff00ff" textLength="248" lengthAdjust="spacingAndGlyphs">' + arch + '</text>'
        '<rect x="297" y="42" width="148" height="32" fill="' + status_fill + '" '
        'stroke="#000000" stroke-width="3"/>'
        '<text x="371" y="63" text-anchor="middle" font-family="monospace" '
        'font-size="12" font-weight="900" fill="#000000">' + status + '</text>'
        '</svg>'
    )


def _fetch_repo_evidence(client, username, project_repos, top_repo_name="", top_langs=None):
    """Aggregate language bytes and file skeletons across top project repos.

    Top-repo-only view under-measures polyglot devs, so languages are
    summed over up to 5 projects and recursive file trees are pulled for
    up to 3 (Dockerfiles, CI workflows, tests, backend and model files).
    Returns (agg_languages, skeletons). Every fetch is guarded; failures
    yield empty maps and the audit falls back to name and topic signals.
    """
    agg = dict(top_langs or {})
    skeletons = {}
    ordered = sorted(
        project_repos or [],
        key=lambda r: ((r or {}).get("stargazers_count", 0) or 0),
        reverse=True,
    )
    skip = (top_repo_name or "").strip().lower()
    lang_fetched = 0
    tree_fetched = 0
    for repo in ordered:
        if not isinstance(repo, dict):
            continue
        name = (repo.get("name", "") or "")
        if not name:
            continue
        if lang_fetched < 4 and name.strip().lower() != skip:
            try:
                langs = client.get_repo_languages(username, name) or {}
            except Exception:
                langs = {}
            for lang, b in (langs or {}).items():
                if b:
                    agg[str(lang)] = agg.get(str(lang), 0) + int(b)
            lang_fetched += 1
        if tree_fetched < 3:
            try:
                branch = (repo.get("default_branch", "") or "")
                fetcher = getattr(client, "get_repo_tree", None)
                paths = fetcher(username, name, branch) if callable(fetcher) else []
            except Exception:
                paths = []
            skeletons[name] = paths or []
            tree_fetched += 1
        if lang_fetched >= 4 and tree_fetched >= 3:
            break
    return agg, skeletons


def _run_full_analysis(client, analyzer_fn, username: str) -> Dict[str, Any]:
    """Run the complete single-user pipeline (used by /battle; /roast keeps its own).

    Raises ValueError when the user cannot be fetched, RuntimeError on
    rate limits. Mirrors the /roast fetch stages: profile, repos, events,
    top-repo readme/languages/verified-commits, then analysis.
    """
    profile_data = client.get_user_profile(username)
    if profile_data is None:
        raise ValueError(
            "GitHub user '@%s' could not be fetched. Either the user does not "
            "exist or GitHub API rate limit was reached." % username
        )
    repos_data = client.get_user_repos(username) or []
    events_data = client.get_recent_activity(username) or []

    try:
        profile_readme = client.get_repo_readme(username, username) or ""
    except Exception:
        profile_readme = ""
    project_repos = [
        r for r in repos_data
        if isinstance(r, dict)
        and (r.get("name", "") or "").strip().lower() != username.lower()
    ]
    top_repo_name = ""
    ordered = sorted(project_repos, key=lambda r: (r or {}).get("stargazers_count", 0), reverse=True)
    if ordered:
        top_repo_name = (ordered[0] or {}).get("name", "")

    readme_content = ""
    top_repo_languages = {}
    verified_commits = []
    if top_repo_name:
        try:
            readme_content = client.get_repo_readme(username, top_repo_name)
        except Exception:
            readme_content = ""
        try:
            top_repo_languages = client.get_repo_languages(username, top_repo_name)
        except Exception:
            top_repo_languages = {}
        try:
            fetcher = getattr(client, "get_repo_commits", None)
            if callable(fetcher):
                verified_commits = fetcher(username, top_repo_name, username, 10) or []
        except Exception:
            verified_commits = []

    audit_langs, repo_skeletons = _fetch_repo_evidence(
        client, username, project_repos, top_repo_name, top_repo_languages
    )

    try:
        return analyzer_fn(
            profile_data, repos_data, username,
            events_data=events_data, readme_content=readme_content,
            repo_languages=top_repo_languages, verified_commits=verified_commits,
            profile_readme=profile_readme, audit_languages=audit_langs,
            repo_files=repo_skeletons,
        )
    except TypeError:
        try:
            return analyzer_fn(
                profile_data, repos_data, username,
                events_data=events_data, readme_content=readme_content,
                repo_languages=top_repo_languages,
            )
        except TypeError:
            try:
                return analyzer_fn(
                    profile_data, repos_data, username,
                    events_data=events_data, readme_content=readme_content,
                )
            except TypeError:
                try:
                    return analyzer_fn(profile_data, repos_data, username, events_data=events_data)
                except TypeError:
                    return analyzer_fn(profile_data, repos_data, username)

init_db()

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")

# System architecture integration: Python + REST API + Cloud Run
# Backend powers UI & Serving.

# Attempt to import core modules with graceful fallback if in-progress by other agents
def get_analyzer_fn():
    """Dynamically get analyze_profile function to support parallel edits."""
    try:
        import analyzer
        import importlib
        importlib.reload(analyzer)
        if hasattr(analyzer, "analyze_profile"):
            return analyzer.analyze_profile
    except Exception:
        pass

    # Built-in fallback analyzer if sibling agent is actively recompiling analyzer.py
    def fallback_analyze(
        profile: Dict[str, Any],
        repos: Any,
        username: str,
        events_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        try:
            import analyzer
            return analyzer.analyze_profile(profile, repos if isinstance(repos, list) else [], username, events_data=events_data)
        except Exception:
            pass

        repos_list = repos if isinstance(repos, list) else []
        repo_count = len(repos_list)
        langs = [r.get("primary_language") for r in repos_list if isinstance(r, dict) and r.get("primary_language")]
        lang_str = ", ".join(list(set(filter(None, langs)))[:3]) if langs else "Code"
        bio = profile.get("bio") or "No bio provided"
        followers = profile.get("followers", 0)

        glance = (
            f"• Core Stack : {lang_str}\n"
            f"• Footprint  : {repo_count} public repos | {followers:,} followers\n"
            f"• Profile    : {bio}"
        )
        roast = (
            "🔥 ARCHETYPE: The Stealth Builder\n\n"
            f"@{username} manages {repo_count} public repositories with '{bio}'. "
            "Either you're a stealth architect or saving the bio for the IPO."
        )
        rescue = (
            f"1. ⚡ 10-MIN QUICK WIN:\n   Pin your best {lang_str} repository and write a 1-sentence bio stating what you actually build.\n\n"
            "2. 🎯 WEEKEND PROJECT:\n   Add an animated demo GIF, quickstart code block, and badges to your top repo's README.\n\n"
            "3. 🚀 CAREER LEVERAGE:\n   Ship 1 reviewed pull request to an upstream open-source project."
        )

        return {
            "username": username,
            "recruiter_glance": glance,
            "roast": roast,
            "rescue": rescue,
            "profile": profile,
            "repo_count": repo_count,
        }

    return fallback_analyze


def get_github_client():
    """Dynamically get GitHubClient instance."""
    try:
        from github_client import GitHubClient
        return GitHubClient()
    except Exception:
        # Fallback inline client using requests
        import requests
        class FallbackGitHubClient:
            def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
                r = requests.get(f"https://api.github.com/users/{username}", headers={"Accept": "application/vnd.github+v3+json"}, timeout=10)
                if r.status_code == 404:
                    return None
                elif r.status_code != 200:
                    raise RuntimeError(f"GitHub API error: {r.status_code}")
                return r.json()

            def get_user_repos(self, username: str, per_page: int = 10, sort: str = "stars") -> Optional[List[Dict[str, Any]]]:
                r = requests.get(f"https://api.github.com/users/{username}/repos", params={"per_page": per_page, "sort": sort}, headers={"Accept": "application/vnd.github+v3+json"}, timeout=10)
                if r.status_code == 404:
                    return []
                elif r.status_code != 200:
                    raise RuntimeError(f"GitHub API error: {r.status_code}")
                return r.json()

            def get_recent_activity(self, username: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
                r = requests.get(f"https://api.github.com/users/{username}/events", params={"per_page": limit}, headers={"Accept": "application/vnd.github+v3+json"}, timeout=10)
                if r.status_code == 404:
                    return []
                return r.json() if r.status_code == 200 else []
        return FallbackGitHubClient()


def get_brutalist_formatter():
    """Dynamically get Brutalist layout formatter."""
    try:
        import output
        import importlib
        importlib.reload(output)
        if hasattr(output, "brutalist_layout"):
            return output.brutalist_layout
    except Exception:
        pass

    def fallback_brutalist(sections: Dict[str, str], width: int = 80) -> str:
        lines = [
            "█" * width,
            "  GITHUB ROAST & RESCUE  ".center(width, "█"),
            "  Honest feedback with actionable improvement advice  ".center(width, "█"),
            "█" * width,
            ""
        ]
        for name, content in sections.items():
            lines.append("▀" * width)
            lines.append(f"  {name.upper()}  ".center(width, "█"))
            lines.append("▄" * width)
            for line in content.split("\n"):
                lines.append(f" █  {line}")
            lines.append("")
        lines.append("≡" * width)
        return "\n".join(lines)

    return fallback_brutalist


# Bento Style Web Dashboard HTML (Neo-Brutalist Edition)
BENTO_WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub Roast & Rescue // Neo-Brutalist Bento</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    :root {
      --bg-canvas: #f4f1ea;
      --border-black: 6px solid #000000;
      --shadow-hard: 12px 12px 0px #000000;
      --shadow-btn: 6px 6px 0px #000000;
      --neon-cyan: #00ffff;
      --neon-magenta: #ff00ff;
      --neon-yellow: #ffff00;
      --font-display: 'Space Grotesk', -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', Courier, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; border-radius: 0 !important; }

    body {
      background-color: var(--bg-canvas);
      background-image:
        radial-gradient(rgba(0,0,0,0.55) 1.5px, transparent 1.6px),
        linear-gradient(rgba(0,0,0,0.10) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,0,0,0.10) 1px, transparent 1px);
      background-size: 26px 26px, 40px 40px, 40px 40px;
      color: #000000;
      font-family: var(--font-display);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem 3rem 1rem;
      overflow-x: hidden;
    }

    .container {
      max-width: 1600px;
      width: 95%;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      position: relative;
      z-index: 1;
    }

    /* Floating backdrop decor – fixed CMYK shapes behind content */
    .bg-decor {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      overflow: hidden;
    }

    .bg-watermark {
      position: absolute;
      top: 34%;
      left: 50%;
      transform: translate(-50%, -50%) rotate(-6deg);
      font-family: var(--font-display);
      font-size: 17vw;
      font-weight: 900;
      letter-spacing: -0.04em;
      white-space: nowrap;
      color: transparent;
      -webkit-text-stroke: 2px rgba(0,0,0,0.10);
    }

    .shape {
      position: absolute;
      border: 5px solid #000000;
      box-shadow: 6px 6px 0px #000000;
      border-radius: 0 !important;
      animation: drift 9s ease-in-out infinite;
    }

    .shape-ring {
      border-radius: 50% !important;
      background: transparent;
    }

    .shape-plus::before,
    .shape-plus::after {
      content: "";
      position: absolute;
      background: inherit;
    }

    @keyframes drift {
      0%, 100% { transform: translateY(0) rotate(var(--r, 0deg)); }
      50% { transform: translateY(-16px) rotate(var(--r, 0deg)); }
    }

    @media (prefers-reduced-motion: reduce) {
      .shape, .bg-watermark { animation: none; }
    }

    /* Hazard-stripe section dividers */
    .hazard-strip {
      height: 18px;
      background: repeating-linear-gradient(-45deg, #000000 0 18px, var(--neon-yellow) 18px 36px);
      border-top: 4px solid #000000;
      border-bottom: 4px solid #000000;
      border-radius: 0 !important;
    }

    /* Marker highlighter – drags the eye to what matters */
    .hl {
      font-weight: 900;
      padding: 0 5px;
      border-radius: 0 !important;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
    }

    .hl-yellow {
      background: linear-gradient(transparent 18%, var(--neon-yellow) 18%, var(--neon-yellow) 88%, transparent 88%);
    }

    .hl-pink {
      background: linear-gradient(transparent 18%, var(--neon-magenta) 18%, var(--neon-magenta) 88%, transparent 88%);
    }

    .hl-cyan {
      background: linear-gradient(transparent 18%, var(--neon-cyan) 18%, var(--neon-cyan) 88%, transparent 88%);
    }

    /* Top Triad Badge */
    .top-badge-row {
      display: flex;
      justify-content: center;
      margin-bottom: 0.5rem;
    }

    .triad-badge {
      background: var(--neon-yellow);
      color: #000000;
      border: var(--border-black);
      box-shadow: var(--shadow-btn);
      padding: 0.5rem 1.5rem;
      font-family: var(--font-mono);
      font-size: 1rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }

    /* Header */
    header {
      text-align: center;
      background: var(--neon-cyan);
      border: var(--border-black);
      box-shadow: var(--shadow-hard);
      padding: 3rem 1rem;
      width: 100%;
      margin-bottom: 2rem;
    }

    h1 {
      font-size: 5rem;
      font-weight: 900;
      letter-spacing: -0.05em;
      text-transform: uppercase;
      line-height: 1;
      margin-bottom: 1rem;
      color: #000000;
      text-shadow: 6px 6px 0px #ffffff;
    }

    h1 span.flame { background: var(--neon-magenta); padding: 0 15px; border: var(--border-black); display: inline-block; transform: rotate(-2deg); }
    h1 span.rescue { background: var(--neon-yellow); padding: 0 15px; border: var(--border-black); display: inline-block; transform: rotate(2deg); }

    p.subtitle {
      color: #000000;
      background: #ffffff;
      display: inline-block;
      padding: 0.5rem 1rem;
      border: 4px solid #000000;
      font-size: 1.5rem;
      font-weight: 800;
      text-transform: uppercase;
      margin-top: 1rem;
    }

    /* Brutalist Input Bar */
    .search-box {
      background: #ffffff;
      border: var(--border-black);
      box-shadow: var(--shadow-hard);
      padding: 1rem;
      display: flex;
      gap: 1rem;
      transition: all 0.1s ease;
      align-items: center;
      position: relative;
      z-index: 50;
      opacity: 1 !important;
    }

    .search-box:focus-within {
      background: var(--neon-yellow);
    }

    .input-prefix {
      color: #000000;
      font-family: var(--font-mono);
      font-weight: 900;
      font-size: 2rem;
      display: flex;
      align-items: center;
      padding-left: 0.5rem;
    }

    input[type="text"] {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #000000;
      font-size: 2rem;
      font-family: var(--font-mono);
      font-weight: 800;
      text-transform: uppercase;
    }

    input[type="text"]::placeholder {
      color: #aaaaaa;
    }

    button.btn-roast {
      background: var(--neon-magenta);
      color: #000000;
      border: var(--border-black);
      box-shadow: var(--shadow-btn);
      padding: 1rem 2rem;
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }

    button.btn-roast:hover {
      transform: translate(-4px, -4px);
      box-shadow: 10px 10px 0px #000000;
      background: var(--neon-cyan);
    }

    button.btn-roast:active {
      transform: translate(2px, 2px);
      box-shadow: 4px 4px 0px #000000;
    }

    .shortcuts-row {
      display: flex;
      justify-content: center;
      gap: 2rem;
      font-size: 1rem;
      font-family: var(--font-mono);
      color: #000000;
      font-weight: 800;
      background: #ffffff;
      border: var(--border-black);
      padding: 1rem;
      box-shadow: var(--shadow-btn);
    }

    .kbd {
      background: var(--neon-yellow);
      padding: 0.2rem 0.5rem;
      border: 3px solid #000000;
      color: #000000;
      font-weight: 900;
      box-shadow: 3px 3px 0px #000;
    }

    .error-box {
      display: none;
      background: #ff0000;
      border: var(--border-black);
      box-shadow: var(--shadow-hard);
      color: #ffffff;
      padding: 2rem;
      font-family: var(--font-mono);
      font-size: 1.5rem;
      font-weight: 900;
      text-transform: uppercase;
    }

    /* Brutalist Grid – widescreen masonry, above-the-fold pack */
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      grid-auto-flow: dense;
      gap: 1.5rem;
      align-items: start;
    }

    .bento-card {
      background: #ffffff;
      border: var(--border-black);
      border-radius: 0 !important;
      padding: 1.75rem;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-hard);
      position: relative;
      z-index: 10;
      min-width: 0;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 6px solid #000000;
    }

    .badge-tag {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 900;
      padding: 0.5rem 1rem;
      border: 4px solid #000;
      box-shadow: 4px 4px 0px #000;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .tag-cyan { background: var(--neon-cyan); color: #000; }
    .tag-orange { background: var(--neon-magenta); color: #000; }
    .tag-lime { background: var(--neon-yellow); color: #000; }
    .tag-purple { background: #ffffff; color: #000; }

    /* Grid Layouts – row 1: Recruiter + Roast / row 2: Mental + Rescue */
    .card-recruiter {
      grid-column: span 4;
      background: #ffffff;
    }

    .card-roast {
      grid-column: span 8;
      background: var(--neon-cyan);
      z-index: 20;
      overflow: visible;
    }

    .card-rescue {
      grid-column: span 8;
      background: var(--neon-yellow);
    }

    .tag-red { background: #ff0000; color: #ffffff; }
    .tag-yellow { background: var(--neon-yellow); color: #000; }

    /* Resume vs. Reality audit card – full-width evidence board */
    .card-reality {
      grid-column: span 12;
      background: #ffffff;
      border: var(--border-black);
      box-shadow: var(--shadow-hard);
      padding: 1.5rem;
      position: relative;
      border-radius: 0 !important;
    }

    .reality-headline {
      font-weight: 700;
      font-size: 0.95rem;
      margin-bottom: 0.75rem;
      color: #1e293b;
    }

    .reality-list {
      display: flex;
      flex-direction: column;
    }

    .reality-item {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
      background: #f8fafc;
      border: 2px solid #000000;
      border-left-width: 8px;
      border-radius: 0 !important;
    }

    @media (max-width: 768px) {
      .reality-item { grid-template-columns: 1fr; }
    }

    .reality-claim { font-weight: 700; color: #ef4444; }
    .reality-truth { color: #0f172a; }
    .sev-high-vibe { border-left-color: #ef4444; }
    .sev-medium-vibe { border-left-color: #f59e0b; }
    .sev-verified { border-left-color: #22c55e; }
    .sev-verified .reality-claim { color: #15803d; }

    .reality-verdict {
      margin-top: 1rem;
      padding: 0.75rem;
      background: #fffbe5;
      border-left: 4px solid #000;
      font-size: 0.9rem;
      font-family: var(--font-mono);
      border-radius: 0 !important;
    }

    .reality-paste {
      margin-top: 1rem;
      border: 2px dashed #000000;
      padding: 0.75rem 1rem;
      border-radius: 0 !important;
    }

    .reality-paste summary {
      cursor: pointer;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 800;
      text-transform: uppercase;
    }

    .reality-paste textarea {
      width: 100%;
      margin-top: 0.75rem;
      font-family: var(--font-mono);
      font-size: 0.9rem;
      border: 3px solid #000000;
      padding: 0.6rem;
      border-radius: 0 !important;
      resize: vertical;
    }

    /* Mental Stability card */
    .card-mental {
      grid-column: span 4;
      background: #ffffff;
      border-top: 12px solid #ff0000;
    }

    .mental-content {
      font-family: var(--font-mono);
      font-size: 1.1rem;
      line-height: 1.7;
      color: #000000;
      font-weight: 800;
      white-space: pre-line;
    }

    .mental-status {
      display: inline-block;
      background: #000000;
      color: #00ff00;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 900;
      padding: 0.3rem 0.7rem;
      border: 3px solid #000000;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 1rem;
    }

    @media (max-width: 1100px) {
      .card-recruiter { grid-column: span 5; }
      .card-roast { grid-column: span 7; }
      .card-mental { grid-column: span 12; }
      .card-rescue { grid-column: span 12; }
    }

    @media (max-width: 860px) {
      .card-recruiter, .card-roast, .card-mental, .card-rescue { grid-column: span 12; }
      h1 { font-size: 3rem; }
      .meme-clip { display: none; }
    }

    /* WALL OF SHAME – off-canvas drawer + fixed toggle tab */
    .shame-toggle {
      position: fixed;
      right: 0;
      top: 50%;
      transform: translateY(-50%);
      z-index: 100;
      background: #ff0000;
      color: #ffffff;
      border: 6px solid #000000;
      border-right: none;
      box-shadow: -6px 6px 0px #000000;
      writing-mode: vertical-rl;
      font-family: var(--font-display);
      font-size: 1.2rem;
      font-weight: 900;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      padding: 1.5rem 0.8rem;
      cursor: pointer;
      border-radius: 0 !important;
    }

    .shame-toggle:hover {
      background: var(--neon-yellow);
      color: #000000;
    }

    .shame-drawer {
      position: fixed;
      top: 0;
      right: 0;
      width: min(400px, 92vw);
      height: 100vh;
      z-index: 99;
      background: var(--neon-yellow);
      border-left: 6px solid #000000;
      box-shadow: -12px 0 0 #000000;
      transform: translateX(100%);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-radius: 0 !important;
    }

    .shame-drawer-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      background: #000000;
      color: #ffffff;
      font-family: var(--font-display);
      font-size: 1.4rem;
      font-weight: 900;
      text-transform: uppercase;
      padding: 1.25rem;
      border-bottom: 6px solid #000000;
    }

    .shame-close {
      background: #ff0000;
      color: #ffffff;
      border: 4px solid #ffffff;
      box-shadow: 4px 4px 0px rgba(255, 255, 255, 0.35);
      font-family: var(--font-display);
      font-size: 1rem;
      font-weight: 900;
      padding: 0.4rem 0.8rem;
      cursor: pointer;
      border-radius: 0 !important;
    }

    .shame-close:hover {
      background: #ffffff;
      color: #000000;
      border-color: #000000;
    }

    .shame-sub {
      background: #ffffff;
      border-bottom: 6px solid #000000;
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 800;
      text-transform: uppercase;
      padding: 0.75rem 1.25rem;
      color: #000000;
    }

    .shame-list {
      overflow-y: auto;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .shame-card {
      background: #ffffff;
      border: 4px solid #000000;
      box-shadow: 6px 6px 0px #000000;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      border-radius: 0 !important;
    }

    .shame-user {
      font-family: var(--font-mono);
      font-size: 1.1rem;
      font-weight: 900;
      color: #000000;
    }

    .shame-archetype {
      display: inline-block;
      align-self: flex-start;
      background: #000000;
      color: var(--neon-yellow);
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.3rem 0.6rem;
      border-radius: 0 !important;
    }

    .shame-preview {
      font-family: var(--font-mono);
      font-size: 0.95rem;
      font-weight: 700;
      line-height: 1.5;
      color: #000000;
    }

    .shame-empty {
      background: #ffffff;
      border: 4px dashed #000000;
      font-family: var(--font-mono);
      font-size: 1rem;
      font-weight: 800;
      padding: 1.5rem;
      text-align: center;
      color: #000000;
      border-radius: 0 !important;
    }

    /* Dimensional planes (scroll-craft): shadow plane / card plane / meme plane */
    .plane-shadow { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
    .plane-card { position: relative; z-index: 20; }
    .plane-meme { position: absolute; z-index: 10; pointer-events: none; }

    .meme-clip {
      position: absolute;
      top: -36px;
      right: -60px;
      width: 240px;
      z-index: 10;
      transform: rotate(12deg);
      background: #ffffff;
      border: 4px solid #000000;
      border-radius: 0 !important;
      box-shadow: 8px 8px 0px #000000;
      padding: 10px 10px 8px 10px;
      pointer-events: none;
      transition: z-index 0s, transform 0.3s ease;
    }

    .card-roast:hover .meme-clip {
      z-index: -1;
      transform: rotate(12deg) scale(0.95) translate(10px, 10px);
    }

    /* Generic Emoji Stickers for other cards */
    .sticker {
      position: absolute;
      z-index: 10;
      background: #ffffff;
      border: 4px solid #000000;
      box-shadow: 6px 6px 0px #000000;
      padding: 15px;
      pointer-events: none;
      transition: z-index 0s, transform 0.3s ease;
    }

    .sticker .sticker-tape {
      position: absolute;
      top: -12px;
      left: 50%;
      width: 70px;
      height: 22px;
      margin-left: -35px;
      background: rgba(255, 255, 0, 0.85);
      border: 2px solid #000;
      transform: rotate(-10deg);
    }

    .sticker-emoji {
      font-size: 3.5rem;
      text-align: center;
      line-height: 1;
    }

    .sticker-recruiter { top: -25px; right: -25px; transform: rotate(15deg); }
    .card-recruiter:hover .sticker-recruiter { z-index: -1; transform: rotate(15deg) scale(0.95) translate(10px, 10px); }

    .sticker-mental { bottom: -25px; right: -15px; transform: rotate(-10deg); }
    .card-mental:hover .sticker-mental { z-index: -1; transform: rotate(-10deg) scale(0.95) translate(10px, 10px); }

    .sticker-rescue { top: -25px; right: 50px; transform: rotate(8deg); }
    .card-rescue:hover .sticker-rescue { z-index: -1; transform: rotate(8deg) scale(0.95) translate(10px, 10px); }

    .meme-clip .meme-pin {
      position: absolute;
      top: -16px;
      left: 50%;
      width: 28px;
      height: 28px;
      margin-left: -14px;
      background: radial-gradient(circle at 35% 30%, #ff5a5a 0 30%, #cc0000 31% 100%);
      border: 3px solid #000000;
      border-radius: 50% !important;
      box-shadow: 3px 3px 0px #000;
    }

    .meme-clip .meme-tape {
      position: absolute;
      top: -12px;
      left: -18px;
      width: 90px;
      height: 26px;
      background: rgba(255, 255, 0, 0.85);
      border: 2px solid #000;
      transform: rotate(-18deg);
      opacity: 0.9;
    }

    .meme-clip img {
      display: block;
      width: 100%;
      height: auto;
      border: 3px solid #000000;
      border-radius: 0 !important;
      background: #fff;
      filter: contrast(1.15) grayscale(0.1);
    }

    .meme-clip .meme-caption {
      margin-top: 8px;
      background: #000000;
      color: var(--neon-yellow);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 6px 8px;
      text-align: center;
      border-radius: 0 !important;
    }

    .meme-clip .meme-archetype {
      margin-top: 6px;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 800;
      text-transform: uppercase;
      text-align: center;
      color: #000;
    }

    /* Content Typography */
    .recruiter-content {
      font-family: var(--font-mono);
      font-size: 1.25rem;
      line-height: 1.8;
      color: #000000;
      white-space: pre-line;
      font-weight: 900;
    }

    .roast-quote-box {
      background: #ffffff;
      border: var(--border-black);
      padding: 2rem;
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 600;
      line-height: 1.75;
      white-space: pre-wrap;
      color: #000000;
      box-shadow: var(--shadow-btn);
    }

    .roast-p {
      margin-bottom: 1rem;
    }

    .roast-p:last-child {
      margin-bottom: 0;
    }

    /* Lucide icons – brutalist defaults */
    .lucide {
      stroke: #000000;
      stroke-width: 2.5px;
      vertical-align: middle;
    }

    .sticker .lucide {
      width: 38px;
      height: 38px;
      stroke-width: 2.8px;
    }

    .badge-tag .lucide,
    .step-header .lucide {
      width: 26px;
      height: 26px;
    }

    .btn-roast .lucide {
      width: 28px;
      height: 28px;
    }

    /* Micro-animations: radar tick, brain pulse, buoy float, flame wiggle */
    .icon-spin:hover {
      transform: rotate(360deg);
      transition: transform 0.6s ease;
    }

    .icon-pulse {
      animation: brain-pulse 1.8s ease-in-out infinite;
    }

    @keyframes brain-pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.15); }
    }

    .icon-buoy {
      animation: buoy-float 3s ease-in-out infinite;
    }

    @keyframes buoy-float {
      0%, 100% { transform: rotate(-5deg); }
      50% { transform: rotate(5deg); }
    }

    .icon-flame {
      animation: flame-wiggle 1.6s ease-in-out infinite;
    }

    @keyframes flame-wiggle {
      0%, 100% { transform: rotate(-6deg) scale(1); }
      50% { transform: rotate(6deg) scale(1.12); }
    }

    @media (prefers-reduced-motion: reduce) {
      .icon-pulse, .icon-buoy, .icon-flame { animation: none; }
    }

    /* Rescue 3-Card Grid */
    .rescue-steps-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 2rem;
      margin-top: 1rem;
    }

    @media (max-width: 800px) {
      .rescue-steps-grid { grid-template-columns: 1fr; }
    }

    .step-card {
      background: #ffffff;
      border: var(--border-black);
      box-shadow: var(--shadow-btn);
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .step-header {
      font-family: var(--font-display);
      font-size: 1.8rem;
      font-weight: 900;
      color: #ffffff;
      background: #000000;
      padding: 1rem;
      border: 4px solid #000000;
      text-transform: uppercase;
      text-align: center;
      box-shadow: 4px 4px 0px var(--neon-magenta);
    }

    .step-body {
      font-family: var(--font-mono);
      font-size: 1.15rem;
      font-weight: 800;
      color: #000000;
      line-height: 1.6;
    }

    .btn-brutal {
      background: var(--neon-magenta);
      color: #000000;
      border: 4px solid #000000;
      box-shadow: 4px 4px 0px #000;
      padding: 0.5rem 1rem;
      font-family: var(--font-display);
      font-size: 1.2rem;
      font-weight: 900;
      text-transform: uppercase;
      cursor: pointer;
      transition: all 0.1s ease;
    }

    .btn-brutal:hover {
      background: var(--neon-cyan);
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0px #000;
    }

    .btn-brutal:active {
      transform: translate(2px, 2px);
      box-shadow: 2px 2px 0px #000;
    }

    /* Subtle brutalist buttons – share bar + battle toggle */
    .btn-subtle {
      background: #ffffff;
      color: #000000;
      border: 4px solid #000000;
      box-shadow: 4px 4px 0px #000000;
      padding: 0.6rem 1.1rem;
      font-family: var(--font-display);
      font-size: 1.05rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      border-radius: 0 !important;
    }

    .btn-subtle:hover {
      background: var(--neon-yellow);
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0px #000000;
    }

    .btn-subtle:active {
      transform: translate(2px, 2px);
      box-shadow: 2px 2px 0px #000000;
    }

    .btn-subtle.active-battle {
      background: #ff0000;
      color: #ffffff;
    }

    .btn-subtle.active-battle .lucide {
      stroke: #ffffff;
    }

    .btn-subtle .lucide {
      width: 22px;
      height: 22px;
    }

    .share-actions-row {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      margin-top: 1.5rem;
    }

    /* Battle mode – opponent input row (hidden until toggled) */
    .battle-input-row {
      display: none;
      background: #ffffff;
      border: var(--border-black);
      box-shadow: var(--shadow-btn);
      padding: 1rem;
      gap: 1rem;
      align-items: center;
      margin-top: 1rem;
    }

    .battle-input-row.open {
      display: flex;
    }

    .battle-input-row .input-prefix {
      font-size: 1.5rem;
    }

    .battle-input-row input[type="text"] {
      font-size: 1.5rem;
    }

    /* Battle Arena modal */
    .battle-overlay {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(0, 0, 0, 0.65);
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }

    .battle-overlay.open {
      display: flex;
    }

    .battle-arena {
      width: min(880px, 95vw);
      max-height: 92vh;
      overflow-y: auto;
      background: var(--neon-yellow);
      border: var(--border-black);
      box-shadow: 12px 12px 0px #000000;
      padding: 2rem;
      border-radius: 0 !important;
    }

    .battle-title {
      font-family: var(--font-display);
      font-size: 2.2rem;
      font-weight: 900;
      text-transform: uppercase;
      background: #000000;
      color: #ffffff;
      display: inline-block;
      padding: 0.5rem 1.2rem;
      border: 4px solid #000000;
      box-shadow: 4px 4px 0px var(--neon-magenta);
      margin-bottom: 1.5rem;
      border-radius: 0 !important;
    }

    .battle-title .lucide {
      stroke: #ffffff;
      width: 30px;
      height: 30px;
    }

    .battle-cols {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }

    @media (max-width: 700px) {
      .battle-cols { grid-template-columns: 1fr; }
    }

    .battle-fighter {
      background: #ffffff;
      border: var(--border-black);
      box-shadow: 6px 6px 0px #000000;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      border-radius: 0 !important;
      position: relative;
    }

    .battle-fighter.winner {
      background: var(--neon-cyan);
    }

    .battle-crown {
      position: absolute;
      top: -22px;
      right: -14px;
      background: #000000;
      border: 4px solid #000000;
      box-shadow: 4px 4px 0px var(--neon-magenta);
      padding: 0.3rem 0.5rem;
      transform: rotate(12deg);
      border-radius: 0 !important;
    }

    .battle-crown .lucide {
      stroke: var(--neon-yellow);
      width: 30px;
      height: 30px;
    }

    .battle-name {
      font-family: var(--font-mono);
      font-size: 1.4rem;
      font-weight: 900;
    }

    .battle-arch {
      display: inline-block;
      align-self: flex-start;
      background: #000000;
      color: var(--neon-yellow);
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 900;
      text-transform: uppercase;
      padding: 0.3rem 0.6rem;
      border-radius: 0 !important;
    }

    .battle-stat {
      font-family: var(--font-mono);
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.6;
    }

    .battle-verdict {
      margin-top: 1.5rem;
      background: #ffffff;
      border: var(--border-black);
      box-shadow: 6px 6px 0px #000000;
      padding: 1.5rem;
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 600;
      line-height: 1.7;
      border-radius: 0 !important;
    }

    .battle-close-row {
      margin-top: 1.5rem;
      display: flex;
      justify-content: flex-end;
    }

    /* Spinner */
    .spinner {
      display: none;
      width: 24px;
      height: 24px;
      border: 6px solid rgba(0, 0, 0, 0.3);
      border-top-color: #000;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="bg-decor" aria-hidden="true">
    <div class="bg-watermark">ROAST ★ RESCUE</div>
    <div class="shape" style="--r: 12deg; top: 12%; left: 2%; width: 72px; height: 72px; background: var(--neon-cyan);"></div>
    <div class="shape shape-ring" style="top: 22%; right: 3%; width: 96px; height: 96px; border-width: 8px;"></div>
    <div class="shape" style="--r: -14deg; top: 46%; left: 1.5%; width: 60px; height: 60px; background: var(--neon-magenta); animation-delay: -3s;"></div>
    <div class="shape" style="--r: 45deg; top: 58%; right: 2%; width: 64px; height: 64px; background: var(--neon-yellow); animation-delay: -5s;"></div>
    <div class="shape shape-ring" style="bottom: 8%; left: 4%; width: 70px; height: 70px; background: var(--neon-yellow); animation-delay: -2s;"></div>
    <div class="shape" style="--r: -8deg; bottom: 12%; right: 5%; width: 88px; height: 28px; background: #000000; animation-delay: -7s;"></div>
  </div>
  <div class="container">
    
    <div class="top-badge-row">
      <div class="triad-badge">⚡ SYSTEM ARCHITECTURE // PYTHON • REST API • CLOUD RUN</div>
    </div>

    <header>
      <h1><span class="flame">ROAST</span> &amp; <span class="rescue">RESCUE</span></h1>
      <p class="subtitle">Bento Dashboard • Zero corporate fluff. Brutal honesty + high-leverage developer advice.</p>
    </header>

    <div class="search-box">
      <span class="input-prefix">@</span>
      <input type="text" id="usernameInput" placeholder="github-username (e.g. octocat, torvalds)" value="octocat" autocomplete="off" spellcheck="false">
      <button class="btn-roast" id="roastBtn" onclick="runRoast()">
        <span class="spinner" id="spinner"></span>
        <span id="btnText">ROAST NOW</span> <i data-lucide="zap"></i>
      </button>
      <button class="btn-subtle" id="toggleBattleBtn" onclick="toggleBattleMode()"><i data-lucide="swords"></i> Battle Mode</button>
    </div>

    <div class="battle-input-row" id="battleRow">
      <span class="input-prefix">VS @</span>
      <input type="text" id="opponentInput" placeholder="opponent-username" value="" autocomplete="off" spellcheck="false">
    </div>

    <div class="shortcuts-row">
      <span><span class="kbd">Enter</span> Analyze</span>
      <span><span class="kbd">Ctrl</span>+<span class="kbd">K</span> Focus Input</span>
    </div>

    <div class="error-box" id="errorBox"></div>

    <div class="hazard-strip" aria-hidden="true"></div>

    <div class="bento-grid">
      
      <!-- 1. Recruiter Scan -->
      <div class="bento-card card-recruiter">
        <div class="sticker sticker-recruiter" aria-hidden="true">
          <div class="sticker-tape"></div>
          <div class="sticker-emoji"><i data-lucide="timer" class="icon-spin"></i></div>
        </div>
        <div class="card-header">
          <span class="badge-tag tag-cyan"><i data-lucide="scan-eye"></i> Recruiter Scan</span>
          <span style="font-size: 0.75rem; color: #64748b; font-family: var(--font-mono);">30-SEC LENS</span>
        </div>
        <div class="recruiter-content" id="recruiterGlanceContent">Loading recruiter scan...</div>
      </div>

      <!-- 2. The Roast + pinned meme clipping behind -->
      <div class="bento-card card-roast plane-card" id="roastCard">
        <div class="plane-shadow"></div>
        <div class="meme-clip plane-meme" id="memeClip" aria-hidden="true">
          <div class="meme-tape"></div>
          <div class="meme-pin"></div>
          <img id="memeImg" src="/assets/tech-deity.svg" alt="Roast archetype meme – photocopy polaroid">
          <div class="meme-caption" id="memeCaption">EXHIBIT A // PHOTOCOPY</div>
          <div class="meme-archetype" id="memeArchetype">THE TECH DEITY</div>
        </div>
        <div class="card-header">
          <span class="badge-tag tag-orange"><i data-lucide="flame" class="icon-flame"></i> The Roast</span>
          <div style="display: flex; gap: 0.75rem; align-items: center;">
            <span style="font-size: 0.75rem; color: #f97316; font-family: var(--font-mono);">PUNCHY WIT</span>
            <button class="btn-brutal" id="copyRoastBtn" onclick="copyRoast()"><i data-lucide="copy" id="copyIcon"></i> Copy Roast</button>
          </div>
        </div>
        <div class="roast-quote-box" id="roastContent">Loading roast...</div>
        <div class="share-actions-row">
          <button class="btn-subtle" id="copyBadgeBtn" onclick="copyBadgeMarkdown()">
            <i data-lucide="badge-check"></i> Copy README Badge
          </button>
          <button class="btn-subtle" onclick="shareRoastOnX()">
            <i data-lucide="share-2"></i> Share on X
          </button>
        </div>
      </div>

      <!-- 2b. Mental Stability (Commit Psych-Eval) – sits below Recruiter Scan -->
      <div class="bento-card card-mental" id="mentalCard">
        <div class="sticker sticker-mental" aria-hidden="true">
          <div class="sticker-tape" style="transform: rotate(8deg);"></div>
          <div class="sticker-emoji"><i data-lucide="brain" class="icon-pulse"></i></div>
        </div>
        <div class="card-header">
          <span class="badge-tag tag-red"><i data-lucide="activity"></i> Mental Stability</span>
          <span style="font-size: 0.75rem; color: #ff0000; font-family: var(--font-mono);">PSYCH-EVAL</span>
        </div>
        <div class="mental-status" id="mentalStatus">[+] AWAITING SCAN</div>
        <div class="mental-content" id="psychEvalContent">Run a roast to evaluate commit psychology…</div>
      </div>

      <!-- 3. The Rescue Plan -->
      <div class="bento-card card-rescue">
        <div class="sticker sticker-rescue" aria-hidden="true">
          <div class="sticker-tape"></div>
          <div class="sticker-emoji"><i data-lucide="life-buoy" class="icon-buoy"></i></div>
        </div>
        <div class="card-header">
          <span class="badge-tag tag-lime"><i data-lucide="life-buoy" class="icon-buoy"></i> The Rescue Plan</span>
          <span style="font-size: 0.75rem; color: #10b981; font-family: var(--font-mono);">ACTION ROADMAP</span>
        </div>
        <div class="rescue-steps-grid" id="rescueStepsGrid">
          <div class="step-card">
            <div class="step-header"><i data-lucide="zap"></i> 10-Min Quick Win</div>
            <div class="step-body" id="rescueStep1">Loading action...</div>
          </div>
          <div class="step-card">
            <div class="step-header"><i data-lucide="target"></i> Weekend Project</div>
            <div class="step-body" id="rescueStep2">Loading action...</div>
          </div>
          <div class="step-card">
            <div class="step-header"><i data-lucide="rocket"></i> Career Growth</div>
            <div class="step-body" id="rescueStep3">Loading action...</div>
          </div>
        </div>
      </div>

      <!-- 5. Resume vs. Reality audit -->
      <div class="bento-card card-reality" id="realityCard">
        <div class="card-header">
          <span class="badge-tag tag-yellow"><i data-lucide="file-search"></i> Resume vs. Reality</span>
          <span class="badge-tag tag-cyan" id="vibeRatioBadge">VIBE AUDIT</span>
        </div>
        <div class="reality-headline" id="realityHeadline">
          Cross-referencing Profile README claims against actual Git telemetry...
        </div>
        <div class="reality-list" id="realityList"></div>
        <div class="reality-verdict" id="realityVerdict"></div>
        <div class="share-actions-row" style="margin-top: 1rem;">
          <button class="btn-subtle" id="uploadResumeBtn" onclick="document.getElementById('resumeFile').click()">
            <i data-lucide="upload"></i> Upload Resume
          </button>
          <input type="file" id="resumeFile" accept=".pdf,.txt,.md,.markdown,.text" hidden onchange="handleResumeFile(this)">
          <span id="resumeFileName" style="font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700; align-self: center;">PDF, TXT or Markdown — compared against live Git telemetry</span>
        </div>
        <details class="reality-paste" id="realityPaste" hidden>
          <summary>No profile README found — paste a bio to audit instead</summary>
          <textarea id="bioPaste" rows="4" placeholder="Paste LinkedIn summary or resume bio…"></textarea>
          <div style="margin-top: 0.6rem;">
            <button class="btn-subtle" onclick="auditPastedBio()">Audit Bio</button>
          </div>
        </details>
      </div>

    </div>

    <div class="hazard-strip" aria-hidden="true"></div>

    <div style="text-align: center; font-size: 0.78rem; color: #64748b; margin-top: 1rem; font-family: var(--font-mono);">
      GitHub Roast &amp; Rescue • Built for AI Hackathon 2026 • Powered by Cloud Run
    </div>
  </div>

  <!-- WALL OF SHAME – off-canvas leaderboard drawer -->
  <button class="shame-toggle" id="shameToggle" onclick="toggleShame()">☠ View Leaderboard</button>
  <aside class="shame-drawer" id="shameDrawer" aria-hidden="true" aria-label="Wall of Shame leaderboard">
    <div class="shame-drawer-header">
      <span>☠ Wall of Shame</span>
      <button class="shame-close" onclick="toggleShame()">✕ Close</button>
    </div>
    <div class="shame-sub">Freshly roasted · hall of commit disgrace</div>
    <div class="shame-list" id="shameList">
      <div class="shame-empty">Loading the hall of shame…</div>
    </div>
  </aside>

  <!-- BATTLE ARENA – head-to-head roast comparison modal -->
  <div class="battle-overlay" id="battleOverlay" onclick="if (event.target === this) toggleBattleArena(false)">
    <div class="battle-arena" id="battleArena" role="dialog" aria-label="Roast battle arena">
      <div class="battle-title"><i data-lucide="swords"></i> Roast Battle</div>
      <div class="battle-cols">
        <div class="battle-fighter" id="fighter1">
          <div class="battle-name" id="battleName1">@—</div>
          <div class="battle-arch" id="battleArch1">—</div>
          <div class="battle-stat" id="battleStats1"></div>
        </div>
        <div class="battle-fighter" id="fighter2">
          <div class="battle-name" id="battleName2">@—</div>
          <div class="battle-arch" id="battleArch2">—</div>
          <div class="battle-stat" id="battleStats2"></div>
        </div>
      </div>
      <div class="battle-verdict" id="battleVerdict"></div>
      <div class="battle-close-row">
        <button class="btn-subtle" onclick="toggleBattleArena(false)">Close Arena</button>
      </div>
    </div>
  </div>

  <script>
    // Meme archetype map – gritty photocopy polaroids
    const MEME_MAP = {
      deity:   { src: '/assets/tech-deity.svg',       label: 'THE TECH DEITY',       caption: 'EXHIBIT A // 10K COMMITS' },
      graveyard: { src: '/assets/graveyard-keeper.svg', label: 'THE GRAVEYARD KEEPER', caption: 'EXHIBIT B // LAST PUSH 2021' },
      ghost:   { src: '/assets/readme-ghost.svg',     label: 'THE README GHOST',     caption: 'EXHIBIT C // NO DOCS' },
      machine: { src: '/assets/commit-machine.svg',   label: 'THE COMMIT MACHINE',   caption: 'EXHIBIT D // 3AM PUSH' }
    };

    function pickMeme(roastText) {
      const t = (roastText || '').toLowerCase();
      if (t.includes('deity') || t.includes('god') || t.includes('legend')) return MEME_MAP.deity;
      if (t.includes('graveyard') || t.includes('empty') || t.includes('abandoned') || t.includes('minimalist')) return MEME_MAP.graveyard;
      if (t.includes('ghost') || t.includes('readme') || t.includes('bio-less') || t.includes('mystery')) return MEME_MAP.ghost;
      if (t.includes('machine') || t.includes('commit') || t.includes('todo-list')) return MEME_MAP.machine;
      const keys = Object.keys(MEME_MAP);
      return MEME_MAP[keys[t.length % keys.length]];
    }

    function brutalEntrance() {
      if (!window.gsap) return;
      gsap.from('.bento-card', {
        y: 90, x: -30, rotation: -1.5, scale: 0.94, opacity: 0,
        duration: 0.65, stagger: 0.11, ease: 'power4.out', clearProps: 'opacity,scale'
      });
      gsap.from('header', { y: -60, rotation: 1.5, opacity: 0, duration: 0.7, ease: 'power4.out' });
      gsap.from('.search-box', { y: 40, scale: 0.97, opacity: 0, duration: 0.55, ease: 'power4.out', delay: 0.15, clearProps: 'all' });
    }

    function springMemeOut() {
      if (!window.gsap) {
        document.getElementById('memeClip').style.opacity = '1';
        return;
      }
      gsap.fromTo('#memeClip',
        { x: -140, y: 20, rotation: 4, opacity: 0, scale: 0.85 },
        { x: 0, y: 0, rotation: 12, opacity: 1, scale: 1, duration: 1.1, ease: 'back.out(1.7)' }
      );
      gsap.fromTo('#roastCard',
        { scale: 0.98, rotation: -0.6 },
        { scale: 1, rotation: 0, duration: 0.6, ease: 'elastic.out(1, 0.55)' }
      );
      gsap.fromTo('.roast-quote-box',
        { x: -24, opacity: 0 },
        { x: 0, opacity: 1, duration: 0.5, ease: 'power4.out', delay: 0.15 }
      );
    }

    // Marker highlighter – escapes HTML first (user data!), then marks
    // numbers yellow, quoted zingers pink, and tech terms cyan.
    function escapeHtml(s) {
      return String(s).replace(/[&<>]/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;'
      }[c]));
    }

    const HL_TECH = /\\b(README|PRs?|APIs?|HTML|CSS|JavaScript|TypeScript|Python|Ruby|Go|Rust|bio|pinned|Quick Win|Weekend Project|Career Growth|open[\\s-]?source|followers?|stars?|forks?|commits?|repos?)\\b/g;

    function highlightRich(text) {
      let h = escapeHtml(text);
      h = h.replace(/("[^"\\n]*"|'[^'\\n]*')/g, '<span class="hl hl-pink">$1</span>');
      h = h.replace(/\\b(\\d[\\d,]*(?:\\s?★)?)\\b/g, '<span class="hl hl-yellow">$1</span>');
      h = h.replace(HL_TECH, '<span class="hl hl-cyan">$1</span>');
      return h;
    }

    function setHighlighted(id, text) {
      document.getElementById(id).innerHTML = highlightRich(text || '');
    }

    let lastUsername = '';
    let battleMode = false;
    let battleOpen = false;

    function toggleBattleMode(force) {
      battleMode = (typeof force === 'boolean') ? force : !battleMode;
      document.getElementById('battleRow').classList.toggle('open', battleMode);
      document.getElementById('toggleBattleBtn').classList.toggle('active-battle', battleMode);
      if (battleMode) {
        document.getElementById('opponentInput').focus();
      }
    }

    async function runRoast() {
      const input = document.getElementById('usernameInput');
      const btn = document.getElementById('roastBtn');
      const spinner = document.getElementById('spinner');
      const btnText = document.getElementById('btnText');
      const errorBox = document.getElementById('errorBox');
      const username = input.value.trim().replace(/^@/, '');

      if (!username) {
        input.focus();
        return;
      }

      if (battleMode) {
        const opp = document.getElementById('opponentInput').value.trim().replace(/^@/, '');
        if (!opp) {
          errorBox.textContent = 'ERROR: Battle Mode needs an opponent — enter one next to VS @.';
          errorBox.style.display = 'block';
          document.getElementById('opponentInput').focus();
          return;
        }
        await runBattle(username, opp);
        return;
      }

      errorBox.style.display = 'none';
      spinner.style.display = 'inline-block';
      btnText.textContent = 'ROASTING...';
      btn.disabled = true;

      try {
        const response = await fetch('/roast', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: username })
        });

        const data = await response.json();

        if (!response.ok || data.status === 'error') {
          throw new Error(data.message || 'Failed to analyze GitHub profile');
        }

        lastUsername = username;
        setHighlighted('recruiterGlanceContent', data.recruiter_glance);
        renderRoast(data.roast);

        const meme = pickMeme(data.roast);
        document.getElementById('memeImg').src = meme.src;
        document.getElementById('memeArchetype').textContent = meme.label;
        document.getElementById('memeCaption').textContent = meme.caption;
        springMemeOut();
        if (window.gsap) {
          gsap.from('.step-card', { y: 50, rotation: -1, opacity: 0, duration: 0.55, stagger: 0.1, ease: 'power4.out', clearProps: 'opacity' });
        }

        // Commit Psych-Eval → Mental Stability card fade-in
        const psychText = (data.psych_eval && data.psych_eval.trim())
          ? data.psych_eval
          : 'PSYCH-EVAL PENDING — commit telemetry insufficient. Push something unhinged and try again.';
        setHighlighted('psychEvalContent', psychText);
        document.getElementById('mentalStatus').textContent = '[+] DIAGNOSIS COMPLETE';
        if (window.gsap) {
          gsap.fromTo('#mentalCard', { opacity: 0, y: 40, rotation: -1 }, { opacity: 1, y: 0, rotation: 0, duration: 0.6, ease: 'power4.out', clearProps: 'opacity,transform' });
        }
        renderReality(data.resume_vs_reality);
        if (window.gsap) {
          gsap.from('#realityCard', { opacity: 0, y: 40, duration: 0.6, ease: 'power4.out', clearProps: 'opacity,transform' });
        }
        loadLeaderboard();

        // Parse rescue into 3 clean cards
        const rescueText = data.rescue || '';
        const steps = rescueText.split(/\\n\\n+/);
        if (steps.length >= 3) {
          setHighlighted('rescueStep1', steps[0].replace(/^1\\.\\s*⚡[^:]*:\\s*/, ''));
          setHighlighted('rescueStep2', steps[1].replace(/^2\\.\\s*🎯[^:]*:\\s*/, ''));
          setHighlighted('rescueStep3', steps[2].replace(/^3\\.\\s*🚀[^:]*:\\s*/, ''));
        } else {
          setHighlighted('rescueStep1', rescueText);
          setHighlighted('rescueStep2', 'Polish top repo documentation and tags.');
          setHighlighted('rescueStep3', 'Ship 1 pull request to an upstream open-source tool.');
        }
        refreshIcons();

      } catch (err) {
        errorBox.textContent = 'ERROR: ' + err.message;
        errorBox.style.display = 'block';
        // Never leave the meme hidden on failure – restore resting state
        if (window.gsap) {
          gsap.set('#memeClip', { x: 0, y: 0, rotation: 12, opacity: 1, scale: 1 });
        } else {
          document.getElementById('memeClip').style.opacity = '1';
        }
      } finally {
        spinner.style.display = 'none';
        btnText.textContent = 'ROAST NOW';
        btn.disabled = false;
      }
    }

    function refreshIcons() {
      try {
        if (window.lucide && typeof lucide.createIcons === 'function') {
          lucide.createIcons();
        }
      } catch (e) { /* CDN offline – raw <i> tags stay harmless */ }
    }

    // Roast readability: archetype line becomes a badge pill,
    // remaining text renders as spaced paragraphs (highlighted).
    // Resume vs. Reality – render server audit (all strings via
    // textContent: pasted bios and README claims can't inject markup).
    function renderReality(r) {
      const badge = document.getElementById('vibeRatioBadge');
      const list = document.getElementById('realityList');
      const verdict = document.getElementById('realityVerdict');
      const head = document.getElementById('realityHeadline');
      const paste = document.getElementById('realityPaste');
      if (!r) return;
      badge.textContent = r.vibe_ratio || 'VIBE AUDIT';
      head.textContent = r.headline || 'Profile README Claims vs. Actual Git Reality';
      list.textContent = '';
      (r.discrepancies || []).forEach((d) => {
        const item = document.createElement('div');
        item.className = 'reality-item sev-' + String(d.severity || 'MEDIUM_VIBE').toLowerCase().replace(/_/g, '-');
        const claim = document.createElement('div');
        claim.className = 'reality-claim';
        claim.textContent = 'CLAIM: ' + (d.claim || '');
        const truth = document.createElement('div');
        truth.className = 'reality-truth';
        truth.textContent = 'GIT REALITY: ' + (d.reality || '');
        item.appendChild(claim);
        item.appendChild(truth);
        list.appendChild(item);
      });
      if (!(r.discrepancies || []).length) {
        const none = document.createElement('div');
        none.className = 'shame-empty';
        none.textContent = 'No inflated claims detected. Suspiciously honest.';
        list.appendChild(none);
      }
      verdict.textContent = r.recruiter_verdict || '';
      paste.hidden = !!r.has_profile_readme;
      refreshIcons();
    }

    // Fallback when no profile README exists: scan pasted bio text for the
    // same claim categories and flag each as self-reported (verify manually).
    const BIO_CATS = [
      { label: 'AI / ML Engineer', re: /\\b(ai|machine learning|deep learning|llms?|pytorch|tensorflow)\\b/i },
      { label: 'Cloud / DevOps Architect', re: /\\b(devops|kubernetes|k8s|docker|terraform|aws|ci\\s*\\/\\s*cd)\\b/i },
      { label: 'Full-Stack Developer', re: /\\b(full.?stack|backend|microservices?)\\b/i },
      { label: 'Systems Engineer', re: /\\b(rust|golang|go|c\\+\\+|embedded|kernel)\\b/i },
      { label: 'Web3 Builder', re: /\\b(web3|solidity|blockchain|smart contracts?)\\b/i }
    ];

    function auditPastedBio() {
      const text = document.getElementById('bioPaste').value || '';
      const list = document.getElementById('realityList');
      const verdict = document.getElementById('realityVerdict');
      document.getElementById('vibeRatioBadge').textContent = 'SELF-REPORTED';
      list.textContent = '';
      const hits = BIO_CATS.filter((c) => c.re.test(text));
      if (!text.trim()) {
        verdict.textContent = 'Paste a bio first — even vibes need input.';
        return;
      }
      if (!hits.length) {
        const none = document.createElement('div');
        none.className = 'shame-empty';
        none.textContent = 'No buzzword claims found. Either humble or unemployed.';
        list.appendChild(none);
      }
      hits.forEach((c) => {
        const item = document.createElement('div');
        item.className = 'reality-item sev-medium-vibe';
        const claim = document.createElement('div');
        claim.className = 'reality-claim';
        claim.textContent = 'CLAIM: ' + c.label;
        const truth = document.createElement('div');
        truth.className = 'reality-truth';
        truth.textContent = 'GIT REALITY: SELF-REPORTED — cross-check against pinned repos manually.';
        item.appendChild(claim);
        item.appendChild(truth);
        list.appendChild(item);
      });
      verdict.textContent = hits.length
        ? 'Self-reported claims logged. Now go earn the receipts in public repos.'
        : 'Clean bio. Suspiciously clean.';
      refreshIcons();
    }

    // Resume upload → compare against live Git telemetry → verdict.
    // PDF engine (pdf.js) lazy-loads only when a PDF is picked; TXT/MD
    // parse natively. Uploaded text is never stored, only scanned.
    let pdfJsLoading = null;

    function ensurePdfJs() {
      if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
      if (pdfJsLoading) return pdfJsLoading;
      pdfJsLoading = new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        s.onload = () => {
          try {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
          } catch (e) {}
          resolve(window.pdfjsLib);
        };
        s.onerror = () => reject(new Error('PDF engine failed to load (check connection)'));
        document.head.appendChild(s);
      });
      return pdfJsLoading;
    }

    async function handleResumeFile(input) {
      const file = input.files && input.files[0];
      if (!file) return;
      const label = document.getElementById('resumeFileName');
      const errorBox = document.getElementById('errorBox');
      const name = file.name || 'resume';
      const lower = name.toLowerCase();
      label.textContent = 'Reading ' + name + '…';
      try {
        let text = '';
        if (lower.endsWith('.pdf')) {
          const pdfjs = await ensurePdfJs();
          const buf = await file.arrayBuffer();
          const pdf = await pdfjs.getDocument({ data: buf }).promise;
          const parts = [];
          const n = Math.min(pdf.numPages, 10);
          for (let p = 1; p <= n; p++) {
            const page = await pdf.getPage(p);
            const tc = await page.getTextContent();
            parts.push(tc.items.map((it) => it.str).join(' '));
          }
          text = parts.join('\\n');
        } else {
          text = await file.text();
        }
        if (!text.trim()) throw new Error('No readable text found in ' + name);
        label.textContent = name + ' (' + text.trim().split(/\\s+/).length + ' words) — auditing…';
        await postResumeAudit(text);
        label.textContent = name + ' — verdict below.';
      } catch (err) {
        errorBox.textContent = 'ERROR: ' + err.message;
        errorBox.style.display = 'block';
        label.textContent = 'Could not audit ' + name + '. Try TXT/Markdown.';
      } finally {
        input.value = '';
      }
    }

    async function postResumeAudit(text) {
      const input = document.getElementById('usernameInput');
      const username = (lastUsername || input.value.trim() || '').replace(/^@/, '');
      if (!username) {
        input.focus();
        throw new Error('Enter a GitHub username first — the resume needs Git telemetry to argue with.');
      }
      const errorBox = document.getElementById('errorBox');
      errorBox.style.display = 'none';
      const response = await fetch('/resume-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, resume_text: text.slice(0, 20000) })
      });
      const data = await response.json();
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || 'Resume audit failed');
      }
      renderReality(data.resume_vs_reality);
      document.getElementById('realityHeadline').textContent = 'Uploaded Resume Claims vs. Actual Git Reality';
      if (window.gsap) {
        gsap.from('#realityCard', { opacity: 0, y: 40, duration: 0.6, ease: 'power4.out', clearProps: 'opacity,transform' });
      }
      const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      document.getElementById('realityCard').scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
    }

    function renderRoast(roastText) {
      const box = document.getElementById('roastContent');
      box.textContent = '';
      const raw = String(roastText || '');
      const lines = raw.split('\\n');
      let body = raw;
      if (lines.length && /ARCHETYPE\\s*:/i.test(lines[0])) {
        const badge = document.createElement('div');
        badge.className = 'badge-tag tag-orange';
        badge.style.marginBottom = '1rem';
        badge.style.fontSize = '1rem';
        badge.style.display = 'inline-block';
        badge.textContent = lines[0].trim();
        box.appendChild(badge);
        body = lines.slice(1).join('\\n').replace(/^\\n+/, '');
      }
      const paras = body.split(/\\n\\s*\\n/).map((s) => s.trim()).filter(Boolean);
      const chunks = paras.length ? paras : [body.trim()].filter(Boolean);
      chunks.forEach((p) => {
        const el = document.createElement('p');
        el.className = 'roast-p';
        el.innerHTML = highlightRich(p);
        box.appendChild(el);
      });
      if (!box.hasChildNodes()) {
        box.textContent = raw;
      }
    }

    function copyBadgeMarkdown() {
      const user = lastUsername || document.getElementById('usernameInput').value.trim().replace(/^@/, '') || 'octocat';
      const origin = window.location.origin;
      const md = '[![GitHub Roast](' + origin + '/badge/' + user + '.svg)](' + origin + ')';
      const done = () => {
        const btn = document.getElementById('copyBadgeBtn');
        btn.innerHTML = '<i data-lucide="check"></i> Badge Copied!';
        refreshIcons();
        setTimeout(() => {
          btn.innerHTML = '<i data-lucide="badge-check"></i> Copy README Badge';
          refreshIcons();
        }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(md).then(done).catch(() => done());
      } else {
        done();
      }
    }

    function shareRoastOnX() {
      const user = lastUsername || 'octocat';
      const arch = document.getElementById('memeArchetype').textContent || 'Developer';
      const text = 'I got roasted by GitHub Roast & Rescue as ' + arch + ' — think your profile survives?';
      const url = window.location.origin + '/badge/' + user + '.svg';
      window.open(
        'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text) + '&url=' + encodeURIComponent(url),
        '_blank', 'noopener,width=600,height=460'
      );
    }

    function toggleBattleArena(open) {
      battleOpen = (typeof open === 'boolean') ? open : !battleOpen;
      const overlay = document.getElementById('battleOverlay');
      overlay.classList.toggle('open', battleOpen);
      overlay.setAttribute('aria-hidden', String(!battleOpen));
      if (battleOpen && window.gsap) {
        gsap.fromTo('#battleArena',
          { scale: 0.85, rotation: -2, opacity: 0 },
          { scale: 1, rotation: 0, opacity: 1, duration: 0.55, ease: 'power4.out', clearProps: 'opacity,transform' });
        gsap.from('.battle-fighter', { y: 40, opacity: 0, duration: 0.5, stagger: 0.1, ease: 'power4.out', delay: 0.1, clearProps: 'opacity,transform' });
      }
    }

    function statLines(prefix, m) {
      return [
        'Graveyard score: ' + m.graveyard + ' (0-star:' + m.zero_star + ' archived:' + m.archived + ' stale:' + m.stale + ')',
        'Code volume: ' + Number(m.code_kb).toLocaleString() + 'KB',
        'Commit hygiene: ' + m.unhinged + ' unhinged / ' + m.commits_seen + ' verified'
      ].join('\\n');
    }

    async function runBattle(user1, user2) {
      const errorBox = document.getElementById('errorBox');
      const btn = document.getElementById('roastBtn');
      const spinner = document.getElementById('spinner');
      const btnText = document.getElementById('btnText');
      errorBox.style.display = 'none';
      spinner.style.display = 'inline-block';
      btnText.textContent = 'BATTLING...';
      btn.disabled = true;
      try {
        const response = await fetch('/battle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user1: user1, user2: user2 })
        });
        const data = await response.json();
        if (!response.ok || data.status === 'error') {
          throw new Error(data.message || 'Battle failed');
        }
        const battle = data.battle;
        const stats = battle.stats || {};
        const u1 = (stats.user1 && stats.user1.username) || user1;
        const u2 = (stats.user2 && stats.user2.username) || user2;
        const arch = battle.archetypes || {};
        const m1 = stats.user1 || {};
        const m2 = stats.user2 || {};
        document.getElementById('battleName1').textContent = '@' + u1;
        document.getElementById('battleName2').textContent = '@' + u2;
        document.getElementById('battleArch1').textContent = arch[u1] || arch[user1] || 'Fighter';
        document.getElementById('battleArch2').textContent = arch[u2] || arch[user2] || 'Fighter';
        document.getElementById('battleStats1').textContent = statLines(u1, m1);
        document.getElementById('battleStats2').textContent = statLines(u2, m2);
        document.getElementById('battleVerdict').textContent = battle.verdict || '';
        const f1 = document.getElementById('fighter1');
        const f2 = document.getElementById('fighter2');
        f1.classList.remove('winner');
        f2.classList.remove('winner');
        [f1, f2].forEach((f) => {
          const old = f.querySelector('.battle-crown');
          if (old) old.remove();
        });
        const champ = battle.winner === u1 ? f1 : (battle.winner === u2 ? f2 : null);
        if (champ) {
          champ.classList.add('winner');
          const crown = document.createElement('div');
          crown.className = 'battle-crown';
          crown.innerHTML = '<i data-lucide="crown"></i>';
          champ.appendChild(crown);
          refreshIcons();
        }
        lastUsername = battle.winner && battle.winner !== 'tie' ? battle.winner : user1;
        toggleBattleArena(true);
        loadLeaderboard();
      } catch (err) {
        errorBox.textContent = 'ERROR: ' + err.message;
        errorBox.style.display = 'block';
      } finally {
        spinner.style.display = 'none';
        btnText.textContent = 'ROAST NOW';
        btn.disabled = false;
      }
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && battleOpen) toggleBattleArena(false);
    });

    function copyRoast() {
      const text = document.getElementById('roastContent').textContent;
      const done = () => {
        const btn = document.getElementById('copyRoastBtn');
        btn.innerHTML = '<i data-lucide="check"></i> Copied!';
        refreshIcons();
        setTimeout(() => {
          btn.innerHTML = '<i data-lucide="copy"></i> Copy Roast';
          refreshIcons();
        }, 2000);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => done());
      } else {
        done();
      }
    }

    // WALL OF SHAME – leaderboard drawer logic
    let shameOpen = false;

    async function loadLeaderboard() {
      const list = document.getElementById('shameList');
      try {
        const res = await fetch('/api/leaderboard');
        const data = await res.json();
        const rows = (data && data.leaderboard) || [];
        if (!rows.length) {
          list.textContent = '';
          const empty = document.createElement('div');
          empty.className = 'shame-empty';
          empty.textContent = 'No victims yet. Be the first disgrace.';
          list.appendChild(empty);
          return;
        }
        list.textContent = '';
        rows.forEach((r, i) => {
          const card = document.createElement('div');
          card.className = 'shame-card';
          const user = document.createElement('div');
          user.className = 'shame-user';
          user.textContent = '#' + (i + 1) + ' @' + (r.username || 'unknown');
          const arch = document.createElement('div');
          arch.className = 'shame-archetype';
          arch.textContent = r.archetype || 'Unknown Archetype';
          const prev = document.createElement('div');
          prev.className = 'shame-preview';
          prev.textContent = r.roast_preview || '';
          card.appendChild(user);
          card.appendChild(arch);
          card.appendChild(prev);
          list.appendChild(card);
        });
        if (window.gsap) {
          gsap.from('.shame-card', { x: 60, opacity: 0, duration: 0.45, stagger: 0.07, ease: 'power4.out', clearProps: 'opacity,transform' });
        }
      } catch (e) {
        list.textContent = '';
        const empty = document.createElement('div');
        empty.className = 'shame-empty';
        empty.textContent = 'Leaderboard unreachable. Shame persists anyway.';
        list.appendChild(empty);
      }
    }

    function toggleShame(force) {
      shameOpen = (typeof force === 'boolean') ? force : !shameOpen;
      const drawer = document.getElementById('shameDrawer');
      drawer.setAttribute('aria-hidden', String(!shameOpen));
      if (window.gsap) {
        gsap.to(drawer, { x: shameOpen ? '0%' : '100%', duration: 0.5, ease: 'power4.out' });
      } else {
        drawer.style.transform = shameOpen ? 'translateX(0)' : 'translateX(100%)';
      }
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && shameOpen) toggleShame(false);
    });

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        document.getElementById('usernameInput').focus();
      } else if (e.key === 'Enter' && document.activeElement === document.getElementById('usernameInput')) {
        runRoast();
      }
    });

    // Run automatically on load for demo profile + brutal entrance
    window.addEventListener('DOMContentLoaded', () => {
      refreshIcons();
      if (window.gsap) {
        gsap.set('#shameDrawer', { x: '100%' });
      }
      brutalEntrance();
      loadLeaderboard();
      runRoast();
    });
  </script>
</body>
</html>
"""


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server for high concurrency in Cloud Run."""
    daemon_threads = True


class RoastHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Cloud Run."""

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight."""
        self._set_headers(HTTPStatus.NO_CONTENT)

    def do_GET(self):
        """Handle GET requests (Dashboard & Healthcheck & Meme Assets)."""
        if self.path in ("/", "/index.html"):
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(BENTO_WEB_HTML.encode("utf-8"))
        elif self.path.startswith("/assets/"):
            import mimetypes
            safe = os.path.normpath(self.path.lstrip("/"))
            if ".." in safe or not safe.startswith("assets/"):
                self._set_headers(403, "application/json")
                self.wfile.write(json.dumps({"error": "Forbidden"}).encode("utf-8"))
                return
            base = os.path.dirname(os.path.abspath(__file__))
            fpath = os.path.join(base, safe)
            if not os.path.isfile(fpath):
                self._set_headers(404, "application/json")
                self.wfile.write(json.dumps({"error": "Asset not found"}).encode("utf-8"))
                return
            ctype, _ = mimetypes.guess_type(fpath)
            self._set_headers(200, ctype or "image/svg+xml")
            with open(fpath, "rb") as f:
                self.wfile.write(f.read())
        elif self.path in ("/health", "/healthz", "/_ah/health"):
            self._set_headers(200, "application/json")
            resp = {
                "status": "healthy",
                "service": "github-roast-and-rescue",
                "version": "1.0.0",
                "target": "google-cloud-run"
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/api/leaderboard":
            self._set_headers(200, "application/json")
            board = get_leaderboard()
            self.wfile.write(json.dumps({"status": "success", "leaderboard": board}).encode("utf-8"))
        elif self.path.startswith("/badge/"):
            raw = self.path[len("/badge/"):].split("?", 1)[0].split("/", 1)[0]
            if raw.lower().endswith(".svg"):
                raw = raw[:-4]
            username = (raw or "").strip().lstrip("@")
            if not username or not USERNAME_REGEX.match(username):
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Invalid username for badge"}).encode("utf-8"))
                return
            archetype, preview, roasted = _badge_context(username)
            svg = _build_badge_svg(username, archetype, preview, roasted)
            payload = svg.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def _handle_resume_audit(self, data: Dict[str, Any]):
        """Audit uploaded resume text against a user's Git telemetry.

        Body: {"username": "...", "resume_text": "..."} with resume_text
        capped at 20k chars. Reuses audit_resume_vs_reality; the text is
        never stored, only scanned. Uploaded text is treated as the resume
        (has_profile_readme equivalent) for the audit.
        """
        username = ((data.get("username") or "").strip().lstrip("@"))
        resume_text = data.get("resume_text") or ""
        if not username:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Field 'username' is required",
            }).encode("utf-8"))
            return
        if not USERNAME_REGEX.match(username):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Invalid GitHub username format '%s'." % username,
            }).encode("utf-8"))
            return
        if not isinstance(resume_text, str) or not resume_text.strip():
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Field 'resume_text' is required (upload or paste a resume).",
            }).encode("utf-8"))
            return
        if len(resume_text) > 20000:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Resume text too large — keep it under 20,000 characters.",
            }).encode("utf-8"))
            return

        try:
            import analyzer as _analyzer_mod
            import importlib as _importlib
            _importlib.reload(_analyzer_mod)
            audit_fn = getattr(_analyzer_mod, "audit_resume_vs_reality", None)
        except Exception:
            audit_fn = None
        if not callable(audit_fn):
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Audit engine temporarily unavailable. Try again shortly.",
            }).encode("utf-8"))
            return

        try:
            client = get_github_client()
            profile = client.get_user_profile(username)
            if profile is None:
                self._set_headers(404, "application/json")
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "GitHub user '@%s' could not be fetched. Either the user does not exist or GitHub API rate limit was reached." % username,
                }).encode("utf-8"))
                return
            repos = client.get_user_repos(username) or []
            projects = [
                r for r in repos
                if isinstance(r, dict)
                and (r.get("name", "") or "").strip().lower() != username.lower()
            ]
            top_langs = {}
            top_name = ""
            ordered = sorted(projects, key=lambda r: (r or {}).get("stargazers_count", 0), reverse=True)
            if ordered:
                top_name = (ordered[0] or {}).get("name", "") or ""
                try:
                    top_langs = client.get_repo_languages(username, top_name) or {}
                except Exception:
                    top_langs = {}
            audit_langs, repo_skeletons = _fetch_repo_evidence(
                client, username, projects, top_name, top_langs
            )
            bio = profile.get("bio") or ""
            try:
                result = audit_fn(
                    resume_text, bio, projects, audit_langs,
                    repo_files=repo_skeletons, resume_label="resume",
                )
            except TypeError:
                result = audit_fn(resume_text, bio, projects, audit_langs)
            result = dict(result)
            result["source"] = "uploaded_resume"
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({
                "status": "success",
                "username": username,
                "resume_vs_reality": result,
            }).encode("utf-8"))
        except RuntimeError as re:
            self._set_headers(429, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": str(re)}).encode("utf-8"))
        except Exception as e:
            traceback.print_exc()
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": "Resume audit error: %s" % str(e)}).encode("utf-8"))

    def _handle_battle(self, data: Dict[str, Any]):
        """Head-to-head roast battle for two usernames (decoupled from /roast)."""
        user1 = ((data.get("user1") or "").strip().lstrip("@"))
        user2 = ((data.get("user2") or "").strip().lstrip("@"))
        if not user1 or not user2:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Fields 'user1' and 'user2' are both required",
            }).encode("utf-8"))
            return
        for handle in (user1, user2):
            if not USERNAME_REGEX.match(handle):
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Invalid GitHub username format '%s'." % handle,
                }).encode("utf-8"))
                return
        if user1.lower() == user2.lower():
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "A roast battle needs two different combatants.",
            }).encode("utf-8"))
            return

        try:
            import analyzer as _analyzer_mod
            import importlib as _importlib
            _importlib.reload(_analyzer_mod)
            compare_fn = getattr(_analyzer_mod, "compare_profiles", None)
        except Exception:
            compare_fn = None
        if not callable(compare_fn):
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": "Battle engine temporarily unavailable. Try again shortly.",
            }).encode("utf-8"))
            return

        try:
            client = get_github_client()
            analyzer_fn = get_analyzer_fn()
            analysis1 = _run_full_analysis(client, analyzer_fn, user1)
            analysis2 = _run_full_analysis(client, analyzer_fn, user2)
            result = compare_fn(analysis1, analysis2)
            result["archetypes"] = {
                analysis1.get("username", user1): analysis1.get("archetype", "Developer"),
                analysis2.get("username", user2): analysis2.get("archetype", "Developer"),
            }
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"status": "success", "battle": result}).encode("utf-8"))
        except ValueError as ve:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": str(ve)}).encode("utf-8"))
        except RuntimeError as re:
            self._set_headers(429, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": str(re)}).encode("utf-8"))
        except Exception as e:
            traceback.print_exc()
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": "Battle error: %s" % str(e)}).encode("utf-8"))

    def do_POST(self):
        """Handle POST requests with {'username': 'handle'}."""
        if self.path in ("/battle", "/api/battle"):
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Missing JSON request body"}).encode("utf-8"))
                return
            try:
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
            except Exception as e:
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Invalid JSON: %s" % str(e)}).encode("utf-8"))
                return
            self._handle_battle(data if isinstance(data, dict) else {})
            return
        if self.path in ("/resume-audit", "/api/resume-audit"):
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Missing JSON request body"}).encode("utf-8"))
                return
            try:
                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body)
            except Exception as e:
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Invalid JSON: %s" % str(e)}).encode("utf-8"))
                return
            self._handle_resume_audit(data if isinstance(data, dict) else {})
            return
        if self.path not in ("/", "/roast", "/api/roast"):
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": "Missing JSON request body"}).encode("utf-8"))
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
        except Exception as e:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
            return

        username = (data.get("username") or "").strip().lstrip("@")
        if not username:
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": "Field 'username' is required"}).encode("utf-8"))
            return

        if not USERNAME_REGEX.match(username):
            self._set_headers(400, "application/json")
            self.wfile.write(json.dumps({
                "status": "error",
                "message": f"Invalid GitHub username format '{username}'. GitHub usernames may only contain alphanumeric characters and hyphens."
            }).encode("utf-8"))
            return

        try:
            # Step 1: Fetch GitHub Data
            client = get_github_client()
            profile_data = client.get_user_profile(username)
            if profile_data is None:
                self._set_headers(404, "application/json")
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": f"GitHub user '@{username}' could not be fetched. Either the user does not exist or GitHub API rate limit was reached."
                }).encode("utf-8"))
                return

            repos_data = client.get_user_repos(username) or []
            events_data = client.get_recent_activity(username) or []

            # Separate the {username}/{username} profile README (personal
            # resume) from true code projects — never roast the profile
            # repo for lacking code, and never crown it "top project".
            try:
                profile_readme = client.get_repo_readme(username, username) or ""
            except Exception:
                profile_readme = ""
            project_repos = [
                r for r in repos_data
                if isinstance(r, dict)
                and (r.get("name", "") or "").strip().lower() != username.lower()
            ]
            top_repo_name = ""
            sorted_projects = sorted(project_repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)
            if sorted_projects:
                top_repo_name = sorted_projects[0].get("name", "")

            readme_content = ""
            top_repo_languages = {}
            verified_commits = []
            if top_repo_name:
                readme_content = client.get_repo_readme(username, top_repo_name)
                top_repo_languages = client.get_repo_languages(username, top_repo_name)
                # Verified commit telemetry grounds the psych-eval (never accuse
                # "no code pushed" off the events feed alone). Defensive getattr
                # keeps the fallback client path working.
                try:
                    fetcher = getattr(client, "get_repo_commits", None)
                    if callable(fetcher):
                        verified_commits = fetcher(username, top_repo_name, username, 10) or []
                except Exception:
                    verified_commits = []

            # Cross-repo evidence so the audit measures the whole portfolio,
            # not just the top repo (languages summed over top projects,
            # file skeletons prove Dockerfiles/CI/tests).
            audit_langs, repo_skeletons = _fetch_repo_evidence(
                client, username, project_repos, top_repo_name, top_repo_languages
            )

            # Step 2: Analyze
            analyzer_fn = get_analyzer_fn()
            try:
                analysis = analyzer_fn(profile_data, repos_data, username, events_data=events_data, readme_content=readme_content, repo_languages=top_repo_languages, verified_commits=verified_commits, profile_readme=profile_readme, audit_languages=audit_langs, repo_files=repo_skeletons)
            except TypeError:
                try:
                    analysis = analyzer_fn(profile_data, repos_data, username, events_data=events_data, readme_content=readme_content)
                except TypeError:
                    try:
                        analysis = analyzer_fn(profile_data, repos_data, username, events_data=events_data)
                    except TypeError:
                        analysis = analyzer_fn(profile_data, repos_data, username)

            # Step 3: Format with Brutalist Style
            brutalist_formatter = get_brutalist_formatter()
            sections = {
                "recruiter_glance": analysis.get("recruiter_glance", ""),
                "roast": analysis.get("roast", ""),
                "rescue": analysis.get("rescue", ""),
            }
            brutalist_text = brutalist_formatter(sections, width=80)

            response_payload = {
                "status": "success",
                "username": username,
                "recruiter_glance": analysis.get("recruiter_glance", ""),
                "roast": analysis.get("roast", ""),
                "rescue": analysis.get("rescue", ""),
                "psych_eval": analysis.get("psych_eval", ""),
                "resume_vs_reality": analysis.get("resume_vs_reality", {}),
                "bento_formatted": brutalist_text,
            }

            # Save to Tech Debt Leaderboard
            archetype = analysis.get("archetype", "The Generalist Builder")
            roast_preview = analysis.get("roast", "")[:120] + "..." if len(analysis.get("roast", "")) > 120 else analysis.get("roast", "")
            save_to_leaderboard(username, archetype, roast_preview)

            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))

        except ValueError as ve:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": str(ve)}).encode("utf-8"))
        except RuntimeError as re:
            self._set_headers(429, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": str(re)}).encode("utf-8"))
        except Exception as e:
            traceback.print_exc()
            self._set_headers(500, "application/json")
            self.wfile.write(json.dumps({"status": "error", "message": f"Internal error: {str(e)}"}).encode("utf-8"))

    def log_message(self, format, *args):
        """Standardized Cloud Run stdout logging."""
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()


def run_server(port: Optional[int] = None):
    """Run the Cloud Run server."""
    if port is None:
        port = int(os.environ.get("PORT", "8080"))

    server_address = ("0.0.0.0", port)
    httpd = ThreadedHTTPServer(server_address, RoastHandler)
    print(f"🚀 GitHub Roast & Rescue Cloud Run server listening on http://0.0.0.0:{port}")
    print(f"👉 Health check: http://0.0.0.0:{port}/health")
    print(f"👉 POST endpoint: http://0.0.0.0:{port}/roast")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    run_server(port_arg)
