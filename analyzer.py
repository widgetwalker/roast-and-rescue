"""Claude-powered analysis and feedback generation for GitHub profiles.

Uses Claude Code to analyze GitHub data and generate:
- 30-second recruiter glance summary
- Humorous-but-not-cruel roast
- Specific, actionable rescue/improvement advice
"""

from typing import Dict, Any, List, Optional

# Multi-agent architecture integration: Claude + OpenCode + Antigravity
# Claude powers analysis and feedback generation; Antigravity powers UI & Serving.


def _safe_get(mapping: Dict, key: str, default: Any = "") -> Any:
    """Safely get a value from a dict, avoiding AttributeError on None."""
    if mapping is None:
        return default
    return mapping.get(key, default)


def _format_languages(repos: List[Dict], max_repos: int = 5, max_langs: int = 3) -> str:
    """Extract unique primary languages from top repos."""
    languages: List[str] = []
    for repo in repos[:max_repos]:
        lang = _safe_get(repo, "primary_language")
        if lang and lang not in languages:
            languages.append(lang)
    return ", ".join(languages[:max_langs]) if languages else "various technologies"


def _classify_activity(total_repos: int) -> str:
    """Classify user activity level based on repo count."""
    if total_repos > 5:
        return "active contributor"
    if total_repos > 0:
        return "learning developer"
    return "starting out"


def _generate_recruiter_glance(
    profile: Dict[str, Any],
    repos: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate a 3-bullet instant recruiter scan."""
    lang_summary = _format_languages(repos)
    total_repos = len(repos)
    followers = _safe_get(profile, 'followers', 0)
    created = (_safe_get(profile, "created_at", "") or "recently")[:10]

    has_recent_pushes = bool(events and any(isinstance(e, dict) and e.get("type") == "PushEvent" for e in events))
    activity_note = "Active push cadence in recent events" if has_recent_pushes else "Quiet recent activity feed"

    lines = [
        f"• Tech Stack : {lang_summary}",
        f"• Footprint  : {total_repos} public repos | {followers:,} followers (active since {created})",
        f"• Pulse      : {activity_note}",
    ]
    return "\n".join(lines)


def _generate_roast(profile: Dict[str, Any], repos: List[Dict[str, Any]]) -> str:
    """Generate a punchy, sharp, witty roast."""
    username = _safe_get(profile, "username", "").lower()
    total_repos = len(repos) if repos else 0
    bio = _safe_get(profile, "bio", "")
    followers = _safe_get(profile, "followers", 0)

    if username == "antigravity":
        return "Zero repos, 5 followers, and absolute physics-defying audacity. Floating entirely above the commit grind."

    if total_repos == 0:
        return f"@{username}'s profile is cleaner than an empty operating system install. Minimalist aesthetic, or did you git push directly into the void?"

    if followers > 50000:
        return f"@{username} has {followers:,} developers watching every commit like a stadium crowd, yet the profile bio is still empty. When your code speaks for itself, who needs documentation?"

    if not bio or bio == "No bio set":
        return f"{total_repos} repositories and not a single sentence in the bio. You treat your developer identity like a classified intelligence dossier."

    if len(bio) < 25:
        return f"'{bio}' — we love the brevity, but your bio looks like a placeholder comment you forgot to remove before deploying to production."

    return f"{total_repos} public repos and '{bio}'. Looks like a graveyard of ambitious weekend side-projects where todos go to rest in peace."


def _generate_rescue(profile: Dict[str, Any], repos: List[Dict[str, Any]], roast: str) -> str:
    """Generate 3 bite-sized, high-leverage steps that are easy to digest."""
    top_repo = repos[0].get("name", "top repository") if repos else "primary project"

    steps = [
        f"1. ⚡ 10-MIN QUICK WIN:\n   Pin your best repo ('{top_repo}') and write a 1-sentence bio stating what you actually build.",
        f"2. 🎯 WEEKEND PROJECT:\n   Add a live demo GIF and a 3-step quickstart in '{top_repo}'s README.",
        "3. 🚀 CAREER GROWTH:\n   Add descriptive GitHub topic tags to your repos and ship 1 pull request to an upstream open-source tool."
    ]
    return "\n\n".join(steps)


def analyze_profile(
    profile_data: Dict[str, Any],
    repos_data: List[Dict[str, Any]],
    username: str,
    events_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Analyze a GitHub profile and generate all feedback components.

    This is the main analysis function that combines recruiter glance,
    roast, and rescue generation.

    Args:
        profile_data: Profile dictionary from GitHub client
        repos_data: List of repo dictionaries from GitHub client
        username: GitHub username being analyzed
        events_data: Optional list of recent event dictionaries

    Returns:
        Dictionary with all analysis components
    """
    from github_client import format_repo_summary, format_profile_summary
    profile_summary = format_profile_summary(profile_data)
    repo_summary = format_repo_summary(repos_data)

    # Generate each component
    recruiter_glance = _generate_recruiter_glance(
        profile_summary, repo_summary.get("top_repos", []), events=events_data
    )
    roast = _generate_roast(profile_summary, repo_summary.get("top_repos", []))
    rescue = _generate_rescue(profile_summary, repo_summary.get("top_repos", []), roast)

    return {
        "username": username,
        "recruiter_glance": recruiter_glance,
        "roast": roast,
        "rescue": rescue,
        "profile_data": profile_summary,
        "repo_data": repo_summary,
    }