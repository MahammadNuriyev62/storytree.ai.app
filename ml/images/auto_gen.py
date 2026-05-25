"""Auto-generate sprites + backgrounds for a story from its art metadata.

Reads art_style / characters[*].art_prompt / characters[*].poses /
settings[*].art_prompt off a Story row, calls Nano Banana via
ml.images.image_gen.generate_image() for each, runs the rembg/U²-Net
extractor on character sheets, and writes per-expression sprites +
backgrounds to static/images/{sprites,backgrounds}/{story_id}/.

Returns the manifest dict suitable for `Story.character_sprites` /
`Story.backgrounds`.

Set IMAGE_MOCK=1 to run end-to-end without spending API credits — every
image becomes a labelled placeholder PNG, sprite extraction still runs.
"""

import io
import os
import zipfile
from pathlib import Path
from typing import List

from ml.images.image_gen import generate_image
from ml.images.sprite_extractor import extract_sprites_from_sheet


def _is_mock() -> bool:
    return os.getenv("IMAGE_MOCK", "").lower() in ("1", "true", "yes")

ROOT = Path(__file__).resolve().parent.parent.parent
STATIC = ROOT / "static"

EXPRESSION_ORDER = ["angry", "sad", "smiling", "neutral", "scared"]

# Default poses used when a character entry omits the `poses` map. Generic but
# unambiguous so the image model has something to draw.
DEFAULT_POSES = {
    "angry": "fists clenched at the sides, jaw set, stern direct stare",
    "sad": "head bowed, shoulders slumped, eyes downcast",
    "smiling": "warm closed-mouth smile, slight tilt of the head",
    "neutral": "standing tall, hands clasped loosely in front, attentive",
    "scared": "eyes wide, both hands raised partway in front of the chest",
}

# Cycle through positions for characters that didn't declare one — gives a
# sensible mix when the LLM forgets to set them.
POSITION_FALLBACKS = ["right", "left", "center"]

# Format scaffolding appended to every character sprite prompt. Keeps the
# layout consistent across stories (5 horizontal poses, white bg, etc.) so
# the same sprite extractor works on every sheet.
SPRITE_SHEET_TEMPLATE = """Five full-body poses arranged horizontally on a single image, plain pure-white
background ONLY (no scenery, no furniture, no lighting effects from any
implied environment — IGNORE any lighting/background context mentioned in
the character description above; this is a sprite reference sheet, not an
in-scene illustration). Generous equal white-space gap between each pose so
no two figures touch or share painted background. Same character in all five
poses, identical outfit, proportions, and hair across all five. Centered
vertical alignment, full body visible in each pose, no cast shadows that
extend toward neighbouring figures.

Left to right, the five expressions are:
1. ANGRY  - {angry}
2. SAD    - {sad}
3. SMILING - {smiling}
4. NEUTRAL - {neutral}
5. SCARED - {scared}"""

# Standard suffix on every background prompt — frames the composition rules
# the SPA assumes (16:9, no characters, painterly VN style).
BACKGROUND_SUFFIX = (
    "Cinematic widescreen 16:9 composition. NO characters or people visible "
    "— just the empty setting. Soft volumetric lighting, painterly "
    "background-art style suitable for a visual novel."
)


def build_sprite_prompt(character: dict, art_style: str) -> str:
    """Compose the full Nano Banana prompt for a character sprite sheet."""
    poses = {**DEFAULT_POSES, **(character.get("poses") or {})}
    parts = [
        "Character sprite reference sheet of " + (character.get("art_prompt") or "").strip(),
    ]
    if art_style:
        parts.append(art_style.strip())
    parts.append(SPRITE_SHEET_TEMPLATE.format(**{k: poses[k] for k in EXPRESSION_ORDER}))
    return "\n\n".join(p for p in parts if p)


def build_background_prompt(setting: dict, art_style: str) -> str:
    """Compose the full Nano Banana prompt for a background image."""
    parts = []
    if art_style:
        parts.append(art_style.strip())
    parts.append(BACKGROUND_SUFFIX)
    parts.append((setting.get("art_prompt") or "").strip())
    return "\n\n".join(p for p in parts if p)


def _slug(name: str) -> str:
    """Filesystem-safe lowercase token from a character name."""
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def generate_story_assets(story) -> dict:
    """Run the full pipeline for `story`. Returns a manifest dict.

    Side effects: writes 5 PNGs per character + 1 PNG per setting under
    static/images/.../{story.id}/. Raises on any image-gen or extraction
    failure — callers should catch and surface the error.
    """
    story_id = story.id
    art_style = story.art_style or ""
    characters = list(story.characters or [])
    settings: List[dict] = list(story.settings or [])

    sprites_dir = STATIC / "images" / "sprites" / str(story_id)
    bgs_dir = STATIC / "images" / "backgrounds" / str(story_id)
    sprites_dir.mkdir(parents=True, exist_ok=True)
    bgs_dir.mkdir(parents=True, exist_ok=True)

    char_manifest: dict = {}
    for i, char in enumerate(characters):
        # Allow Pydantic Character to slip through too — coerce to dict.
        if hasattr(char, "model_dump"):
            char = char.model_dump()
        if not char.get("art_prompt"):
            print(f"[auto_gen] skipping {char.get('name')!r} — no art_prompt")
            continue

        name = char["name"]
        slug = _slug(name)
        prompt = build_sprite_prompt(char, art_style)
        print(f"[auto_gen] sprite sheet: {name} ...")
        sheet_bytes = generate_image(prompt)

        if _is_mock():
            # Mock-mode placeholder isn't a real sprite sheet — the extractor
            # would find 0 components. Just drop the same placeholder under each
            # expression slot so manifest/static-serving still gets exercised.
            for expr in EXPRESSION_ORDER:
                (sprites_dir / f"{slug}-{expr}.png").write_bytes(sheet_bytes)
        else:
            zip_bytes = extract_sprites_from_sheet(sheet_bytes)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                extracted = sorted(zf.namelist())
                n = len(extracted)
                if n == 0:
                    raise RuntimeError(
                        f"{name}: extractor found 0 sprites — sheet generation "
                        f"likely failed. Inspect the raw cache PNG."
                    )
                # Tolerate under-generation (e.g. photorealistic prompts that
                # add props like tables/bars can merge two figures into one
                # connected component, yielding 4 sprites instead of 5). Map
                # the first N extracted sprites to the first N expressions
                # in EXPRESSION_ORDER; fill any missing slots from `neutral`
                # if available, else the last extracted sprite.
                taken = extracted[: len(EXPRESSION_ORDER)]
                for sprite_name, expr in zip(taken, EXPRESSION_ORDER):
                    (sprites_dir / f"{slug}-{expr}.png").write_bytes(zf.read(sprite_name))
                if n < len(EXPRESSION_ORDER):
                    # Pick a fallback we already wrote — prefer 'neutral' (most
                    # generally re-usable), fall back to the last available.
                    fallback_expr = "neutral" if n > EXPRESSION_ORDER.index("neutral") else EXPRESSION_ORDER[n - 1]
                    fallback_bytes = (sprites_dir / f"{slug}-{fallback_expr}.png").read_bytes()
                    for expr in EXPRESSION_ORDER[n:]:
                        (sprites_dir / f"{slug}-{expr}.png").write_bytes(fallback_bytes)
                    missing = EXPRESSION_ORDER[n:]
                    print(
                        f"[auto_gen] WARNING {name}: only {n}/{len(EXPRESSION_ORDER)} "
                        f"sprites extracted; filled {missing} from {fallback_expr!r}"
                    )

        position = char.get("position") or POSITION_FALLBACKS[i % len(POSITION_FALLBACKS)]
        char_manifest[name] = {
            "description": (char.get("description") or "")[:200],
            "position": position,
            "expressions": {
                expr: f"/static/images/sprites/{story_id}/{slug}-{expr}.png"
                for expr in EXPRESSION_ORDER
            },
        }
        print(f"[auto_gen]   extracted {len(EXPRESSION_ORDER)} expressions for {name}")

    bg_manifest: dict = {}
    for setting in settings:
        if hasattr(setting, "model_dump"):
            setting = setting.model_dump()
        sid = setting.get("id")
        if not sid or not setting.get("art_prompt"):
            print(f"[auto_gen] skipping setting {sid!r} — missing id or art_prompt")
            continue
        prompt = build_background_prompt(setting, art_style)
        print(f"[auto_gen] background: {sid} ...")
        png_bytes = generate_image(prompt)
        (bgs_dir / f"{sid}.png").write_bytes(png_bytes)
        bg_manifest[sid] = {
            "description": setting.get("description") or "",
            "url": f"/static/images/backgrounds/{story_id}/{sid}.png",
        }

    return {"character_sprites": char_manifest, "backgrounds": bg_manifest}
