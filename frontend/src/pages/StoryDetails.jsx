import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { loadProgress, clearProgress } from "../progress.js";

export default function StoryDetails() {
  const { id } = useParams();
  const [story, setStory] = useState(null);
  const [err, setErr] = useState(null);
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    api.getStory(id).then(setStory).catch((e) => setErr(String(e)));
    setProgress(loadProgress(id));
  }, [id]);

  const handleRestart = () => {
    clearProgress(id);
    setProgress(null);
  };

  if (err) return <p className="text-red-300 text-center mt-10">{err}</p>;
  if (!story) return <p className="text-center text-white/50 mt-10">Loading…</p>;

  const st = story.initial_state || {};

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="glass rounded-2xl p-6 sm:p-8">
        <div className="text-4xl mb-3">{(story.emojis || []).join(" ")}</div>
        <h1 className="text-3xl font-extrabold mb-2">{story.title}</h1>
        <p className="text-white/70 mb-5">{story.description}</p>

        <div className="flex flex-wrap gap-2 mb-6">
          {(story.themes || []).map((t) => (
            <span key={t} className="text-xs px-2 py-1 rounded-lg bg-white/10">{t}</span>
          ))}
        </div>

        {(story.main_characters || []).concat(story.characters || []).length > 0 && (
          <div className="mb-6">
            <h2 className="font-bold mb-2">Characters</h2>
            <div className="grid sm:grid-cols-2 gap-3">
              {(story.main_characters || []).concat(story.characters || []).map((c) => (
                <div key={c.name} className="dark-glass rounded-xl p-3">
                  <div className="font-semibold">{c.name}</div>
                  <div className="text-xs text-purple-300">{c.role}</div>
                  <div className="text-xs text-white/60 mt-1">{c.description}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {st.inventory && (
          <div className="mb-6 text-sm text-white/70">
            <span className="font-bold">You begin with:</span>{" "}
            {st.inventory.join(", ") || "nothing"}.
          </div>
        )}

        <div className="flex flex-wrap gap-3 items-center">
          {progress ? (
            <>
              <Link
                to={`/play/${story.id}?scene=${progress.sceneId}&page=${progress.page}`}
                className="inline-block px-6 py-3 rounded-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 hover:scale-105 transition"
              >
                ▶️ Continue — scene {progress.sceneId} · page {progress.page}
              </Link>
              <button
                onClick={handleRestart}
                className="inline-block px-4 py-3 rounded-xl text-sm dark-glass hover:scale-105 transition"
                title="Forget saved progress and start over"
              >
                ↻ Restart from beginning
              </button>
            </>
          ) : (
            <Link
              to={`/play/${story.id}`}
              className="inline-block px-6 py-3 rounded-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 hover:scale-105 transition"
            >
              ▶️ Begin the Adventure
            </Link>
          )}
          <Link
            to={`/story/${story.id}/tree`}
            className="inline-block px-4 py-3 rounded-xl text-sm dark-glass hover:scale-105 transition"
            title="See every scene and choice as a graph"
          >
            🌳 Story map
          </Link>
        </div>
      </div>
    </div>
  );
}
