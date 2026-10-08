"""Deep analysis and feedback generation for GitHub profiles.

Uses deep heuristic profiling across 15+ profile signals (languages, repos,
stars, forks, commit cadence, bio, follower ratios, events) to generate:
- 30-second recruiter glance summary
- Witty, customized, razor-sharp humorous roast (no generic templates)
- Highly personalized, actionable, diagnostic rescue plan
"""

import re
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Core Architecture Integration
# Engine powers analysis and feedback generation; Backend powers UI & Serving.

TUTORIAL_PATTERNS = [
    r"(^|[-_])(todo|todolist|calculator|weather|counter|quiz|recipe|clock)([-_]|$)",
    r"(^|[-_])(clone|netflix-clone|spotify-clone|amazon-clone|twitter-clone|instagram-clone)([-_]|$)",
    r"(^|[-_])(first-contributions|leetcode|dsa-prep|interview-prep)([-_]|$)",
]

LANGUAGE_HUMOR = {
    "python": [
        "Python loyalist — where 80% of debugging is print statements and your virtualenv folder weighs more than the operating system.",
        "Python enthusiast — you refuse to write curly braces, yet your list comprehensions are completely unreadable.",
        "Python dev — you imported an ML library once and now your LinkedIn says 'AI Engineer'."
    ],
    "javascript": [
        "JavaScript/TypeScript maximalist — you've probably switched build tools 4 times this year and still haven't written a unit test.",
        "JS purist — `[1, 2] + [3, 4] === '1, 23, 4'` makes perfect sense to you.",
        "JavaScript dev — your `node_modules` folder has more files than the Library of Congress."
    ],
    "typescript": [
        "TypeScript devotee — writing 50 lines of complex utility types just to render a single button with zero runtime bugs (allegedly).",
        "TS architect — you spend more time wrestling with `any` than actually shipping features.",
        "TypeScript fan — trying to fix JavaScript by turning it into Java."
    ],
    "rust": [
        "Rust evangelist — fighting the borrow checker for 6 hours straight just to say your CLI tool is memory-safe.",
        "Rustacean — you rewrite everything in Rust, even when a bash script would do.",
        "Rust dev — if your code compiles on the first try, you assume there's a bug in the compiler."
    ],
    "c++": [
        "C/C++ veteran — raw pointers, manual memory allocation, and segmentation faults are your idea of an adrenaline rush.",
        "C++ dev — your compile times are so long you've mastered 3 new hobbies.",
        "C++ programmer — holding on to legacy codebases like a badge of honor."
    ],
    "c": [
        "C purist — living so close to bare metal you can hear the electrons screaming. Where abstractions go to die.",
        "C programmer — `malloc` is your middle name, and memory leaks are your closest friends."
    ],
    "go": [
        "Go pragmatic — if err != nil { return nil, err } is tattooed on your forearm. Zero generics trauma.",
        "Go dev — writing boilerplate code like it's a religion.",
        "Golang fan — you love interfaces but secretly miss having a real type system."
    ],
    "java": [
        "Java enterprise architect — AbstractSingletonProxyFactoryBean energy. 14 layers of inheritance to print Hello World.",
        "Java dev — you consider 500MB of RAM a 'lightweight' microservice.",
        "Java veteran — waiting for the JVM to warm up since 1995."
    ],
    "c#": [
        ".NET / C# builder — enterprise stability wrapped in Microsoft warmth. Probably has a Visual Studio license on company credit.",
        "C# dev — you're basically a Java developer who actually likes their IDE."
    ],
    "php": [
        "PHP soldier — still powering 75% of the internet while everyone else debates JavaScript frameworks.",
        "PHP dev — hiding the `.php` extensions so nobody knows what you're running."
    ],
    "html": [
        "Markup specialist — HTML and CSS are beautiful, but opening tags and flexbox alignment won't survive a systems design interview.",
        "HTML/CSS dev — you spend 4 hours centering a div and call it a day."
    ],
    "jupyter notebook": [
        "Jupyter data scientist — code that runs exclusively on your local machine in out-of-order execution cells.",
        "Data Scientist — your git commits are just 50MB JSON blobs of cell output."
    ],
    "shell": [
        "Bash wizard — 500-line shell scripts with zero comments that run production deployments on a prayer.",
        "Shell script purist — who needs Python when you have `awk`, `sed`, and pure chaos?"
    ],
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
    events: Optional[List[Dict[str, Any]]] = None,
    readme_content: str = "",
    repo_languages: Optional[Dict[str, int]] = None
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
    if followers > 20000 or top_star_count > 5000:
        archetype = random.choice(["The Open-Source Titan", "The Tech Deity", "The 10x Engineer Personified"])
    elif public_repos <= 1:
        archetype = random.choice(["The Digital Ghost", "The Stealth Operative", "The Empty Canvas"])
    elif len(repos) > 0 and (fork_count / max(1, len(repos))) >= 0.5:
        archetype = random.choice(["The Fork Tourist", "The Cloner", "The Open-Source Spectator"])
    elif len(tutorial_repos) >= 2:
        archetype = random.choice(["The Tutorial Island Castaway", "The Bootcamp Graduate", "The 'To-Do App' Connoisseur"])
    elif following > 150 and following > (followers * 3):
        archetype = random.choice(["The Follow-For-Follow Optimist", "The Networker, Not Coder", "The Reply-Guy Engineer"])
    elif len(repos) >= 8 and total_stars <= 2:
        archetype = random.choice(["The Side-Quest Graveyard Keeper", "The Serial Project Abandoner", "The 90%-Done Architect", "The Domain Name Hoarder"])
    elif top_star_count >= 100 and (total_stars - top_star_count) < (top_star_count * 0.15):
        archetype = random.choice(["The One-Hit Wonder", "The Accidental Viral Repo Owner", "The Atlas Holding The World"])
    elif len(sorted_langs) >= 4 and all(count <= 2 for _, count in sorted_langs):
        archetype = random.choice(["The Shiny Object Framework Hopper", "The 'Hello World' Polyglot", "The Technology Tourist"])
    elif not bio and not company and not location and len(repos) >= 3:
        archetype = random.choice(["The Unlicensed Secret Agent", "The Anonymous Committer", "The Witness Protection Program Dev"])
    elif primary_lang.lower() in ("c", "c++", "rust"):
        archetype = random.choice(["The Low-Level Memory Gladiator", "The Borrow-Checker Masochist", "The Segfault Survivor"])
    elif primary_lang.lower() in ("python", "jupyter notebook"):
        archetype = random.choice(["The AI/Data Alchemist", "The Standard Library Devotee", "The Indentation Purist"])
    elif primary_lang.lower() in ("javascript", "typescript"):
        archetype = random.choice(["The Full-Stack Maximalist", "The Node_Modules Hoarder", "The 'I Could Build This In React' Guy"])

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
        "readme_content": readme_content,
        "repo_languages": repo_languages,
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


def _generate_roast(
    profile: Dict[str, Any], 
    repos: List[Dict[str, Any]], 
    events: Optional[List[Dict[str, Any]]] = None, 
    readme_content: str = "",
    repo_languages: Optional[Dict[str, int]] = None
) -> str:
    """Generate an authentic, razor-sharp, laugh-out-loud witty roast specific to this profile."""
    f = _extract_profile_features(profile, repos, events, readme_content, repo_languages)
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
            "Recruiters probably don't even send you InMails; they send handwritten letters via courier."
            "The rest of GitHub is fighting for a 10-star side project while you commit directly to main like an ancient deity who doesn't believe in code review."
        )

    # 3. SPECIAL CASE: Digital Ghost / Void
    if total_repos <= 1:
        return (
            f"👻 ARCHETYPE: {archetype}\n\n"
            f"@{u}'s GitHub profile is cleaner than a brand-new MacBook fresh out of the shrink-wrap. "
            f"You have {total_repos} public repository. Either you are an elite cybersecurity ghost working for an intelligence agency, "
            "or your entire software engineering journey lives on an unbacked-up desktop folder named 'new_folder_final_v2'.\n\n"
            "Recruiters looking at this profile aren't deciding whether to hire you; they're wondering if you've discovered `git push` yet."
            "Give the world a sign of life, even if it's just an unformatted markdown file."
        )

    # 4. FORK HOARDER
    if total_repos >= 3 and (fork_count / max(1, len(repos))) >= 0.5:
        fork_example = [r.get("name") for r in repos if r.get("is_fork")]
        sample_fork = fork_example[0] if fork_example else "famous-library"
        roasts = [
            (
                f"🍴 ARCHETYPE: {archetype}\n\n"
                f"You've got {total_repos} repositories, but {fork_count} of them are literal forks! "
                f"Clicking the 'Fork' button on '{sample_fork}' does not make you an open-source contributor, chief—that's digital hoarder behavior. "
                "You're collecting repositories like unopened browser tabs you promise you'll read over the weekend.\n\n"
                "Recruiters want to see what YOU built, not a museum tour of repositories other engineers wrote while you watched."
            ),
            (
                f"🍴 ARCHETYPE: {archetype}\n\n"
                f"With {fork_count} forks out of {total_repos} repos, your GitHub profile looks less like a developer portfolio "
                f"and more like a mirror site for '{sample_fork}'. It's great that you know how the 'Fork' button works, but "
                "at some point you actually have to write your own code.\n\n"
                "Stop treating GitHub like a Pinterest board of code you'll never read."
            )
        ]
        return random.choice(roasts)

    # 5. TUTORIAL ISLAND RESIDENT
    if len(tutorial_repos) >= 2:
        tut_list = ", ".join(f"'{t}'" for t in tutorial_repos[:3])
        roasts = [
            (
                f"🏝️ ARCHETYPE: {archetype}\n\n"
                f"We took one look at your repository lineup: {tut_list}. "
                "Congratulations on completing every YouTube tutorial from 2022!"
                "You are one 'Weather App' away from an honorary Udemy certificate, but the software industry is still waiting for your debut.\n\n"
                "Building a todo app with local storage is a rite of passage, but shipping three of them is a hostage situation."
                "Break out of the tutorial sandbox before you end up cloning Twitter for the fourth time."
            ),
            (
                f"🏝️ ARCHETYPE: {archetype}\n\n"
                f"Ah yes, the holy trinity: {tut_list}. "
                "Your profile is a monument to Codecademy modules and 12-hour freeCodeCamp videos."
                "But learning how to write 'Hello World' in 5 different frameworks isn't exactly engineering.\n\n"
                "Time to close the guided tutorials and try building something without a safety net."
            )
        ]
        return random.choice(roasts)

    # 6. FOLLOW-FOR-FOLLOW TRAP
    if following > 150 and following > (followers * 3):
        return (
            f"🤝 ARCHETYPE: {archetype}\n\n"
            f"Following {following:,} developers with only {followers} following you back? "
            "Bro, this is GitHub, not a 2015 Instagram follow-back train."
            f"Those {following:,} engineers aren't going to star your empty repositories out of mutual respect.\n\n"
            f"Meanwhile, your primary language is {primary_lang}, and '{top_repo}' is sitting there waiting for inbound traffic that isn't coming. "
            "Stop playing community manager and commit some code."
        )

    # 7. ONE-HIT WONDER
    if f["top_star_count"] >= 30 and (total_stars - f["top_star_count"]) < 10:
        roasts = [
            (
                f"🎸 ARCHETYPE: {archetype}\n\n"
                f"Your entire developer identity is carrying '{top_repo}' on its back like Atlas holding the globe. "
                f"That project has {f['top_star_count']} stars, while the rest of your {total_repos - 1} repositories look like "
                "failed experimental solo albums that got zero radio play.\n\n"
                f"If someone deletes '{top_repo}', your profile immediately defaults back to a blank slate. Diversify your portfolio before the hype fades!"
            ),
            (
                f"🎸 ARCHETYPE: {archetype}\n\n"
                f"You really hit the jackpot with '{top_repo}', didn't you? {f['top_star_count']} stars! "
                f"It's a shame your other {total_repos - 1} repos have a combined star count lower than the number of times you've refreshed your notifications.\n\n"
                "You're one deleted repository away from being totally irrelevant again."
            )
        ]
        return random.choice(roasts)

    # 8. GENERAL HIGH-OCTANE ROAST (Tailored with specific repo names, bio analysis, and language jabs)
    lang_jokes = LANGUAGE_HUMOR.get(primary_lang.lower(), [f"{primary_lang} enthusiast — doing your best to make compilers happy."])
    lang_jab = random.choice(lang_jokes)
    
    # Bio commentary
    if not bio:
        bio_critique = random.choice([
            f"{total_repos} repositories and not a single sentence in the bio. You treat your developer identity like an FBI classified dossier.",
            "Your bio is as empty as a swallowed exception. Give us something to work with here!"
        ])
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
    
    repo_langs = f.get("repo_languages")
    
    readme = f["readme_content"]
    is_profile_repo = bool(u) and top_repo.strip().lower() == u.strip().lower()
    if is_profile_repo:
        # A {username}/{username} profile README is *supposed* to be all
        # markdown — never roast it for lacking code.
        desc_jab = (
            f"Your '{top_repo}' profile README is doing the most — personal "
            "landing-page energy. Respect for the branding; now point that"
            "same effort at a repo with an actual test suite."
        )
    elif not readme:
        desc_jab = f"The README for '{top_repo}' is completely missing. Code should be self-documenting, but your repos are self-isolating."
    elif repo_langs is not None and sum(repo_langs.values()) < 500 and len(readme) > 1000:
        total_code_bytes = sum(repo_langs.values())
        desc_jab = f"Wait, '{top_repo}' has a massive {len(readme)}-character README, but only {total_code_bytes} bytes of actual code?! You wrote a whole dissertation for a starter template. Documentation writing checks your codebase literally cannot cash."
    elif len(readme) < 50:
        desc_jab = f"The README for '{top_repo}' is basically a Post-It note. You expect people to `npm install` based on 3 words of documentation?"
    elif "getting started" not in readme.lower() and "install" not in readme.lower():
        desc_jab = f"Your '{top_repo}' README is a philosophical essay without any installation instructions. Nobody wants to read your manifesto, they just want the setup command."
    elif len(readme) > 5000:
        desc_jab = f"The README for '{top_repo}' is longer than a Lord of the Rings book. Documentation is great, but nobody is reading a dissertation to use a simple tool."
    else:
        if empty_descs >= 3:
            desc_jab = f"Your top repo has a README, but {empty_descs} out of your {total_repos} repositories don't even have descriptions. Do you expect recruiters to open `src/index.js` and guess the business model?"
        else:
            desc_jab = f"With {total_stars} total stars across {total_repos} repos, you are firmly operating in the indie trenches."

    # Commit commentary
    commit_jab = ""
    if commits:
        lazy_commits = [c for c in commits if any(k in c.lower() for k in ["fix", "update", "wip", "typo", "test", "asdf", "done", "changes"])]
        if lazy_commits:
            commit_jab = f"\n\nAlso, your recent commit history includes poetic masterpieces like '{lazy_commits[0]}'. Git blame must feel like a crime scene investigation."
        elif "wip" in " ".join(commits).lower() or "test" in " ".join(commits).lower():
            commit_jab = "\n\nYour commits read like a stream of consciousness. Stop pushing 'WIP' directly to main."

    verdicts = [
        "Verdict: You have the raw building blocks of a solid engineer, but your profile currently looks like a garage workshop after a tornado hit it.",
        "Verdict: Strong chaotic-neutral energy. Your profile needs a refactor more urgently than your code does.",
        "Verdict: You clearly love writing code, but you definitely don't love organizing it."
    ]
    
    return (
        f"🔥 ARCHETYPE: {archetype}\n\n"
        f"{bio_critique}\n\n"
        f"{repo_callout}. {desc_jab} {lang_jab}{commit_jab}\n\n"
        f"{random.choice(verdicts)}"
    )


def _generate_rescue(
    profile: Dict[str, Any],
    repos: List[Dict[str, Any]],
    roast: str,
    events: Optional[List[Dict[str, Any]]] = None
) -> str:
    """Generate 3 intensely specific, diagnostic, actionable rescue steps tailored to this user."""
    f = _extract_profile_features(profile, repos, events)
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
            "1. ⚡ 10-MIN QUICK WIN: Direct Your Developer Audience\n"
            f"   You have {followers:,} developers viewing your profile daily.\n"
            "   👉 Add a direct link to your official documentation, newsletter, or project hub in your profile website/bio.\n"
            "   Convert your immense inbound GitHub traffic into an owned distribution channel."
        )
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Architectural Governance for '{top_repo}'\n"
            f"   With {top_star_count:,} stars, '{top_repo}' is essential community infrastructure:\n"
            "   • Add an `ARCHITECTURE.md` explaining system invariants for prospective contributors.\n"
            "   • Set up automated PR triage bots and GitHub Discussion categories to prevent issue burnout.\n"
            "   • Configure automated benchmarking CI workflows to catch performance regressions."
        )
        career_step = (
            "3. 🚀 CAREER LEVERAGE: Formalize Sustainability & Foundation Status\n"
            "   You are operating at ecosystem-scale. Protect maintainer longevity:\n"
            "   👉 Establish GitHub Sponsors or Open Collective funding, define a `SECURITY.md` advisory process, and recruit trusted co-maintainers to avoid bus-factor risk."
        )
        return f"{quick_win}\n\n{weekend_proj}\n\n{career_step}"

    # 1. QUICK WIN (10-Minute Fix): Address their single biggest cosmetic vulnerability
    if not bio or len(bio) < 15:
        suggested_bio = f"Building high-performance {primary_lang} systems & tools | Maintainer of @{top_repo} | Open to software engineering roles"
        quick_win = (
            "1. ⚡ 10-MIN QUICK WIN: Fix Your Missing Identity\n"
            "   Your bio is currently empty or minimal. Copy-paste this tailored bio right now into your profile settings:\n"
            f"   👉 \"{suggested_bio}\"\n"
            "   Recruiters filter out zero-bio profiles in under 3 seconds. Give them an instant value proposition."
        )
    elif empty_descs >= 2:
        target_repo = second_repo or top_repo
        quick_win = (
            "1. ⚡ 10-MIN QUICK WIN: Stop the Invisible Repo Epidemic\n"
            f"   {empty_descs} of your repos have zero description. Go to '{top_repo}' and '{target_repo}' right now.\n"
            f"   👉 Click the ⚙️ icon next to 'About' and write a 1-sentence summary (e.g. 'A lightweight {primary_lang} service for data processing with zero runtime dependencies.').\n"
            "   Without descriptions, your repos are completely invisible to GitHub search."
        )
    elif not f["location"] or not f["blog"]:
        quick_win = (
            "1. ⚡ 10-MIN QUICK WIN: Turn On Discovery Signals\n"
            "   You haven't listed a Location or personal link. Tech recruiters filter candidate pools by region (e.g., 'San Francisco', 'Remote', 'London').\n"
            "   👉 Fill out your city/region and link your LinkedIn or portfolio URL to double your recruiter contact rate."
        )
    else:
        quick_win = (
            "1. ⚡ 10-MIN QUICK WIN: Pin Your Strongest Assets\n"
            "   Don't let GitHub randomly display your oldest repos. Go to your profile overview and customize your 'Pinned Repositories'.\n"
            f"   👉 Pin '{top_repo}' first, followed by your 2 cleanest {primary_lang} repositories. Hide any forks or unfinished experiments."
        )

    # 2. WEEKEND PROJECT (1-2 Days): Address their project portfolio / code quality gap
    if len(tutorial_repos) >= 1:
        tut_name = tutorial_repos[0]
        quickstart_command = "npm install && npm start" if primary_lang.lower() in ("javascript", "typescript") else "pip install -r requirements.txt && python main.py"
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Graduate '{tut_name}' from Tutorial Hell\n"
            "   Turn this beginner project into a portfolio-grade asset recruiters respect:\n"
            "   • Add real authentication (OAuth / JWT) and a persistent database (PostgreSQL / Supabase).\n"
            "   • Deploy it live to a free cloud host (Vercel, Render, or Railway) and put the live URL at the top of the README.\n"
            f"   • Add a 3-step Quickstart block (`{quickstart_command}`)."
        )
    elif fork_count >= 3 and (fork_count / max(1, total_repos)) >= 0.4:
        weekend_proj = (
            "2. 🎯 WEEKEND PROJECT: Ship 1 Authentic Standalone Project\n"
            f"   Over 40% of your repos are forks. Unpin them and build one original application from scratch in {primary_lang}.\n"
            "   • Pick a specific real-world problem (e.g., a CLI tool, API wrapper, or data dashboard).\n"
            "   • Write clean commits from `git init` to `v1.0.0`.\n"
            "   • Include an animated GIF in the README showing the tool in action."
        )
    elif top_star_count > 50:
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: Open-Source Governance for '{top_repo}'\n"
            f"   '{top_repo}' already has {top_star_count} stars! Elevate it into a production-grade open source project:\n"
            "   • Add a `CONTRIBUTING.md` guide and an Issue/PR template (`.github/ISSUE_TEMPLATE/`).\n"
            "   • Set up GitHub Actions CI to run automated unit tests on every pull request.\n"
            "   • Create a formal GitHub Release (`v1.0.0`) with release notes."
        )
    else:
        weekend_proj = (
            f"2. 🎯 WEEKEND PROJECT: The README Glow-Up for '{top_repo}'\n"
            "   80% of hiring managers decide whether to interview based on the top repository's README alone:\n"
            f"   • Add a 5-second screen recording / GIF showing '{top_repo}' working before any walls of text.\n"
            "   • Add tech stack shields/badges (e.g., Python 3.12, Fast, License MIT).\n"
            "   • Include an Architecture section explaining WHY you made specific technical decisions."
        )

    # 3. CAREER LEVERAGE (Next 30 Days): Long-term compounding growth
    if not f["has_recent_activity"]:
        career_step = (
            "3. 🚀 CAREER LEVERAGE: Re-ignite Your Public Heartbeat\n"
            "   Your public activity graph is flatlining. Recruiters look for consistency, not 1-day commit spikes.\n"
            f"   👉 Pick '{top_repo}', update outdated dependencies, write 3 unit tests, and commit twice a week.\n"
            "   Consistent green squares signal reliability and momentum."
        )
    elif len(f["all_langs"]) >= 4:
        career_step = (
            f"3. 🚀 CAREER LEVERAGE: Establish a Coherent {primary_lang} Senior Narrative\n"
            f"   You have repos scattered across {', '.join(f['all_langs'][:4])}. Generalists get passed over for specialist roles.\n"
            f"   👉 Position yourself as an authority in {primary_lang}. Focus your next 2 projects entirely on {primary_lang} ecosystem depth (performance tuning, concurrency, or distributed systems)."
        )
    else:
        career_step = (
            "3. 🚀 CAREER LEVERAGE: Ship 1 Public Pull Request to Upstream Open Source\n"
            "   You've proven you can write code in your own silo. The ultimate differentiator for senior engineering interviews is public collaboration.\n"
            f"   👉 Search GitHub for active {primary_lang} repos with the 'good first issue' label. Submit 1 clean, reviewed PR. Link that merged PR directly on your resume."
        )

    return f"{quick_win}\n\n{weekend_proj}\n\n{career_step}"


def _parse_gh_datetime(value: str) -> Optional[datetime]:
    """Parse a GitHub ISO-8601 timestamp; None when unparseable."""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


def _diagnose_mental_stability(
    events: Optional[List[Dict[str, Any]]],
    repos: Optional[List[Dict[str, Any]]] = None,
    verified_commits: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Diagnose commit psychology from VERIFIED telemetry only.

    Ground truth hierarchy: repo size/count from the API (repos always list
    real code) beats the events feed (which only embeds commit summaries for
    recent pushes and is empty for quiet weeks). We NEVER claim "no code
    pushed" when the account owns repos with actual code in them.
    """
    repos = [r for r in (repos or []) if isinstance(r, dict)]
    verified_commits = [c for c in (verified_commits or []) if isinstance(c, dict)]

    repo_count = len(repos)
    total_kb = sum(int(r.get("size", 0) or 0) for r in repos)
    has_real_code = repo_count > 0 and total_kb > 0
    code_scale = f"{total_kb // 1024}MB" if total_kb >= 1024 else f"{total_kb}KB"

    # --- commit signals: events feed + verified /commits telemetry ---
    event_msgs: List[str] = []
    push_refs_main = 0
    total_pushes = 0
    event_hours: List[int] = []
    for event in events or []:
        if not isinstance(event, dict) or event.get("type") != "PushEvent":
            continue
        total_pushes += 1
        payload = event.get("payload", {}) or {}
        if (payload.get("ref") or "") == "refs/heads/main":
            push_refs_main += 1
        dt = _parse_gh_datetime(event.get("created_at", ""))
        if dt is not None:
            event_hours.append(dt.hour)
        for c in payload.get("commits", []) or []:
            msg = (c.get("message", "") or "") if isinstance(c, dict) else ""
            if msg:
                event_msgs.append(msg)

    verified_msgs = [c.get("message", "") for c in verified_commits if c.get("message")]
    verified_hours = [
        dt.hour
        for dt in (_parse_gh_datetime(c.get("date", "")) for c in verified_commits)
        if dt is not None
    ]
    all_msgs = event_msgs + verified_msgs
    all_hours = event_hours + verified_hours
    total = len(all_msgs)

    swear_words = ["fuck", "shit", "damn", "crap", "hell", "bitch", "ass"]
    vague_words = {"fix", "update", "wip", "test", "stuff", "changes", "done", "asdf"}
    lowered = [m.lower() for m in all_msgs]
    swear_count = sum(1 for m in lowered if any(w in m for w in swear_words))
    vague_count = sum(1 for m in lowered if m.strip() in vague_words or len(m.strip()) < 10)
    late_night = sum(1 for h in all_hours if h < 6)

    if swear_count > 0:
        return (
            "Diagnosis: Terminal Rage Syndrome"
            f"({swear_count} profanity-laced commit(s) in verified history. "
            "Have you tried taking a walk?)"
        )

    if repo_count >= 15 and total_kb > 50000:
        return (
            "Diagnosis: Serial Project Sprawler"
            f"({repo_count} repositories holding {code_scale} of real code, "
            "yet new repos keep appearing instead of documentation.)"
        )

    if total > 0 and late_night > total * 0.4:
        return (
            "Diagnosis: Vampire Coder"
            f"({late_night} of the last {total} verified commits landed "
            "between midnight and 6 AM. The sun misses you.)"
        )

    if total_pushes >= 2 and push_refs_main == total_pushes:
        return (
            "Diagnosis: Main-Branch Cowboy"
            f"(all {total_pushes} recent pushes went straight to main — "
            "feature branches are apparently decorative.)"
        )

    if total > 0 and vague_count > total * 0.5:
        example = next(
            (m for m in all_msgs if m.strip().lower() in vague_words), "fix"
        )
        return (
            "Diagnosis: Commit Message Amnesia"
            f"({vague_count} of {total} verified commits are just "
            f"'{example.strip()}'. What are you hiding?)"
        )

    if total == 0 and not has_real_code and repo_count == 0:
        return "Diagnosis: Blank Canvas (No public repos and no recent pushes — beautifully mysterious, totally unhirable.)"

    if total == 0 and has_real_code:
        return (
            "Diagnosis: Silent Professional"
            f"({repo_count} repos, {code_scale} of code on record, but zero "
            "commit chatter in the recent window. Suspiciously well-adjusted.)"
        )

    if total == 0:
        return "Diagnosis: Catatonic (No recent commit telemetry found)"

    return "Diagnosis: Tragically Stable (Your commit history is painfully professional and boring.)"

_AI_PAT = re.compile(r"\b(ai|artificial intelligence|machine learning|deep learning|llms?|pytorch|tensorflow|computer vision|nlp|data scien\w*|neural nets?)\b")
_DEVOPS_PAT = re.compile(r"\b(devops|cloud(?!flare)|kubernetes|k8s|docker|terraform|aws|azure|gcp|ci\s*/\s*cd|site reliability|\bsre\b)\b")
_SYSTEMS_PAT = re.compile(r"\b(rust|golang|\bgo\b|c\+\+|embedded|kernels?|systems programming|low.level)\b")
_FULLSTACK_PAT = re.compile(r"\b(full.?stack|backend|microservices?|rest apis?)\b")
_WEB3_PAT = re.compile(r"\b(web3|solidity|blockchain|smart contracts?|defi|nfts?)\b")
_BACKEND_LANGS = {"python", "go", "rust", "java", "php", "ruby", "c#", "c++", "kotlin", "swift", "scala"}
_FRONTEND_LANGS = {"html", "css", "javascript"}
_INFRA_MARKERS = ("dockerfile", "docker", "kubernetes", "k8s", "terraform", "github actions", "ci/cd", "pytest", "jest", "unittest", "coverage", "travis", "circleci")
_DB_MARKERS = ("postgres", "mysql", "mongo", "sqlite", "database", "prisma", "redis", "sqlalchemy", "supabase")
_ML_FRAMEWORKS = ("torch", "tensorflow", "sklearn", "scikit", "transformers", "keras", "jax")


def _skeleton_evidence(
    repo_files: Optional[Dict[str, List[str]]],
) -> Dict[str, Any]:
    """Distill recursive file skeletons into verifiable evidence flags.

    Scans lowercased repo paths for Dockerfiles, CI workflows, test suites,
    backend code, database artifacts and ML model files. Pure basename /
    substring matching with strict test-file rules ("latest.md" must NOT
    count as a test — looking at you, substring matching).
    """
    paths: List[str] = []
    if isinstance(repo_files, dict):
        for file_list in repo_files.values():
            if isinstance(file_list, list):
                paths.extend(
                    p.lower() for p in file_list if isinstance(p, str)
                )

    def base(p: str) -> str:
        return p.rsplit("/", 1)[-1]

    docker, ci, tests, backend, db, models = [], [], [], [], [], []
    for p in paths:
        b = base(p)
        if b in ("dockerfile", "containerfile") or b.startswith("docker-compose") or b == "docker-compose.yml" or b == "docker-compose.yaml":
            docker.append(p)
        if p.startswith(".github/workflows/") or b in ("travis.yml", ".travis.yml", "circle.yml", "config.yml", "gitlab-ci.yml", "jenkinsfile", "azure-pipelines.yml"):
            ci.append(p)
        if (b.startswith("test_") or b.startswith("test.") or b.endswith(("_test.py", "_test.js", "_test.ts", "_test.go", "_test.rb"))
                or ".spec." in b or b.startswith("spec_")
                or "/tests/" in p or p.startswith("tests/")):
            tests.append(p)
        if b.endswith((".py", ".go", ".rs", ".java", ".php", ".rb", ".js", ".ts")) and "test" not in b and "spec" not in b:
            backend.append(p)
        if b.endswith((".sql",)) or "schema.prisma" in b or "/migrations/" in p or "/models/" in p or "alembic" in p:
            db.append(p)
        if b.endswith((".pt", ".pth", ".onnx", ".safetensors", ".h5", ".ckpt", ".bin")) or b.endswith(".ipynb"):
            models.append(p)

    return {
        "repos_scanned": len(repo_files) if isinstance(repo_files, dict) else 0,
        "docker": sorted(set(docker))[:3],
        "ci": sorted(set(ci))[:3],
        "tests": sorted(set(tests))[:3],
        "backend": sorted(set(backend))[:3],
        "db": sorted(set(db))[:3],
        "models": sorted(set(models))[:3],
    }


def audit_resume_vs_reality(
    profile_readme: str = "",
    bio: str = "",
    repos: Optional[List[Dict[str, Any]]] = None,
    repo_languages: Optional[Dict[str, int]] = None,
    repo_files: Optional[Dict[str, List[str]]] = None,
    resume_label: str = "profile README",
) -> Dict[str, Any]:
    """Cross-reference resume claims against Git telemetry.

    Deterministic keyword + telemetry heuristics only (no RAG/vector DB).
    `repos` should be true project repos (profile repo already excluded).
    `repo_files` maps repo name → recursive lowercased paths and turns
    "0 Dockerfiles" style verdicts from name-guessing into verified fact.
    Returns {"vibe_ratio", "has_profile_readme", "headline",
    "discrepancies": [{"claim", "reality", "severity"}], "recruiter_verdict"}.
    Severity is HIGH_VIBE (claim, zero evidence), MEDIUM_VIBE (partial) or
    VERIFIED (receipts attached).
    """
    text = ((profile_readme or "") + "\n" + (bio or "")).lower()
    has_readme = bool((profile_readme or "").strip())
    projects = [r for r in (repos or []) if isinstance(r, dict)]

    total_kb = sum(int(r.get("size", 0) or 0) for r in projects)
    has_code = total_kb > 0

    lang_bytes: Dict[str, int] = {
        str(k): int(v or 0) for k, v in (repo_languages or {}).items() if v
    }
    if sum(lang_bytes.values()) <= 0:
        # Fall back to primary-language repo counts across projects
        for r in projects:
            lang = ((r.get("language") or "").strip())
            if lang:
                lang_bytes[lang] = lang_bytes.get(lang, 0) + 1000
    lang_total = sum(lang_bytes.values())

    def share(*names: str) -> float:
        if lang_total <= 0:
            return 0.0
        wanted = {n.lower() for n in names}
        return sum(b for lang, b in lang_bytes.items() if lang.lower() in wanted) / lang_total

    frontend_share = share("html", "css", "javascript")
    python_share = share("python")
    systems_share = share("rust", "go", "c", "c++", "c#", "zig")
    backend_share = share(*_BACKEND_LANGS)

    blob = "\n".join(
        ((r.get("name") or "") + " " + (r.get("description") or "") + " " +
         " ".join(r.get("topics") or [] if isinstance(r.get("topics"), list) else []))
        for r in projects
    ).lower()
    infra_hits = [k for k in _INFRA_MARKERS if k in blob]
    db_hits = [k for k in _DB_MARKERS if k in blob]
    ml_fw = [k for k in _ML_FRAMEWORKS if k in blob]
    skel = _skeleton_evidence(repo_files)
    skel_repos = skel["repos_scanned"]

    def _cite(items: List[str], kind: str) -> str:
        shown = ", ".join(items[:2])
        extra = "" if len(items) <= 2 else " (+%d more)" % (len(items) - 2)
        return "%s (%s%s)" % (kind, shown, extra)

    findings: List[Dict[str, str]] = []

    def add(claim: str, reality: str, severity: str) -> None:
        findings.append({"claim": claim, "reality": reality, "severity": severity})

    # 1. AI / ML
    if _AI_PAT.search(text):
        if python_share >= 0.3 and (ml_fw or skel["models"]):
            proof = _cite(skel["models"], "model artifacts") if skel["models"] else ", ".join(ml_fw[:2])
            add("AI / ML Engineer",
                "VERIFIED-ish: %.0f%% Python with %s in the codebase. Touch grass anyway." % (100 * python_share, proof),
                "VERIFIED")
        elif python_share >= 0.3:
            add("AI / ML Engineer",
                "%.0f%% Python but zero PyTorch/TensorFlow anywhere — currently a sklearn-curious script kiddie." % (100 * python_share),
                "MEDIUM_VIBE")
        else:
            add("AI / ML Engineer",
                "%d%% frontend HTML/CSS/JS vibe templates; zero model architectures, zero PyTorch." % round(100 * frontend_share),
                "HIGH_VIBE")

    # 2. DevOps / Cloud — file skeletons turn this from guessing into fact
    if _DEVOPS_PAT.search(text):
        proof_files = skel["docker"] + skel["ci"]
        if skel_repos and (skel["docker"] and skel["ci"]):
            add("Cloud / DevOps Architect",
                "VERIFIED-ish: %s plus %s across scanned repos. PagerDuty fears you." % (
                    _cite(skel["docker"], "Dockerfile"), _cite(skel["ci"], "CI")),
                "VERIFIED")
        elif skel_repos and proof_files:
            add("Cloud / DevOps Architect",
                "Partial receipts: %s, but the other half of the pipeline is missing." % _cite(proof_files, "infra files"),
                "MEDIUM_VIBE")
        elif skel_repos:
            add("Cloud / DevOps Architect",
                "Scanned %d repo file trees: 0 Dockerfiles, 0 CI workflows. The cloud is just someone else's laptop to you." % skel_repos,
                "HIGH_VIBE")
        elif len(infra_hits) >= 2:
            add("Cloud / DevOps Architect",
                "VERIFIED-ish: %s found across scanned repos. PagerDuty fears you." % ", ".join(infra_hits[:3]),
                "VERIFIED")
        elif len(infra_hits) == 1:
            add("Cloud / DevOps Architect",
                "Exactly one infra signal (%s) across all repos. An architect with one brick." % infra_hits[0],
                "MEDIUM_VIBE")
        else:
            add("Cloud / DevOps Architect",
                "0 Dockerfiles or CI/CD pipelines found across all repos. The cloud is just someone else's laptop to you.",
                "HIGH_VIBE")

    # 3. Full-stack
    if _FULLSTACK_PAT.search(text):
        db_evidence = skel["db"] or db_hits
        code_evidence = bool(skel["backend"]) or backend_share >= 0.2
        if code_evidence and db_evidence:
            proof = _cite(skel["db"], "db models") if skel["db"] else db_hits[0]
            add("Full-Stack Developer",
                "VERIFIED-ish: backend code on record plus %s. The stack is, in fact, full." % proof,
                "VERIFIED")
        elif code_evidence:
            add("Full-Stack Developer",
                "Backend bytes exist but zero database models on record. Full-stack minus the stack's bottom half.",
                "MEDIUM_VIBE")
        else:
            add("Full-Stack Developer",
                "Pure client-side scripts; zero server or database models on record.",
                "HIGH_VIBE")

    # 4. Systems
    if _SYSTEMS_PAT.search(text):
        if systems_share > 0:
            add("Systems Engineer",
                "VERIFIED-ish: %.0f%% systems-language bytes. Valgrind sends regards." % (100 * systems_share),
                "VERIFIED")
        else:
            add("Systems Engineer",
                "0 bytes of Rust or Go in public repos. The closest thing to systems programming here is CSS grid.",
                "HIGH_VIBE")

    # 5. Web3
    if _WEB3_PAT.search(text):
        if share("solidity") > 0:
            add("Web3 Builder",
                "VERIFIED-ish: Solidity bytes on-chain of evidence.",
                "VERIFIED")
        else:
            add("Web3 Builder",
                "0 Solidity, 0 contracts. Your bags are purely emotional.",
                "HIGH_VIBE")

    claims = len(findings)
    verified = sum(1 for d in findings if d["severity"] == "VERIFIED")
    if claims:
        vibe = round(100 * (claims - verified) / claims)
    else:
        vibe = 15 if has_code else 50
    verifiable = 100 - vibe

    label = resume_label or "profile README"
    if vibe >= 60:
        verdict = ("Your %s writes checks your repositories cannot cash. "
                   "Recruiters read both — delete two adjectives or ship one backend." % label)
    elif vibe >= 30:
        verdict = ("Resume and reality mostly agree, but a few claims need receipts. "
                   "Pin the repo that proves the loudest bullet point.")
    else:
        verdict = ("Receipts attached. The resume and the repos tell the same story — "
                   "now go touch grass.")

    return {
        "vibe_ratio": "%d%% Vibe / %d%% Verifiable" % (vibe, verifiable),
        "has_profile_readme": has_readme,
        "headline": "Profile README Claims vs. Actual Git Reality",
        "discrepancies": findings[:5],
        "recruiter_verdict": verdict,
    }


def analyze_profile(
    profile_data: Dict[str, Any],
    repos_data: List[Dict[str, Any]],
    username: str,
    events_data: Optional[List[Dict[str, Any]]] = None,
    readme_content: str = "",
    repo_languages: Optional[Dict[str, int]] = None,
    verified_commits: Optional[List[Dict[str, str]]] = None,
    profile_readme: str = "",
    audit_languages: Optional[Dict[str, int]] = None,
    repo_files: Optional[Dict[str, List[str]]] = None,
    resume_label: str = "profile README",
) -> Dict[str, Any]:
    """Analyze a GitHub profile and generate all feedback components.

    Combines recruiter glance, deep personalized roast, and diagnostic rescue plan.

    Args:
        profile_data: Profile dictionary from GitHub client
        repos_data: List of repo dictionaries from GitHub client
        username: GitHub username being analyzed
        events_data: Optional list of recent event dictionaries
        verified_commits: Optional verified commits from /repos/{o}/{r}/commits
            (each {"message": str, "date": str}); grounds the psych-eval
        audit_languages: Optional cross-repo aggregated language bytes for
            the reality audit (falls back to repo_languages)
        repo_files: Optional repo name → recursive path list for the audit
        resume_label: Label used in verdict copy ("profile README"/"resume")

    Returns:
        Dictionary with all analysis components
    """
    from github_client import format_repo_summary, format_profile_summary
    profile_summary = format_profile_summary(profile_data)
    repo_summary = format_repo_summary(repos_data)

    top_repos = repo_summary.get("top_repos", [])

    # Separate the {username}/{username} profile repo from true code
    # projects so no component centers (or roasts) the profile README.
    handle = (profile_summary.get("username", "") or "").strip().lower()
    raw_projects = [
        r for r in (repos_data or [])
        if isinstance(r, dict)
        and (r.get("name", "") or "").strip().lower() != handle
    ] if handle else list(repos_data or [])
    project_top_repos = [
        r for r in top_repos
        if isinstance(r, dict)
        and (r.get("name", "") or "").strip().lower() != handle
    ] if handle else list(top_repos)

    # Generate each component with deep personalization
    recruiter_glance = _generate_recruiter_glance(profile_summary, project_top_repos, events=events_data)
    roast = _generate_roast(profile_summary, project_top_repos, events=events_data, readme_content=readme_content, repo_languages=repo_languages)
    rescue = _generate_rescue(profile_summary, project_top_repos, roast, events=events_data)
    psych_eval = _diagnose_mental_stability(
        events_data, repos=repos_data, verified_commits=verified_commits
    )
    raw_bio = ((profile_data or {}).get("bio") or "")
    if raw_bio == "No bio set":
        raw_bio = ""
    reality = audit_resume_vs_reality(
        profile_readme, raw_bio, raw_projects,
        audit_languages if audit_languages else repo_languages,
        repo_files=repo_files, resume_label=resume_label,
    )

    # Extract archetype for the leaderboard
    f = _extract_profile_features(profile_summary, project_top_repos, events=events_data)

    return {
        "status": "success",
        "username": username,
        "recruiter_glance": recruiter_glance,
        "roast": roast,
        "rescue": rescue,
        "psych_eval": psych_eval,
        "resume_vs_reality": reality,
        "archetype": f.get("archetype", "Developer"),
        "profile_data": profile_summary,
        "repo_data": repo_summary,
        # Additive battle telemetry (never breaks existing consumers)
        "total_size_kb": sum(
            int(r.get("size", 0) or 0)
            for r in (repos_data or [])
            if isinstance(r, dict)
        ),
        "recent_commits": [
            c.get("message", "")
            for c in (verified_commits or [])
            if isinstance(c, dict) and c.get("message")
        ][:10],
    }


_VAGUE_TOKENS = {"fix", "update", "wip", "test", "stuff", "changes", "done", "asdf"}
_SWEAR_TOKENS = ["fuck", "shit", "damn", "crap", "hell", "bitch", "ass"]


def _battle_metrics(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Compute verified, JSON-safe battle metrics from one analysis dict."""
    repo_data = analysis.get("repo_data", {}) or {}
    top = [r for r in (repo_data.get("top_repos", []) or []) if isinstance(r, dict)]
    now = datetime.utcnow()

    zero_star = sum(1 for r in top if (r.get("stars", 0) or 0) == 0)
    archived = sum(1 for r in top if r.get("archived"))
    stale = 0
    for r in top:
        dt = _parse_gh_datetime(r.get("last_push", ""))
        if dt is not None and (now - dt).days > 365:
            stale += 1

    msgs = [
        m for m in (analysis.get("recent_commits", []) or [])
        if isinstance(m, str) and m.strip()
    ]
    lowered = [m.lower() for m in msgs]
    vague = sum(
        1 for m in lowered if m.strip() in _VAGUE_TOKENS or len(m.strip()) < 10
    )
    profane = sum(1 for m in lowered if any(w in m for w in _SWEAR_TOKENS))

    return {
        "graveyard": zero_star + archived + stale,
        "zero_star": zero_star,
        "archived": archived,
        "stale": stale,
        "code_kb": int(analysis.get("total_size_kb", 0) or 0),
        "commits_seen": len(msgs),
        "unhinged": vague + profane,
        "vague": vague,
        "profane": profane,
    }


def compare_profiles(
    analysis1: Dict[str, Any], analysis2: Dict[str, Any]
) -> Dict[str, Any]:
    """Score two analyzed profiles head-to-head on verified telemetry.

    Rounds (lower-is-better unless noted):
      1. Graveyard Score — 0-star + archived + stale (>1yr) repos
      2. Code Volume — total repository size in KB (higher wins)
      3. Commit Hygiene — vague/profane messages in verified commits

    Returns {"winner", "loser", "verdict", "stats"} — all JSON-safe.
    The "winner" is the stronger engineer (survives the interview);
    the loser gets relegated to Jira tickets.
    """
    u1 = analysis1.get("username", "dev-1") or "dev-1"
    u2 = analysis2.get("username", "dev-2") or "dev-2"
    m1 = _battle_metrics(analysis1)
    m2 = _battle_metrics(analysis2)

    s1 = s2 = 0
    rounds = []

    def award(name: str, better: int) -> None:
        # better: 1 → u1 takes the round, -1 → u2, 0 → tie
        nonlocal s1, s2
        if better > 0:
            s1 += 1
        elif better < 0:
            s2 += 1
        rounds.append({"round": name, "winner": u1 if better > 0 else (u2 if better < 0 else "tie")})

    award("graveyard", (m2["graveyard"] > m1["graveyard"]) - (m1["graveyard"] > m2["graveyard"]))
    award("code_volume", (m1["code_kb"] > m2["code_kb"]) - (m2["code_kb"] > m1["code_kb"]))

    if m1["commits_seen"] == 0 and m2["commits_seen"] == 0:
        award("hygiene", 0)
        hygiene_note = "neither combatant left verifiable commit evidence"
    else:
        award("hygiene", (m2["unhinged"] > m1["unhinged"]) - (m1["unhinged"] > m2["unhinged"]))
        hygiene_note = (
            f"@{u1} has {m1['unhinged']} unhinged message(s) in "
            f"{m1['commits_seen']} verified commits vs "
            f"{m2['unhinged']} in {m2['commits_seen']} for @{u2}"
        )

    if s1 == s2:
        # Tiebreak on total stars across top repos (verified), then call it even
        stars1 = sum(int(r.get("stars", 0) or 0) for r in ((analysis1.get("repo_data", {}) or {}).get("top_repos", []) or []))
        stars2 = sum(int(r.get("stars", 0) or 0) for r in ((analysis2.get("repo_data", {}) or {}).get("top_repos", []) or []))
        if stars1 == stars2:
            return {
                "winner": "tie",
                "loser": "tie",
                "verdict": (
                    f"Dead heat. @{u1} and @{u2} are equally mid — "
                    "the interview panel falls asleep and both get"
                    "relegated to writing Jira tickets about Jira tickets."
                ),
                "stats": {"user1": {"username": u1, **m1}, "user2": {"username": u2, **m2}, "rounds": rounds, "score": {u1: s1, u2: s2}},
            }
        winner, loser = (u1, u2) if stars1 > stars2 else (u2, u1)
        deciding = f"a {max(stars1, stars2):,}-star haul breaks the tie"
    else:
        winner, loser = (u1, u2) if s1 > s2 else (u2, u1)
        deciding = f"a {max(s1, s2)}–{min(s1, s2)} round split"

    wm = m1 if winner == u1 else m2
    lm = m2 if winner == u1 else m1
    verdict = (
        f"@{winner} survives the technical interview with {wm['code_kb']:,}KB "
        f"of code against {lm['code_kb']:,}KB ({deciding}; {hygiene_note}). "
        f"@{loser} — with a graveyard score of {lm['graveyard']} — is hereby "
        "relegated to triaging Jira tickets about the legacy repo nobody will delete."
    )
    return {
        "winner": winner,
        "loser": loser,
        "verdict": verdict,
        "stats": {"user1": {"username": u1, **m1}, "user2": {"username": u2, **m2}, "rounds": rounds, "score": {u1: s1, u2: s2}},
    }