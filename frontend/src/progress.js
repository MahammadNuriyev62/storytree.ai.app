// Per-story play-progress, persisted to localStorage so the reader can
// continue from where they left off across sessions.
//
// Stored under one key per story: `storytree:progress:{storyId}` →
//   { sceneId: number, page: number, ts: number (epoch ms) }
//
// Writes happen as the SPA navigates (Play.jsx calls saveProgress on every
// scene+page sync). Reads happen on the story details page (to render a
// Continue button) and the home page (to badge stories that have progress).

const KEY = (storyId) => `storytree:progress:${storyId}`;

export function saveProgress(storyId, sceneId, page) {
  if (storyId == null || sceneId == null) return;
  try {
    localStorage.setItem(
      KEY(storyId),
      JSON.stringify({ sceneId, page: page ?? 1, ts: Date.now() }),
    );
  } catch {
    // QuotaExceeded / disabled storage — silently drop. The reader can
    // still play; they just won't get the resume affordance.
  }
}

export function loadProgress(storyId) {
  if (storyId == null) return null;
  try {
    const raw = localStorage.getItem(KEY(storyId));
    if (!raw) return null;
    const obj = JSON.parse(raw);
    if (!obj || typeof obj.sceneId !== "number") return null;
    return obj;
  } catch {
    return null;
  }
}

export function clearProgress(storyId) {
  if (storyId == null) return;
  try {
    localStorage.removeItem(KEY(storyId));
  } catch {}
}
