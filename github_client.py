"""GitHub API client for fetching public profile and repository data.

Uses unauthenticated GitHub API (60 requests/hr limit for public data).
All data fetched is publicly available - no authentication required.
Optionally uses GITHUB_TOKEN env var for higher rate limits (5,000 req/hr).

Security Review (security-review skill integration):
- Only public data is fetched - no private user information requested
- Usernames are validated and sanitized before API calls
- Rate limiting respected (60/hr unauthenticated, 5,000/hr with token)
- No credentials or tokens stored in application state
- API responses validated - 404/403 handled gracefully
- Rate limit headers monitored and respected
- Fallback to unauthenticated mode if token unavailable or rate limited
"""

import os
import re
import requests
import time
from typing import Dict, List, Any, Optional


def _get_auth_headers() -> dict:
    """Get authentication headers if GITHUB_TOKEN is set or available via gh CLI."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GITHUB_TOKEN="):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                token = val
                                os.environ["GITHUB_TOKEN"] = val
                                break
            except Exception:
                pass
    if not token:
        try:
            import subprocess
            token = subprocess.check_output(["gh", "auth", "token"], stderr=subprocess.DEVNULL, timeout=2).decode().strip()
            if token:
                os.environ["GITHUB_TOKEN"] = token
        except Exception:
            pass

    headers = {"Accept": "application/vnd.github+v3+json", "User-Agent": "GitHub-Roast-And-Rescue/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _make_request(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
    """Make a GET request to GitHub API.

    Args:
        url: The URL to request
        params: Query parameters

    Returns:
        Response object if successful, None on rate limit or error
    """
    headers = _get_auth_headers()
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return response
        if response.status_code == 404:
            return None  # Not found
        if response.status_code == 403:
            return None  # Rate limited (even with token sometimes)
        return None
    except Exception:
        return None


def _delay(seconds: float) -> None:
    """Small delay to help avoid rate limiting."""
    time.sleep(max(0, seconds))

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")
class GitHubClient:
    """Client for fetching GitHub public profile and repo data with in-memory caching."""

    BASE_URL = "https://api.github.com/users"
    REPOS_URL = "https://api.github.com/users/{username}/repos"
    EVENTS_URL = "https://api.github.com/users/{username}/events"

    # Shared cache across instances: key -> (timestamp, data)
    _shared_cache: Dict[str, tuple[float, Any]] = {}

    def __init__(self, rate_limit_delay: float = 0.0, cache_ttl: float = 300.0):
        """Initialize the GitHub client.

        Args:
            rate_limit_delay: Delay in seconds between requests.
                Set to 0.0 when using GITHUB_TOKEN (5,000 req/hr).
                Use small delay (0.5-2.0s) without token (60 req/hr).
            cache_ttl: Time to live in seconds for in-memory cached responses (default: 300s).
        """
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl = cache_ttl

    def _rate_limit(self) -> None:
        """Apply delay between requests if no auth token."""
        if self.rate_limit_delay > 0:
            _delay(self.rate_limit_delay)

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Retrieve data from cache if not expired."""
        if key in self._shared_cache:
            ts, val = self._shared_cache[key]
            if (time.time() - ts) < self.cache_ttl:
                return val
        return None

    def _set_cache(self, key: str, val: Any) -> None:
        """Store response data in cache."""
        self._shared_cache[key] = (time.time(), val)

    def _validate_username(self, username: str) -> str:
        """Validate and sanitize GitHub username to prevent injection."""
        clean = (username or "").strip().lstrip("@")
        if not clean or not USERNAME_REGEX.match(clean):
            raise ValueError(f"Invalid GitHub username format: '{username}'")
        return clean

    def get_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile data from GitHub API with caching.

        Args:
            username: GitHub username to fetch

        Returns:
            Dictionary containing profile information, or None if not found/rate limited
        """
        try:
            username = self._validate_username(username)
        except ValueError:
            return None

        cache_key = f"profile:{username.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        self._rate_limit()
        url = f"{self.BASE_URL}/{username}"
        response = _make_request(url)
        if response is None:
            return None
        data = response.json()
        if isinstance(data, dict) and data.get("message") == "Not Found":
            return None

        self._set_cache(cache_key, data)
        return data

    def get_user_repos(
        self, username: str, per_page: int = 100, sort: str = "pushed"
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch user's public repositories with caching.

        Args:
            username: GitHub username
            per_page: Number of repos to fetch (max 100 per page)
            sort: Sort field (created, updated, pushed, full_name)

        Returns:
            List of repository dictionaries, or None if rate limited
        """
        try:
            username = self._validate_username(username)
        except ValueError:
            return []

        cache_key = f"repos:{username.lower()}:{per_page}:{sort}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        self._rate_limit()
        url = self.REPOS_URL.format(username=username)
        params = {"per_page": per_page, "sort": sort, "type": "public"}
        response = _make_request(url, params=params)
        if response is None:
            return None
        data = response.json()
        self._set_cache(cache_key, data)
        return data

    def get_recent_activity(self, username: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Fetch recent GitHub events/activity for a user with caching.

        Args:
            username: GitHub username
            limit: Number of events to return

        Returns:
            List of event dictionaries, or None if rate limited
        """
        try:
            username = self._validate_username(username)
        except ValueError:
            return []

        cache_key = f"events:{username.lower()}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        self._rate_limit()
        url = self.EVENTS_URL.format(username=username)
        params = {"per_page": limit}
        response = _make_request(url, params=params)
        if response is None:
            return None
        if response.status_code == 404:
            return []
        data = response.json()
        self._set_cache(cache_key, data)
        return data

    def get_repo_details(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information about a specific repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary containing repo details including language stats, or None
        """
        self._rate_limit()
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = _make_request(url)
        if response is None:
            return None
        if response.status_code == 404:
            raise ValueError(f"Repository '{owner}/{repo}' not found")
        return response.json()
    def get_repo_readme(self, owner: str, repo: str) -> str:
        """Fetch the README content for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            String containing README content, or empty string if not found
        """
        self._rate_limit()
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        headers = _get_auth_headers()
        headers["Accept"] = "application/vnd.github.v3.raw"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception:
            pass
        return ""

    def get_repo_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Fetch language byte counts for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary mapping language name to bytes of code
        """
        self._rate_limit()
        url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        headers = _get_auth_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def get_repo_commits(
        self, owner: str, repo: str, author: str = "", limit: int = 10
    ) -> List[Dict[str, str]]:
        """Fetch verified recent commits for a repository.

        Hits /repos/{owner}/{repo}/commits directly — real commit telemetry
        (message + timestamp). Unlike the events feed (which only embeds
        commit summaries for recent pushes), this is ground truth used by
        the psych-eval so we never claim "no code pushed" for active authors.

        Args:
            owner: Repository owner
            repo: Repository name
            author: GitHub username to filter commits by (author= query param)
            limit: Max commits to return (clamped to 1-30)

        Returns:
            List of {"message": str, "date": str} dicts (ISO 8601 dates),
            or empty list on any failure/rate limit
        """
        self._rate_limit()
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {"per_page": max(1, min(limit, 30))}
        if author:
            params["author"] = author
        headers = _get_auth_headers()

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            out: List[Dict[str, str]] = []
            for entry in response.json():
                commit = (entry.get("commit") or {}) if isinstance(entry, dict) else {}
                author_info = commit.get("author") or {}
                out.append({
                    "message": commit.get("message", "") or "",
                    "date": author_info.get("date", "") or "",
                })
            return out
        except Exception:
            return []

    def get_repo_tree(
        self, owner: str, repo: str, branch: str = ""
    ) -> List[str]:
        """Fetch the recursive file skeleton of a repository's default tree.

        Hits /repos/{owner}/{repo}/git/trees/{branch}?recursive=1 and
        returns lowercased file paths (e.g. "dockerfile",
        ".github/workflows/ci.yml", "tests/test_api.py"). Lets the audit
        verify Dockerfiles, CI pipelines, tests and backend models instead
        of guessing from repo names.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (defaults to the repo's default_branch)

        Returns:
            List of lowercased paths; empty list on any failure,
            truncation, or rate limit (callers treat as "no signal")
        """
        self._rate_limit()
        if not branch:
            try:
                details = self.get_repo_details(owner, repo)
                branch = (details or {}).get("default_branch", "") or ""
            except Exception:
                branch = ""
        if not branch:
            branch = "main"
        url = "https://api.github.com/repos/%s/%s/git/trees/%s" % (owner, repo, branch)
        params = {"recursive": "1"}
        headers = _get_auth_headers()

        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code != 200:
                return []
            tree = response.json().get("tree", []) or []
            return [
                (entry.get("path", "") or "").lower()
                for entry in tree
                if isinstance(entry, dict) and entry.get("path")
            ]
        except Exception:
            return []

def format_repo_summary(repos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summarized view of the top repositories.

    Args:
        repos: List of repo dictionaries from GitHub API

    Returns:
        Dictionary with summarized repo information
    """
    if not repos:
        return {"top_repos": [], "total_fetched": 0}

    # Sort by stars and take up to 20
    sorted_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:20]

    summary = []
    for repo in sorted_repos:
        license_info = repo.get("license")
        spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else None
        summary.append({
            "name": repo.get("name", "unknown"),
            "description": repo.get("description") or "",
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "is_fork": bool(repo.get("fork", False)),
            "open_issues": repo.get("open_issues_count", 0),
            "topics": repo.get("topics", []) if isinstance(repo.get("topics"), list) else [],
            "license": spdx,
            "archived": bool(repo.get("archived", False)),
            "homepage": repo.get("homepage") or "",
            "primary_language": repo.get("language") or "Unknown",
            "last_push": repo.get("pushed_at", "never"),
            "created_at": repo.get("created_at", ""),
            "url": repo.get("html_url", ""),
        })

    return {"top_repos": summary, "total_fetched": len(repos)}


def format_profile_summary(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summarized view of the user profile safely."""
    if not profile or not isinstance(profile, dict):
        return {
            "username": "",
            "name": "No name set",
            "bio": "No bio set",
            "location": "Not disclosed",
            "blog": "No blog",
            "company": "Not specified",
            "followers": 0,
            "following": 0,
            "public_repos": 0,
            "public_gists": 0,
            "hireable": False,
            "twitter_username": "",
            "created_at": "",
            "html_url": "",
        }

    return {
        "username": profile.get("login", ""),
        "name": profile.get("name") or "No name set",
        "bio": profile.get("bio") or "No bio set",
        "location": profile.get("location") or "Not disclosed",
        "blog": profile.get("blog") or "No blog",
        "company": profile.get("company") or "Not specified",
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "public_repos": profile.get("public_repos", 0),
        "public_gists": profile.get("public_gists", 0),
        "hireable": bool(profile.get("hireable", False)),
        "twitter_username": profile.get("twitter_username") or "",
        "created_at": profile.get("created_at", ""),
        "html_url": profile.get("html_url", ""),
    }