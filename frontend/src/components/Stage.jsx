import { motion, AnimatePresence } from "framer-motion";

// Renders the visual layers of a scene: background image + character sprites,
// anchored to the bottom of the viewport. The mood gradient already lives on
// the parent <Play> element, so this component sits on top of it.
//
// `stage`            : { setting, characters_present } (or null/undefined)
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

export default function Stage({ stage, backgrounds, characterSprites }) {
  const settingId = stage && stage.setting;
  const bgUrl =
    settingId && backgrounds && backgrounds[settingId]
      ? backgrounds[settingId].url
      : null;

  const present = (stage && stage.characters_present) || [];

  // Resolve each present character to {url, position, key}; drop unknown names.
  const sprites = present
    .map((c, i) => {
      const meta = characterSprites && characterSprites[c.name];
      if (!meta) return null;
      const url =
        meta.expressions &&
        (meta.expressions[c.expression] || meta.expressions.neutral);
      if (!url) return null;
      return {
        key: `${c.name}-${i}`,
        name: c.name,
        url,
        leftPct: POSITION_LEFT_PCT[meta.position] ?? 50,
      };
    })
    .filter(Boolean);

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
              key={s.key + s.url}
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
