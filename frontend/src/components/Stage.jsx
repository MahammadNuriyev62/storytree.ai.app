import { motion, AnimatePresence } from "framer-motion";

// Renders the visual layers of a scene: background image + character sprites,
// anchored to the bottom of the viewport. The mood gradient already lives on
// the parent <Play> element, so this component sits on top of it.
//
// `setting`          : background id (string) or null
// `characters`       : [{name, expression}, ...] for the CURRENT page
// `backgrounds`      : story.backgrounds manifest, keyed by setting id
// `characterSprites` : story.character_sprites manifest, keyed by character name

// Horizontal anchor points (% from viewport left) for each `position` hint.
// Sprites stand in the middle of the screen — the scene-text ribbon sits at
// the bottom and the HUD column hugs the top-right, so this band stays clear
// from the head zone down to the upper edge of the text card.
const POSITION_LEFT_PCT = {
  left: 35,
  center: 50,
  right: 62,
};

// When multiple sprites resolve to the SAME anchor — which happens whenever
// the story has more than 3 characters and the metadata generator had to
// double up positions (observed on story 7, where Céline and Francesca both
// landed at `right`) — spread them around the anchor instead of stacking.
// 12% is roughly the sprite width, so two sprites in the same slot read as
// "next to each other" rather than "overlapping" while still staying inside
// the slot's natural visual band.
const COLLISION_SPREAD_PCT = 12;

function spreadCollisions(sprites) {
  const byAnchor = new Map();
  sprites.forEach((s, i) => {
    if (!byAnchor.has(s.leftPct)) byAnchor.set(s.leftPct, []);
    byAnchor.get(s.leftPct).push(i);
  });
  const out = sprites.map((s) => ({ ...s }));
  for (const [anchor, idxs] of byAnchor) {
    if (idxs.length <= 1) continue;
    const spread = (idxs.length - 1) * COLLISION_SPREAD_PCT;
    const start = anchor - spread / 2;
    idxs.forEach((idx, k) => {
      out[idx].leftPct = start + k * COLLISION_SPREAD_PCT;
    });
  }
  return out;
}

export default function Stage({
  setting,
  characters,
  backgrounds,
  characterSprites,
}) {
  const bgUrl =
    setting && backgrounds && backgrounds[setting]
      ? backgrounds[setting].url
      : null;

  // Resolve each present character to {url, position, key}; drop unknowns.
  const sprites = spreadCollisions(
    (characters || [])
      .map((c, i) => {
        const meta = characterSprites && characterSprites[c.name];
        if (!meta) return null;
        const url =
          meta.expressions &&
          (meta.expressions[c.expression] || meta.expressions.neutral);
        if (!url) return null;
        return {
          // Key by name + expression so a mood swap re-animates, but identity
          // is preserved when the same character stays put.
          key: `${c.name}-${c.expression || "neutral"}`,
          name: c.name,
          url,
          leftPct: POSITION_LEFT_PCT[meta.position] ?? 50,
        };
      })
      .filter(Boolean)
  );

  return (
    <div className="stage-layer">
      <AnimatePresence mode="wait">
        {bgUrl && (
          <motion.div
            key={bgUrl}
            className="stage-bg"
            style={{ backgroundImage: `url(${bgUrl})` }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.9 }}
          />
        )}
      </AnimatePresence>

      {/* Vertical fade-to-dark at the top + sides so HUD/text stay readable. */}
      {bgUrl && <div className="stage-scrim" />}

      {/* Character sprites, anchored to bottom of the viewport. */}
      <div className="stage-sprites">
        <AnimatePresence>
          {sprites.map((s) => (
            <motion.img
              key={s.key}
              src={s.url}
              alt={s.name}
              className="sprite"
              style={{ left: `${s.leftPct}%` }}
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 24 }}
              transition={{ duration: 0.45, ease: "easeOut" }}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
