import assert from "assert";
import { GitHubClient, format_profile_summary, format_repo_summary } from "../src/githubClient.js";

/**
 * Unit Test Suite
 * Tests isolated components, utility functions, edge case inputs, and data transformers.
 */
export function runUnitTests(): { passed: number; total: number } {
  console.log("🧩 Running Core Unit Test Suite...");
  let passed = 0;
  let total = 0;

  function unitTest(name: string, fn: () => void) {
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

  const client = new GitHubClient();

  // Test 1: Username Validation - Standard
  unitTest("Username validation: Accepts standard alphanumeric usernames", () => {
    assert.strictEqual(client.validateUsername("octocat"), "octocat");
    assert.strictEqual(client.validateUsername("torvalds"), "torvalds");
    assert.strictEqual(client.validateUsername("user-123"), "user-123");
  });

  // Test 2: Username Validation - Leading @ Strip
  unitTest("Username validation: Strips leading '@' automatically", () => {
    assert.strictEqual(client.validateUsername("@torvalds"), "torvalds");
    assert.strictEqual(client.validateUsername("@octocat"), "octocat");
  });

  // Test 3: Username Validation - Rejections
  unitTest(
    "Username validation: Rejects path traversal, whitespace, empty, and invalid characters",
    () => {
      assert.throws(() => client.validateUsername(""), /Invalid/i);
      assert.throws(() => client.validateUsername("   "), /Invalid/i);
      assert.throws(() => client.validateUsername("../etc/passwd"), /Invalid/i);
      assert.throws(() => client.validateUsername("user/repo"), /Invalid/i);
      assert.throws(() => client.validateUsername("user name"), /Invalid/i);
      assert.throws(() => client.validateUsername("-invalidleading"), /Invalid/i);
      assert.throws(() => client.validateUsername("invalidtrailing-"), /Invalid/i);
    }
  );

  // Test 4: Format profile summary with null input
  unitTest("Profile summary formatter: Handles null and undefined inputs safely", () => {
    const res = format_profile_summary(null);
    assert.strictEqual(res.username, "");
    assert.strictEqual(res.followers, 0);
    assert.strictEqual(res.public_repos, 0);
    assert.strictEqual(res.bio, "No bio set");
  });

  // Test 5: Format profile summary with complete data
  unitTest("Profile summary formatter: Correctly maps profile fields", () => {
    const raw = {
      login: "developer",
      name: "Dev Elo",
      bio: "Crafting resilient microservices",
      public_repos: 42,
      followers: 1337,
      created_at: "2018-05-12T10:00:00Z",
    };
    const res = format_profile_summary(raw);
    assert.strictEqual(res.username, "developer");
    assert.strictEqual(res.name, "Dev Elo");
    assert.strictEqual(res.followers, 1337);
    assert.strictEqual(res.public_repos, 42);
    assert(res.bio.includes("resilient"));
  });

  // Test 6: Repo summary formatter with empty list
  unitTest("Repo summary formatter: Handles empty repository lists cleanly", () => {
    const res = format_repo_summary([]);
    assert.strictEqual(res.total_fetched, 0);
    assert.strictEqual(res.top_repos.length, 0);
  });

  // Test 7: Repo summary formatter with multiple repositories and star sorting
  unitTest("Repo summary formatter: Ranks repositories by star count descending", () => {
    const repos = [
      { name: "repo-low", stargazers_count: 5, language: "Go", fork: false },
      { name: "repo-high", stargazers_count: 500, language: "TypeScript", fork: false },
      { name: "repo-mid", stargazers_count: 50, language: "Python", fork: false },
    ];
    const res = format_repo_summary(repos);
    assert.strictEqual(res.total_fetched, 3);
    assert.strictEqual(res.top_repos[0].name, "repo-high");
    assert.strictEqual(res.top_repos[0].stars, 500);
    assert.strictEqual(res.top_repos[1].name, "repo-mid");
    assert.strictEqual(res.top_repos[2].name, "repo-low");
  });

  // Test 8: Repo summary metadata and primary language mapping
  unitTest("Repo summary formatter: Correctly preserves repository metadata and languages", () => {
    const repos = [
      { name: "r1", language: "Rust", stargazers_count: 10, fork: false },
      { name: "r2", language: "TypeScript", stargazers_count: 15, fork: false },
    ];
    const res = format_repo_summary(repos);
    assert.strictEqual(res.top_repos[0].primary_language, "TypeScript");
    assert.strictEqual(res.top_repos[1].primary_language, "Rust");
  });

  console.log(`  ✨ ${passed}/${total} Core Unit tests passed.\n`);
  return { passed, total };
}
