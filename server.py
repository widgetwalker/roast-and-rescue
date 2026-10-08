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

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")

# Multi-agent architecture integration: Claude + OpenCode + Antigravity
# Antigravity serves as the HTTP / Cloud Run backend & Bento UI agent.

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
            f"• Tech Stack : {lang_str}\n"
            f"• Footprint  : {repo_count} public repos | {followers:,} followers\n"
            f"• Profile    : {bio}"
        )

        roast = (
            f"@{username} manages {repo_count} public repositories with '{bio}'. "
            f"Either you're a stealth architect or saving the bio for the IPO."
        )

        rescue = (
            f"1. ⚡ 10-MIN QUICK WIN:\n   Pin your best repo and write a 1-sentence bio.\n\n"
            f"2. 🎯 WEEKEND PROJECT:\n   Add a live demo GIF and quickstart to your top repo's README.\n\n"
            f"3. 🚀 CAREER GROWTH:\n   Ship 1 pull request to an upstream open-source tool."
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
  <style>
    :root {
      --bg-canvas: #0a0c10;
      --bg-card: #12151e;
      --bg-card-alt: #181d2a;
      --border-dark: 2.5px solid #2a3144;
      --border-black: 2.5px solid #000000;
      --shadow-hard: 5px 5px 0px #000000;
      --shadow-cyan: 5px 5px 0px #00F0FF;
      --shadow-orange: 5px 5px 0px #FF4D00;
      --shadow-lime: 5px 5px 0px #D4FF00;
      --neon-cyan: #00F0FF;
      --neon-orange: #FF4D00;
      --neon-lime: #D4FF00;
      --neon-purple: #C084FC;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --font-display: 'Space Grotesk', -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-canvas);
      background-image: 
        radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px);
      background-size: 20px 20px;
      color: var(--text-main);
      font-family: var(--font-display);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2.5rem 1rem;
    }

    .container {
      max-width: 1060px;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    /* Top Triad Badge */
    .top-badge-row {
      display: flex;
      justify-content: center;
      margin-bottom: 0.25rem;
    }

    .triad-badge {
      background: #000000;
      color: var(--neon-cyan);
      border: 2px solid var(--neon-cyan);
      box-shadow: 3px 3px 0px var(--neon-cyan);
      padding: 0.35rem 0.9rem;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      border-radius: 4px;
    }

    /* Header */
    header {
      text-align: center;
    }

    h1 {
      font-size: 3rem;
      font-weight: 800;
      letter-spacing: -0.04em;
      text-transform: uppercase;
      line-height: 1.05;
      margin-bottom: 0.5rem;
      color: #ffffff;
      text-shadow: 3px 3px 0px #000;
    }

    h1 span.flame { color: var(--neon-orange); }
    h1 span.rescue { color: var(--neon-lime); }

    p.subtitle {
      color: var(--text-muted);
      font-size: 1.05rem;
      font-weight: 500;
    }

    /* Brutalist Input Bar */
    .search-box {
      background: #141722;
      border: 3px solid #ffffff;
      box-shadow: 6px 6px 0px #000000;
      border-radius: 8px;
      padding: 0.5rem;
      display: flex;
      gap: 0.5rem;
      transition: all 0.15s ease;
    }

    .search-box:focus-within {
      border-color: var(--neon-lime);
      box-shadow: 6px 6px 0px var(--neon-lime);
    }

    .input-prefix {
      color: var(--neon-orange);
      font-family: var(--font-mono);
      font-weight: 800;
      font-size: 1.4rem;
      display: flex;
      align-items: center;
      padding-left: 0.75rem;
    }

    input[type="text"] {
      flex: 1;
      background: transparent;
      border: none;
      outline: none;
      color: #ffffff;
      font-size: 1.2rem;
      font-family: var(--font-mono);
      font-weight: 700;
    }

    input[type="text"]::placeholder {
      color: #475569;
    }

    button.btn-roast {
      background: var(--neon-lime);
      color: #000000;
      border: 2.5px solid #000000;
      box-shadow: 4px 4px 0px #000000;
      padding: 0.85rem 1.75rem;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }

    button.btn-roast:hover {
      transform: translate(-2px, -2px);
      box-shadow: 6px 6px 0px #000000;
      background: #e1ff33;
    }

    button.btn-roast:active {
      transform: translate(2px, 2px);
      box-shadow: 1px 1px 0px #000000;
    }

    .shortcuts-row {
      display: flex;
      justify-content: center;
      gap: 1.5rem;
      font-size: 0.82rem;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }

    .kbd {
      background: #1e2433;
      padding: 0.15rem 0.45rem;
      border: 1.5px solid #3b4560;
      border-radius: 4px;
      color: #f1f5f9;
      font-weight: 700;
      box-shadow: 1px 1px 0px #000;
    }

    .error-box {
      display: none;
      background: #3b1115;
      border: 2.5px solid #ff4d4d;
      box-shadow: 4px 4px 0px #000;
      color: #ffcccc;
      padding: 1rem;
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.9rem;
    }

    /* Bento Grid */
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 1.25rem;
    }

    .bento-card {
      background: var(--bg-card);
      border: var(--border-dark);
      border-radius: 10px;
      padding: 1.4rem;
      display: flex;
      flex-direction: column;
      box-shadow: var(--shadow-hard);
      transition: transform 0.15s ease, border-color 0.15s ease;
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1rem;
      padding-bottom: 0.6rem;
      border-bottom: 1.5px dashed rgba(255, 255, 255, 0.12);
    }

    .badge-tag {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 800;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      border: 2px solid #000;
      box-shadow: 2px 2px 0px #000;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .tag-cyan { background: var(--neon-cyan); color: #000; }
    .tag-orange { background: var(--neon-orange); color: #000; }
    .tag-lime { background: var(--neon-lime); color: #000; }
    .tag-purple { background: var(--neon-purple); color: #000; }

    /* Grid Layouts */
    .card-recruiter {
      grid-column: span 5;
      border: 2.5px solid #2a3144;
    }

    .card-roast {
      grid-column: span 7;
      border: 2.5px solid #3d2319;
      background: linear-gradient(180deg, #181216 0%, #12151e 100%);
    }

    .card-rescue {
      grid-column: span 12;
      border: 2.5px solid #1c2e24;
    }

    .card-terminal {
      grid-column: span 12;
      border: 2.5px solid #2a3144;
    }

    @media (max-width: 860px) {
      .card-recruiter, .card-roast { grid-column: span 12; }
      h1 { font-size: 2.2rem; }
    }

    /* Content Typography */
    .recruiter-content {
      font-family: var(--font-mono);
      font-size: 0.88rem;
      line-height: 1.7;
      color: #e2e8f0;
      white-space: pre-line;
    }

    .roast-quote-box {
      background: rgba(255, 77, 0, 0.08);
      border-left: 4px solid var(--neon-orange);
      padding: 1rem 1.2rem;
      border-radius: 4px;
      font-size: 1.15rem;
      font-weight: 700;
      line-height: 1.5;
      color: #fff;
      font-style: italic;
    }

    /* Rescue 3-Card Grid */
    .rescue-steps-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-top: 0.5rem;
    }

    @media (max-width: 800px) {
      .rescue-steps-grid { grid-template-columns: 1fr; }
    }

    .step-card {
      background: #181d2a;
      border: 2px solid #2d364f;
      box-shadow: 3px 3px 0px #000;
      border-radius: 8px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .step-header {
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 800;
      color: var(--neon-lime);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .step-body {
      font-size: 0.92rem;
      color: #cbd5e1;
      line-height: 1.5;
    }

    /* Terminal Output */
    .terminal-box {
      background: #05060a;
      border: 2px solid #1f2535;
      border-radius: 6px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      color: #38bdf8;
      overflow-x: auto;
      white-space: pre;
      line-height: 1.45;
    }

    .btn-brutal {
      background: #1e2433;
      color: #f1f5f9;
      border: 2px solid #3b4560;
      box-shadow: 2px 2px 0px #000;
      padding: 0.35rem 0.85rem;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 700;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.1s ease;
    }

    .btn-brutal:hover {
      background: #2b3347;
      border-color: #60a5fa;
      transform: translate(-1px, -1px);
      box-shadow: 3px 3px 0px #000;
    }

    .btn-brutal:active {
      transform: translate(1px, 1px);
      box-shadow: 1px 1px 0px #000;
    }

    /* Spinner */
    .spinner {
      display: none;
      width: 18px;
      height: 18px;
      border: 3px solid rgba(0, 0, 0, 0.3);
      border-top-color: #000;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="container">
    
    <div class="top-badge-row">
      <div class="triad-badge">⚡ TRIAD ARCHITECTURE // CLAUDE • OPENCODE • ANTIGRAVITY</div>
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
        <span id="btnText">ROAST NOW ⚡</span>
      </button>
    </div>

    <div class="shortcuts-row">
      <span><span class="kbd">Enter</span> Analyze</span>
      <span><span class="kbd">Ctrl</span>+<span class="kbd">K</span> Focus Input</span>
      <span><span class="kbd">C</span> Copy Terminal Layout</span>
    </div>

    <div class="error-box" id="errorBox"></div>

    <div class="bento-grid">
      
      <!-- 1. Recruiter Scan -->
      <div class="bento-card card-recruiter">
        <div class="card-header">
          <span class="badge-tag tag-cyan">⏱️ Recruiter Scan</span>
          <span style="font-size: 0.75rem; color: #64748b; font-family: var(--font-mono);">30-SEC LENS</span>
        </div>
        <div class="recruiter-content" id="recruiterGlanceContent">Loading recruiter scan...</div>
      </div>

      <!-- 2. The Roast -->
      <div class="bento-card card-roast">
        <div class="card-header">
          <span class="badge-tag tag-orange">🔥 The Roast</span>
          <span style="font-size: 0.75rem; color: #f97316; font-family: var(--font-mono);">PUNCHY WIT</span>
        </div>
        <div class="roast-quote-box" id="roastContent">Loading roast...</div>
      </div>

      <!-- 3. The Rescue Plan -->
      <div class="bento-card card-rescue">
        <div class="card-header">
          <span class="badge-tag tag-lime">🛟 The Rescue Plan</span>
          <span style="font-size: 0.75rem; color: #10b981; font-family: var(--font-mono);">ACTION ROADMAP</span>
        </div>
        <div class="rescue-steps-grid" id="rescueStepsGrid">
          <div class="step-card">
            <div class="step-header">⚡ 10-Min Quick Win</div>
            <div class="step-body" id="rescueStep1">Loading action...</div>
          </div>
          <div class="step-card">
            <div class="step-header">🎯 Weekend Project</div>
            <div class="step-body" id="rescueStep2">Loading action...</div>
          </div>
          <div class="step-card">
            <div class="step-header">🚀 Career Growth</div>
            <div class="step-body" id="rescueStep3">Loading action...</div>
          </div>
        </div>
      </div>

      <!-- 4. Terminal ASCII Frame -->
      <div class="bento-card card-terminal">
        <div class="card-header">
          <span class="badge-tag tag-purple">📺 Bento Terminal ASCII</span>
          <button class="btn-brutal" id="copyBtn" onclick="copyTerminalOutput()">📋 Copy Terminal Layout</button>
        </div>
        <div class="terminal-box" id="rawOutput">Terminal format will appear here...</div>
      </div>

    </div>

    <div style="text-align: center; font-size: 0.78rem; color: #64748b; margin-top: 1rem; font-family: var(--font-mono);">
      GitHub Roast &amp; Rescue • Built for AI Hackathon 2026 • Powered by Cloud Run
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

        document.getElementById('recruiterGlanceContent').textContent = data.recruiter_glance;
        document.getElementById('roastContent').textContent = data.roast;
        document.getElementById('rawOutput').textContent = data.bento_formatted || 'Bento layout generated.';

        // Parse rescue into 3 clean cards
        const rescueText = data.rescue || '';
        const steps = rescueText.split(/\\n\\n+/);
        if (steps.length >= 3) {
          document.getElementById('rescueStep1').textContent = steps[0].replace(/^1\\.\\s*⚡[^:]*:\\s*/, '');
          document.getElementById('rescueStep2').textContent = steps[1].replace(/^2\\.\\s*🎯[^:]*:\\s*/, '');
          document.getElementById('rescueStep3').textContent = steps[2].replace(/^3\\.\\s*🚀[^:]*:\\s*/, '');
        } else {
          document.getElementById('rescueStep1').textContent = rescueText;
          document.getElementById('rescueStep2').textContent = 'Polish top repo documentation and tags.';
          document.getElementById('rescueStep3').textContent = 'Ship 1 pull request to an upstream open-source tool.';
        }

      } catch (err) {
        errorBox.textContent = 'ERROR: ' + err.message;
        errorBox.style.display = 'block';
      } finally {
        spinner.style.display = 'none';
        btnText.textContent = 'ROAST NOW ⚡';
        btn.disabled = false;
      }
    }

    function copyTerminalOutput() {
      const text = document.getElementById('rawOutput').textContent;
      navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copyBtn');
        const orig = btn.textContent;
        btn.textContent = '✅ COPIED!';
        setTimeout(() => { btn.textContent = orig; }, 2000);
      });
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
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
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
                "status": "active",
                "easter_egg": "antigravity",
                "agents": {
                    "claude": "AI Analysis & Prompt Architecture",
                    "opencode": "GitHub REST API Client & Rate-Limit Handling",
                    "antigravity": "Cloud Run Server & Neo-Brutalist Dashboard"
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
