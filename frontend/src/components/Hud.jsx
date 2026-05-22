import { motion } from "framer-motion";

const VITALS = ["health", "hp", "life", "sanity", "oxygen", "stamina", "energy", "mana"];

function StatBar({ name, value, accent }) {
  const pct = Math.max(0, Math.min(100, Number(value)));
  const low = pct < 30;
  return (
    <div className="mb-2">
      <div className="flex justify-between text-[11px] uppercase tracking-wide text-white/70">
        <span>{name}</span>
        <span className={low ? "text-red-300 font-bold" : ""}>{Math.round(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: low ? "#ff5d6c" : accent }}
          initial={false}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export default function Hud({ state, accent }) {
  const stats = (state && state.stats) || {};
  const inventory = (state && state.inventory) || [];
  const vitals = Object.entries(stats).filter(([k]) => VITALS.includes(k.toLowerCase()));
  const chips = Object.entries(stats).filter(([k]) => !VITALS.includes(k.toLowerCase()));

  return (
    <div className="dark-glass rounded-2xl p-4">
      <h3 className="text-xs font-bold uppercase tracking-widest text-white/60 mb-3">Status</h3>

      {vitals.map(([k, v]) => (
        <StatBar key={k} name={k} value={v} accent={accent} />
      ))}

      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {chips.map(([k, v]) => (
            <span key={k} className="text-xs px-2 py-1 rounded-lg bg-white/10">
              {k}: <b>{String(v)}</b>
            </span>
          ))}
        </div>
      )}

      <h3 className="text-xs font-bold uppercase tracking-widest text-white/60 mt-5 mb-2">
        Inventory
      </h3>
      {inventory.length === 0 ? (
        <p className="text-xs text-white/40 italic">Empty</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {inventory.map((item, i) => (
            <motion.span
              key={`${item}-${i}`}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-xs px-2 py-1 rounded-lg bg-purple-500/20 border border-purple-400/30"
            >
              🎒 {item}
            </motion.span>
          ))}
        </div>
      )}
    </div>
  );
}
