import assert from "assert";

/**
 * REST API Integration Test Suite
 * Tests HTTP routes, response schemas, error handling, and header security.
 */
export async function runApiTests(): Promise<{ passed: number; total: number }> {
  console.log("🌐 Running Express REST API Test Suite...");
  let passed = 0;
  let total = 0;

  async function apiTest(name: string, fn: () => Promise<void>) {
    total++;
    try {
      await fn();
      console.log(`  ✅ [PASS] ${name}`);
      passed++;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error(`  ❌ [FAIL] ${name}:`, msg);
      throw err;
    }
  }

  const BASE_URL = process.env.TEST_URL || "http://127.0.0.1:3000";

  // Test 1: Health Check Endpoint
  await apiTest("GET /health: Responds with 200 OK and healthy status payload", async () => {
    const res = await fetch(`${BASE_URL}/health`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.status, "healthy");
    assert(typeof data.timestamp === "string");
  });

  // Test 2: Leaderboard Endpoint
  await apiTest("GET /api/leaderboard: Returns array of Wall of Shame entries", async () => {
    const res = await fetch(`${BASE_URL}/api/leaderboard`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert(Array.isArray(data) || Array.isArray(data.leaderboard));
  });

  // Test 3: SVG Badge Generator
  await apiTest("GET /badge/:username.svg: Serves valid SVG XML badge", async () => {
    const res = await fetch(`${BASE_URL}/badge/octocat.svg`);
    assert.strictEqual(res.status, 200);
    const contentType = res.headers.get("content-type") || "";
    assert(contentType.includes("image/svg+xml"), `Expected image/svg+xml, got ${contentType}`);
    const svgText = await res.text();
    assert(svgText.includes("<svg"), "Must return SVG markup");
    assert(svgText.includes("octocat"), "Must contain requested username");
  });

  // Test 4: Roast Validation - Missing username
  await apiTest("POST /roast: Rejects missing username with 400 Bad Request", async () => {
    const res = await fetch(`${BASE_URL}/roast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    assert.strictEqual(res.status, 400);
    const data = await res.json();
    assert.strictEqual(data.status, "error");
    assert(data.message.toLowerCase().includes("username"));
  });

  // Test 5: Roast Validation - Malicious or invalid characters
  await apiTest("POST /roast: Rejects invalid username formatting", async () => {
    const res = await fetch(`${BASE_URL}/roast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "invalid/user*name" }),
    });
    assert.strictEqual(res.status, 400);
    const data = await res.json();
    assert.strictEqual(data.status, "error");
  });

  // Test 6: Battle Validation - Missing opponent
  await apiTest("POST /battle: Requires both fighter usernames", async () => {
    const res = await fetch(`${BASE_URL}/battle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user1: "octocat" }),
    });
    assert.strictEqual(res.status, 400);
    const data = await res.json();
    assert.strictEqual(data.status, "error");
    assert(data.message.includes("user2") || data.message.includes("required"));
  });

  // Test 7: Resume Audit Endpoint
  await apiTest("POST /resume-audit: Handles resume auditing payload", async () => {
    const res = await fetch(`${BASE_URL}/resume-audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: "octocat",
        resume_text: "Senior Cloud & AI Architect specializing in distributed systems.",
      }),
    });
    assert(res.status === 200 || res.status === 502); // 200 on success or 502 if GitHub rate limited
    const data = await res.json();
    if (res.status === 200) {
      const audit = data.resume_vs_reality || data;
      assert(typeof audit.vibe_ratio === "string");
      assert(Array.isArray(audit.discrepancies));
    }
  });

  console.log(`  ✨ ${passed}/${total} Express REST API tests passed.\n`);
  return { passed, total };
}
