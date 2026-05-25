import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "../api.js";

export default function Home() {
  const [stories, setStories] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.listStories().then((d) => setStories(d.stories)).catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-extrabold mb-3">
          Infinite stories. <span className="text-purple-300">Your choices.</span>
        </h1>
        <p className="text-white/70 max-w-2xl mx-auto">
          Branching adventures generated on the fly, with a living world that
          remembers what you do.
        </p>
        <Link
          to="/create"
          className="inline-block mt-6 px-6 py-3 rounded-xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 hover:scale-105 transition"
        >
          ✨ Create a Story
        </Link>
      </div>

      {err && <p className="text-red-300 text-center">{err}</p>}
      {!stories && !err && <p className="text-center text-white/50">Loading…</p>}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stories?.map((s, i) => (
          <motion.div
            key={s.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Link
              to={`/story/${s.id}`}
              className="block glass rounded-2xl p-5 h-full hover:scale-[1.02] transition"
            >
              <div className="text-3xl mb-2">{(s.emojis || []).join(" ") || "📖"}</div>
              <h3 className="font-bold text-lg mb-1">{s.title}</h3>
              <p className="text-sm text-white/60 line-clamp-3">{s.description}</p>
            </Link>
          </motion.div>
        ))}
      </div>

      {stories?.length === 0 && (
        <p className="text-center text-white/50 mt-10">
          No stories yet — create the first one!
        </p>
      )}
    </div>
  );
}
