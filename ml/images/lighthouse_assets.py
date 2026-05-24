"""Asset manifest for *The Lighthouse in Winter* (3 sprite sheets + 6 backgrounds).

The image bytes were generated manually via gemini.google.com (free tier, no
billing impact). This module:

  1. Pins the canonical text prompts that produced each asset.
  2. `wire_uploads()` copies each `dev_fixtures/*.png` into the production image
     cache at `.image_cache/{cache_key}.png` — keyed by the SAME hash the
     production `generate_image()` would compute — so any future call hits the
     cache instead of the API.
  3. Runs the rembg/U²-Net sprite extractor on each character sheet and saves
     the per-expression PNGs under `static/images/sprites/{story_id}/`.
  4. Copies each background PNG into `static/images/backgrounds/{story_id}/`.
  5. Returns a manifest dict suitable for `Story.character_sprites` /
     `Story.backgrounds` columns — values are public `/static/...` URLs the SPA
     can drop straight into <img src>.

Run directly to wire everything: `python -m ml.images.lighthouse_assets`.
"""

import io
import shutil
import zipfile
from pathlib import Path
from typing import Dict

from ml.images.image_gen import CACHE_DIR, DEFAULT_MODEL, _cache_key
from ml.images.sprite_extractor import extract_sprites_from_sheet

ROOT = Path(__file__).resolve().parent.parent.parent
DEV_FIXTURES = ROOT / "dev_fixtures"
STATIC = ROOT / "static"

# Left-to-right order of expressions in every sprite sheet — matches the
# numbered list in each character prompt below.
EXPRESSION_ORDER = ["angry", "sad", "smiling", "neutral", "scared"]


# --- Character sprite prompts ----------------------------------------------
# Five full-body poses in a single sheet, white background, anime-illustration
# style. Same template for all three secondary characters (Iwan, Morvah, Henk);
# the protagonist (Anouk) is deliberately NOT visualised — visual-novel
# convention is to leave the player-POV character invisible.

IWAN_PROMPT = """Character sprite reference sheet of Iwan, a man in his early forties with a
weatherworn handsome face, salt-and-pepper dark hair, a few days of stubble,
and quiet, watchful eyes. He is the lighthouse keeper on the storm-battered
Cornish coast, a widower who has lived alone for years. He wears a thick
charcoal wool fisherman's sweater, worn navy oilskin waterproof trousers
tucked into heavy black rubber boots, and a faded canvas knit beanie. Anime-
illustration style, clean lines, soft cel shading, slightly desaturated
coastal-winter palette (slate blue, charcoal, weathered grey).

Five full-body poses arranged horizontally on a single image, plain pure-white
background, equal spacing between each pose, clear gap between figures, no
overlap, no shadows touching between poses. Same character in all five poses,
identical outfit, proportions, and hair across all five. Centered vertical
alignment, full body visible in each pose.

Left to right, the five expressions are:
1. ANGRY  - jaw set, contained anger, fists at his sides, stern stare
2. SAD    - head bowed, one hand resting on a wall for support, distant look
3. SMILING - a quiet, warm half-smile with the eyes crinkled at the corners
4. NEUTRAL - standing tall, hands in his pockets, watchful and grounded
5. SCARED - eyes wide but contained, one hand on his chest, body half-turned"""


MORVAH_PROMPT = """Character sprite reference sheet of Morvah, a woman in her early sixties with
sharp blue eyes and grey hair pinned up in a loose bun with strands escaping,
a warm weathered face with deep laugh lines. She is the keeper of the tiny
village shop on the Cornish coast, widowed years ago, sharp-tongued but
secretly kind. She wears a thick burgundy hand-knit cardigan over a faded
blue cotton blouse, a long charcoal wool skirt, dark grey wool tights, and
sturdy brown leather brogues. Around her neck hangs a pair of reading
glasses on a thin chain. Anime-illustration style, clean lines, soft cel
shading, slightly desaturated coastal-winter palette (slate blue, charcoal,
warm amber, burgundy).

Five full-body poses arranged horizontally on a single image, plain pure-white
background, equal spacing between each pose, clear gap between figures, no
overlap, no shadows touching between poses. Same character in all five poses,
identical outfit, proportions, and hair across all five. Centered vertical
alignment, full body visible in each pose.

Left to right, the five expressions are:
1. ANGRY  - hands on hips, sharp glare, mouth a thin line
2. SAD    - arms folded across her chest, head slightly turned away, eyes lowered
3. SMILING - a warm knowing half-smile, slight tilt of head
4. NEUTRAL - hands clasped in front of her, attentive listening pose
5. SCARED - hands raised slightly, body half-turned, eyes wide"""


HENK_PROMPT = """Character sprite reference sheet of Henk, a man in his late thirties with a
warm intelligent face, gentle laugh lines around the eyes, slightly tousled
honey-brown hair, and wire-frame glasses. He is the late husband of the
protagonist — depicted as he was before his long illness took him, so he
looks healthy, kind, and present. He wears a soft oatmeal-coloured cable-
knit sweater over a faded chambray button-down shirt, dark slim-fit jeans,
and worn brown leather loafers. A simple gold wedding band on his left
hand. Anime-illustration style, clean lines, soft cel shading, slightly
warmer palette than the coastal-winter setting (oatmeal, soft amber,
chambray blue) — he is a memory in a colder world.

Five full-body poses arranged horizontally on a single image, plain pure-white
background, equal spacing between each pose, clear gap between figures, no
overlap, no shadows touching between poses. Same character in all five poses,
identical outfit, proportions, and hair across all five. Centered vertical
alignment, full body visible in each pose.

Left to right, the five expressions are:
1. ANGRY  - jaw tight, brows drawn together, hands at his sides
2. SAD    - head bowed, hands in his pockets, eyes lowered
3. SMILING - a wide warm smile reaching his eyes, slightly tilted head
4. NEUTRAL - hands clasped loosely in front, attentive listening pose
5. SCARED - eyes wide, one hand raised partway as if to ward something off"""


SPRITE_PROMPTS: Dict[str, str] = {
    "Iwan": IWAN_PROMPT,
    "Morvah": MORVAH_PROMPT,
    "Henk": HENK_PROMPT,
}

# Maps Character name -> dev_fixtures filename (without .png extension).
SPRITE_UPLOAD: Dict[str, str] = {
    "Iwan": "iwan_sheet",
    "Morvah": "morvah_sheet",
    "Henk": "henk_sheet",
}


# --- Background prompts -----------------------------------------------------
# All backgrounds share a style prelude so they stay tonally consistent. The
# full prompt for each is `BACKGROUND_PRELUDE + "\n\n" + setting_description`.

BACKGROUND_PRELUDE = """Anime-style background illustration, soft cel shading, slightly desaturated
coastal-winter palette (slate blue, charcoal, weathered grey, warm amber
accents from lamps/fire/candlelight). Cinematic widescreen 16:9 composition.
NO characters or people visible — just the empty setting. Soft volumetric
lighting, painterly background-art style suitable for a visual novel."""


BACKGROUND_SETTINGS: Dict[str, str] = {
    "cottage_interior_day": (
        "Interior of a small one-room Cornish stone cottage in mid-morning "
        "winter light. A modest wood-burning stove glows in one corner; a "
        "worn armchair faces it draped with a knitted throw. A small writing "
        "desk under a salt-fogged window looks out toward grey sea. Bookshelves "
        "with weathered spines, a few framed photographs on the mantel, an "
        "empty teacup on the desk. Cool blue daylight from the window mixed "
        "with the warm amber of the stove."
    ),
    "cottage_interior_night": (
        "Same one-room Cornish stone cottage interior at night, lit only by "
        "the wood-burning stove and a single oil lamp on the writing desk. "
        "The window is a dark mirror reflecting the warm interior. Shadows "
        "stretch long across worn floorboards. Intimate, quiet, melancholy."
    ),
    "lighthouse_exterior": (
        "Tall white-and-red banded Cornish lighthouse on a wind-scoured rocky "
        "headland at dusk. Heavy grey clouds churn overhead, sea spray bursts "
        "against the rocks below. The lantern room glows a warm amber high "
        "above. A narrow gravel path winds up to the keeper's cottage at the "
        "lighthouse base. No people."
    ),
    "lighthouse_interior": (
        "Interior of the lighthouse lantern room at the very top of the tower. "
        "The huge brass-and-glass Fresnel lens dominates the centre, polished "
        "and gleaming. Wraparound windows look out onto storm-grey sea and "
        "sky. Brass instruments, a maintenance log on a small table, a worn "
        "leather chair. Warm amber light from the lamp mechanism, cool blue "
        "light from the sea outside."
    ),
    "cliffs_storm": (
        "Black slate Cornish cliffs in the teeth of a winter storm. Heavy "
        "rain slants in from the sea. Massive waves crash against the cliff "
        "base, sending white spray high. A narrow muddy footpath edges the "
        "cliff top, dotted with windblown gorse. Sky a turbulent mass of "
        "near-black clouds shot through with a single thin gap of pale light. "
        "Dramatic, dangerous, cold."
    ),
    "village_shop": (
        "Interior of a tiny old-fashioned Cornish village shop. Wooden floors, "
        "narrow aisles, shelves crowded with tinned goods, biscuits, candles, "
        "fishing line, postcards. A small counter under a hanging brass bell. "
        "A pot-bellied stove in the corner glows warmly. Small-paned windows "
        "showing the grey village lane outside. Warm amber interior light "
        "against the cold outside."
    ),
}


# Visual placement hint for the SPA — left/right side of the frame. The
# protagonist is invisible (player POV), so we only ever show one or two NPCs
# at once.
SPRITE_POSITIONS: Dict[str, str] = {
    "Iwan": "right",
    "Morvah": "left",
    "Henk": "center",
}


def _bg_prompt(setting_id: str) -> str:
    return BACKGROUND_PRELUDE + "\n\n" + BACKGROUND_SETTINGS[setting_id]


def build_manifest(story_id: int) -> dict:
    """Return the manifest dict (no I/O) that should be saved on the Story row.

    URLs assume the assets have already been written to `static/images/...` —
    call `wire_uploads()` to actually create them.
    """
    sprites: Dict[str, dict] = {}
    for name, prompt in SPRITE_PROMPTS.items():
        sprites[name] = {
            "description": prompt.splitlines()[0],  # one-line gloss for prompt context
            "position": SPRITE_POSITIONS[name],
            "expressions": {
                expr: f"/static/images/sprites/{story_id}/{name.lower()}-{expr}.png"
                for expr in EXPRESSION_ORDER
            },
        }

    backgrounds: Dict[str, dict] = {}
    for setting_id, description in BACKGROUND_SETTINGS.items():
        backgrounds[setting_id] = {
            "description": description,
            "url": f"/static/images/backgrounds/{story_id}/{setting_id}.png",
        }

    return {"character_sprites": sprites, "backgrounds": backgrounds}


def wire_uploads(story_id: int, *, force: bool = False) -> dict:
    """Populate cache + static/ from `dev_fixtures/`. Returns the manifest.

    Idempotent: skips work whose outputs already exist unless `force=True`.
    Raises FileNotFoundError if any expected upload is missing.
    """
    sprites_dir = STATIC / "images" / "sprites" / str(story_id)
    bgs_dir = STATIC / "images" / "backgrounds" / str(story_id)
    sprites_dir.mkdir(parents=True, exist_ok=True)
    bgs_dir.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # --- Sprite sheets: cache + extract per-expression PNGs ---
    for name, fname in SPRITE_UPLOAD.items():
        src = DEV_FIXTURES / f"{fname}.png"
        if not src.exists():
            raise FileNotFoundError(f"missing sprite sheet upload: {src}")

        prompt = SPRITE_PROMPTS[name]
        key = _cache_key(prompt, DEFAULT_MODEL, None)
        cache_dst = CACHE_DIR / f"{key}.png"
        if force or not cache_dst.exists():
            shutil.copyfile(src, cache_dst)
            print(f"  cached  {name:<7} -> .image_cache/{key}.png")
        else:
            print(f"  cache hit {name:<7} -> .image_cache/{key}.png")

        # Extract per-expression sprites. Skip if all 5 are already present.
        expression_paths = [
            sprites_dir / f"{name.lower()}-{expr}.png" for expr in EXPRESSION_ORDER
        ]
        if not force and all(p.exists() for p in expression_paths):
            print(f"  extracted {name:<7} -> {sprites_dir.name}/ (already done)")
            continue

        sheet_bytes = src.read_bytes()
        zip_bytes = extract_sprites_from_sheet(sheet_bytes)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            extracted = sorted(zf.namelist())  # sprite_1.png .. sprite_5.png
            if len(extracted) != len(EXPRESSION_ORDER):
                raise RuntimeError(
                    f"{name}: extractor returned {len(extracted)} sprites, "
                    f"expected {len(EXPRESSION_ORDER)}: {extracted}"
                )
            for sprite_name, expr, dst in zip(extracted, EXPRESSION_ORDER, expression_paths):
                dst.write_bytes(zf.read(sprite_name))
        print(f"  extracted {name:<7} -> {len(EXPRESSION_ORDER)} expressions")

    # --- Backgrounds: cache + copy to static/ ---
    for setting_id in BACKGROUND_SETTINGS:
        src = DEV_FIXTURES / f"bg_{setting_id}.png"
        if not src.exists():
            raise FileNotFoundError(f"missing background upload: {src}")

        prompt = _bg_prompt(setting_id)
        key = _cache_key(prompt, DEFAULT_MODEL, None)
        cache_dst = CACHE_DIR / f"{key}.png"
        static_dst = bgs_dir / f"{setting_id}.png"

        if force or not cache_dst.exists():
            shutil.copyfile(src, cache_dst)
        if force or not static_dst.exists():
            shutil.copyfile(src, static_dst)
        print(f"  bg {setting_id:<24} -> static + cache ({key})")

    return build_manifest(story_id)


if __name__ == "__main__":
    import sys
    sid = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print(f"Wiring assets for story_id={sid}...")
    manifest = wire_uploads(sid)
    print("\nManifest:")
    import json
    print(json.dumps(manifest, indent=2))
