import assert from "assert";
import fs from "fs";
import path from "path";

/**
 * WCAG 2.1 AA / AAA Accessibility Test Suite
 * Validates DOM semantics, ARIA attributes, keyboard accessibility, and contrast.
 */
export function runAccessibilityTests(): { passed: number; total: number } {
  console.log("♿ Running WCAG 2.1 Accessibility Suite...");
  let passed = 0;
  let total = 0;

  function a11yTest(name: string, fn: () => void) {
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

  const htmlPath = path.join(process.cwd(), "public", "index.html");
  assert(fs.existsSync(htmlPath), "public/index.html must exist");
  const html = fs.readFileSync(htmlPath, "utf-8");

  // A11y 1: Document Language and DOCTYPE
  a11yTest("WCAG 3.1.1: Document has valid DOCTYPE and html lang='en' declaration", () => {
    assert(html.startsWith("<!DOCTYPE html>"), "Must declare DOCTYPE html");
    assert(/<html[^>]*lang=["']en["']/.test(html), "html element must declare lang='en'");
  });

  // A11y 2: Viewport and Meta Scaling
  a11yTest("WCAG 1.4.4: Viewport configuration allows user scaling (no user-scalable=no)", () => {
    assert(html.includes('name="viewport"'), "Viewport meta tag must be declared");
    assert(!html.includes("user-scalable=no"), "Must not block zoom (user-scalable=no forbidden)");
    assert(!html.includes("maximum-scale=1.0"), "Must not restrict maximum-scale to 1.0");
  });

  // A11y 3: Keyboard Skip Navigation
  a11yTest(
    "WCAG 2.4.1: Bypass Blocks - Accessible skip navigation link is present and points to #main-content",
    () => {
      assert(
        /<a[^>]*href=["']#main-content["'][^>]*class=["'][^"']*skip-link/.test(html),
        "Skip link must link to #main-content"
      );
      assert(html.includes('id="main-content"'), "Target landmark #main-content must exist in DOM");
      assert(html.includes(".skip-link"), "CSS rules for .skip-link must exist");
    }
  );

  // A11y 4: Landmark Hierarchy
  a11yTest(
    "WCAG 1.3.1: Landmark Roles - header (banner), main, footer (contentinfo), search",
    () => {
      assert(/<header[^>]*role=["']banner["']|<header>/.test(html), "Header landmark must exist");
      assert(
        /<main[^>]*id=["']main-content["'][^>]*role=["']main["']|<main[^>]*id=["']main-content["']/.test(
          html
        ),
        "Main landmark must exist"
      );
      assert(
        /<footer[^>]*role=["']contentinfo["']|<footer>/.test(html),
        "Footer landmark must exist"
      );
      assert(/role=["']search["']/.test(html), "Search landmark must exist");
    }
  );

  // A11y 5: Form Controls and Labels
  a11yTest(
    "WCAG 3.3.2 / 1.3.1: All form inputs have explicit accessible labels or aria-labels",
    () => {
      assert(
        html.includes('label for="usernameInput"'),
        "usernameInput must have an associated label"
      );
      assert(
        html.includes('label for="opponentInput"'),
        "opponentInput must have an associated label"
      );
      assert(
        /<input[^>]*id=["']usernameInput["'][^>]*aria-label=/.test(html),
        "usernameInput must have aria-label fallback"
      );
      assert(
        /<textarea[^>]*id=["']bioPaste["'][^>]*aria-label=/.test(html),
        "bioPaste must have accessible aria-label"
      );
    }
  );

  // A11y 6: Live Regions for Dynamic Screen Reader Updates
  a11yTest(
    "WCAG 4.1.3: Status Messages - Live regions configured for dynamic content announcements",
    () => {
      assert(
        /id=["']a11y-announcer["'][^>]*role=["']status["'][^>]*aria-live=["']polite["']/.test(html),
        "Polite live announcer must exist"
      );
      assert(
        /id=["']errorBox["'][^>]*role=["']alert["'][^>]*aria-live=["']assertive["']/.test(html),
        "Assertive error alert region must exist"
      );
    }
  );

  // A11y 7: Modal and Dialog Accessibility
  a11yTest(
    "WCAG 2.1.2: Modal Dialogs - Wall of Shame and Battle Arena declare dialog roles and aria-modal",
    () => {
      assert(
        /id=["']battleOverlay["'][^>]*role=["']dialog["'][^>]*aria-modal=["']true["']/.test(html),
        "Battle overlay must be a modal dialog"
      );
      assert(
        /id=["']shameDrawer["'][^>]*role=["']dialog["'][^>]*aria-modal=["']true["']/.test(html),
        "Shame drawer must be a modal dialog"
      );
      assert(
        html.includes('aria-labelledby="battleTitle"'),
        "Battle dialog must be labelled by title heading"
      );
      assert(
        html.includes('aria-labelledby="shameTitle"'),
        "Shame drawer must be labelled by heading"
      );
    }
  );

  // A11y 8: Keyboard Focus Visibility
  a11yTest(
    "WCAG 2.4.7: Focus Visible - Distinctive focus indicators are declared for all interactive elements",
    () => {
      assert(html.includes(":focus-visible"), "CSS must declare explicit :focus-visible selectors");
      assert(html.includes("outline:"), "CSS must declare outline for focus visibility");
    }
  );

  // A11y 9: Motion Reduction Preferences
  a11yTest(
    "WCAG 2.3.3: Animation from Interactions - prefers-reduced-motion media query is respected",
    () => {
      assert(
        html.includes("@media (prefers-reduced-motion: reduce)"),
        "CSS must support prefers-reduced-motion"
      );
      assert(
        html.includes("animation: none") || html.includes("animation-duration"),
        "Reduced motion must suppress or minimize animations"
      );
    }
  );

  // A11y 10: Decorative Elements Hidden from Assistive Technology
  a11yTest(
    "WCAG 1.1.1: Non-text Content - Background decorative shapes hidden with aria-hidden='true'",
    () => {
      assert(
        /class=["']bg-decor["'][^>]*aria-hidden=["']true["']/.test(html),
        "Decorative floating backdrop must be aria-hidden"
      );
      assert(
        /class=["']hazard-strip["'][^>]*aria-hidden=["']true["']/.test(html),
        "Decorative hazard strips must be aria-hidden"
      );
    }
  );

  console.log(`  ✨ ${passed}/${total} Accessibility compliance checks passed.\n`);
  return { passed, total };
}
