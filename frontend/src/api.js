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
  getDescription: () => jget(`${API}/stories/description`),
  getScene: (storyId, choiceId = null) =>
    jget(
      choiceId == null
        ? `${API}/stories/${storyId}/scene`
        : `${API}/stories/${storyId}/scene?choice_id=${choiceId}`
    ),
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
