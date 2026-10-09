import { GitHubClient } from "./githubClient.js";
import { getCachedBadge } from "./leaderboard.js";
import { BadgeContext } from "./types.js";

export async function badgeContext(client: GitHubClient, username: string): Promise<BadgeContext> {
  const cached = getCachedBadge(username);
  if (cached) {
    return { archetype: cached.archetype, preview: cached.preview, roasted: true };
  }
  try {
    const profile = await client.get_user_profile(username);
    if (!profile) {
      return {
        archetype: "UNROASTED",
        preview: "Run a roast to earn an archetype",
        roasted: false,
      };
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

export function buildBadgeSvg(
  username: string,
  archetype: string,
  preview: string,
  roasted: boolean
): string {
  const esc = (s: string) =>
    (s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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
