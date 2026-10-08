/**
 * GitHub API client for fetching public profile and repository data.
 *
 * Uses unauthenticated GitHub API (60 requests/hr limit for public data).
 * All data fetched is publicly available - no authentication required.
 * Optionally uses GITHUB_TOKEN env var for higher rate limits (5,000 req/hr).
 */

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

export class GitHubClient {
  private static sharedCache = new Map<string, { timestamp: number; data: any }>();
  private cacheTtl: number;

  constructor(cacheTtlSeconds: number = 300) {
    this.cacheTtl = cacheTtlSeconds * 1000;
  }

  private getFromCache(key: string): any | null {
    const entry = GitHubClient.sharedCache.get(key);
    if (entry && Date.now() - entry.timestamp < this.cacheTtl) {
      return entry.data;
    }
    return null;
  }

  private setCache(key: string, data: any): void {
    GitHubClient.sharedCache.set(key, { timestamp: Date.now(), data });
  }

  public validateUsername(username: string): string {
    const clean = (username || "").trim().replace(/^@/, "");
    if (!clean || !USERNAME_REGEX.test(clean)) {
      throw new Error(`Invalid GitHub username format: '${username}'`);
    }
    return clean;
  }

  public async get_user_profile(username: string): Promise<any | null> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return null;
    }

    const cacheKey = `profile:${clean.toLowerCase()}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const res = await fetch(`https://api.github.com/users/${encodeURIComponent(clean)}`, {
        headers: getAuthHeaders(),
      });
      if (res.status === 404) return null;
      if (!res.ok) {
        if (res.status === 403 || res.status === 429) {
          throw new Error("GitHub API rate limit exceeded");
        }
        return null;
      }
      const data = await res.json();
      if (data && data.message === "Not Found") return null;
      this.setCache(cacheKey, data);
      return data;
    } catch (err: any) {
      if (err.message?.includes("rate limit")) throw err;
      return null;
    }
  }

  public async get_user_repos(
    username: string,
    per_page: number = 100,
    sort: string = "pushed"
  ): Promise<any[] | null> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return [];
    }

    const cacheKey = `repos:${clean.toLowerCase()}:${per_page}:${sort}`;
    const cached = this.getFromCache(cacheKey);
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
          throw new Error("GitHub API rate limit exceeded");
        }
        return null;
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        this.setCache(cacheKey, data);
        return data;
      }
      return [];
    } catch (err: any) {
      if (err.message?.includes("rate limit")) throw err;
      return [];
    }
  }

  public async get_recent_activity(username: string, limit: number = 5): Promise<any[] | null> {
    let clean: string;
    try {
      clean = this.validateUsername(username);
    } catch {
      return [];
    }

    const cacheKey = `events:${clean.toLowerCase()}:${limit}`;
    const cached = this.getFromCache(cacheKey);
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
        return null;
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        this.setCache(cacheKey, data);
        return data;
      }
      return [];
    } catch (err: any) {
      if (err.message?.includes("rate limit")) throw err;
      return [];
    }
  }

  public async get_repo_details(owner: string, repo: string): Promise<any | null> {
    try {
      const res = await fetch(
        `https://api.github.com/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
        { headers: getAuthHeaders() }
      );
      if (res.status === 404) return null;
      if (!res.ok) return null;
      return await res.json();
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
        return (await res.json()) || {};
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
  ): Promise<Array<{ message: string; date: string }>> {
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
      return data.map((entry: any) => ({
        message: entry?.commit?.message || "",
        date: entry?.commit?.author?.date || "",
      }));
    } catch {
      return [];
    }
  }

  public async get_repo_tree(
    owner: string,
    repo: string,
    branch: string = ""
  ): Promise<string[]> {
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
        .filter((entry: any) => typeof entry?.path === "string")
        .map((entry: any) => entry.path.toLowerCase());
    } catch {
      return [];
    }
  }
}

export function format_repo_summary(repos: any[]): { top_repos: any[]; total_fetched: number } {
  if (!Array.isArray(repos) || repos.length === 0) {
    return { top_repos: [], total_fetched: 0 };
  }

  const sortedRepos = [...repos]
    .sort((a, b) => (Number(b?.stargazers_count) || 0) - (Number(a?.stargazers_count) || 0))
    .slice(0, 20);

  const summary = sortedRepos.map((repo) => ({
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

export function format_profile_summary(profile: any): Record<string, any> {
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
