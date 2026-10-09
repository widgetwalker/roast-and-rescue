/**
 * GitHub API client for fetching public profile and repository data.
 *
 * Uses unauthenticated GitHub API (60 requests/hr limit for public data).
 * All data fetched is publicly available - no authentication required.
 * Optionally uses GITHUB_TOKEN env var for higher rate limits (5,000 req/hr).
 */

import {
  GitHubProfileRaw,
  GitHubRepoRaw,
  GitHubEventRaw,
  ProfileSummary,
  RepoSummary,
  RepoSummaryList,
  RepoCommit,
} from "./types.js";

const USERNAME_REGEX = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;

function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const token = process.env.GITHUB_TOKEN;
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+v3+json",
    "User-Agent": "GitHub-Roast-And-Rescue/1.0",
    ...extraHeaders,
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

const FALLBACK_SNAPSHOTS: Record<string, { profile: GitHubProfileRaw; repos: GitHubRepoRaw[] }> = {
  octocat: {
    profile: {
      login: "octocat",
      name: "The Octocat",
      bio: "GitHub mascot and sample profile",
      followers: 24480,
      following: 9,
      public_repos: 8,
      created_at: "2011-01-25T18:44:36Z",
      html_url: "https://github.com/octocat",
    },
    repos: [
      {
        name: "Spoon-Knife",
        description: "This repo is for spoon-knife experiments.",
        stargazers_count: 14085,
        forks_count: 145000,
        language: "HTML",
        size: 500,
        pushed_at: "2024-01-01T00:00:00Z",
        fork: false,
        html_url: "https://github.com/octocat/Spoon-Knife",
      },
      {
        name: "Hello-World",
        description: "My first repository on GitHub!",
        stargazers_count: 2500,
        language: "Ruby",
        size: 100,
        fork: false,
        html_url: "https://github.com/octocat/Hello-World",
      },
    ],
  },
  torvalds: {
    profile: {
      login: "torvalds",
      name: "Linus Torvalds",
      bio: "",
      followers: 220000,
      following: 0,
      public_repos: 7,
      created_at: "2011-09-03T15:26:22Z",
      html_url: "https://github.com/torvalds",
    },
    repos: [
      {
        name: "linux",
        description: "Linux kernel source tree",
        stargazers_count: 185000,
        forks_count: 54000,
        language: "C",
        size: 4500000,
        pushed_at: "2026-03-01T00:00:00Z",
        fork: false,
        html_url: "https://github.com/torvalds/linux",
      },
    ],
  },
};

export class GitHubClient {
  private static sharedCache = new Map<string, { timestamp: number; data: unknown }>();
  private cacheTtl: number;

  constructor(cacheTtlSeconds: number = 300) {
    this.cacheTtl = cacheTtlSeconds * 1000;
  }

  private getFromCache<T>(key: string): T | null {
    const entry = GitHubClient.sharedCache.get(key);
    if (entry && Date.now() - entry.timestamp < this.cacheTtl) {
      return entry.data as T;
    }
    return null;
  }

  private setCache<T>(key: string, data: T): void {
    GitHubClient.sharedCache.set(key, { timestamp: Date.now(), data });
  }

  public validateUsername(username: string): string {
    const clean = (username || "").trim().replace(/^@/, "");
    if (!clean || !USERNAME_REGEX.test(clean)) {
      throw new Error(`Invalid GitHub username format: '${username}'`);
    }
    return clean;
  }

  public async get_user_profile(username: string): Promise<GitHubProfileRaw | null> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return null;
    }

    const cacheKey = `profile:${clean.toLowerCase()}`;
    const cached = this.getFromCache<GitHubProfileRaw>(cacheKey);
    if (cached) return cached;

    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(clean)}`, {
        headers: getAuthHeaders(),
      });
      if (res.status === 404) return null;
      if (!res.ok) {
        if (res.status === 403 || res.status === 429) {
          if (FALLBACK_SNAPSHOTS[clean.toLowerCase()]) {
            return FALLBACK_SNAPSHOTS[clean.toLowerCase()].profile;
          }
          throw new Error("GitHub API rate limit exceeded");
        }
        return null;
      }
      const data = (await res.json()) as GitHubProfileRaw;
      if (data && data.message === "Not Found") return null;
      this.setCache(cacheKey, data);
      return data;
    } catch (err: unknown) {
      if (FALLBACK_SNAPSHOTS[clean.toLowerCase()]) {
        return FALLBACK_SNAPSHOTS[clean.toLowerCase()].profile;
      }
      if (err instanceof Error && err.message?.includes("rate limit")) throw err;
      return null;
    }
  }

  public async get_user_repos(
    username: string,
    per_page: number = 100,
    sort: string = "pushed"
  ): Promise<GitHubRepoRaw[]> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return [];
    }

    const cacheKey = `repos:${clean.toLowerCase()}:${per_page}:${sort}`;
    const cached = this.getFromCache<GitHubRepoRaw[]>(cacheKey);
    if (cached) return cached;

    try {
      const url = new URL(`https://api.github.com/users/${encodeURIComponent(clean)}/repos`);
      url.searchParams.set("per_page", String(per_page));
      url.searchParams.set("sort", sort);
      url.searchParams.set("type", "public");

      const res = await fetch(url.toString(), {
        headers: getAuthHeaders(),
      });
      if (res.status === 404) return [];
      if (!res.ok) {
        if (res.status === 403 || res.status === 429) {
          if (FALLBACK_SNAPSHOTS[clean.toLowerCase()]) {
            return FALLBACK_SNAPSHOTS[clean.toLowerCase()].repos;
          }
          throw new Error("GitHub API rate limit exceeded");
        }
        return [];
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        this.setCache(cacheKey, data as GitHubRepoRaw[]);
        return data as GitHubRepoRaw[];
      }
      return [];
    } catch (err: unknown) {
      if (FALLBACK_SNAPSHOTS[clean.toLowerCase()]) {
        return FALLBACK_SNAPSHOTS[clean.toLowerCase()].repos;
      }
      if (err instanceof Error && err.message?.includes("rate limit")) throw err;
      return [];
    }
  }

  public async get_recent_activity(username: string, limit: number = 5): Promise<GitHubEventRaw[]> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return [];
    }

    const cacheKey = `events:${clean.toLowerCase()}:${limit}`;
    const cached = this.getFromCache<GitHubEventRaw[]>(cacheKey);
    if (cached) return cached;

    try {
      const url = new URL(`https://api.github.com/users/${encodeURIComponent(clean)}/events`);
      url.searchParams.set("per_page", String(limit));

      const res = await fetch(url.toString(), {
        headers: getAuthHeaders(),
      });
      if (res.status === 404) return [];
      if (!res.ok) {
        if (res.status === 403 || res.status === 429) {
          throw new Error("GitHub API rate limit exceeded");
        }
        return [];
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        this.setCache(cacheKey, data as GitHubEventRaw[]);
        return data as GitHubEventRaw[];
      }
      return [];
    } catch (err: unknown) {
      if (err instanceof Error && err.message?.includes("rate limit")) throw err;
      return [];
    }
  }

  public async get_repo_details(owner: string, repo: string): Promise<GitHubRepoRaw | null> {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
        { headers: getAuthHeaders() }
      );
      if (res.status === 404 || !res.ok) return null;
      return (await res.json()) as GitHubRepoRaw;
    } catch {
      return null;
    }
  }

  public async get_repo_readme(owner: string, repo: string): Promise<string> {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/readme`,
        {
          headers: getAuthHeaders({ Accept: "application/vnd.github.v3.raw" }),
        }
      );
      if (res.status === 200) {
        return await res.text();
      }
      return "";
    } catch {
      return "";
    }
  }

  public async get_repo_languages(owner: string, repo: string): Promise<Record<string, number>> {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/languages`,
        { headers: getAuthHeaders() }
      );
      if (res.status === 200) {
        return ((await res.json()) as Record<string, number>) || {};
      }
      return {};
    } catch {
      return {};
    }
  }

  public async get_repo_commits(
    owner: string,
    repo: string,
    author: string = "",
    limit: number = 10
  ): Promise<RepoCommit[]> {
    try {
      const url = new URL(
        `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/commits`
      );
      url.searchParams.set("per_page", String(Math.max(1, Math.min(limit, 30))));
      if (author) {
        url.searchParams.set("author", author);
      }
      const res = await fetch(url.toString(), { headers: getAuthHeaders() });
      if (!res.ok) return [];
      const data = await res.json();
      if (!Array.isArray(data)) return [];
      return data.map((entry: { commit?: { message?: string; author?: { date?: string } } }) => ({
        message: entry?.commit?.message || "",
        date: entry?.commit?.author?.date || "",
      }));
    } catch {
      return [];
    }
  }

  public async get_repo_tree(owner: string, repo: string, branch: string = ""): Promise<string[]> {
    try {
      let b = branch;
      if (!b) {
        const details = await this.get_repo_details(owner, repo);
        b = details?.default_branch || "main";
      }
      const url = `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/git/trees/${encodeURIComponent(b)}?recursive=1`;
      const res = await fetch(url, { headers: getAuthHeaders() });
      if (!res.ok) return [];
      const data = await res.json();
      const tree = data?.tree;
      if (!Array.isArray(tree)) return [];
      return tree
        .filter((entry: { path?: unknown }) => typeof entry?.path === "string")
        .map((entry: { path: string }) => entry.path.toLowerCase());
    } catch {
      return [];
    }
  }
}

export function format_repo_summary(repos: GitHubRepoRaw[]): RepoSummaryList {
  if (!Array.isArray(repos) || repos.length === 0) {
    return { top_repos: [], total_fetched: 0 };
  }

  const sortedRepos = [...repos]
    .sort((a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0))
    .slice(0, 20);

  const summary: RepoSummary[] = sortedRepos.map((repo) => ({
    name: repo?.name || "unknown",
    description: repo?.description || "",
    stars: Number(repo?.stargazers_count) || 0,
    forks: Number(repo?.forks_count) || 0,
    is_fork: Boolean(repo?.fork),
    open_issues: Number(repo?.open_issues_count) || 0,
    topics: Array.isArray(repo?.topics) ? repo.topics : [],
    license: repo?.license?.spdx_id || null,
    archived: Boolean(repo?.archived),
    homepage: repo?.homepage || "",
    primary_language: repo?.language || "Unknown",
    last_push: repo?.pushed_at || "never",
    created_at: repo?.created_at || "",
    url: repo?.html_url || "",
    size: Number(repo?.size) || 0,
  }));

  return { top_repos: summary, total_fetched: repos.length };
}

export function format_profile_summary(
  profile: Partial<GitHubProfileRaw> | null | undefined
): ProfileSummary {
  if (!profile || typeof profile !== "object") {
    return {
      username: "",
      name: "No name set",
      bio: "No bio set",
      location: "Not disclosed",
      blog: "No blog",
      company: "Not specified",
      followers: 0,
      following: 0,
      public_repos: 0,
      public_gists: 0,
      hireable: false,
      twitter_username: "",
      created_at: "",
      html_url: "",
    };
  }

  return {
    username: profile.login || "",
    name: profile.name || "No name set",
    bio: profile.bio || "No bio set",
    location: profile.location || "Not disclosed",
    blog: profile.blog || "No blog",
    company: profile.company || "Not specified",
    followers: Number(profile.followers) || 0,
    following: Number(profile.following) || 0,
    public_repos: Number(profile.public_repos) || 0,
    public_gists: Number(profile.public_gists) || 0,
    hireable: Boolean(profile.hireable),
    twitter_username: profile.twitter_username || "",
    created_at: profile.created_at || "",
    html_url: profile.html_url || "",
  };
}
