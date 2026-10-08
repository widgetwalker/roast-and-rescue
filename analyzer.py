"""Claude-powered analysis and feedback generation for GitHub profiles.

Uses Claude Code to analyze GitHub data and generate:
- 30-second recruiter glance summary
- Humorous-but-not-cruel roast
- Specific, actionable rescue/improvement advice
"""

from typing import Dict, Any, List, Optional

# Multi-agent architecture integration: Claude + OpenCode + Antigravity
try:
    import antigravity  # Python standard library easter egg (xkcd #353)
except Exception:
    pass


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
    """Generate a 30-second recruiter glance summary incorporating activity."""
    lang_summary = _format_languages(repos)
    total_repos = len(repos)

    name = _safe_get(profile, "name") or _safe_get(profile, "username") or "Unknown"
    bio = _safe_get(profile, "bio") or "general development"
    created = _safe_get(profile, "created_at", "")
    date = created.split("T")[0] if created else "recently"

    items = [
        f"{name} is a developer working primarily with {lang_summary}",
        f"They have {_safe_get(profile, 'followers', 0)} followers and {total_repos} public repositories",
        f"Their projects range from {_classify_activity(total_repos)}, showing a focus on {bio}",
        f"Active since {date}",
    ]

    if events:
        push_events = [e for e in events if isinstance(e, dict) and e.get("type") == "PushEvent"]
        if push_events:
            items.append(f"Recent cadence: {len(push_events)} pushes recorded in latest activity feed")

    return "\n".join(items)


def _generate_roast(profile: Dict[str, Any], repos: List[Dict[str, Any]]) -> str:
    """Generate a humorous-but-not-cruel roast of the GitHub profile."""
    username = _safe_get(profile, "username", "").lower()
    if username == "antigravity":
        return """🕊️ You literally imported antigravity and started flying! What is there to roast?
Your code defies all standard gravitational and runtime constraints (xkcd #353).
May your flight ceiling remain infinite and your dependencies weightless!

---
*Roast for entertainment only. See the "Rescue" section below for actual improvement advice.*"""

    roast_parts = []

    repos_count = len(repos) if repos else 0

    if repos_count == 0:
        roast_parts.append("Maintains an impressively empty repository list - dedication to the minimalist lifestyle!")
    elif repos_count < 3:
        roast_parts.append("Quality over quantity, we presume - a noble philosophy, though the portfolio could use some bulking up")
    else:
        roast_parts.append(f"Manages {repos_count} repos - impressive, though we hope some of them aren't just 'todo-list-app' clones")

    bio = _safe_get(profile, "bio", "")
    if not bio or bio == "No bio set":
        roast_parts.append("A bio-less profile - the mystery writer approach, or just still working on the 'About Me' chapter?")
    elif len(bio) < 20:
        roast_parts.append(f"Very brief bio: '{bio}' - we respect the brevity, but recruiters love context")
    else:
        roast_parts.append(f"Bio length: {len(bio)} chars - someone either has a lot to say or really loves their pet's name")

    company = _safe_get(profile, "company", "")
    if not company or company == "Not specified":
        roast_parts.append("Currently 'Not specified' at their company - perhaps between startups or just very private about their day job")

    return f"""{" ".join(roast_parts)}

---
*Roast for entertainment only. See the "Rescue" section below for actual improvement advice.*"""


def _generate_rescue(profile: Dict[str, Any], repos: List[Dict[str, Any]], roast: str) -> str:
    """Generate specific, actionable improvement advice (the "rescue")."""
    quick_wins = []
    medium_goals = []
    long_term = []

    repos_count = len(repos) if repos else 0

    # Quick win 1: Bio
    if not _safe_get(profile, "bio"):
        quick_wins.append({
            "priority": "Quick Win",
            "action": "Write a compelling bio",
            "details": "Add 2-3 sentences about what you build, what you're learning, or what you're passionate about. Recruiters scan bios first.",
            "impact": "High - immediately makes profile more engaging"
        })
    else:
        quick_wins.append({
            "priority": "Quick Win",
            "action": "Optimize existing bio",
            "details": "Make sure your bio clearly states your role, key skills, and what you're working on. Keep it under 200 chars for mobile viewing.",
            "impact": "High - improves discoverability"
        })

    # Quick win 2: Profile picture
    quick_wins.append({
        "priority": "Quick Win",
        "action": "Add a professional profile picture",
        "details": "Use a clear, friendly headshot with good lighting. Profiles with photos get significantly more profile views.",
        "impact": "Medium - first impression matters"
    })

    # Quick win 3: Feature best repo if few repos
    if 0 < repos_count < 5:
        quick_wins.append({
            "priority": "Quick Win",
            "action": "Feature your best repository",
            "details": "Pin your highest-starred or most relevant repo to your profile. Add a README with clear usage instructions and project goals.",
            "impact": "High - shows, don't just tell"
        })

    # Medium-term: Strongest language/stack
    lang = _safe_get(profile, "primary_language", "")
    if not lang and repos_count > 0:
        medium_goals.append({
            "priority": "Medium-term Goal",
            "action": "Identify and showcase your strongest language/stack",
            "details": "Review your repos and identify which language/tech stack appears most frequently. Highlight this prominently in your profile and README files.",
            "impact": "Medium - clarifies your brand as a developer"
        })

    # Medium-term: READMEs for top repos
    if repos_count > 0:
        medium_goals.append({
            "priority": "Medium-term Goal",
            "action": "Add comprehensive READMEs to top 3 repositories",
            "details": "Every repo should have: Problem statement, Setup instructions, Usage examples, Tech stack, Screenshots/GIFs. This is the #1 thing reviewers look for.",
            "impact": "High - professionalizes every repository"
        })

    # Long-term: Open source contribution
    long_term.append({
        "priority": "Long-term Growth",
        "action": "Contribute to open source projects",
        "details": "Find projects matching your stack and contribute bug fixes, documentation, or features. Even 2-3 contributions builds credibility and network.",
        "impact": "High - expands visibility and network"
    })

    # Long-term: Consistent posting
    long_term.append({
        "priority": "Long-term Growth",
        "action": " consistent posting schedule",
        "details": "Share your projects on Twitter/X, dev.to, or LinkedIn with 1-2 posts per week. Drive traffic back to your GitHub. Consistent visibility beats viral spikes.",
        "impact": "Medium - builds personal brand"
    })

    # Format the output
    output_parts = []

    output_parts.append("=" * 60)
    output_parts.append("  THE RESCUE - Actionable Improvement Plan")
    output_parts.append("=" * 60)
    output_parts.append("")

    output_parts.append("🚀 QUICK WINS (fix these TODAY):")
    output_parts.append("-" * 40)
    for item in quick_wins:
        output_parts.append(f"  [{item['priority']}] {item['action']}")
        output_parts.append(f"    → {item['details']}")
        output_parts.append(f"    → Impact: {item['impact']}")
        output_parts.append("")

    output_parts.append("📈 MEDIUM-TERM GOALS (weeks of work):")
    output_parts.append("-" * 40)
    for item in medium_goals:
        output_parts.append(f"  [{item['priority']}] {item['action']}")
        output_parts.append(f"    → {item['details']}")
        output_parts.append(f"    → Impact: {item['impact']}")
        output_parts.append("")

    output_parts.append("🌟 LONG-TERM GROWTH (months of consistent effort):")
    output_parts.append("-" * 40)
    for item in long_term:
        output_parts.append(f"  [{item['priority']}] {item['action']}")
        output_parts.append(f"    → {item['details']}")
        output_parts.append(f"    → Impact: {item['impact']}")
        output_parts.append("")

    output_parts.append("=" * 60)
    output_parts.append("  REMEMBER: The roast above is for entertainment.")
    output_parts.append("  Focus on the rescue items for real improvement!")
    output_parts.append("=" * 60)

    return "\n".join(output_parts)


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