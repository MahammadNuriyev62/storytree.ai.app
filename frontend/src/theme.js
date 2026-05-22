// Mood theming: the scene's background, accent, and vignette react to the
// narrative phase (pacing) and to danger in the world state (e.g. low health).

export const PACING_MOODS = {
  setup: {
    label: "Setup",
    bg: ["#0b1e3a", "#10243f", "#0a1730"], // calm deep blue
    accent: "#5b8def",
    glow: "rgba(91,141,239,0.35)",
  },
  rising: {
    label: "Rising",
    bg: ["#1a1442", "#2a1854", "#140d33"], // tense violet
    accent: "#a06bff",
    glow: "rgba(160,107,255,0.4)",
  },
  climax: {
    label: "Climax",
    bg: ["#3a0f1f", "#4a1020", "#260910"], // burning crimson
    accent: "#ff5d6c",
    glow: "rgba(255,93,108,0.5)",
  },
  resolution: {
    label: "Resolution",
    bg: ["#10302a", "#123b32", "#0a221d"], // settled green-gold
    accent: "#52d6a8",
    glow: "rgba(82,214,168,0.4)",
  },
};

export function moodFor(pacing) {
  return PACING_MOODS[pacing] || PACING_MOODS.rising;
}

// 0 (safe) -> 1 (mortal danger). Drives a red vignette overlay.
export function dangerLevel(state) {
  const stats = (state && state.stats) || {};
  // pick the most "vital"-looking stat present
  const vital =
    stats.health ?? stats.hp ?? stats.sanity ?? stats.life ?? null;
  if (vital == null) return 0;
  const v = Math.max(0, Math.min(100, Number(vital)));
  return v >= 50 ? 0 : (50 - v) / 50;
}

export function backgroundGradient(mood) {
  const [a, b, c] = mood.bg;
  return `radial-gradient(1200px 800px at 50% -10%, ${a}, ${b} 45%, ${c} 100%)`;
}
