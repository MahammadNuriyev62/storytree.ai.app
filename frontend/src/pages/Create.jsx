import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const LENGTHS = [
  { label: "Short", scenes: 25, emoji: "⚡", hint: "~30 min" },
  { label: "Medium", scenes: 50, emoji: "📖", hint: "~1 hr" },
  { label: "Epic", scenes: 100, emoji: "📚", hint: "~3 hr" },
];
const DIFFS = [
  { label: "Easy", value: 0.1, emoji: "🟢" },
  { label: "Medium", value: 0.3, emoji: "🟡" },
  { label: "Hard", value: 0.6, emoji: "🔴" },
  { label: "Nightmare", value: 0.9, emoji: "💀" },
];

export default function Create() {
  const nav = useNavigate();
  const [description, setDescription] = useState("");
  const [nScenes, setNScenes] = useState(50);
  const [difficulty, setDifficulty] = useState(0.3);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const surprise = async () => {
    try {
      const d = await api.getDescription();
      setDescription(d.description);
    } catch (e) {
      setErr(String(e));
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const story = await api.createStory({ description, n_scenes: nScenes, difficulty });
      nav(`/story/${story.id}`);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-extrabold mb-6 text-center">✨ Create Your Story</h1>
      <form onSubmit={submit} className="glass rounded-2xl p-6 space-y-6">
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="font-semibold">Story concept</label>
            <button type="button" onClick={surprise} className="text-sm text-purple-300 hover:underline">
              🎲 Surprise me
            </button>
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            required
            minLength={10}
            placeholder="Setting, characters, the central conflict…"
            className="w-full p-3 rounded-xl bg-white/10 border border-white/20 focus:border-purple-400 outline-none resize-none"
          />
        </div>

        <div>
          <label className="font-semibold block mb-2">Target length</label>
          <div className="grid grid-cols-3 gap-3">
            {LENGTHS.map((l) => (
              <button
                type="button"
                key={l.scenes}
                onClick={() => setNScenes(l.scenes)}
                className={`dark-glass rounded-xl p-3 text-center transition ${
                  nScenes === l.scenes ? "ring-2 ring-purple-400" : "opacity-80"
                }`}
              >
                <div className="text-2xl">{l.emoji}</div>
                <div className="font-bold text-sm">{l.label}</div>
                <div className="text-xs text-white/50">{l.scenes} · {l.hint}</div>
              </button>
            ))}
          </div>
          <p className="text-xs text-white/40 mt-2">
            A soft target — the storyteller decides the real ending.
          </p>
        </div>

        <div>
          <label className="font-semibold block mb-2">Difficulty</label>
          <div className="grid grid-cols-4 gap-2">
            {DIFFS.map((d) => (
              <button
                type="button"
                key={d.value}
                onClick={() => setDifficulty(d.value)}
                className={`dark-glass rounded-xl p-3 text-center transition ${
                  difficulty === d.value ? "ring-2 ring-pink-400" : "opacity-80"
                }`}
              >
                <div className="text-2xl">{d.emoji}</div>
                <div className="font-bold text-xs">{d.label}</div>
              </button>
            ))}
          </div>
        </div>

        {err && <p className="text-red-300 text-sm">{err}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full py-3 rounded-xl font-bold text-lg bg-gradient-to-r from-purple-500 to-pink-500 hover:scale-[1.02] transition disabled:opacity-60"
        >
          {busy ? "✨ Conjuring your world…" : "🎭 Generate Story"}
        </button>
      </form>
    </div>
  );
}
