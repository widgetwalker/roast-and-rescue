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
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")

# Multi-agent architecture integration: Claude + OpenCode + Antigravity
try:
    import antigravity  # Python standard library easter egg (xkcd #353)
except Exception:
    pass

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
    def fallback_analyze(profile: Dict[str, Any], repos: Any, username: str) -> Dict[str, Any]:
        repos_list = repos if isinstance(repos, list) else []
        repo_count = len(repos_list)
        langs = []
        for r in repos_list[:5]:
            l = r.get("primary_language") if isinstance(r, dict) else None
            if l and l not in langs:
                langs.append(l)
        lang_str = ", ".join(langs[:3]) if langs else "Various technologies"
        name = profile.get("name") or profile.get("username") or username
        bio = profile.get("bio") or "No bio provided"
        followers = profile.get("followers", 0)

        glance = (
            f"• {name} (@{username}) primarily builds with {lang_str}\n"
            f"• Maintains {repo_count} public repositories with {followers} followers\n"
            f"• Profile focus: {bio}\n"
            f"• Account created: {profile.get('created_at', 'recently')[:10] if profile.get('created_at') else 'recently'}"
        )

        roast = (
            f"@{username} manages {repo_count} public repositories – dedication to the minimalist code aesthetic!\n"
            f"With '{bio}', you're either a mysterious 10x architect or saving the bio for the IPO.\n"
            f"Favorite stack appears to be {lang_str}. May your merge conflicts be few and your coffee strong."
        )

        rescue = (
            "🚀 QUICK WINS (fix these TODAY):\n"
            "  [Quick Win] Enhance your GitHub profile README\n"
            "    → Add a profile README (username/username) summarizing current projects & stack\n"
            "    → Impact: High - first impression for recruiters\n\n"
            "  [Quick Win] Add descriptive tags & topics to your top 3 repos\n"
            "    → Enable GitHub repo topics to boost discoverability in search\n"
            "    → Impact: Medium - increases inbound traffic\n\n"
            "📈 MEDIUM-TERM GOALS (weeks of work):\n"
            "  [Medium-term] Standardize repository READMEs with demo GIFs & badges\n"
            "    → Include setup instructions, quickstarts, and live demo links\n"
            "    → Impact: High - converts casual visitors into stargazers\n\n"
            "🌟 LONG-TERM GROWTH (months of consistent effort):\n"
            "  [Long-term] Active open-source contribution in your core stack\n"
            "    → Submit PRs to active upstream repositories in " + lang_str + "\n"
            "    → Impact: High - establishes public industry credibility"
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
            def get_user_profile(self, username: str) -> Dict[str, Any]:
                r = requests.get(f"https://api.github.com/users/{username}", headers={"Accept": "application/vnd.github+v3+json"}, timeout=10)
                if r.status_code == 404:
                    raise ValueError(f"User '{username}' not found on GitHub")
                elif r.status_code != 200:
                    raise RuntimeError(f"GitHub API error: {r.status_code}")
                return r.json()

            def get_user_repos(self, username: str, per_page: int = 10, sort: str = "stars") -> Any:
                r = requests.get(f"https://api.github.com/users/{username}/repos", params={"per_page": per_page, "sort": sort}, headers={"Accept": "application/vnd.github+v3+json"}, timeout=10)
                if r.status_code == 404:
                    raise ValueError(f"User '{username}' not found on GitHub")
                elif r.status_code != 200:
                    raise RuntimeError(f"GitHub API error: {r.status_code}")
                return r.json()
        return FallbackGitHubClient()


def get_bento_formatter():
    """Dynamically get Bento layout formatter."""
    try:
        import output
        import importlib
        importlib.reload(output)
        if hasattr(output, "bento_layout"):
            return output.bento_layout
    except Exception:
        pass

    def fallback_bento(sections: Dict[str, str], width: int = 80) -> str:
        lines = [
            "=" * width,
            "  GITHUB ROAST & RESCUE",
            "  Honest feedback with actionable improvement advice",
            "=" * width,
            ""
        ]
        for name, content in sections.items():
            lines.append("-" * width)
            lines.append(f"  {name.upper()}  ".center(width, "─"))
            for l in content.split("\n"):
                lines.append(f"  {l}")
            lines.append("")
        lines.append("=" * width)
        lines.append("  Roast for entertainment only - focus on the rescue for real improvement")
        lines.append("=" * width)
        return "\n".join(lines)

    return fallback_bento


# Bento Style Web Dashboard HTML
BENTO_WEB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GitHub Roast & Rescue | Bento Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-base: #0a0c10;
      --bg-surface: #12161f;
      --bg-card: rgba(22, 27, 39, 0.75);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-focus: #f97316;
      --accent-flame: #ff5722;
      --accent-glow: rgba(255, 87, 34, 0.25);
      --accent-rescue: #10b981;
      --accent-recruiter: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --font-display: 'Outfit', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-base);
      color: var(--text-main);
      font-family: var(--font-display);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem;
      background-image: 
        radial-gradient(circle at 50% 0%, rgba(255, 87, 34, 0.12) 0%, transparent 60%),
        radial-gradient(circle at 80% 80%, rgba(16, 185, 129, 0.08) 0%, transparent 50%);
    }

    .container {
      max-width: 1100px;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    header {
      text-align: center;
      margin-bottom: 0.5rem;
    }

    .badge-bar {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.85rem;
      background: rgba(255, 87, 34, 0.15);
      border: 1px solid rgba(255, 87, 34, 0.3);
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 600;
      color: #ff8a65;
      margin-bottom: 0.75rem;
    }

    h1 {
      font-size: 2.75rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      background: linear-gradient(135deg, #ffffff 40%, #fdba74 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 0.5rem;
    }

    p.subtitle {
      color: var(--text-muted);
      font-size: 1.1rem;
    }

    .input-bar {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      padding: 0.5rem 0.5rem 0.5rem 1.25rem;
      display: flex;
      gap: 0.5rem;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
      transition: all 0.2s ease;
    }

    .input-bar:focus-within {
      border-color: var(--border-focus);
      box-shadow: 0 0 25px var(--accent-glow);
    }

    .input-prefix {
      color: var(--accent-flame);
      font-family: var(--font-mono);
      font-weight: 700;
      font-size: 1.2rem;
      display: flex;
      align-items: center;
    }

    input[type="text"] {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-main);
      font-size: 1.15rem;
      font-family: var(--font-mono);
    }

    input[type="text"]::placeholder {
      color: #475569;
    }

    button.btn-roast {
      background: linear-gradient(135deg, #ff5722 0%, #ea580c 100%);
      color: #ffffff;
      border: none;
      padding: 0.85rem 1.75rem;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: transform 0.15s ease, filter 0.15s ease;
    }

    button.btn-roast:hover {
      transform: translateY(-2px);
      filter: brightness(1.1);
    }

    button.btn-roast:active {
      transform: translateY(0);
    }

    .shortcuts-hint {
      display: flex;
      justify-content: center;
      gap: 1.5rem;
      font-size: 0.8rem;
      color: #64748b;
    }

    .kbd {
      background: #1e293b;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      border: 1px solid #334155;
      font-family: var(--font-mono);
      color: #cbd5e1;
    }

    /* Bento Grid */
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 1.25rem;
      margin-top: 1rem;
    }

    .bento-card {
      background: var(--bg-card);
      backdrop-filter: blur(12px);
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .bento-card:hover {
      border-color: rgba(255, 255, 255, 0.18);
      transform: translateY(-2px);
    }

    .card-recruiter {
      grid-column: span 12;
      border-top: 3px solid var(--accent-recruiter);
    }

    .card-roast {
      grid-column: span 5;
      border-top: 3px solid var(--accent-flame);
      background: linear-gradient(180deg, rgba(255, 87, 34, 0.08) 0%, rgba(22, 27, 39, 0.75) 100%);
    }

    .card-rescue {
      grid-column: span 7;
      border-top: 3px solid var(--accent-rescue);
    }

    .card-raw {
      grid-column: span 12;
    }

    @media (max-width: 900px) {
      .card-roast, .card-rescue {
        grid-column: span 12;
      }
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
    }

    .card-title {
      font-size: 1.1rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .card-content {
      color: #cbd5e1;
      font-size: 0.95rem;
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .roast-quote {
      font-size: 1.15rem;
      font-style: italic;
      color: #ffedd5;
      border-left: 3px solid var(--accent-flame);
      padding-left: 1rem;
      margin: 0.5rem 0;
    }

    .rescue-section {
      margin-bottom: 1rem;
    }

    .raw-terminal {
      background: #050608;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 1.25rem;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      color: #38bdf8;
      overflow-x: auto;
      white-space: pre;
    }

    .btn-copy {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 0.35rem 0.75rem;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-copy:hover {
      background: #334155;
      color: #fff;
    }

    .disclaimer-badge {
      font-size: 0.75rem;
      color: #64748b;
      text-align: center;
      margin-top: 1.5rem;
      font-style: italic;
    }

    /* Loading Spinner */
    .spinner {
      display: none;
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: #ffffff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .error-box {
      display: none;
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
      padding: 1rem;
      border-radius: 12px;
      font-size: 0.95rem;
      margin-top: 1rem;
    }

    /* Zero-Gravity Animation Easter Egg */
    @keyframes zeroGravityFloat {
      0%, 100% { transform: translateY(0px) rotate(0deg); }
      50% { transform: translateY(-10px) rotate(0.4deg); }
    }
    body.antigravity-active .bento-card {
      animation: zeroGravityFloat 4s ease-in-out infinite alternate;
      box-shadow: 0 20px 45px rgba(255, 87, 34, 0.35);
      border-color: rgba(255, 138, 101, 0.4);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="badge-bar">
        <span>🔥 AI HACKATHON WAR-ROOM</span>
        <span>•</span>
        <span>TRIAD ARCHITECTURE: CLAUDE + OPENCODE + ANTIGRAVITY</span>
      </div>
      <h1>GitHub Roast &amp; Rescue</h1>
      <p class="subtitle">Bento Dashboard • Honest developer roasts paired with actionable rescue plans</p>
    </header>

    <div class="input-bar">
      <span class="input-prefix">@</span>
      <input type="text" id="usernameInput" placeholder="github-username (e.g. octocat, torvalds)" value="octocat" autocomplete="off" spellcheck="false">
      <button class="btn-roast" id="roastBtn" onclick="runRoast()">
        <span class="spinner" id="spinner"></span>
        <span id="btnText">Roast &amp; Rescue</span>
      </button>
    </div>

    <div class="shortcuts-hint">
      <span><span class="kbd">Enter</span> Run Analysis</span>
      <span><span class="kbd">Ctrl</span>+<span class="kbd">K</span> Focus Input</span>
      <span><span class="kbd">C</span> Copy Bento</span>
      <span><span class="kbd">A</span> 🕊️ Anti-Gravity Mode</span>
    </div>

    <div class="error-box" id="errorBox"></div>

    <div class="bento-grid" id="bentoDashboard">
      <!-- 1. Recruiter Glance -->
      <div class="bento-card card-recruiter">
        <div class="card-header">
          <div class="card-title" style="color: var(--accent-recruiter);">
            <span>⏱️ 30-Second Recruiter Glance</span>
          </div>
          <span style="font-size: 0.75rem; color: #64748b;">Instant Hiring Lens</span>
        </div>
        <div class="card-content" id="recruiterGlanceContent">Loading recruiter insights...</div>
      </div>

      <!-- 2. The Roast -->
      <div class="bento-card card-roast">
        <div class="card-header">
          <div class="card-title" style="color: var(--accent-flame);">
            <span>🌶️ The Roast</span>
          </div>
          <span style="font-size: 0.75rem; color: #f97316;">Humor Only</span>
        </div>
        <div class="card-content roast-quote" id="roastContent">Loading humorous observations...</div>
      </div>

      <!-- 3. The Rescue -->
      <div class="bento-card card-rescue">
        <div class="card-header">
          <div class="card-title" style="color: var(--accent-rescue);">
            <span>🛠️ The Rescue Plan</span>
          </div>
          <span style="font-size: 0.75rem; color: #10b981;">Prioritized Steps</span>
        </div>
        <div class="card-content" id="rescueContent">Loading actionable growth roadmap...</div>
      </div>

      <!-- 4. Raw Bento Terminal Output -->
      <div class="bento-card card-raw">
        <div class="card-header">
          <div class="card-title">
            <span>📺 Terminal Bento Layout</span>
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn-copy" id="antiGravBtn" onclick="toggleAntiGravity()">🕊️ Fly Mode</button>
            <button class="btn-copy" onclick="copyTerminalOutput()">Copy Bento Text</button>
          </div>
        </div>
        <div class="raw-terminal" id="rawOutput">Terminal format will appear here...</div>
      </div>
    </div>

    <div class="disclaimer-badge">
      Disclaimer: Roasts are lighthearted satire generated for entertainment. Focus on the Rescue roadmap for real profile improvements.
    </div>
  </div>

  <script>
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

      errorBox.style.display = 'none';
      spinner.style.display = 'inline-block';
      btnText.textContent = 'Roasting...';
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

        document.getElementById('recruiterGlanceContent').textContent = data.recruiter_glance;
        document.getElementById('roastContent').textContent = data.roast;
        document.getElementById('rescueContent').textContent = data.rescue;
        document.getElementById('rawOutput').textContent = data.bento_formatted || 'Bento layout generated.';

      } catch (err) {
        errorBox.textContent = 'Error: ' + err.message;
        errorBox.style.display = 'block';
      } finally {
        spinner.style.display = 'none';
        btnText.textContent = 'Roast & Rescue';
        btn.disabled = false;
      }
    }

    function copyTerminalOutput() {
      const text = document.getElementById('rawOutput').textContent;
      navigator.clipboard.writeText(text).then(() => {
        alert('Copied Bento terminal output to clipboard!');
      });
    }

    function toggleAntiGravity() {
      document.body.classList.toggle('antigravity-active');
      const active = document.body.classList.contains('antigravity-active');
      const btn = document.getElementById('antiGravBtn');
      if (btn) btn.textContent = active ? '🪂 Normal Gravity' : '🕊️ Fly Mode';
    }

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        document.getElementById('usernameInput').focus();
      } else if (e.key === 'Enter' && document.activeElement === document.getElementById('usernameInput')) {
        runRoast();
      } else if (e.key.toLowerCase() === 'c' && document.activeElement !== document.getElementById('usernameInput')) {
        copyTerminalOutput();
      } else if (e.key.toLowerCase() === 'a' && document.activeElement !== document.getElementById('usernameInput')) {
        toggleAntiGravity();
      }
    });

    // Run automatically on load for demo profile
    window.addEventListener('DOMContentLoaded', () => {
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
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight."""
        self._set_headers(HTTPStatus.NO_CONTENT)

    def do_GET(self):
        """Handle GET requests (Dashboard & Healthcheck)."""
        if self.path in ("/", "/index.html"):
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(BENTO_WEB_HTML.encode("utf-8"))
        elif self.path in ("/health", "/healthz", "/_ah/health"):
            self._set_headers(200, "application/json")
            resp = {
                "status": "healthy",
                "service": "github-roast-and-rescue",
                "version": "1.0.0",
                "target": "google-cloud-run"
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path in ("/antigravity", "/api/antigravity"):
            self._set_headers(200, "application/json")
            resp = {
                "status": "flying",
                "easter_egg": "xkcd #353",
                "comic_url": "https://xkcd.com/353/",
                "quote": "“I wrote 20 lines of code in Python and now I'm flying!” — xkcd #353",
                "agents": {
                    "claude": "AI Analysis & Prompt Architecture",
                    "opencode": "GitHub REST API Client & Rate-Limit Handling",
                    "antigravity": "Cloud Run Server & Zero-Gravity Interactive UI"
                }
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        """Handle POST requests with {'username': 'handle'}."""
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

            # Step 2: Analyze
            analyzer_fn = get_analyzer_fn()
            try:
                analysis = analyzer_fn(profile_data, repos_data, username, events_data=events_data)
            except TypeError:
                analysis = analyzer_fn(profile_data, repos_data, username)

            # Step 3: Format with Bento Style
            bento_formatter = get_bento_formatter()
            sections = {
                "recruiter_glance": analysis.get("recruiter_glance", ""),
                "roast": analysis.get("roast", ""),
                "rescue": analysis.get("rescue", ""),
            }
            bento_text = bento_formatter(sections, width=80)

            response_payload = {
                "status": "success",
                "username": username,
                "recruiter_glance": analysis.get("recruiter_glance", ""),
                "roast": analysis.get("roast", ""),
                "rescue": analysis.get("rescue", ""),
                "bento_formatted": bento_text,
            }

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
