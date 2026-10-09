/**
 * Domain types and strict interfaces for GitHub Roast & Rescue.
 * Provides complete type safety across API clients, heuristics, and controllers.
 */

export interface GitHubProfileRaw {
  login: string;
  id?: number;
  name?: string | null;
  bio?: string | null;
  company?: string | null;
  blog?: string | null;
  location?: string | null;
  email?: string | null;
  hireable?: boolean | null;
  twitter_username?: string | null;
  public_repos: number;
  public_gists?: number;
  followers: number;
  following: number;
  created_at: string;
  updated_at?: string;
  html_url: string;
  avatar_url?: string;
  message?: string;
}

export interface GitHubRepoRaw {
  id?: number;
  name: string;
  full_name?: string;
  description?: string | null;
  fork: boolean;
  html_url: string;
  url?: string;
  stargazers_count: number;
  watchers_count?: number;
  forks_count?: number;
  language?: string | null;
  open_issues_count?: number;
  pushed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  size?: number;
  archived?: boolean;
  disabled?: boolean;
  homepage?: string | null;
  topics?: string[];
  license?: {
    key?: string;
    name?: string;
    spdx_id?: string | null;
  } | null;
  default_branch?: string;
}

export interface GitHubEventRaw {
  id?: string;
  type?: string;
  created_at?: string;
  repo?: {
    id?: number;
    name?: string;
    url?: string;
  };
  payload?: Record<string, unknown>;
}

export interface RepoCommit {
  message: string;
  date: string;
}

export interface ProfileSummary {
  username: string;
  name: string;
  bio: string;
  location: string;
  blog: string;
  company: string;
  followers: number;
  following: number;
  public_repos: number;
  public_gists: number;
  hireable: boolean;
  twitter_username: string;
  created_at: string;
  html_url: string;
}

export interface RepoSummary {
  name: string;
  description: string;
  stars: number;
  forks: number;
  is_fork: boolean;
  open_issues: number;
  topics: string[];
  license: string | null;
  archived: boolean;
  homepage: string;
  primary_language: string;
  last_push: string;
  created_at: string;
  url: string;
  size: number;
}

export interface RepoSummaryList {
  top_repos: RepoSummary[];
  total_fetched: number;
}

export interface AnalysisEvidence {
  aggLanguages: Record<string, number>;
  skeletons: Record<string, string[]>;
}

export interface AnalysisContextOptions {
  events_data?: GitHubEventRaw[] | null;
  readme_content?: string;
  repo_languages?: Record<string, number> | null;
  verified_commits?: RepoCommit[];
  profile_readme?: string;
  audit_languages?: Record<string, number>;
  repo_files?: Record<string, string[]>;
}

export interface ResumeClaimValidation {
  skill: string;
  status: "verified" | "exaggerated" | "missing" | "unverified";
  details: string;
  evidence?: string;
}

export interface ResumeAuditResult {
  source: string;
  detected_skills: string[];
  verified_skills: string[];
  exaggerated_claims: string[];
  score: number;
  verdict: string;
  claim_breakdown: ResumeClaimValidation[];
  recommendations: string[];
}

export interface RoastAnalysis {
  username: string;
  archetype: string;
  seniority: string;
  specialty: string;
  years_on_github: number;
  total_stars: number;
  total_forks: number;
  active_repos: number;
  recruiter_glance: string;
  roast: string;
  rescue: string;
  psych_eval: string;
  resume_vs_reality: ResumeAuditResult;
  stats: {
    total_stars: number;
    total_forks: number;
    followers: number;
    following: number;
    repos_analyzed: number;
    primary_language: string;
    language_breakdown: Record<string, number>;
  };
}

export interface BattleCombatantStats {
  username: string;
  archetype: string;
  score: number;
  stars: number;
  repos: number;
  followers: number;
  roast_quote: string;
}

export interface BattleResult {
  winner: string;
  loser: string;
  margin: string;
  breakdown: {
    user1: BattleCombatantStats;
    user2: BattleCombatantStats;
  };
  battle_roast: string;
  archetypes?: Record<string, string>;
}

export interface LeaderboardEntry {
  username: string;
  archetype: string;
  roast_preview: string;
  timestamp: string;
}

export interface BadgeContext {
  archetype: string;
  preview: string;
  roasted: boolean;
}
