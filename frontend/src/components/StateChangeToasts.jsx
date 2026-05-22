import { AnimatePresence, motion } from "framer-motion";

// Floating notifications for what changed entering the current scene.
// Colorize by a quick heuristic on the change text.
function tone(text) {
  const t = text.toLowerCase();
  if (/-\d|lost|damage|wound|fell|broke|died|perish|fail/.test(t))
    return "border-red-400/40 bg-red-500/15";
  if (/\+\d|found|gained|picked up|learned|unlocked|trust|allied/.test(t))
    return "border-emerald-400/40 bg-emerald-500/15";
  return "border-white/20 bg-white/10";
}

export default function StateChangeToasts({ changes }) {
  return (
    <div className="fixed top-4 right-4 z-30 flex flex-col gap-2 w-64">
      <AnimatePresence>
        {(changes || []).map((c, i) => (
          <motion.div
            key={`${c}-${i}`}
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            transition={{ delay: i * 0.25 }}
            className={`text-sm px-3 py-2 rounded-xl border backdrop-blur ${tone(c)}`}
          >
            {c}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
