import { motion } from "framer-motion";

// Standing runs -100 (hostile) .. +100 (devoted). Bar fills from the center.
function standingLabel(v) {
  if (v >= 70) return "Devoted";
  if (v >= 30) return "Ally";
  if (v > -30) return "Neutral";
  if (v > -70) return "Wary";
  return "Hostile";
}

export default function RelationshipsPanel({ relationships }) {
  const entries = Object.entries(relationships || {});
  if (entries.length === 0) return null;

  return (
    <div className="dark-glass rounded-2xl p-4">
      <h3 className="text-xs font-bold uppercase tracking-widest text-white/60 mb-3">
        Relationships
      </h3>
      <div className="space-y-3">
        {entries.map(([name, raw]) => {
          const v = Math.max(-100, Math.min(100, Number(raw)));
          const half = Math.abs(v) / 2; // 0..50 (% of full bar from center)
          const positive = v >= 0;
          return (
            <div key={name}>
              <div className="flex justify-between text-xs">
                <span className="text-white/80">{name}</span>
                <span className={positive ? "text-emerald-300" : "text-red-300"}>
                  {standingLabel(v)}
                </span>
              </div>
              <div className="relative h-2 mt-1 rounded-full bg-white/10">
                <div className="absolute left-1/2 top-0 h-full w-px bg-white/30" />
                <motion.div
                  className="absolute top-0 h-full rounded-full"
                  style={{
                    background: positive ? "#52d6a8" : "#ff5d6c",
                    left: positive ? "50%" : `${50 - half}%`,
                  }}
                  initial={false}
                  animate={{ width: `${half}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
