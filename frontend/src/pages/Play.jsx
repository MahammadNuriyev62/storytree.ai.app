import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";
import { moodFor, backgroundGradient, dangerLevel } from "../theme.js";
import TypewriterText from "../components/TypewriterText.jsx";
import Hud from "../components/Hud.jsx";
import RelationshipsPanel from "../components/RelationshipsPanel.jsx";
import StateChangeToasts from "../components/StateChangeToasts.jsx";

export default function Play() {
  const { id } = useParams();
  const [scene, setScene] = useState(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingText, setLoadingText] = useState("Entering the story…");
  const [showChoices, setShowChoices] = useState(false);
  const [finished, setFinished] = useState(false);
  const [err, setErr] = useState(null);
  const [toasts, setToasts] = useState([]);
  const toastTimer = useRef(null);

  const load = async (choiceId) => {
    setLoading(true);
    setShowChoices(false);
    try {
      const s = await api.getScene(id, choiceId);
      setScene(s);
      // surface what changed as toasts, then auto-dismiss
      setToasts(s.state_changes || []);
      clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(() => setToasts([]), 4500);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setFinished(false);
    api.getStory(id).then((s) => setTitle(s.title)).catch(() => {});
    load(null);
    return () => clearTimeout(toastTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const choose = (c) => {
    if (c.next_scene_id == null) {
      setFinished(true);
      return;
    }
    setLoadingText(c.loading_text || "The story unfolds…");
    load(c.id);
  };

  const replay = () => {
    setFinished(false);
    load(null);
  };

  const mood = moodFor(scene && scene.pacing);
  const danger = dangerLevel(scene && scene.state);

  if (err)
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-center">
        <div>
          <p className="text-red-300 mb-4">{err}</p>
          <button onClick={() => load(null)} className="px-4 py-2 rounded-xl dark-glass">
            🔄 Retry
          </button>
        </div>
      </div>
    );

  return (
    <div className="scene-bg min-h-screen" style={{ background: backgroundGradient(mood) }}>
      <div className="vignette" style={{ opacity: danger }} />
      <StateChangeToasts changes={toasts} />

      <div className="relative z-10 max-w-6xl mx-auto px-4 py-5 grid lg:grid-cols-[1fr_320px] gap-6">
        <main>
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <Link to={`/story/${id}`} className="text-sm text-white/70 hover:text-white">
              ← {title || "Back"}
            </Link>
            <span
              className="text-xs uppercase tracking-widest px-3 py-1 rounded-full"
              style={{ background: mood.glow, color: "#fff" }}
            >
              {mood.label}
            </span>
          </div>

          {/* Scene card */}
          <div className="glass rounded-2xl p-6 sm:p-8 min-h-[50vh] relative overflow-hidden">
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <motion.div
                  className="text-5xl mb-4"
                  animate={{ scale: [1, 1.15, 1] }}
                  transition={{ repeat: Infinity, duration: 1.6 }}
                >
                  📖
                </motion.div>
                <p className="text-white/80 italic max-w-md">{loadingText}</p>
              </div>
            ) : (
              <AnimatePresence mode="wait">
                <motion.div
                  key={scene && scene.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <TypewriterText text={scene && scene.text} onDone={() => setShowChoices(true)} />

                  <div className="mt-8 space-y-3">
                    <AnimatePresence>
                      {showChoices &&
                        (scene.choices || []).map((c, i) => {
                          const finale = c.next_scene_id == null;
                          return (
                            <motion.button
                              key={c.id}
                              initial={{ opacity: 0, x: -16 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.12 }}
                              onClick={() => choose(c)}
                              className={`w-full text-left p-4 rounded-xl transition hover:scale-[1.02] ${
                                finale
                                  ? "bg-gradient-to-r from-purple-600 to-pink-600 border-2"
                                  : "dark-glass"
                              }`}
                              style={finale ? { borderColor: mood.accent } : {}}
                            >
                              <span className="mr-2">{finale ? "🏁" : "▶️"}</span>
                              {c.text}
                            </motion.button>
                          );
                        })}
                    </AnimatePresence>
                  </div>
                </motion.div>
              </AnimatePresence>
            )}
          </div>
        </main>

        {/* Side panels (state-reactive) */}
        <aside className="space-y-4 lg:sticky lg:top-5 self-start">
          <Hud state={scene && scene.state} accent={mood.accent} />
          <RelationshipsPanel relationships={scene && scene.state && scene.state.relationships} />
        </aside>
      </div>

      {/* End card */}
      <AnimatePresence>
        {finished && (
          <motion.div
            className="fixed inset-0 z-40 flex items-center justify-center p-6 bg-black/60 backdrop-blur"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="glass rounded-2xl p-8 text-center max-w-md"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
            >
              <div className="text-6xl mb-4">🎉</div>
              <h2 className="text-3xl font-extrabold mb-2">The End</h2>
              <p className="text-white/70 mb-6">You've reached the end of this path.</p>
              <div className="flex gap-3 justify-center">
                <button onClick={replay} className="px-5 py-2 rounded-xl bg-purple-500 hover:bg-purple-600 font-bold">
                  🔄 Replay
                </button>
                <Link to="/" className="px-5 py-2 rounded-xl dark-glass font-bold">
                  📚 Library
                </Link>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
