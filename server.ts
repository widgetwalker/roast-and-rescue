import express, { Request, Response } from "express";
import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";
import { GitHubClient } from "./src/githubClient.js";
import {
  analyze_profile,
  audit_resume_vs_reality,
  compare_profiles,
} from "./src/analyzer.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = parseInt(process.env.PORT || "3000", 10);
const HOST = "0.0.0.0";

const USERNAME_REGEX = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;

// In-memory Leaderboard Store (Mock of SQLite database)
interface LeaderboardEntry {
  username: string;
  archetype: string;
  roast_preview: string;
  timestamp: string;
}

const leaderboardStore: LeaderboardEntry[] = [];

function saveToLeaderboard(username: string, archetype: string, roastPreview: string) {
  try {
    const existingIndex = leaderboardStore.findIndex(
      (entry) => entry.username.toLowerCase() === username.toLowerCase()
    );
    const item: LeaderboardEntry = {
      username,
      archetype,
      roast_preview: roastPreview,
      timestamp: new Date().toISOString(),
    };
    if (existingIndex >= 0) {
      leaderboardStore.splice(existingIndex, 1);
    }
    leaderboardStore.unshift(item);
    if (leaderboardStore.length > 50) {
      leaderboardStore.pop();
    }
  } catch (err) {
    console.error("Leaderboard save error:", err);
  }
}

function getLeaderboard(): LeaderboardEntry[] {
  return leaderboardStore.slice(0, 10);
}

function getCachedBadge(username: string): { archetype: string; preview: string } | null {
  const item = leaderboardStore.find(
    (entry) => entry.username.toLowerCase() === username.toLowerCase()
  );
  if (item) {
    return { archetype: item.archetype || "Roasted Dev", preview: item.roast_preview || "" };
  }
  return null;
}

async function badgeContext(
  client: GitHubClient,
  username: string
): Promise<{ archetype: string; preview: string; roasted: boolean }> {
  const cached = getCachedBadge(username);
  if (cached) {
    return { archetype: cached.archetype, preview: cached.preview, roasted: true };
  }
  try {
    const profile = await client.get_user_profile(username);
    if (!profile) {
      return { archetype: "UNROASTED", preview: "Run a roast to earn an archetype", roasted: false };
    }
    const followers = profile.followers || 0;
    const repos = profile.public_repos || 0;
    return {
      archetype: `Fresh Meat (${followers} followers)`,
      preview: `@${username} commands ${repos} public repos — awaiting judgment`,
      roasted: false,
    };
  } catch {
    return { archetype: "UNROASTED", preview: "Run a roast to earn an archetype", roasted: false };
  }
}

function buildBadgeSvg(username: string, archetype: string, preview: string, roasted: boolean): string {
  const esc = (s: string) =>
    (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const user = esc(username);
  const arch = esc((archetype || "Developer").slice(0, 26));
  const status = roasted ? "ROASTED" : "AWAITING ROAST";
  const statusFill = roasted ? "#00ffff" : "#ffffff";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="460" height="90" viewBox="0 0 460 90" role="img" aria-label="GitHub Roast badge for @${user}">
<rect x="3" y="3" width="454" height="84" fill="#ffff00" stroke="#000000" stroke-width="5"/>
<text x="18" y="30" font-family="monospace" font-size="14" font-weight="900" fill="#000000" textLength="420" lengthAdjust="spacingAndGlyphs">&#x1F525; ROAST &amp; RESCUE // @${user}</text>
<rect x="15" y="42" width="272" height="32" fill="#000000"/>
<text x="27" y="64" font-family="monospace" font-size="14" font-weight="900" fill="#ff00ff" textLength="248" lengthAdjust="spacingAndGlyphs">${arch}</text>
<rect x="297" y="42" width="148" height="32" fill="${statusFill}" stroke="#000000" stroke-width="3"/>
<text x="371" y="63" text-anchor="middle" font-family="monospace" font-size="12" font-weight="900" fill="#000000">${status}</text>
</svg>`;
}

function brutalistLayout(sections: Record<string, string>, width: number = 80): string {
  const center = (str: string, len: number, padChar: string = "█") => {
    const padLen = Math.max(0, len - str.length);
    const left = Math.floor(padLen / 2);
    const right = padLen - left;
    return padChar.repeat(left) + str + padChar.repeat(right);
  };
  const lines: string[] = [
    "█".repeat(width),
    center("  GITHUB ROAST & RESCUE  ", width, "█"),
    center("  Honest feedback with actionable improvement advice  ", width, "█"),
    "█".repeat(width),
    "",
  ];
  for (const [name, content] of Object.entries(sections)) {
    lines.push("▀".repeat(width));
    lines.push(center(`  ${name.toUpperCase()}  `, width, "█"));
    lines.push("▄".repeat(width));
    for (const line of (content || "").split("\n")) {
      lines.push(` █  ${line}`);
    }
    lines.push("");
  }
  lines.push("≡".repeat(width));
  return lines.join("\n");
}

async function fetchRepoEvidence(
  client: GitHubClient,
  username: string,
  projectRepos: any[],
  topRepoName: string = "",
  topLangs: Record<string, number> = {}
): Promise<{ aggLanguages: Record<string, number>; skeletons: Record<string, string[]> }> {
  const agg: Record<string, number> = { ...(topLangs || {}) };
  const skeletons: Record<string, string[]> = {};
  const ordered = [...(projectRepos || [])].sort(
    (a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0)
  );
  const skip = (topRepoName || "").trim().toLowerCase();
  let langFetched = 0;
  let treeFetched = 0;

  for (const repo of ordered) {
    if (!repo || typeof repo !== "object") continue;
    const name = repo.name || "";
    if (!name) continue;

    if (langFetched < 4 && name.trim().toLowerCase() !== skip) {
      try {
        const langs = await client.get_repo_languages(username, name);
        for (const [lang, b] of Object.entries(langs || {})) {
          if (b) agg[lang] = (agg[lang] || 0) + Number(b);
        }
      } catch {}
      langFetched++;
    }

    if (treeFetched < 3) {
      try {
        const branch = repo.default_branch || "";
        const paths = await client.get_repo_tree(username, name, branch);
        skeletons[name] = paths || [];
      } catch {
        skeletons[name] = [];
      }
      treeFetched++;
    }

    if (langFetched >= 4 && treeFetched >= 3) break;
  }

  return { aggLanguages: agg, skeletons };
}

async function runFullAnalysis(client: GitHubClient, username: string): Promise<Record<string, any>> {
  const profile_data = await client.get_user_profile(username);
  if (!profile_data) {
    throw new Error(
      `GitHub user '@${username}' could not be fetched. Either the user does not exist or GitHub API rate limit was reached.`
    );
  }
  const repos_data = (await client.get_user_repos(username)) || [];
  const events_data = (await client.get_recent_activity(username)) || [];

  let profile_readme = "";
  try {
    profile_readme = (await client.get_repo_readme(username, username)) || "";
  } catch {}

  const project_repos = repos_data.filter(
    (r) => String(r?.name || "").trim().toLowerCase() !== username.toLowerCase()
  );

  const ordered = [...project_repos].sort(
    (a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0)
  );
  const top_repo_name = ordered[0]?.name || "";

  let readme_content = "";
  let top_repo_languages: Record<string, number> = {};
  let verified_commits: any[] = [];

  if (top_repo_name) {
    try {
      readme_content = await client.get_repo_readme(username, top_repo_name);
    } catch {}
    try {
      top_repo_languages = (await client.get_repo_languages(username, top_repo_name)) || {};
    } catch {}
    try {
      verified_commits = (await client.get_repo_commits(username, top_repo_name, username, 10)) || [];
    } catch {}
  }

  const { aggLanguages, skeletons } = await fetchRepoEvidence(
    client,
    username,
    project_repos,
    top_repo_name,
    top_repo_languages
  );

  return analyze_profile(profile_data, repos_data, username, {
    events_data,
    readme_content,
    repo_languages: top_repo_languages,
    verified_commits,
    profile_readme,
    audit_languages: aggLanguages,
    repo_files: skeletons,
  });
}

// App Middleware
app.use(cors());
app.use(express.json({ limit: "20mb" }));

// Static Assets & Web Dashboard
app.use("/assets", express.static(path.join(__dirname, "assets")));
app.use(express.static(path.join(__dirname, "public")));

// Route: Dashboard GET / and /index.html
app.get(["/", "/index.html"], (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

// Route: Architecture diagram GET /architecture.html
app.get("/architecture.html", (_req: Request, res: Response) => {
  res.sendFile(path.join(__dirname, "architecture.html"));
});

// Route: Health checks
app.get(["/health", "/healthz", "/_ah/health"], (_req: Request, res: Response) => {
  res.json({
    status: "healthy",
    service: "github-roast-and-rescue",
    version: "1.0.0",
    target: "google-cloud-run",
  });
});

// Route: Leaderboard GET /api/leaderboard
app.get("/api/leaderboard", (_req: Request, res: Response) => {
  const board = getLeaderboard();
  res.json({ status: "success", leaderboard: board });
});

// Route: Badge GET /badge/:username and /badge/:username.svg
app.get(["/badge/:username", "/badge/:username.svg"], async (req: Request, res: Response) => {
  let raw = req.params.username || "";
  if (raw.toLowerCase().endsWith(".svg")) {
    raw = raw.slice(0, -4);
  }
  const username = raw.trim().replace(/^@/, "");
  if (!username || !USERNAME_REGEX.test(username)) {
    res.status(400).json({ error: "Invalid username for badge" });
    return;
  }
  const client = new GitHubClient();
  const ctx = await badgeContext(client, username);
  const svg = buildBadgeSvg(username, ctx.archetype, ctx.preview, ctx.roasted);
  res.setHeader("Content-Type", "image/svg+xml; charset=utf-8");
  res.setHeader("Cache-Control", "public, max-age=3600");
  res.send(svg);
});

// Route: POST /roast & /api/roast
app.post(["/roast", "/api/roast"], async (req: Request, res: Response) => {
  if (!req.body || typeof req.body !== "object" || Object.keys(req.body).length === 0) {
    res.status(400).json({ error: "Missing JSON request body" });
    return;
  }

  const username = String(req.body.username || "").trim().replace(/^@/, "");
  if (!username) {
    res.status(400).json({ status: "error", message: "Field 'username' is required" });
    return;
  }

  if (!USERNAME_REGEX.test(username)) {
    res.status(400).json({
      status: "error",
      message: `Invalid GitHub username format '${username}'. GitHub usernames may only contain alphanumeric characters and hyphens.`,
    });
    return;
  }

  try {
    const client = new GitHubClient();
    const profile_data = await client.get_user_profile(username);
    if (!profile_data) {
      res.status(404).json({
        status: "error",
        message: `GitHub user '@${username}' could not be fetched. Either the user does not exist or GitHub API rate limit was reached.`,
      });
      return;
    }

    const repos_data = (await client.get_user_repos(username)) || [];
    const events_data = (await client.get_recent_activity(username)) || [];

    let profile_readme = "";
    try {
      profile_readme = (await client.get_repo_readme(username, username)) || "";
    } catch {}

    const project_repos = repos_data.filter(
      (r) => String(r?.name || "").trim().toLowerCase() !== username.toLowerCase()
    );

    const ordered = [...project_repos].sort(
      (a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0)
    );
    const top_repo_name = ordered[0]?.name || "";

    let readme_content = "";
    let top_repo_languages: Record<string, number> = {};
    let verified_commits: any[] = [];

    if (top_repo_name) {
      try {
        readme_content = await client.get_repo_readme(username, top_repo_name);
      } catch {}
      try {
        top_repo_languages = (await client.get_repo_languages(username, top_repo_name)) || {};
      } catch {}
      try {
        verified_commits = (await client.get_repo_commits(username, top_repo_name, username, 10)) || [];
      } catch {}
    }

    const { aggLanguages, skeletons } = await fetchRepoEvidence(
      client,
      username,
      project_repos,
      top_repo_name,
      top_repo_languages
    );

    const analysis = analyze_profile(profile_data, repos_data, username, {
      events_data,
      readme_content,
      repo_languages: top_repo_languages,
      verified_commits,
      profile_readme,
      audit_languages: aggLanguages,
      repo_files: skeletons,
    });

    const sections = {
      recruiter_glance: analysis.recruiter_glance || "",
      roast: analysis.roast || "",
      rescue: analysis.rescue || "",
    };
    const brutalist_text = brutalistLayout(sections, 80);

    const archetype = analysis.archetype || "The Generalist Builder";
    const roast_preview =
      (analysis.roast || "").length > 120
        ? (analysis.roast || "").slice(0, 120) + "..."
        : analysis.roast || "";
    saveToLeaderboard(username, archetype, roast_preview);

    res.json({
      status: "success",
      username,
      recruiter_glance: analysis.recruiter_glance || "",
      roast: analysis.roast || "",
      rescue: analysis.rescue || "",
      psych_eval: analysis.psych_eval || "",
      resume_vs_reality: analysis.resume_vs_reality || {},
      bento_formatted: brutalist_text,
    });
  } catch (err: any) {
    if (err.message?.includes("rate limit")) {
      res.status(429).json({ status: "error", message: err.message });
      return;
    }
    console.error("Roast error:", err);
    res.status(500).json({ status: "error", message: `Internal error: ${err.message}` });
  }
});

// Route: POST /battle & /api/battle
app.post(["/battle", "/api/battle"], async (req: Request, res: Response) => {
  if (!req.body || typeof req.body !== "object" || Object.keys(req.body).length === 0) {
    res.status(400).json({ error: "Missing JSON request body" });
    return;
  }

  const user1 = String(req.body.user1 || "").trim().replace(/^@/, "");
  const user2 = String(req.body.user2 || "").trim().replace(/^@/, "");

  if (!user1 || !user2) {
    res.status(400).json({
      status: "error",
      message: "Fields 'user1' and 'user2' are both required",
    });
    return;
  }

  for (const handle of [user1, user2]) {
    if (!USERNAME_REGEX.test(handle)) {
      res.status(400).json({
        status: "error",
        message: `Invalid GitHub username format '${handle}'.`,
      });
      return;
    }
  }

  if (user1.toLowerCase() === user2.toLowerCase()) {
    res.status(400).json({
      status: "error",
      message: "A roast battle needs two different combatants.",
    });
    return;
  }

  try {
    const client = new GitHubClient();
    const analysis1 = await runFullAnalysis(client, user1);
    const analysis2 = await runFullAnalysis(client, user2);

    const result = compare_profiles(analysis1, analysis2);
    result.archetypes = {
      [analysis1.username || user1]: analysis1.archetype || "Developer",
      [analysis2.username || user2]: analysis2.archetype || "Developer",
    };

    res.json({ status: "success", battle: result });
  } catch (err: any) {
    if (err.message?.includes("could not be fetched")) {
      res.status(404).json({ status: "error", message: err.message });
      return;
    }
    if (err.message?.includes("rate limit")) {
      res.status(429).json({ status: "error", message: err.message });
      return;
    }
    console.error("Battle error:", err);
    res.status(500).json({ status: "error", message: `Battle error: ${err.message}` });
  }
});

// Route: POST /resume-audit & /api/resume-audit
app.post(["/resume-audit", "/api/resume-audit"], async (req: Request, res: Response) => {
  if (!req.body || typeof req.body !== "object" || Object.keys(req.body).length === 0) {
    res.status(400).json({ error: "Missing JSON request body" });
    return;
  }

  const username = String(req.body.username || "").trim().replace(/^@/, "");
  const resume_text = typeof req.body.resume_text === "string" ? req.body.resume_text : "";

  if (!username) {
    res.status(400).json({ status: "error", message: "Field 'username' is required" });
    return;
  }

  if (!USERNAME_REGEX.test(username)) {
    res.status(400).json({
      status: "error",
      message: `Invalid GitHub username format '${username}'.`,
    });
    return;
  }

  if (!resume_text.trim()) {
    res.status(400).json({
      status: "error",
      message: "Field 'resume_text' is required (upload or paste a resume).",
    });
    return;
  }

  if (resume_text.length > 20000) {
    res.status(400).json({
      status: "error",
      message: "Resume text too large — keep it under 20,000 characters.",
    });
    return;
  }

  try {
    const client = new GitHubClient();
    const profile = await client.get_user_profile(username);
    if (!profile) {
      res.status(404).json({
        status: "error",
        message: `GitHub user '@${username}' could not be fetched. Either the user does not exist or GitHub API rate limit was reached.`,
      });
      return;
    }

    const repos = (await client.get_user_repos(username)) || [];
    const projects = repos.filter(
      (r) => String(r?.name || "").trim().toLowerCase() !== username.toLowerCase()
    );

    let top_langs: Record<string, number> = {};
    let top_name = "";
    const ordered = [...projects].sort(
      (a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0)
    );
    if (ordered.length > 0) {
      top_name = ordered[0]?.name || "";
      try {
        top_langs = (await client.get_repo_languages(username, top_name)) || {};
      } catch {}
    }

    const { aggLanguages, skeletons } = await fetchRepoEvidence(
      client,
      username,
      projects,
      top_name,
      top_langs
    );

    const bio = profile.bio || "";
    const result = audit_resume_vs_reality(
      resume_text,
      bio,
      projects,
      aggLanguages,
      skeletons,
      "resume"
    );
    result.source = "uploaded_resume";

    res.json({
      status: "success",
      username,
      resume_vs_reality: result,
    });
  } catch (err: any) {
    if (err.message?.includes("rate limit")) {
      res.status(429).json({ status: "error", message: err.message });
      return;
    }
    console.error("Resume audit error:", err);
    res.status(500).json({ status: "error", message: `Resume audit error: ${err.message}` });
  }
});

// Start Express Server
app.listen(PORT, HOST, () => {
  console.log(`🚀 GitHub Roast & Rescue Node.js server listening on http://${HOST}:${PORT}`);
  console.log(`👉 Health check: http://${HOST}:${PORT}/health`);
  console.log(`👉 POST endpoint: http://${HOST}:${PORT}/roast`);
});
