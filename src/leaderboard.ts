import { LeaderboardEntry } from "./types.js";

const leaderboardStore: LeaderboardEntry[] = [];

export function saveToLeaderboard(username: string, archetype: string, roastPreview: string): void {
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

export function getLeaderboard(): LeaderboardEntry[] {
  return leaderboardStore.slice(0, 10);
}

export function getCachedBadge(username: string): { archetype: string; preview: string } | null {
  const item = leaderboardStore.find(
    (entry) => entry.username.toLowerCase() === username.toLowerCase()
  );
  if (item) {
    return { archetype: item.archetype || "Roasted Dev", preview: item.roast_preview || "" };
  }
  return null;
}
