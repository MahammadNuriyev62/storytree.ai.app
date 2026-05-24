import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";
import { moodFor, backgroundGradient, dangerLevel } from "../theme.js";
import { paginate } from "../pagination.js";
import TypewriterText from "../components/TypewriterText.jsx";
import Hud from "../components/Hud.jsx";
import RelationshipsPanel from "../components/RelationshipsPanel.jsx";
import StateChangeToasts from "../components/StateChangeToasts.jsx";
import Stage from "../components/Stage.jsx";

export default function Play() {
  const { id } = useParams();
  const [scene, setScene] = useState(null);
  const [title, setTitle] = useState("");
  const [storyAssets, setStoryAssets] = useState({
    backgrounds: null,
    characterSprites: null,
  });
  const [loading, setLoading] = useState(true);
  const [loadingText, setLoadingText] = useState("Entering the story…");
  const [pageIndex, setPageIndex] = useState(0);
  const [pageDone, setPageDone] = useState(false);
  const [finished, setFinished] = useState(false);
  const [err, setErr] = useState(null);
  const [toasts, setToasts] = useState([]);
  const toastTimer = useRef(null);

  const pages = useMemo(() => paginate(scene && scene.text), [scene && scene.text]);
  const isLastPage = pageIndex >= pages.length - 1;

  const load = async (choiceId) => {
    setLoading(true);
    setPageIndex(0);
    setPageDone(false);
    try {
      const s = await api.getScene(id, choiceId);
      setScene(s);
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
    api
      .getStory(id)
      .then((s) => {
        setTitle(s.title);
        setStoryAssets({
          backgrounds: s.backgrounds || null,
          characterSprites: s.character_sprites || null,
        });
      })
      .catch(() => {});
    load(null);
    return () => clearTimeout(toastTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const next = () => {
    if (!pageDone || isLastPage) return;
    setPageIndex((i) => i + 1);
    setPageDone(false);
  };

  // Space / ArrowRight advances to the next page.
  useEffect(() => {
    const onKey = (e) => {
      if (loading || finished) return;
      if (e.key === " " || e.key === "ArrowRight") {
        if (pageDone && !isLastPage) {
          e.preventDefault();
          next();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageDone, isLastPage, loading, finished]);

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
    <div
      className="scene-bg relative min-h-screen overflow-hidden"
      style={{ background: backgroundGradient(mood) }}
    >
      <Stage
        stage={scene && scene.stage}
        backgrounds={storyAssets.backgrounds}
        characterSprites={storyAssets.characterSprites}
      />
      <div className="vignette" style={{ opacity: danger }} />
      <StateChangeToasts changes={toasts} />

      {/* Top bar: back + mood pill, spans full width over the stage. */}
      <header className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-5 py-4 pointer-events-none">
        <Link
          to={`/story/${id}`}
          className="text-sm text-white/80 hover:text-white dark-glass px-3 py-1.5 rounded-full pointer-events-auto"
        >
          ← {title || "Back"}
        </Link>
        <span
          className="text-xs uppercase tracking-widest px-3 py-1.5 rounded-full pointer-events-auto"
          style={{ background: mood.glow, color: "#fff" }}
        >
          {mood.label}
        </span>
      </header>

      {/* Top-right HUD column: stats + relationships, capped height, scrolls
          if needed. Sized so it never reaches the head zone of mid-stage sprites. */}
      <aside className="absolute top-16 right-4 z-20 w-[260px] space-y-3 max-h-[55vh] overflow-y-auto panel-scroll">
        <Hud state={scene && scene.state} accent={mood.accent} />
        <RelationshipsPanel relationships={scene && scene.state && scene.state.relationships} />
      </aside>

      {/* Bottom text card: full-width VN-style ribbon. Choices replace the
          scene text on the last page, so the card grows downward naturally. */}
      <main className="absolute bottom-4 left-0 right-0 z-20 px-4">
        <div className="glass rounded-2xl p-5 sm:p-6 max-w-5xl mx-auto relative">
          {loading ? (
            <div className="flex items-center gap-4 py-2">
              <motion.div
                className="text-3xl"
                animate={{ scale: [1, 1.15, 1] }}
                transition={{ repeat: Infinity, duration: 1.6 }}
              >
                📖
              </motion.div>
              <p className="text-white/80 italic">{loadingText}</p>
            </div>
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={`${scene && scene.id}-${pageIndex}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35 }}
              >
                <TypewriterText text={pages[pageIndex]} onDone={() => setPageDone(true)} />

                {pageDone && !isLastPage && (
                  <div className="mt-4 flex justify-end">
                    <motion.button
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={next}
                      className="px-6 py-2.5 rounded-xl dark-glass hover:scale-105 transition font-medium"
                      title="Space or →"
                    >
                      Next →
                    </motion.button>
                  </div>
                )}

                {pageDone && isLastPage && (
                  <div className="mt-4 grid sm:grid-cols-2 gap-3 max-h-[42vh] overflow-y-auto panel-scroll">
                    <AnimatePresence>
                      {(scene.choices || []).map((c, i) => {
                        const finale = c.next_scene_id == null;
                        return (
                          <motion.button
                            key={c.id}
                            initial={{ opacity: 0, x: -16 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.12 }}
                            onClick={() => choose(c)}
                            className={`text-left p-3 rounded-xl transition hover:scale-[1.02] ${
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
                )}
              </motion.div>
            </AnimatePresence>
          )}

          {/* Page progress dots */}
          {!loading && pages.length > 1 && (
            <div className="absolute -top-3 left-0 right-0 flex justify-center gap-1.5">
              {pages.map((_, i) => (
                <span
                  key={i}
                  className="h-1.5 rounded-full transition-all"
                  style={{
                    width: i === pageIndex ? 18 : 6,
                    background:
                      i < pageIndex
                        ? "rgba(255,255,255,0.55)"
                        : i === pageIndex
                        ? mood.accent
                        : "rgba(255,255,255,0.18)",
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </main>

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
