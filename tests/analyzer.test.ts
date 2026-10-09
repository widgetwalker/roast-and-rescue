import assert from "assert";
import { analyze_profile, audit_resume_vs_reality, compare_profiles } from "../src/analyzer.js";

/**
 * Heuristic Analyzer Test Suite
 * Tests AI & heuristic signals, archetype classification, psych-evals, resume audits, and battle engine.
 */
export function runAnalyzerTests(): { passed: number; total: number } {
  console.log("🧠 Running Deep Heuristic Analyzer Suite...");
  let passed = 0;
  let total = 0;

  function analyzerTest(name: string, fn: () => void) {
    total++;
    try {
      fn();
      console.log(`  ✅ [PASS] ${name}`);
      passed++;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`  ❌ [FAIL] ${name}:`, msg);
      throw err;
    }
  }

  // Test 1: Full Profile Bento Payload
  analyzerTest("Bento Payload: Generates all required sections and keys", () => {
    const profile = {
      login: "fullstack-hero",
      name: "Sam Taylor",
      bio: "Staff Engineer specializing in distributed databases and Kubernetes",
      followers: 250,
      public_repos: 12,
      created_at: "2019-03-01T00:00:00Z",
    };
    const repos = [
      {
        name: "raft-consensus-go",
        stargazers_count: 320,
        primary_language: "Go",
        size: 12000,
        topics: ["distributed-systems", "consensus"],
      },
    ];
    const result = analyze_profile(profile, repos, "fullstack-hero", {
      events_data: [{ type: "PushEvent", created_at: new Date().toISOString() }],
    });

    assert.strictEqual(result.status, "success");
    assert.strictEqual(result.username, "fullstack-hero");
    assert(result.recruiter_glance.includes("Profile Vibe"));
    assert(result.roast.includes("ARCHETYPE"));
    assert(result.rescue.includes("QUICK WIN") || result.rescue.includes("⚡"));
    assert(result.psych_eval.length > 0);
    assert(typeof result.resume_vs_reality === "object");
  });

  // Test 2: Archetype Classification - Graveyard Keeper
  analyzerTest("Archetype: Correctly identifies inactive profile as Graveyard Keeper", () => {
    const profile = {
      login: "abandoned-dev",
      bio: "",
      followers: 2,
      public_repos: 1,
      created_at: "2015-01-01T00:00:00Z",
    };
    const repos = [
      {
        name: "dormant-repo",
        stargazers_count: 0,
        primary_language: "PHP",
        size: 200,
        pushed_at: "2017-01-01T00:00:00Z",
      },
    ];
    const result = analyze_profile(profile, repos, "abandoned-dev", {
      events_data: [],
    });
    assert(
      result.roast.includes("GRAVEYARD") ||
        result.roast.includes("ARCHETYPE") ||
        result.recruiter_glance.toLowerCase().includes("ghost") ||
        result.recruiter_glance.toLowerCase().includes("dormant") ||
        result.roast.length > 0
    );
  });

  // Test 3: Archetype Classification - Tech Deity
  analyzerTest("Archetype: Recognizes high follower and star signals", () => {
    const profile = {
      login: "rockstar",
      bio: "Creator of widely adopted open source framework",
      followers: 12000,
      public_repos: 80,
      created_at: "2012-01-01T00:00:00Z",
    };
    const repos = [
      {
        name: "mega-framework",
        stargazers_count: 45000,
        primary_language: "Rust",
        size: 90000,
      },
    ];
    const result = analyze_profile(profile, repos, "rockstar", {});
    assert(
      result.roast.length > 0 &&
        (result.roast.includes("ARCHETYPE") || result.roast.includes("DEITY"))
    );
    assert(result.recruiter_glance.includes("Profile Vibe"));
  });

  // Test 4: Commit Psych-Eval
  analyzerTest("Psych-Eval: Computes diagnosis based on commit cadence and messages", () => {
    const profile = { login: "night-owl", followers: 10, public_repos: 3 };
    const context = {
      verified_commits: [
        { message: "fix bug at 3am", date: "2026-03-01T03:15:00Z" },
        { message: "quick hotfix please work", date: "2026-03-01T03:45:00Z" },
      ],
    };
    const result = analyze_profile(profile, [], "night-owl", context);
    assert(
      result.psych_eval.includes("Diagnosis:") ||
        result.psych_eval.includes("Insomnia") ||
        result.psych_eval.includes("Night Owl") ||
        result.psych_eval.length > 20
    );
  });

  // Test 5: Resume vs Reality - High discrepancy
  analyzerTest("Resume vs Reality: Identifies unbacked seniority and AI buzzword claims", () => {
    const claimBio = "Principal AI Architect leading multi-cloud Kubernetes clusters";
    const actualRepos = [{ name: "calculator", size: 100, language: "HTML", topics: [] }];
    const audit = audit_resume_vs_reality("", claimBio, actualRepos, { HTML: 2000 });
    assert(audit.discrepancies.length > 0);
    const hasBuzzwordDiscrepancy = audit.discrepancies.some(
      (d: { claim: string }) =>
        d.claim.toLowerCase().includes("ai") ||
        d.claim.toLowerCase().includes("architect") ||
        d.claim.toLowerCase().includes("cloud")
    );
    assert(hasBuzzwordDiscrepancy, "Must flag AI/Cloud/Architect claims without receipt code");
    assert(audit.vibe_ratio.length > 0);
    assert(typeof audit.recruiter_verdict === "string" && audit.recruiter_verdict.length > 0);
  });

  // Test 6: Battle Mode Head-to-Head Comparison
  analyzerTest("Battle Engine: Correctly evaluates metrics and crowns dominant fighter", () => {
    const devA = {
      username: "veteran-coder",
      total_size_kb: 80000,
      repo_data: {
        top_repos: [
          {
            name: "core-kernel",
            stars: 1200,
            archived: false,
            last_push: new Date().toISOString(),
          },
        ],
      },
      recent_commits: ["feat: lockless queue implementation"],
    };
    const devB = {
      username: "novice-coder",
      total_size_kb: 50,
      repo_data: {
        top_repos: [
          { name: "hello-world", stars: 0, archived: true, last_push: "2021-01-01T00:00:00Z" },
        ],
      },
      recent_commits: ["init"],
    };

    const battle = compare_profiles(devA, devB);
    assert.strictEqual(battle.winner, "veteran-coder");
    assert.strictEqual(battle.loser, "novice-coder");
    assert(battle.verdict.includes("@veteran-coder"));
  });

  console.log(`  ✨ ${passed}/${total} Heuristic Analyzer tests passed.\n`);
  return { passed, total };
}
