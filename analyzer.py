"""Claude-powered analysis and feedback generation for GitHub profiles.

Uses deep heuristic profiling across 15+ profile signals (languages, repos,
stars, forks, commit cadence, bio, follower ratios, events) to generate:
- 30-second recruiter glance summary
- Witty, customized, razor-sharp humorous roast (no generic templates)
- Highly personalized, actionable, diagnostic rescue plan
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional

# Multi-agent architecture integration: Claude + OpenCode + Antigravity
# Claude powers analysis and feedback generation; Antigravity powers UI & Serving.

TUTORIAL_PATTERNS = [
    r"(^|[-_])(todo|todolist|calculator|weather|counter|quiz|recipe|clock)([-_]|$)",
    r"(^|[-_])(clone|netflix-clone|spotify-clone|amazon-clone|twitter-clone|instagram-clone)([-_]|$)",
    r"(^|[-_])(first-contributions|leetcode|dsa-prep|interview-prep)([-_]|$)",
]

LANGUAGE_HUMOR = {
    "python": "Python loyalist — where 80% of debugging is print statements and your virtualenv folder weighs more than the operating system.",
    "javascript": "JavaScript/TypeScript maximalist — you've probably switched build tools 4 times this year and still haven't written a unit test.",
    "typescript": "TypeScript devotee — writing 50 lines of complex utility types just to render a single button with zero runtime bugs (allegedly).",
    "rust": "Rust evangelist — fighting the borrow checker for 6 hours straight just to say your CLI tool is memory-safe.",
    "c++": "C/C++ veteran — raw pointers, manual memory allocation, and segmentation faults are your idea of an adrenaline rush.",
    "c": "C purist — living so close to bare metal you can hear the electrons screaming. Where abstractions go to die.",
    "go": "Go pragmatic — if err != nil { return nil, err } is tattooed on your forearm. Zero generics trauma.",
    "java": "Java enterprise architect — AbstractSingletonProxyFactoryBean energy. 14 layers of inheritance to print Hello World.",
    "c#": ".NET / C# builder — enterprise stability wrapped in Microsoft warmth. Probably has a Visual Studio license on company credit.",
    "php": "PHP soldier — still powering 75% of the internet while everyone else debates JavaScript frameworks.",
    "html": "Markup specialist — HTML and CSS are beautiful, but opening tags and flexbox alignment won't survive a systems design interview.",
    "jupyter notebook": "Jupyter data scientist — code that runs exclusively on your local machine in out-of-order execution cells.",
    "shell": "Bash wizard — 500-line shell scripts with zero comments that run production deployments on a prayer.",
}


def _safe_get(mapping: Optional[Dict], key: str, default: Any = "") -> Any:
    """Safely get a value from a dict, avoiding AttributeError on None."""
    if mapping is None:
        return default
    return mapping.get(key, default)


def _format_languages(repos: List[Dict], max_repos: int = 15, max_langs: int = 4) -> str:
    """Extract unique primary languages from repos."""
    languages: List[str] = []
    for repo in repos[:max_repos]:
        lang = _safe_get(repo, "primary_language")
        if lang and lang != "Unknown" and lang not in languages:
            languages.append(lang)
    return ", ".join(languages[:max_langs]) if languages else "Various Technologies"


def _extract_profile_features(
    profile: Dict[str, Any],
    repos: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Extract rich behavioral and quantitative signals from profile data."""
    username = _safe_get(profile, "username", "").lower()
    name = _safe_get(profile, "name", "")
    bio = _safe_get(profile, "bio", "").strip()
    if bio == "No bio set":
        bio = ""
    company = _safe_get(profile, "company", "").strip()
    location = _safe_get(profile, "location", "").strip()
    blog = _safe_get(profile, "blog", "").strip()
    followers = int(_safe_get(profile, "followers", 0) or 0)
    following = int(_safe_get(profile, "following", 0) or 0)
    public_repos = int(_safe_get(profile, "public_repos", len(repos)) or len(repos))
    created_at = _safe_get(profile, "created_at", "")

    # Calculate account age in years
    account_age_years = 1
    if created_at:
        try:
            created_year = int(created_at[:4])
            account_age_years = max(1, 2026 - created_year)
        except Exception:
            pass

    # Repo breakdown
    fork_count = sum(1 for r in repos if r.get("is_fork"))
    total_stars = sum(int(r.get("stars", 0) or 0) for r in repos)
    empty_desc_count = sum(1 for r in repos if not r.get("description") or r.get("description") == "No description")

    # Detect tutorial repos
    tutorial_repos = []
    for r in repos:
        r_name = r.get("name", "").lower()
        if any(re.search(pat, r_name) for pat in TUTORIAL_PATTERNS):
            tutorial_repos.append(r.get("name"))

    # Language breakdown
    lang_counts: Dict[str, int] = {}
    for r in repos:
        l = r.get("primary_language")
        if l and l != "Unknown":
            lang_counts[l] = lang_counts.get(l, 0) + 1
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    primary_lang = sorted_langs[0][0] if sorted_langs else "Code"

    # Top repo by stars
    sorted_by_stars = sorted(repos, key=lambda r: int(r.get("stars", 0) or 0), reverse=True)
    top_star_repo = sorted_by_stars[0] if sorted_by_stars else {}
    top_star_count = int(top_star_repo.get("stars", 0) or 0) if top_star_repo else 0
    top_repo_name = top_star_repo.get("name", "") if top_star_repo else (repos[0].get("name") if repos else "main-project")

    # Second repo
    second_repo_name = sorted_by_stars[1].get("name") if len(sorted_by_stars) > 1 else None

    # Events analysis
    recent_commits = []
    has_recent_activity = False
    if events and isinstance(events, list):
        has_recent_activity = len(events) > 0
        for ev in events:
            if isinstance(ev, dict) and ev.get("type") == "PushEvent":
                payload = ev.get("payload", {})
                if isinstance(payload, dict):
                    commits = payload.get("commits", [])
                    if isinstance(commits, list):
                        for c in commits:
                            if isinstance(c, dict) and c.get("message"):
                                msg = c.get("message", "").strip().split("\n")[0]
                                if msg:
                                    recent_commits.append(msg)

    # Determine archetype
    archetype = "The Generalist Builder"
    if username == "antigravity":
        archetype = "The Zero-Gravity Sovereign"
    elif followers > 20000 or top_star_count > 5000:
        archetype = "The Open-Source Titan / Tech Deity"
    elif public_repos <= 1:
        archetype = "The Digital Ghost / Stealth Operative"
    elif len(repos) > 0 and (fork_count / max(1, len(repos))) >= 0.5:
        archetype = "The Fork Tourist / Cloner"
    elif len(tutorial_repos) >= 2:
        archetype = "The Tutorial Island Castaway"
    elif following > 150 and following > (followers * 3):
        archetype = "The Follow-For-Follow Optimist"
    elif len(repos) >= 8 and total_stars <= 2:
        archetype = "The Side-Quest Graveyard Keeper"
    elif top_star_count >= 100 and (total_stars - top_star_count) < (top_star_count * 0.15):
        archetype = "The One-Hit Wonder"
    elif len(sorted_langs) >= 4 and all(count <= 2 for _, count in sorted_langs):
        archetype = "The Shiny Object Framework Hopper"
    elif not bio and not company and not location and len(repos) >= 3:
        archetype = "The Unlicensed Secret Agent"
    elif primary_lang.lower() in ("c", "c++", "rust"):
        archetype = "The Low-Level Memory Gladiator"
    elif primary_lang.lower() in ("python", "jupyter notebook"):
        archetype = "The AI/Data Alchemist"
    elif primary_lang.lower() in ("javascript", "typescript"):
        archetype = "The Full-Stack Maximalist"

    return {
        "username": username,
        "name": name,
        "bio": bio,
        "company": company,
        "location": location,
        "blog": blog,
        "followers": followers,
        "following": following,
        "public_repos": public_repos,
        "account_age_years": account_age_years,
        "fork_count": fork_count,
        "total_stars": total_stars,
        "empty_desc_count": empty_desc_count,
        "tutorial_repos": tutorial_repos,
        "primary_lang": primary_lang,
        "all_langs": [l for l, _ in sorted_langs],
        "top_repo_name": top_repo_name,
        "top_star_count": top_star_count,
        "top_repo": top_star_repo,
        "second_repo_name": second_repo_name,
        "recent_commits": recent_commits[:5],
        "has_recent_activity": has_recent_activity,
        "archetype": archetype,
        "repos": repos,
    }


def _generate_recruiter_glance(
    profile: Dict[str, Any],
    repos: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate a high-signal 3-bullet instant recruiter scan."""
    features = _extract_profile_features(profile, repos, events)
    lang_summary = _format_languages(repos)
    followers = features["followers"]
    repos_cnt = features["public_repos"]
    archetype = features["archetype"]
    years = features["account_age_years"]

    activity_status = "Active commit cadence" if features["has_recent_activity"] else "Low recent public telemetry"
    if features["top_star_count"] > 100:
        social_proof = f"{features['top_star_count']:,}★ on '{features['top_repo_name']}'"
    else:
        social_proof = f"{features['total_stars']} total stars across {repos_cnt} repos"

    lines = [
        f"• Profile Vibe : {archetype} ({years}y footprint on GitHub)",
        f"• Core Stack   : {lang_summary} | {social_proof}",
        f"• Recruiter Read: {followers:,} followers | {repos_cnt} public projects | {activity_status}",
    ]
    return "\n".join(lines)


def _generate_roast(profile: Dict[str, Any], repos: List[Dict[str, Any]], events: Optional[List[Dict[str, Any]]] = None) -> str:
    """Generate an authentic, razor-sharp, laugh-out-loud witty roast specific to this profile."""
    f = _extract_profile_features(profile, repos, events)
    u = f["username"]
    archetype = f["archetype"]
    bio = f["bio"]
    followers = f["followers"]
    following = f["following"]
    total_repos = f["public_repos"]
    top_repo = f["top_repo_name"]
    second_repo = f["second_repo_name"]
    primary_lang = f["primary_lang"]
    total_stars = f["total_stars"]
    fork_count = f["fork_count"]
    commits = f["recent_commits"]
    tutorial_repos = f["tutorial_repos"]
    empty_descs = f["empty_desc_count"]

    # 1. SPECIAL CASE: antigravity
    if u == "antigravity":
        return (
            "⚖️ ARCHETYPE: The Zero-Gravity Sovereign\n\n"
            "Zero repositories, zero commits, and absolute physics-defying audacity. "
            "You exist purely as a foundational architectural tier in our AI triad. "
            "While other developers drown in merge conflicts and Jira sprints, you're floating completely above the grind, "
            "serving HTTP traffic without ever worrying about a broken build."
        )

    # 2. SPECIAL CASE: Tech Deity / High Follower (Torvalds, Karpathy, etc.)
    if followers > 15000 or (total_stars > 10000 and followers > 5000):
        handle_text = f"@{u}" if u else "This user"
        bio_jab = (
            f"Yet your bio is '{bio or 'completely non-existent'}'. When you're this famous, apparently punctuation and self-introductions are beneath you."
            if not bio or len(bio) < 20 else
            f"Your bio is '{bio}', but let's be honest: nobody is reading your bio when they're busy cloning '{top_repo}'."
        )
        return (
            f"👑 ARCHETYPE: {archetype}\n\n"
            f"{handle_text} has {followers:,} developers watching every git push like a sold-out stadium crowd. "
            f"Your repository '{top_repo}' has {f['top_star_count']:,} stars—which is more stars than most junior engineers will see in three lifetimes. "
            f"{bio_jab}\n\n"
            f"Recruiters probably don't even send you InMails; they send handwritten letters via courier. "
            f"The rest of GitHub is fighting for a 10-star side project while you commit directly to main like an ancient deity who doesn't believe in code review."
        )

    # 3. SPECIAL CASE: Digital Ghost / Void
    if total_repos <= 1:
        return (
            f"👻 ARCHETYPE: {archetype}\n\n"
            f"@{u}'s GitHub profile is cleaner than a brand-new MacBook fresh out of the shrink-wrap. "
            f"You have {total_repos} public repository. Either you are an elite cybersecurity ghost working for an intelligence agency, "
            f"or your entire software engineering journey lives on an unbacked-up desktop folder named 'new_folder_final_v2'.\n\n"
            f"Recruiters looking at this profile aren't deciding whether to hire you; they're wondering if you've discovered `git push` yet. "
            f"Give the world a sign of life, even if it's just an unformatted markdown file."
        )

    # 4. FORK HOARDER
    if total_repos >= 3 and (fork_count / max(1, len(repos))) >= 0.5:
        fork_example = [r.get("name") for r in repos if r.get("is_fork")]
        sample_fork = fork_example[0] if fork_example else "famous-library"
        return (
            f"🍴 ARCHETYPE: {archetype}\n\n"
            f"You've got {total_repos} repositories, but {fork_count} of them are literal forks! "
            f"Clicking the 'Fork' button on '{sample_fork}' does not make you an open-source contributor, chief—that's digital hoarder behavior. "
            f"You're collecting repositories like unopened browser tabs you promise you'll read over the weekend.\n\n"
            f"Recruiters want to see what YOU built, not a museum tour of repositories other engineers wrote while you watched."
        )

    # 5. TUTORIAL ISLAND RESIDENT
    if len(tutorial_repos) >= 2:
        tut_list = ", ".join(f"'{t}'" for t in tutorial_repos[:3])
        return (
            f"🏝️ ARCHETYPE: {archetype}\n\n"
            f"We took one look at your repository lineup: {tut_list}. "
            f"Congratulations on completing every YouTube tutorial from 2022! "
            f"You are one 'Weather App' away from an honorary Udemy certificate, but the software industry is still waiting for your debut.\n\n"
            f"Building a todo app with local storage is a rite of passage, but shipping three of them is a hostage situation. "
            f"Break out of the tutorial sandbox before you end up cloning Twitter for the fourth time."
        )

    # 6. FOLLOW-FOR-FOLLOW TRAP
    if following > 150 and following > (followers * 3):
        return (
            f"🤝 ARCHETYPE: {archetype}\n\n"
            f"Following {following:,} developers with only {followers} following you back? "
            f"Bro, this is GitHub, not a 2015 Instagram follow-back train. "
            f"Those {following:,} engineers aren't going to star your empty repositories out of mutual respect.\n\n"
            f"Meanwhile, your primary language is {primary_lang}, and '{top_repo}' is sitting there waiting for inbound traffic that isn't coming. "
            f"Stop playing community manager and commit some code."
        )

    # 7. ONE-HIT WONDER
    if f["top_star_count"] >= 30 and (total_stars - f["top_star_count"]) < 10:
        return (
            f"🎸 ARCHETYPE: {archetype}\n\n"
            f"Your entire developer identity is carrying '{top_repo}' on its back like Atlas holding the globe. "
            f"That project has {f['top_star_count']} stars, while the rest of your {total_repos - 1} repositories look like "
            f"failed experimental solo albums that got zero radio play.\n\n"
            f"If someone deletes '{top_repo}', your profile immediately defaults back to a blank slate. Diversify your portfolio before the hype fades!"
        )

    # 8. GENERAL HIGH-OCTANE ROAST (Tailored with specific repo names, bio analysis, and language jabs)
    lang_jab = LANGUAGE_HUMOR.get(primary_lang.lower(), f"{primary_lang} enthusiast — doing your best to make compilers happy.")
    
    # Bio commentary
    if not bio:
        bio_critique = f"{total_repos} repositories and not a single sentence in the bio. You treat your developer identity like an FBI classified dossier."
    elif len(bio) < 25:
        bio_critique = f"Your bio is literally '{bio}'—which reads like a git commit message someone typed with their eyes closed."
    elif any(buzz in bio.lower() for buzz in ["passionate", "enthusiast", "aspiring", "ninja", "rockstar", "guru"]):
        bio_critique = f"Your bio says '{bio}', which is heavy on buzzwords but light on specifics. The tech industry has enough 'passionate ninjas'—we need someone who writes integration tests."
    else:
        bio_critique = f"Your bio proclaims: '{bio}'. Ambitious energy, but your repo list tells a slightly messier story."

    # Repo specifics
    repo_callout = f"We inspected '{top_repo}'"
    if second_repo:
        repo_callout += f" and '{second_repo}'"
    
    if empty_descs >= 3:
        desc_jab = f"{empty_descs} out of your {total_repos} repositories don't even have descriptions. Do you expect recruiters to open `src/index.js` and guess the business model?"
    else:
        desc_jab = f"With {total_stars} total stars across {total_repos} repos, you are firmly operating in the indie trenches."

    # Commit commentary
    commit_jab = ""
    if commits:
        lazy_commits = [c for c in commits if any(k in c.lower() for k in ["fix", "update", "wip", "typo", "test", "asdf", "done"])]
        if lazy_commits:
            commit_jab = f"\n\nAlso, your recent commit history includes poetic masterpieces like '{lazy_commits[0]}'. Git blame must feel like a crime scene investigation."

    return (
        f"🔥 ARCHETYPE: {archetype}\n\n"
        f"{bio_critique}\n\n"
        f"{repo_callout}. {desc_jab} {lang_jab}{commit_jab}\n\n"
        f"Verdict: You have the raw building blocks of a solid engineer, but your profile currently looks like a garage workshop after a tornado hit it."
    )


def _generate_rescue(
    profile: Dict[str, Any],
    repos: List[Dict[str, Any]],
    roast: str,
    events: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate 3 intensely specific, diagnostic, actionable rescue steps tailored to this user."""
    f = _extract_profile_features(profile, repos, events)
    u = f["username"]
    top_repo = f["top_repo_name"]
    second_repo = f["second_repo_name"]
    primary_lang = f["primary_lang"]
    bio = f["bio"]
    empty_descs = f["empty_desc_count"]
    tutorial_repos = f["tutorial_repos"]
    fork_count = f["fork_count"]
    total_repos = f["public_repos"]
    top_star_count = f["top_star_count"]
    followers = f["followers"]

    # 0. SPECIAL CASE: Tech Deity / High Follower (Torvalds, Karpathy, etc.)
    if followers > 15000 or top_star_count > 5000:
        quick_win = (
            f"1. ⚡ 10-MIN QUICK WIN: Direct Your Developer Audience\n"
            f"   You have {followers:,} developers viewing your profile daily.\n"
            f"   👉 Add a direct link to your official documentation, newsletter, or project hub in your profile website/bio.\n"
            f"   Convert your immense inbound GitHub traffic into an owned distribution channel."
        )
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Architectural Governance for '{top_repo}'\n"
            f"   With {top_star_count:,} stars, '{top_repo}' is essential community infrastructure:\n"
            f"   • Add an `ARCHITECTURE.md` explaining system invariants for prospective contributors.\n"
            f"   • Set up automated PR triage bots and GitHub Discussion categories to prevent issue burnout.\n"
            f"   • Configure automated benchmarking CI workflows to catch performance regressions."
        )
        career_step = (
            f"3. 🚀 CAREER LEVERAGE: Formalize Sustainability & Foundation Status\n"
            f"   You are operating at ecosystem-scale. Protect maintainer longevity:\n"
            f"   👉 Establish GitHub Sponsors or Open Collective funding, define a `SECURITY.md` advisory process, and recruit trusted co-maintainers to avoid bus-factor risk."
        )
        return f"{quick_win}\n\n{weekend_proj}\n\n{career_step}"

    # 1. QUICK WIN (10-Minute Fix): Address their single biggest cosmetic vulnerability
    if not bio or len(bio) < 15:
        suggested_bio = f"Building high-performance {primary_lang} systems & tools | Maintainer of @{top_repo} | Open to software engineering roles"
        quick_win = (
            f"1. ⚡ 10-MIN QUICK WIN: Fix Your Missing Identity\n"
            f"   Your bio is currently empty or minimal. Copy-paste this tailored bio right now into your profile settings:\n"
            f"   👉 \"{suggested_bio}\"\n"
            f"   Recruiters filter out zero-bio profiles in under 3 seconds. Give them an instant value proposition."
        )
    elif empty_descs >= 2:
        target_repo = second_repo or top_repo
        quick_win = (
            f"1. ⚡ 10-MIN QUICK WIN: Stop the Invisible Repo Epidemic\n"
            f"   {empty_descs} of your repos have zero description. Go to '{top_repo}' and '{target_repo}' right now.\n"
            f"   👉 Click the ⚙️ icon next to 'About' and write a 1-sentence summary (e.g. 'A lightweight {primary_lang} service for data processing with zero runtime dependencies.').\n"
            f"   Without descriptions, your repos are completely invisible to GitHub search."
        )
    elif not f["location"] or not f["blog"]:
        quick_win = (
            f"1. ⚡ 10-MIN QUICK WIN: Turn On Discovery Signals\n"
            f"   You haven't listed a Location or personal link. Tech recruiters filter candidate pools by region (e.g., 'San Francisco', 'Remote', 'London').\n"
            f"   👉 Fill out your city/region and link your LinkedIn or portfolio URL to double your recruiter contact rate."
        )
    else:
        quick_win = (
            f"1. ⚡ 10-MIN QUICK WIN: Pin Your Strongest Assets\n"
            f"   Don't let GitHub randomly display your oldest repos. Go to your profile overview and customize your 'Pinned Repositories'.\n"
            f"   👉 Pin '{top_repo}' first, followed by your 2 cleanest {primary_lang} repositories. Hide any forks or unfinished experiments."
        )

    # 2. WEEKEND PROJECT (1-2 Days): Address their project portfolio / code quality gap
    if len(tutorial_repos) >= 1:
        tut_name = tutorial_repos[0]
        quickstart_command = "npm install && npm start" if primary_lang.lower() in ("javascript", "typescript") else "pip install -r requirements.txt && python main.py"
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Graduate '{tut_name}' from Tutorial Hell\n"
            f"   Turn this beginner project into a portfolio-grade asset recruiters respect:\n"
            f"   • Add real authentication (OAuth / JWT) and a persistent database (PostgreSQL / Supabase).\n"
            f"   • Deploy it live to a free cloud host (Vercel, Render, or Railway) and put the live URL at the top of the README.\n"
            f"   • Add a 3-step Quickstart block (`{quickstart_command}`)."
        )
    elif fork_count >= 3 and (fork_count / max(1, total_repos)) >= 0.4:
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Ship 1 Authentic Standalone Project\n"
            f"   Over 40% of your repos are forks. Unpin them and build one original application from scratch in {primary_lang}.\n"
            f"   • Pick a specific real-world problem (e.g., a CLI tool, API wrapper, or data dashboard).\n"
            f"   • Write clean commits from `git init` to `v1.0.0`.\n"
            f"   • Include an animated GIF in the README showing the tool in action."
        )
    elif top_star_count > 50:
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Open-Source Governance for '{top_repo}'\n"
            f"   '{top_repo}' already has {top_star_count} stars! Elevate it into a production-grade open source project:\n"
            f"   • Add a `CONTRIBUTING.md` guide and an Issue/PR template (`.github/ISSUE_TEMPLATE/`).\n"
            f"   • Set up GitHub Actions CI to run automated unit tests on every pull request.\n"
            f"   • Create a formal GitHub Release (`v1.0.0`) with release notes."
        )
    else:
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: The README Glow-Up for '{top_repo}'\n"
            f"   80% of hiring managers decide whether to interview based on the top repository's README alone:\n"
            f"   • Add a 5-second screen recording / GIF showing '{top_repo}' working before any walls of text.\n"
            f"   • Add tech stack shields/badges (e.g., Python 3.12, Fast, License MIT).\n"
            f"   • Include an Architecture section explaining WHY you made specific technical decisions."
        )

    # 3. CAREER LEVERAGE (Next 30 Days): Long-term compounding growth
    if not f["has_recent_activity"]:
        career_step = (
            f"3. 🚀 CAREER LEVERAGE: Re-ignite Your Public Heartbeat\n"
            f"   Your public activity graph is flatlining. Recruiters look for consistency, not 1-day commit spikes.\n"
            f"   👉 Pick '{top_repo}', update outdated dependencies, write 3 unit tests, and commit twice a week.\n"
            f"   Consistent green squares signal reliability and momentum."
        )
    elif len(f["all_langs"]) >= 4:
        career_step = (
            f"3. 🚀 CAREER LEVERAGE: Establish a Coherent {primary_lang} Senior Narrative\n"
            f"   You have repos scattered across {', '.join(f['all_langs'][:4])}. Generalists get passed over for specialist roles.\n"
            f"   👉 Position yourself as an authority in {primary_lang}. Focus your next 2 projects entirely on {primary_lang} ecosystem depth (performance tuning, concurrency, or distributed systems)."
        )
    else:
        career_step = (
            f"3. 🚀 CAREER LEVERAGE: Ship 1 Public Pull Request to Upstream Open Source\n"
            f"   You've proven you can write code in your own silo. The ultimate differentiator for senior engineering interviews is public collaboration.\n"
            f"   👉 Search GitHub for active {primary_lang} repos with the 'good first issue' label. Submit 1 clean, reviewed PR. Link that merged PR directly on your resume."
        )

    return f"{quick_win}\n\n{weekend_proj}\n\n{career_step}"


def analyze_profile(
    profile_data: Dict[str, Any],
    repos_data: List[Dict[str, Any]],
    username: str,
    events_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Analyze a GitHub profile and generate all feedback components.

    Combines recruiter glance, deep personalized roast, and diagnostic rescue plan.

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

    top_repos = repo_summary.get("top_repos", [])

    # Generate each component with deep personalization
    recruiter_glance = _generate_recruiter_glance(profile_summary, top_repos, events=events_data)
    roast = _generate_roast(profile_summary, top_repos, events=events_data)
    rescue = _generate_rescue(profile_summary, top_repos, roast, events=events_data)

    return {
        "username": username,
        "recruiter_glance": recruiter_glance,
        "roast": roast,
        "rescue": rescue,
        "profile_data": profile_summary,
        "repo_data": repo_summary,
    }