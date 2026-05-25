// Thin wrapper over the StoryTree /api endpoints.
const API = "/api";

async function jget(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`GET ${url} -> ${r.status}`);
  return r.json();
}

export const api = {
  listStories: () => jget(`${API}/stories`),
  getStory: (id) => jget(`${API}/stories/${id}`),
  getStoryTree: (id) => jget(`${API}/stories/${id}/tree`),
  getDescription: () => jget(`${API}/stories/description`),
  getScene: (storyId, { choiceId = null, sceneId = null } = {}) => {
    const params = new URLSearchParams();
    if (choiceId != null) params.set("choice_id", choiceId);
    if (sceneId != null) params.set("scene_id", sceneId);
    const qs = params.toString();
    return jget(`${API}/stories/${storyId}/scene${qs ? "?" + qs : ""}`);
  },
  createStory: async (payload) => {
    const r = await fetch(`${API}/stories`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(`create story -> ${r.status}`);
    return r.json();
  },
};
