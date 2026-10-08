/**
 * Deep analysis and feedback generation for GitHub profiles.
 *
 * Uses deep heuristic profiling across 15+ profile signals (languages, repos,
 * stars, forks, commit cadence, bio, follower ratios, events) to generate:
 * - 30-second recruiter glance summary
 * - Witty, customized, razor-sharp humorous roast (no generic templates)
 * - Highly personalized, actionable, diagnostic rescue plan
 */

import { format_profile_summary, format_repo_summary } from "./githubClient.js";

const TUTORIAL_PATTERNS = [
  /(^|[-_])(todo|todolist|calculator|weather|counter|quiz|recipe|clock)([-_]|$)/i,
  /(^|[-_])(clone|netflix-clone|spotify-clone|amazon-clone|twitter-clone|instagram-clone)([-_]|$)/i,
  /(^|[-_])(first-contributions|leetcode|dsa-prep|interview-prep)([-_]|$)/i,
];

const LANGUAGE_HUMOR: Record<string, string[]> = {
  python: [
    "Python loyalist — where 80% of debugging is print statements and your virtualenv folder weighs more than the operating system.",
    "Python enthusiast — you refuse to write curly braces, yet your list comprehensions are completely unreadable.",
    "Python dev — you imported an ML library once and now your LinkedIn says 'AI Engineer'.",
  ],
  javascript: [
    "JavaScript/TypeScript maximalist — you've probably switched build tools 4 times this year and still haven't written a unit test.",
    "JS purist — `[1, 2] + [3, 4] === '1, 23, 4'` makes perfect sense to you.",
    "JavaScript dev — your `node_modules` folder has more files than the Library of Congress.",
  ],
  typescript: [
    "TypeScript devotee — writing 50 lines of complex utility types just to render a single button with zero runtime bugs (allegedly).",
    "TS architect — you spend more time wrestling with `any` than actually shipping features.",
    "TypeScript fan — trying to fix JavaScript by turning it into Java.",
  ],
  rust: [
    "Rust evangelist — fighting the borrow checker for 6 hours straight just to say your CLI tool is memory-safe.",
    "Rustacean — you rewrite everything in Rust, even when a bash script would do.",
    "Rust dev — if your code compiles on the first try, you assume there's a bug in the compiler.",
  ],
  "c++": [
    "C/C++ veteran — raw pointers, manual memory allocation, and segmentation faults are your idea of an adrenaline rush.",
    "C++ dev — your compile times are so long you've mastered 3 new hobbies.",
    "C++ programmer — holding on to legacy codebases like a badge of honor.",
  ],
  c: [
    "C purist — living so close to bare metal you can hear the electrons screaming. Where abstractions go to die.",
    "C programmer — `malloc` is your middle name, and memory leaks are your closest friends.",
  ],
  go: [
    "Go pragmatic — if err != nil { return nil, err } is tattooed on your forearm. Zero generics trauma.",
    "Go dev — writing boilerplate code like it's a religion.",
    "Golang fan — you love interfaces but secretly miss having a real type system.",
  ],
  java: [
    "Java enterprise architect — AbstractSingletonProxyFactoryBean energy. 14 layers of inheritance to print Hello World.",
    "Java dev — you consider 500MB of RAM a 'lightweight' microservice.",
    "Java veteran — waiting for the JVM to warm up since 1995.",
  ],
  "c#": [
    ".NET / C# builder — enterprise stability wrapped in Microsoft warmth. Probably has a Visual Studio license on company credit.",
    "C# dev — you're basically a Java developer who actually likes their IDE.",
  ],
  php: [
    "PHP soldier — still powering 75% of the internet while everyone else debates JavaScript frameworks.",
    "PHP dev — hiding the `.php` extensions so nobody knows what you're running.",
  ],
  html: [
    "Markup specialist — HTML and CSS are beautiful, but opening tags and flexbox alignment won't survive a systems design interview.",
    "HTML/CSS dev — you spend 4 hours centering a div and call it a day.",
  ],
  "jupyter notebook": [
    "Jupyter data scientist — code that runs exclusively on your local machine in out-of-order execution cells.",
    "Data Scientist — your git commits are just 50MB JSON blobs of cell output.",
  ],
  shell: [
    "Bash wizard — 500-line shell scripts with zero comments that run production deployments on a prayer.",
    "Shell script purist — who needs Python when you have `awk`, `sed`, and pure chaos?",
  ],
};

function randomChoice<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function safeGet(mapping: any, key: string, defaultVal: any = ""): any {
  if (!mapping || typeof mapping !== "object") return defaultVal;
  return mapping[key] !== undefined && mapping[key] !== null ? mapping[key] : defaultVal;
}

function formatLanguages(repos: any[], maxRepos: number = 15, maxLangs: number = 4): string {
  const languages: string[] = [];
  for (const repo of repos.slice(0, maxRepos)) {
    const lang = safeGet(repo, "primary_language");
    if (lang && lang !== "Unknown" && !languages.includes(lang)) {
      languages.push(lang);
    }
  }
  return languages.length > 0 ? languages.slice(0, maxLangs).join(", ") : "Various Technologies";
}

function extractProfileFeatures(
  profile: any,
  repos: any[],
  events: any[] | null = null,
  readme_content: string = "",
  repo_languages: Record<string, number> | null = null
): Record<string, any> {
  const username = String(safeGet(profile, "username", "")).toLowerCase();
  const name = String(safeGet(profile, "name", ""));
  let bio = String(safeGet(profile, "bio", "")).trim();
  if (bio === "No bio set") bio = "";

  const company = String(safeGet(profile, "company", "")).trim();
  const location = String(safeGet(profile, "location", "")).trim();
  const blog = String(safeGet(profile, "blog", "")).trim();
  const followers = Number(safeGet(profile, "followers", 0)) || 0;
  const following = Number(safeGet(profile, "following", 0)) || 0;
  const public_repos = Number(safeGet(profile, "public_repos", repos.length)) || repos.length;
  const created_at = String(safeGet(profile, "created_at", ""));

  let account_age_years = 1;
  if (created_at) {
    try {
      const created_year = parseInt(created_at.slice(0, 4), 10);
      if (!isNaN(created_year)) {
        account_age_years = Math.max(1, 2026 - created_year);
      }
    } catch {}
  }

  const fork_count = repos.filter((r) => r?.is_fork).length;
  const total_stars = repos.reduce((sum, r) => sum + (Number(r?.stars) || 0), 0);
  const empty_desc_count = repos.filter(
    (r) => !r?.description || r?.description === "No description"
  ).length;

  const tutorial_repos: string[] = [];
  for (const r of repos) {
    const r_name = String(r?.name || "").toLowerCase();
    if (TUTORIAL_PATTERNS.some((pat) => pat.test(r_name))) {
      tutorial_repos.push(r.name);
    }
  }

  const lang_counts: Record<string, number> = {};
  for (const r of repos) {
    const l = r?.primary_language;
    if (l && l !== "Unknown") {
      lang_counts[l] = (lang_counts[l] || 0) + 1;
    }
  }
  const sorted_langs = Object.entries(lang_counts).sort((a, b) => b[1] - a[1]);
  const primary_lang = sorted_langs.length > 0 ? sorted_langs[0][0] : "Code";

  const sorted_by_stars = [...repos].sort((a, b) => (Number(b?.stars) || 0) - (Number(a?.stars) || 0));
  const top_star_repo = sorted_by_stars[0] || {};
  const top_star_count = Number(top_star_repo?.stars) || 0;
  const top_repo_name = top_star_repo?.name || (repos[0]?.name ? repos[0].name : "main-project");
  const second_repo_name = sorted_by_stars.length > 1 ? sorted_by_stars[1]?.name : null;

  const recent_commits: string[] = [];
  let has_recent_activity = false;
  if (Array.isArray(events)) {
    has_recent_activity = events.length > 0;
    for (const ev of events) {
      if (ev?.type === "PushEvent") {
        const payload = ev.payload || {};
        const commits = payload.commits || [];
        if (Array.isArray(commits)) {
          for (const c of commits) {
            const msg = (c?.message || "").trim().split("\n")[0];
            if (msg) recent_commits.push(msg);
          }
        }
      }
    }
  }

  let archetype = "The Generalist Builder";
  if (followers > 20000 || top_star_count > 5000) {
    archetype = randomChoice(["The Open-Source Titan", "The Tech Deity", "The 10x Engineer Personified"]);
  } else if (public_repos <= 1) {
    archetype = randomChoice(["The Digital Ghost", "The Stealth Operative", "The Empty Canvas"]);
  } else if (repos.length > 0 && fork_count / Math.max(1, repos.length) >= 0.5) {
    archetype = randomChoice(["The Fork Tourist", "The Cloner", "The Open-Source Spectator"]);
  } else if (tutorial_repos.length >= 2) {
    archetype = randomChoice([
      "The Tutorial Island Castaway",
      "The Bootcamp Graduate",
      "The 'To-Do App' Connoisseur",
    ]);
  } else if (following > 150 && following > followers * 3) {
    archetype = randomChoice([
      "The Follow-For-Follow Optimist",
      "The Networker, Not Coder",
      "The Reply-Guy Engineer",
    ]);
  } else if (repos.length >= 8 && total_stars <= 2) {
    archetype = randomChoice([
      "The Side-Quest Graveyard Keeper",
      "The Serial Project Abandoner",
      "The 90%-Done Architect",
      "The Domain Name Hoarder",
    ]);
  } else if (top_star_count >= 100 && total_stars - top_star_count < top_star_count * 0.15) {
    archetype = randomChoice([
      "The One-Hit Wonder",
      "The Accidental Viral Repo Owner",
      "The Atlas Holding The World",
    ]);
  } else if (sorted_langs.length >= 4 && sorted_langs.every(([_, count]) => count <= 2)) {
    archetype = randomChoice([
      "The Shiny Object Framework Hopper",
      "The 'Hello World' Polyglot",
      "The Technology Tourist",
    ]);
  } else if (!bio && !company && !location && repos.length >= 3) {
    archetype = randomChoice([
      "The Unlicensed Secret Agent",
      "The Anonymous Committer",
      "The Witness Protection Program Dev",
    ]);
  } else if (["c", "c++", "rust"].includes(primary_lang.toLowerCase())) {
    archetype = randomChoice([
      "The Low-Level Memory Gladiator",
      "The Borrow-Checker Masochist",
      "The Segfault Survivor",
    ]);
  } else if (["python", "jupyter notebook"].includes(primary_lang.toLowerCase())) {
    archetype = randomChoice([
      "The AI/Data Alchemist",
      "The Standard Library Devotee",
      "The Indentation Purist",
    ]);
  } else if (["javascript", "typescript"].includes(primary_lang.toLowerCase())) {
    archetype = randomChoice([
      "The Full-Stack Maximalist",
      "The Node_Modules Hoarder",
      "The 'I Could Build This In React' Guy",
    ]);
  }

  return {
    username,
    name,
    bio,
    company,
    location,
    blog,
    followers,
    following,
    public_repos,
    account_age_years,
    fork_count,
    total_stars,
    empty_desc_count,
    tutorial_repos,
    primary_lang,
    all_langs: sorted_langs.map(([l]) => l),
    top_repo_name,
    top_star_count,
    top_repo: top_star_repo,
    second_repo_name,
    recent_commits: recent_commits.slice(0, 5),
    has_recent_activity,
    archetype,
    repos,
    readme_content,
    repo_languages,
  };
}

function generateRecruiterGlance(
  profile: any,
  repos: any[],
  events: any[] | null = null
): string {
  const f = extractProfileFeatures(profile, repos, events);
  const lang_summary = formatLanguages(repos);
  const followers = f.followers;
  const repos_cnt = f.public_repos;
  const archetype = f.archetype;
  const years = f.account_age_years;

  const activity_status = f.has_recent_activity
    ? "Active commit cadence"
    : "Low recent public telemetry";
  const social_proof =
    f.top_star_count > 100
      ? `${f.top_star_count.toLocaleString()}★ on '${f.top_repo_name}'`
      : `${f.total_stars} total stars across ${repos_cnt} repos`;

  return [
    `• Profile Vibe : ${archetype} (${years}y footprint on GitHub)`,
    `• Core Stack   : ${lang_summary} | ${social_proof}`,
    `• Recruiter Read: ${followers.toLocaleString()} followers | ${repos_cnt} public projects | ${activity_status}`,
  ].join("\n");
}

function generateRoast(
  profile: any,
  repos: any[],
  events: any[] | null = null,
  readme_content: string = "",
  repo_languages: Record<string, number> | null = null
): string {
  const f = extractProfileFeatures(profile, repos, events, readme_content, repo_languages);
  const u = f.username;
  const archetype = f.archetype;
  const bio = f.bio;
  const followers = f.followers;
  const following = f.following;
  const total_repos = f.public_repos;
  const top_repo = f.top_repo_name;
  const second_repo = f.second_repo_name;
  const primary_lang = f.primary_lang;
  const total_stars = f.total_stars;
  const fork_count = f.fork_count;
  const commits = f.recent_commits;
  const tutorial_repos = f.tutorial_repos;
  const empty_descs = f.empty_desc_count;

  // High Follower / Tech Deity
  if (followers > 15000 || (total_stars > 10000 && followers > 5000)) {
    const handle_text = u ? `@${u}` : "This user";
    const bio_jab =
      !bio || bio.length < 20
        ? `Yet your bio is '${bio || "completely non-existent"}'. When you're this famous, apparently punctuation and self-introductions are beneath you.`
        : `Your bio is '${bio}', but let's be honest: nobody is reading your bio when they're busy cloning '${top_repo}'.`;
    return [
      `👑 ARCHETYPE: ${archetype}\n`,
      `${handle_text} has ${followers.toLocaleString()} developers watching every git push like a sold-out stadium crowd. `,
      `Your repository '${top_repo}' has ${f.top_star_count.toLocaleString()} stars—which is more stars than most junior engineers will see in three lifetimes. `,
      `${bio_jab}\n`,
      "Recruiters probably don't even send you InMails; they send handwritten letters via courier.",
      "The rest of GitHub is fighting for a 10-star side project while you commit directly to main like an ancient deity who doesn't believe in code review.",
    ].join("\n");
  }

  // Digital Ghost
  if (total_repos <= 1) {
    return [
      `👻 ARCHETYPE: ${archetype}\n`,
      `@${u}'s GitHub profile is cleaner than a brand-new MacBook fresh out of the shrink-wrap. `,
      `You have ${total_repos} public repository. Either you are an elite cybersecurity ghost working for an intelligence agency, `,
      "or your entire software engineering journey lives on an unbacked-up desktop folder named 'new_folder_final_v2'.\n",
      "Recruiters looking at this profile aren't deciding whether to hire you; they're wondering if you've discovered `git push` yet.",
      "Give the world a sign of life, even if it's just an unformatted markdown file.",
    ].join("\n");
  }

  // Fork Hoarder
  if (total_repos >= 3 && fork_count / Math.max(1, repos.length) >= 0.5) {
    const fork_example = repos.filter((r) => r?.is_fork).map((r) => r.name);
    const sample_fork = fork_example[0] || "famous-library";
    const roasts = [
      `🍴 ARCHETYPE: ${archetype}\n\nYou've got ${total_repos} repositories, but ${fork_count} of them are literal forks! Clicking the 'Fork' button on '${sample_fork}' does not make you an open-source contributor, chief—that's digital hoarder behavior. You're collecting repositories like unopened browser tabs you promise you'll read over the weekend.\n\nRecruiters want to see what YOU built, not a museum tour of repositories other engineers wrote while you watched.`,
      `🍴 ARCHETYPE: ${archetype}\n\nWith ${fork_count} forks out of ${total_repos} repos, your GitHub profile looks less like a developer portfolio and more like a mirror site for '${sample_fork}'. It's great that you know how the 'Fork' button works, but at some point you actually have to write your own code.\n\nStop treating GitHub like a Pinterest board of code you'll never read.`,
    ];
    return randomChoice(roasts);
  }

  // Tutorial Island
  if (tutorial_repos.length >= 2) {
    const tut_list = tutorial_repos.slice(0, 3).map((t) => `'${t}'`).join(", ");
    const roasts = [
      `🏝️ ARCHETYPE: ${archetype}\n\nWe took one look at your repository lineup: ${tut_list}. Congratulations on completing every YouTube tutorial from 2022! You are one 'Weather App' away from an honorary Udemy certificate, but the software industry is still waiting for your debut.\n\nBuilding a todo app with local storage is a rite of passage, but shipping three of them is a hostage situation. Break out of the tutorial sandbox before you end up cloning Twitter for the fourth time.`,
      `🏝️ ARCHETYPE: ${archetype}\n\nAh yes, the holy trinity: ${tut_list}. Your profile is a monument to Codecademy modules and 12-hour freeCodeCamp videos. But learning how to write 'Hello World' in 5 different frameworks isn't exactly engineering.\n\nTime to close the guided tutorials and try building something without a safety net.`,
    ];
    return randomChoice(roasts);
  }

  // Follow-for-Follow
  if (following > 150 && following > followers * 3) {
    return [
      `🤝 ARCHETYPE: ${archetype}\n`,
      `Following ${following.toLocaleString()} developers with only ${followers} following you back? `,
      "Bro, this is GitHub, not a 2015 Instagram follow-back train. ",
      `Those ${following.toLocaleString()} engineers aren't going to star your empty repositories out of mutual respect.\n`,
      `Meanwhile, your primary language is ${primary_lang}, and '${top_repo}' is sitting there waiting for inbound traffic that isn't coming. `,
      "Stop playing community manager and commit some code.",
    ].join("\n");
  }

  // One-Hit Wonder
  if (f.top_star_count >= 30 && total_stars - f.top_star_count < 10) {
    const roasts = [
      `🎸 ARCHETYPE: ${archetype}\n\nYour entire developer identity is carrying '${top_repo}' on its back like Atlas holding the globe. That project has ${f.top_star_count} stars, while the rest of your ${total_repos - 1} repositories look like failed experimental solo albums that got zero radio play.\n\nIf someone deletes '${top_repo}', your profile immediately defaults back to a blank slate. Diversify your portfolio before the hype fades!`,
      `🎸 ARCHETYPE: ${archetype}\n\nYou really hit the jackpot with '${top_repo}', didn't you? ${f.top_star_count} stars! It's a shame your other ${total_repos - 1} repos have a combined star count lower than the number of times you've refreshed your notifications.\n\nYou're one deleted repository away from being totally irrelevant again.`,
    ];
    return randomChoice(roasts);
  }

  // General Tailored Roast
  const lang_jokes = LANGUAGE_HUMOR[primary_lang.toLowerCase()] || [
    `${primary_lang} enthusiast — doing your best to make compilers happy.`,
  ];
  const lang_jab = randomChoice(lang_jokes);

  let bio_critique: string;
  if (!bio) {
    bio_critique = randomChoice([
      `${total_repos} repositories and not a single sentence in the bio. You treat your developer identity like an FBI classified dossier.`,
      "Your bio is as empty as a swallowed exception. Give us something to work with here!",
    ]);
  } else if (bio.length < 25) {
    bio_critique = `Your bio is literally '${bio}'—which reads like a git commit message someone typed with their eyes closed.`;
  } else if (/(passionate|enthusiast|aspiring|ninja|rockstar|guru)/i.test(bio)) {
    bio_critique = `Your bio says '${bio}', which is heavy on buzzwords but light on specifics. The tech industry has enough 'passionate ninjas'—we need someone who writes integration tests.`;
  } else {
    bio_critique = `Your bio proclaims: '${bio}'. Ambitious energy, but your repo list tells a slightly messier story.`;
  }

  let repo_callout = `We inspected '${top_repo}'`;
  if (second_repo) repo_callout += ` and '${second_repo}'`;

  const readme = f.readme_content;
  const is_profile_repo = Boolean(u) && top_repo.trim().toLowerCase() === u.trim().toLowerCase();
  let desc_jab = "";

  if (is_profile_repo) {
    desc_jab = `Your '${top_repo}' profile README is doing the most — personal landing-page energy. Respect for the branding; now point that same effort at a repo with an actual test suite.`;
  } else if (!readme) {
    desc_jab = `The README for '${top_repo}' is completely missing. Code should be self-documenting, but your repos are self-isolating.`;
  } else if (
    repo_languages &&
    Object.values(repo_languages).reduce((a, b) => a + b, 0) < 500 &&
    readme.length > 1000
  ) {
    const total_code_bytes = Object.values(repo_languages).reduce((a, b) => a + b, 0);
    desc_jab = `Wait, '${top_repo}' has a massive ${readme.length}-character README, but only ${total_code_bytes} bytes of actual code?! You wrote a whole dissertation for a starter template. Documentation writing checks your codebase literally cannot cash.`;
  } else if (readme.length < 50) {
    desc_jab = `The README for '${top_repo}' is basically a Post-It note. You expect people to \`npm install\` based on 3 words of documentation?`;
  } else if (!readme.toLowerCase().includes("getting started") && !readme.toLowerCase().includes("install")) {
    desc_jab = `Your '${top_repo}' README is a philosophical essay without any installation instructions. Nobody wants to read your manifesto, they just want the setup command.`;
  } else if (readme.length > 5000) {
    desc_jab = `The README for '${top_repo}' is longer than a Lord of the Rings book. Documentation is great, but nobody is reading a dissertation to use a simple tool.`;
  } else if (empty_descs >= 3) {
    desc_jab = `Your top repo has a README, but ${empty_descs} out of your ${total_repos} repositories don't even have descriptions. Do you expect recruiters to open \`src/index.js\` and guess the business model?`;
  } else {
    desc_jab = `With ${total_stars} total stars across ${total_repos} repos, you are firmly operating in the indie trenches.`;
  }

  let commit_jab = "";
  if (commits && commits.length > 0) {
    const lazy_commits = commits.filter((c: string) =>
      /(fix|update|wip|typo|test|asdf|done|changes)/i.test(c)
    );
    if (lazy_commits.length > 0) {
      commit_jab = `\n\nAlso, your recent commit history includes poetic masterpieces like '${lazy_commits[0]}'. Git blame must feel like a crime scene investigation.`;
    } else if (commits.some((c: string) => /(wip|test)/i.test(c))) {
      commit_jab = "\n\nYour commits read like a stream of consciousness. Stop pushing 'WIP' directly to main.";
    }
  }

  const verdicts = [
    "Verdict: You have the raw building blocks of a solid engineer, but your profile currently looks like a garage workshop after a tornado hit it.",
    "Verdict: Strong chaotic-neutral energy. Your profile needs a refactor more urgently than your code does.",
    "Verdict: You clearly love writing code, but you definitely don't love organizing it.",
  ];

  return [
    `🔥 ARCHETYPE: ${archetype}\n`,
    `${bio_critique}\n`,
    `${repo_callout}. ${desc_jab} ${lang_jab}${commit_jab}\n`,
    randomChoice(verdicts),
  ].join("\n");
}

function generateRescue(
  profile: any,
  repos: any[],
  _roast: string,
  events: any[] | null = null
): string {
  const f = extractProfileFeatures(profile, repos, events);
  const top_repo = f.top_repo_name;
  const second_repo = f.second_repo_name;
  const primary_lang = f.primary_lang;
  const bio = f.bio;
  const empty_descs = f.empty_desc_count;
  const tutorial_repos = f.tutorial_repos;
  const fork_count = f.fork_count;
  const total_repos = f.public_repos;
  const top_star_count = f.top_star_count;
  const followers = f.followers;

  if (followers > 15000 || top_star_count > 5000) {
    const quick_win = [
      "1. ⚡ 10-MIN QUICK WIN: Direct Your Developer Audience",
      `   You have ${followers.toLocaleString()} developers viewing your profile daily.`,
      "   👉 Add a direct link to your official documentation, newsletter, or project hub in your profile website/bio.",
      "   Convert your immense inbound GitHub traffic into an owned distribution channel.",
    ].join("\n");

    const weekend_proj = [
      `2. 🎯 WEEKEND PROJECT: Architectural Governance for '${top_repo}'`,
      `   With ${top_star_count.toLocaleString()} stars, '${top_repo}' is essential community infrastructure:`,
      "   • Add an `ARCHITECTURE.md` explaining system invariants for prospective contributors.",
      "   • Set up automated PR triage bots and GitHub Discussion categories to prevent issue burnout.",
      "   • Configure automated benchmarking CI workflows to catch performance regressions.",
    ].join("\n");

    const career_step = [
      "3. 🚀 CAREER LEVERAGE: Formalize Sustainability & Foundation Status",
      "   You are operating at ecosystem-scale. Protect maintainer longevity:",
      "   👉 Establish GitHub Sponsors or Open Collective funding, define a `SECURITY.md` advisory process, and recruit trusted co-maintainers to avoid bus-factor risk.",
    ].join("\n");

    return `${quick_win}\n\n${weekend_proj}\n\n${career_step}`;
  }

  let quick_win: string;
  if (!bio || bio.length < 15) {
    const suggested_bio = `Building high-performance ${primary_lang} systems & tools | Maintainer of @${top_repo} | Open to software engineering roles`;
    quick_win = [
      "1. ⚡ 10-MIN QUICK WIN: Fix Your Missing Identity",
      "   Your bio is currently empty or minimal. Copy-paste this tailored bio right now into your profile settings:",
      `   👉 "${suggested_bio}"`,
      "   Recruiters filter out zero-bio profiles in under 3 seconds. Give them an instant value proposition.",
    ].join("\n");
  } else if (empty_descs >= 2) {
    const target_repo = second_repo || top_repo;
    quick_win = [
      "1. ⚡ 10-MIN QUICK WIN: Stop the Invisible Repo Epidemic",
      `   ${empty_descs} of your repos have zero description. Go to '${top_repo}' and '${target_repo}' right now.`,
      `   👉 Click the ⚙️ icon next to 'About' and write a 1-sentence summary (e.g. 'A lightweight ${primary_lang} service for data processing with zero runtime dependencies.').`,
      "   Without descriptions, your repos are completely invisible to GitHub search.",
    ].join("\n");
  } else if (!f.location || !f.blog) {
    quick_win = [
      "1. ⚡ 10-MIN QUICK WIN: Turn On Discovery Signals",
      "   You haven't listed a Location or personal link. Tech recruiters filter candidate pools by region (e.g., 'San Francisco', 'Remote', 'London').",
      "   👉 Fill out your city/region and link your LinkedIn or portfolio URL to double your recruiter contact rate.",
    ].join("\n");
  } else {
    quick_win = [
      "1. ⚡ 10-MIN QUICK WIN: Pin Your Strongest Assets",
      "   Don't let GitHub randomly display your oldest repos. Go to your profile overview and customize your 'Pinned Repositories'.",
      `   👉 Pin '${top_repo}' first, followed by your 2 cleanest ${primary_lang} repositories. Hide any forks or unfinished experiments.`,
    ].join("\n");
  }

  let weekend_proj: string;
  if (tutorial_repos.length >= 1) {
    const tut_name = tutorial_repos[0];
    const quickstart_command = ["javascript", "typescript"].includes(primary_lang.toLowerCase())
      ? "npm install && npm start"
      : "pip install -r requirements.txt && python main.py";
    weekend_proj = [
      `2. 🎯 WEEKEND PROJECT: Graduate '${tut_name}' from Tutorial Hell`,
      "   Turn this beginner project into a portfolio-grade asset recruiters respect:",
      "   • Add real authentication (OAuth / JWT) and a persistent database (PostgreSQL / Supabase).",
      "   • Deploy it live to a free cloud host (Vercel, Render, or Railway) and put the live URL at the top of the README.",
      `   • Add a 3-step Quickstart block (\`${quickstart_command}\`).`,
    ].join("\n");
  } else if (fork_count >= 3 && fork_count / Math.max(1, total_repos) >= 0.4) {
    weekend_proj = [
      "2. 🎯 WEEKEND PROJECT: Ship 1 Authentic Standalone Project",
      `   Over 40% of your repos are forks. Unpin them and build one original application from scratch in ${primary_lang}.`,
      "   • Pick a specific real-world problem (e.g., a CLI tool, API wrapper, or data dashboard).",
      "   • Write clean commits from `git init` to `v1.0.0`.",
      "   • Include an animated GIF in the README showing the tool in action.",
    ].join("\n");
  } else if (top_star_count > 50) {
    weekend_proj = [
      `2. 🎯 WEEKEND PROJECT: Open-Source Governance for '${top_repo}'`,
      `   '${top_repo}' already has ${top_star_count} stars! Elevate it into a production-grade open source project:`,
      "   • Add a `CONTRIBUTING.md` guide and an Issue/PR template (`.github/ISSUE_TEMPLATE/`).",
      "   • Set up GitHub Actions CI to run automated unit tests on every pull request.",
      "   • Create a formal GitHub Release (`v1.0.0`) with release notes.",
    ].join("\n");
  } else {
    weekend_proj = [
      `2. 🎯 WEEKEND PROJECT: The README Glow-Up for '${top_repo}'`,
      "   80% of hiring managers decide whether to interview based on the top repository's README alone:",
      `   • Add a 5-second screen recording / GIF showing '${top_repo}' working before any walls of text.`,
      "   • Add tech stack shields/badges (e.g., Python 3.12, Fast, License MIT).",
      "   • Include an Architecture section explaining WHY you made specific technical decisions.",
    ].join("\n");
  }

  let career_step: string;
  if (!f.has_recent_activity) {
    career_step = [
      "3. 🚀 CAREER LEVERAGE: Re-ignite Your Public Heartbeat",
      "   Your public activity graph is flatlining. Recruiters look for consistency, not 1-day commit spikes.",
      `   👉 Pick '${top_repo}', update outdated dependencies, write 3 unit tests, and commit twice a week.`,
      "   Consistent green squares signal reliability and momentum.",
    ].join("\n");
  } else if (f.all_langs.length >= 4) {
    career_step = [
      `3. 🚀 CAREER LEVERAGE: Establish a Coherent ${primary_lang} Senior Narrative`,
      `   You have repos scattered across ${f.all_langs.slice(0, 4).join(", ")}. Generalists get passed over for specialist roles.`,
      `   👉 Position yourself as an authority in ${primary_lang}. Focus your next 2 projects entirely on ${primary_lang} ecosystem depth (performance tuning, concurrency, or distributed systems).`,
    ].join("\n");
  } else {
    career_step = [
      "3. 🚀 CAREER LEVERAGE: Ship 1 Public Pull Request to Upstream Open Source",
      "   You've proven you can write code in your own silo. The ultimate differentiator for senior engineering interviews is public collaboration.",
      `   👉 Search GitHub for active ${primary_lang} repos with the 'good first issue' label. Submit 1 clean, reviewed PR. Link that merged PR directly on your resume.`,
    ].join("\n");
  }

  return `${quick_win}\n\n${weekend_proj}\n\n${career_step}`;
}

function parseGhDate(value: string): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

function diagnoseMentalStability(
  events: any[] | null,
  repos: any[] = [],
  verified_commits: any[] = []
): string {
  const safeRepos = Array.isArray(repos) ? repos : [];
  const safeCommits = Array.isArray(verified_commits) ? verified_commits : [];

  const repo_count = safeRepos.length;
  const total_kb = safeRepos.reduce((sum, r) => sum + (Number(r?.size) || 0), 0);
  const has_real_code = repo_count > 0 && total_kb > 0;
  const code_scale = total_kb >= 1024 ? `${Math.floor(total_kb / 1024)}MB` : `${total_kb}KB`;

  const event_msgs: string[] = [];
  let push_refs_main = 0;
  let total_pushes = 0;
  const event_hours: number[] = [];

  for (const event of events || []) {
    if (event?.type !== "PushEvent") continue;
    total_pushes++;
    const payload = event.payload || {};
    if (payload.ref === "refs/heads/main") push_refs_main++;
    const dt = parseGhDate(event.created_at);
    if (dt) event_hours.push(dt.getUTCHours());
    for (const c of payload.commits || []) {
      const msg = c?.message || "";
      if (msg) event_msgs.push(msg);
    }
  }

  const verified_msgs = safeCommits.map((c) => c?.message || "").filter(Boolean);
  const verified_hours: number[] = [];
  for (const c of safeCommits) {
    const dt = parseGhDate(c?.date);
    if (dt) verified_hours.push(dt.getUTCHours());
  }

  const all_msgs = [...event_msgs, ...verified_msgs];
  const all_hours = [...event_hours, ...verified_hours];
  const total = all_msgs.length;

  const swear_words = ["fuck", "shit", "damn", "crap", "hell", "bitch", "ass"];
  const vague_words = new Set(["fix", "update", "wip", "test", "stuff", "changes", "done", "asdf"]);
  const lowered = all_msgs.map((m) => m.toLowerCase());
  const swear_count = lowered.filter((m) => swear_words.some((w) => m.includes(w))).length;
  const vague_count = lowered.filter(
    (m) => vague_words.has(m.trim()) || m.trim().length < 10
  ).length;
  const late_night = all_hours.filter((h) => h < 6).length;

  if (swear_count > 0) {
    return `Diagnosis: Terminal Rage Syndrome (${swear_count} profanity-laced commit(s) in verified history. Have you tried taking a walk?)`;
  }

  if (repo_count >= 15 && total_kb > 50000) {
    return `Diagnosis: Serial Project Sprawler (${repo_count} repositories holding ${code_scale} of real code, yet new repos keep appearing instead of documentation.)`;
  }

  if (total > 0 && late_night > total * 0.4) {
    return `Diagnosis: Vampire Coder (${late_night} of the last ${total} verified commits landed between midnight and 6 AM. The sun misses you.)`;
  }

  if (total_pushes >= 2 && push_refs_main === total_pushes) {
    return `Diagnosis: Main-Branch Cowboy (all ${total_pushes} recent pushes went straight to main — feature branches are apparently decorative.)`;
  }

  if (total > 0 && vague_count > total * 0.5) {
    const example = all_msgs.find((m) => vague_words.has(m.trim().toLowerCase())) || "fix";
    return `Diagnosis: Commit Message Amnesia (${vague_count} of ${total} verified commits are just '${example.trim()}'. What are you hiding?)`;
  }

  if (total === 0 && !has_real_code && repo_count === 0) {
    return "Diagnosis: Blank Canvas (No public repos and no recent pushes — beautifully mysterious, totally unhirable.)";
  }

  if (total === 0 && has_real_code) {
    return `Diagnosis: Silent Professional (${repo_count} repos, ${code_scale} of code on record, but zero commit chatter in the recent window. Suspiciously well-adjusted.)`;
  }

  if (total === 0) {
    return "Diagnosis: Catatonic (No recent commit telemetry found)";
  }

  return "Diagnosis: Tragically Stable (Your commit history is painfully professional and boring.)";
}

const AI_PAT = /\b(ai|artificial intelligence|machine learning|deep learning|llms?|pytorch|tensorflow|computer vision|nlp|data scien\w*|neural nets?)\b/i;
const DEVOPS_PAT = /\b(devops|cloud(?!flare)|kubernetes|k8s|docker|terraform|aws|azure|gcp|ci\s*\/\s*cd|site reliability|\bsre\b)\b/i;
const SYSTEMS_PAT = /\b(rust|golang|\bgo\b|c\+\+|embedded|kernels?|systems programming|low.level)\b/i;
const FULLSTACK_PAT = /\b(full.?stack|backend|microservices?|rest apis?)\b/i;
const WEB3_PAT = /\b(web3|solidity|blockchain|smart contracts?|defi|nfts?)\b/i;
const BACKEND_LANGS = new Set(["python", "go", "rust", "java", "php", "ruby", "c#", "c++", "kotlin", "swift", "scala"]);
const INFRA_MARKERS = ["dockerfile", "docker", "kubernetes", "k8s", "terraform", "github actions", "ci/cd", "pytest", "jest", "unittest", "coverage", "travis", "circleci"];
const DB_MARKERS = ["postgres", "mysql", "mongo", "sqlite", "database", "prisma", "redis", "sqlalchemy", "supabase"];
const ML_FRAMEWORKS = ["torch", "tensorflow", "sklearn", "scikit", "transformers", "keras", "jax"];

function skeletonEvidence(repo_files: Record<string, string[]> | null = null): Record<string, any> {
  const paths: string[] = [];
  if (repo_files && typeof repo_files === "object") {
    for (const list of Object.values(repo_files)) {
      if (Array.isArray(list)) {
        paths.push(...list.filter((p) => typeof p === "string").map((p) => p.toLowerCase()));
      }
    }
  }

  const base = (p: string) => p.split("/").pop() || "";
  const docker: string[] = [];
  const ci: string[] = [];
  const tests: string[] = [];
  const backend: string[] = [];
  const db: string[] = [];
  const models: string[] = [];

  for (const p of paths) {
    const b = base(p);
    if (
      b === "dockerfile" ||
      b === "containerfile" ||
      b.startsWith("docker-compose") ||
      b === "docker-compose.yml" ||
      b === "docker-compose.yaml"
    ) {
      docker.push(p);
    }
    if (
      p.startsWith(".github/workflows/") ||
      ["travis.yml", ".travis.yml", "circle.yml", "config.yml", "gitlab-ci.yml", "jenkinsfile", "azure-pipelines.yml"].includes(b)
    ) {
      ci.push(p);
    }
    if (
      b.startsWith("test_") ||
      b.startsWith("test.") ||
      b.endsWith("_test.py") ||
      b.endsWith("_test.js") ||
      b.endsWith("_test.ts") ||
      b.endsWith("_test.go") ||
      b.endsWith("_test.rb") ||
      b.includes(".spec.") ||
      b.startsWith("spec_") ||
      p.includes("/tests/") ||
      p.startsWith("tests/")
    ) {
      tests.push(p);
    }
    if (
      [".py", ".go", ".rs", ".java", ".php", ".rb", ".js", ".ts"].some((ext) => b.endsWith(ext)) &&
      !b.includes("test") &&
      !b.includes("spec")
    ) {
      backend.push(p);
    }
    if (
      b.endsWith(".sql") ||
      b === "schema.prisma" ||
      p.includes("/migrations/") ||
      p.includes("/models/") ||
      p.includes("alembic")
    ) {
      db.push(p);
    }
    if (
      [".pt", ".pth", ".onnx", ".safetensors", ".h5", ".ckpt", ".bin"].some((ext) => b.endsWith(ext)) ||
      b.endsWith(".ipynb")
    ) {
      models.push(p);
    }
  }

  const uniq = (arr: string[]) => Array.from(new Set(arr)).sort().slice(0, 3);

  return {
    repos_scanned: repo_files ? Object.keys(repo_files).length : 0,
    docker: uniq(docker),
    ci: uniq(ci),
    tests: uniq(tests),
    backend: uniq(backend),
    db: uniq(db),
    models: uniq(models),
  };
}

export function audit_resume_vs_reality(
  profile_readme: string = "",
  bio: string = "",
  repos: any[] = [],
  repo_languages: Record<string, number> | null = null,
  repo_files: Record<string, string[]> | null = null,
  resume_label: string = "profile README"
): Record<string, any> {
  const text = `${profile_readme || ""}\n${bio || ""}`.toLowerCase();
  const has_readme = Boolean((profile_readme || "").trim());
  const projects = Array.isArray(repos) ? repos : [];

  const total_kb = projects.reduce((sum, r) => sum + (Number(r?.size) || 0), 0);
  const has_code = total_kb > 0;

  const lang_bytes: Record<string, number> = {};
  if (repo_languages) {
    for (const [k, v] of Object.entries(repo_languages)) {
      if (v) lang_bytes[k] = Number(v) || 0;
    }
  }
  if (Object.values(lang_bytes).reduce((a, b) => a + b, 0) <= 0) {
    for (const r of projects) {
      const lang = (r?.primary_language || r?.language || "").trim();
      if (lang) {
        lang_bytes[lang] = (lang_bytes[lang] || 0) + 1000;
      }
    }
  }
  const lang_total = Object.values(lang_bytes).reduce((a, b) => a + b, 0);

  const share = (...names: string[]) => {
    if (lang_total <= 0) return 0.0;
    const wanted = new Set(names.map((n) => n.toLowerCase()));
    let sum = 0;
    for (const [lang, b] of Object.entries(lang_bytes)) {
      if (wanted.has(lang.toLowerCase())) sum += b;
    }
    return sum / lang_total;
  };

  const frontend_share = share("html", "css", "javascript");
  const python_share = share("python");
  const systems_share = share("rust", "go", "c", "c++", "c#", "zig");
  const backend_share = share(...Array.from(BACKEND_LANGS));

  const blob = projects
    .map(
      (r) =>
        `${r?.name || ""} ${r?.description || ""} ${(Array.isArray(r?.topics) ? r.topics : []).join(" ")}`
    )
    .join("\n")
    .toLowerCase();

  const infra_hits = INFRA_MARKERS.filter((k) => blob.includes(k));
  const db_hits = DB_MARKERS.filter((k) => blob.includes(k));
  const ml_fw = ML_FRAMEWORKS.filter((k) => blob.includes(k));
  const skel = skeletonEvidence(repo_files);
  const skel_repos = skel.repos_scanned;

  const cite = (items: string[], kind: string) => {
    const shown = items.slice(0, 2).join(", ");
    const extra = items.length > 2 ? ` (+${items.length - 2} more)` : "";
    return `${kind} (${shown}${extra})`;
  };

  const findings: Array<{ claim: string; reality: string; severity: string }> = [];
  const add = (claim: string, reality: string, severity: string) => {
    findings.push({ claim, reality, severity });
  };

  // 1. AI / ML
  if (AI_PAT.test(text)) {
    if (python_share >= 0.3 && (ml_fw.length > 0 || skel.models.length > 0)) {
      const proof = skel.models.length > 0 ? cite(skel.models, "model artifacts") : ml_fw.slice(0, 2).join(", ");
      add(
        "AI / ML Engineer",
        `VERIFIED-ish: ${Math.round(100 * python_share)}% Python with ${proof} in the codebase. Touch grass anyway.`,
        "VERIFIED"
      );
    } else if (python_share >= 0.3) {
      add(
        "AI / ML Engineer",
        `${Math.round(100 * python_share)}% Python but zero PyTorch/TensorFlow anywhere — currently a sklearn-curious script kiddie.`,
        "MEDIUM_VIBE"
      );
    } else {
      add(
        "AI / ML Engineer",
        `${Math.round(100 * frontend_share)}% frontend HTML/CSS/JS vibe templates; zero model architectures, zero PyTorch.`,
        "HIGH_VIBE"
      );
    }
  }

  // 2. DevOps / Cloud
  if (DEVOPS_PAT.test(text)) {
    const proof_files = [...skel.docker, ...skel.ci];
    if (skel_repos && skel.docker.length > 0 && skel.ci.length > 0) {
      add(
        "Cloud / DevOps Architect",
        `VERIFIED-ish: ${cite(skel.docker, "Dockerfile")} plus ${cite(skel.ci, "CI")} across scanned repos. PagerDuty fears you.`,
        "VERIFIED"
      );
    } else if (skel_repos && proof_files.length > 0) {
      add(
        "Cloud / DevOps Architect",
        `Partial receipts: ${cite(proof_files, "infra files")}, but the other half of the pipeline is missing.`,
        "MEDIUM_VIBE"
      );
    } else if (skel_repos) {
      add(
        "Cloud / DevOps Architect",
        `Scanned ${skel_repos} repo file trees: 0 Dockerfiles, 0 CI workflows. The cloud is just someone else's laptop to you.`,
        "HIGH_VIBE"
      );
    } else if (infra_hits.length >= 2) {
      add(
        "Cloud / DevOps Architect",
        `VERIFIED-ish: ${infra_hits.slice(0, 3).join(", ")} found across scanned repos. PagerDuty fears you.`,
        "VERIFIED"
      );
    } else if (infra_hits.length === 1) {
      add(
        "Cloud / DevOps Architect",
        `Exactly one infra signal (${infra_hits[0]}) across all repos. An architect with one brick.`,
        "MEDIUM_VIBE"
      );
    } else {
      add(
        "Cloud / DevOps Architect",
        "0 Dockerfiles or CI/CD pipelines found across all repos. The cloud is just someone else's laptop to you.",
        "HIGH_VIBE"
      );
    }
  }

  // 3. Full-Stack
  if (FULLSTACK_PAT.test(text)) {
    const db_evidence = skel.db.length > 0 || db_hits.length > 0;
    const code_evidence = skel.backend.length > 0 || backend_share >= 0.2;
    if (code_evidence && db_evidence) {
      const proof = skel.db.length > 0 ? cite(skel.db, "db models") : db_hits[0];
      add(
        "Full-Stack Developer",
        `VERIFIED-ish: backend code on record plus ${proof}. The stack is, in fact, full.`,
        "VERIFIED"
      );
    } else if (code_evidence) {
      add(
        "Full-Stack Developer",
        "Backend bytes exist but zero database models on record. Full-stack minus the stack's bottom half.",
        "MEDIUM_VIBE"
      );
    } else {
      add(
        "Full-Stack Developer",
        "Pure client-side scripts; zero server or database models on record.",
        "HIGH_VIBE"
      );
    }
  }

  // 4. Systems
  if (SYSTEMS_PAT.test(text)) {
    if (systems_share > 0) {
      add(
        "Systems Engineer",
        `VERIFIED-ish: ${Math.round(100 * systems_share)}% systems-language bytes. Valgrind sends regards.`,
        "VERIFIED"
      );
    } else {
      add(
        "Systems Engineer",
        "0 bytes of Rust or Go in public repos. The closest thing to systems programming here is CSS grid.",
        "HIGH_VIBE"
      );
    }
  }

  // 5. Web3
  if (WEB3_PAT.test(text)) {
    if (share("solidity") > 0) {
      add("Web3 Builder", "VERIFIED-ish: Solidity bytes on-chain of evidence.", "VERIFIED");
    } else {
      add("Web3 Builder", "0 Solidity, 0 contracts. Your bags are purely emotional.", "HIGH_VIBE");
    }
  }

  const claims = findings.length;
  const verified = findings.filter((d) => d.severity === "VERIFIED").length;
  let vibe = 50;
  if (claims > 0) {
    vibe = Math.round((100 * (claims - verified)) / claims);
  } else {
    vibe = has_code ? 15 : 50;
  }
  const verifiable = 100 - vibe;

  const label = resume_label || "profile README";
  let verdict: string;
  if (vibe >= 60) {
    verdict = `Your ${label} writes checks your repositories cannot cash. Recruiters read both — delete two adjectives or ship one backend.`;
  } else if (vibe >= 30) {
    verdict =
      "Resume and reality mostly agree, but a few claims need receipts. Pin the repo that proves the loudest bullet point.";
  } else {
    verdict =
      "Receipts attached. The resume and the repos tell the same story — now go touch grass.";
  }

  return {
    vibe_ratio: `${vibe}% Vibe / ${verifiable}% Verifiable`,
    has_profile_readme: has_readme,
    headline: "Profile README Claims vs. Actual Git Reality",
    discrepancies: findings.slice(0, 5),
    recruiter_verdict: verdict,
  };
}

export function analyze_profile(
  profile_data: any,
  repos_data: any[],
  username: string,
  options: {
    events_data?: any[] | null;
    readme_content?: string;
    repo_languages?: Record<string, number> | null;
    verified_commits?: any[] | null;
    profile_readme?: string;
    audit_languages?: Record<string, number> | null;
    repo_files?: Record<string, string[]> | null;
    resume_label?: string;
  } = {}
): Record<string, any> {
  const profile_summary = format_profile_summary(profile_data);
  const repo_summary = format_repo_summary(repos_data);

  const handle = String(profile_summary.username || "").toLowerCase();
  const raw_projects = repos_data.filter(
    (r) => String(r?.name || "").toLowerCase() !== handle
  );
  const project_top_repos = repo_summary.top_repos.filter(
    (r) => String(r?.name || "").toLowerCase() !== handle
  );

  const recruiter_glance = generateRecruiterGlance(profile_summary, project_top_repos, options.events_data);
  const roast = generateRoast(
    profile_summary,
    project_top_repos,
    options.events_data,
    options.readme_content || "",
    options.repo_languages
  );
  const rescue = generateRescue(profile_summary, project_top_repos, roast, options.events_data);
  const psych_eval = diagnoseMentalStability(
    options.events_data || null,
    repos_data,
    options.verified_commits || []
  );

  let raw_bio = String(profile_data?.bio || "");
  if (raw_bio === "No bio set") raw_bio = "";

  const reality = audit_resume_vs_reality(
    options.profile_readme || "",
    raw_bio,
    raw_projects,
    options.audit_languages || options.repo_languages || null,
    options.repo_files || null,
    options.resume_label || "profile README"
  );

  const f = extractProfileFeatures(profile_summary, project_top_repos, options.events_data);

  return {
    status: "success",
    username,
    recruiter_glance,
    roast,
    rescue,
    psych_eval,
    resume_vs_reality: reality,
    archetype: f.archetype || "Developer",
    profile_data: profile_summary,
    repo_data: repo_summary,
    total_size_kb: repos_data.reduce((sum, r) => sum + (Number(r?.size) || 0), 0),
    recent_commits: (options.verified_commits || [])
      .map((c) => c?.message || "")
      .filter(Boolean)
      .slice(0, 10),
  };
}

const VAGUE_TOKENS = new Set(["fix", "update", "wip", "test", "stuff", "changes", "done", "asdf"]);
const SWEAR_TOKENS = ["fuck", "shit", "damn", "crap", "hell", "bitch", "ass"];

function battleMetrics(analysis: Record<string, any>): Record<string, any> {
  const repo_data = analysis.repo_data || {};
  const top = Array.isArray(repo_data.top_repos) ? repo_data.top_repos : [];
  const now = Date.now();

  const zero_star = top.filter((r: any) => (Number(r?.stars) || 0) === 0).length;
  const archived = top.filter((r: any) => Boolean(r?.archived)).length;
  let stale = 0;
  for (const r of top) {
    const dt = parseGhDate(r?.last_push);
    if (dt && now - dt.getTime() > 365 * 24 * 60 * 60 * 1000) {
      stale++;
    }
  }

  const msgs = (analysis.recent_commits || []).filter((m: any) => typeof m === "string" && m.trim());
  const lowered = msgs.map((m: string) => m.toLowerCase());
  const vague = lowered.filter((m: string) => VAGUE_TOKENS.has(m.trim()) || m.trim().length < 10).length;
  const profane = lowered.filter((m: string) => SWEAR_TOKENS.some((w) => m.includes(w))).length;

  return {
    graveyard: zero_star + archived + stale,
    zero_star,
    archived,
    stale,
    code_kb: Number(analysis.total_size_kb) || 0,
    commits_seen: msgs.length,
    unhinged: vague + profane,
    vague,
    profane,
  };
}

export function compare_profiles(
  analysis1: Record<string, any>,
  analysis2: Record<string, any>
): Record<string, any> {
  const u1 = analysis1.username || "dev-1";
  const u2 = analysis2.username || "dev-2";
  const m1 = battleMetrics(analysis1);
  const m2 = battleMetrics(analysis2);

  let s1 = 0;
  let s2 = 0;
  const rounds: Array<{ round: string; winner: string }> = [];

  const award = (name: string, better: number) => {
    if (better > 0) s1++;
    else if (better < 0) s2++;
    rounds.push({ round: name, winner: better > 0 ? u1 : better < 0 ? u2 : "tie" });
  };

  award("graveyard", (m2.graveyard > m1.graveyard ? 1 : 0) - (m1.graveyard > m2.graveyard ? 1 : 0));
  award("code_volume", (m1.code_kb > m2.code_kb ? 1 : 0) - (m2.code_kb > m1.code_kb ? 1 : 0));

  let hygiene_note = "";
  if (m1.commits_seen === 0 && m2.commits_seen === 0) {
    award("hygiene", 0);
    hygiene_note = "neither combatant left verifiable commit evidence";
  } else {
    award("hygiene", (m2.unhinged > m1.unhinged ? 1 : 0) - (m1.unhinged > m2.unhinged ? 1 : 0));
    hygiene_note = `@${u1} has ${m1.unhinged} unhinged message(s) in ${m1.commits_seen} verified commits vs ${m2.unhinged} in ${m2.commits_seen} for @${u2}`;
  }

  if (s1 === s2) {
    const stars1 = ((analysis1.repo_data?.top_repos || []) as any[]).reduce(
      (sum, r) => sum + (Number(r?.stars) || 0),
      0
    );
    const stars2 = ((analysis2.repo_data?.top_repos || []) as any[]).reduce(
      (sum, r) => sum + (Number(r?.stars) || 0),
      0
    );

    if (stars1 === stars2) {
      return {
        winner: "tie",
        loser: "tie",
        verdict: `Dead heat. @${u1} and @${u2} are equally mid — the interview panel falls asleep and both get relegated to writing Jira tickets about Jira tickets.`,
        stats: {
          user1: { username: u1, ...m1 },
          user2: { username: u2, ...m2 },
          rounds,
          score: { [u1]: s1, [u2]: s2 },
        },
      };
    }

    const winner = stars1 > stars2 ? u1 : u2;
    const loser = stars1 > stars2 ? u2 : u1;
    const deciding = `a ${Math.max(stars1, stars2).toLocaleString()}-star haul breaks the tie`;
    const wm = winner === u1 ? m1 : m2;
    const lm = winner === u1 ? m2 : m1;

    return {
      winner,
      loser,
      verdict: `@${winner} survives the technical interview with ${wm.code_kb.toLocaleString()}KB of code against ${lm.code_kb.toLocaleString()}KB (${deciding}; ${hygiene_note}). @${loser} — with a graveyard score of ${lm.graveyard} — is hereby relegated to triaging Jira tickets about the legacy repo nobody will delete.`,
      stats: {
        user1: { username: u1, ...m1 },
        user2: { username: u2, ...m2 },
        rounds,
        score: { [u1]: s1, [u2]: s2 },
      },
    };
  }

  const winner = s1 > s2 ? u1 : u2;
  const loser = s1 > s2 ? u2 : u1;
  const deciding = `a ${Math.max(s1, s2)}–${Math.min(s1, s2)} round split`;
  const wm = winner === u1 ? m1 : m2;
  const lm = winner === u1 ? m2 : m1;

  return {
    winner,
    loser,
    verdict: `@${winner} survives the technical interview with ${wm.code_kb.toLocaleString()}KB of code against ${lm.code_kb.toLocaleString()}KB (${deciding}; ${hygiene_note}). @${loser} — with a graveyard score of ${lm.graveyard} — is hereby relegated to triaging Jira tickets about the legacy repo nobody will delete.`,
    stats: {
      user1: { username: u1, ...m1 },
      user2: { username: u2, ...m2 },
      rounds,
      score: { [u1]: s1, [u2]: s2 },
    },
  };
}
