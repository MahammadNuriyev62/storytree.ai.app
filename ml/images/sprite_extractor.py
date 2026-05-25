"""Extract individual sprites from a 5-pose horizontal sprite sheet.

We KNOW the sheet's structure (our generator prompt guarantees it):
- Exactly 5 figures, left-to-right
- Roughly equal horizontal spacing
- Plain pure-white background
- Optional label strip ("ANGRY / SAD / SMILING / NEUTRAL / SCARED") at the
  bottom of the sheet (Nano Banana sometimes adds it)

Given that, the robust approach is **fixed vertical-band slicing**: divide
the sheet into 5 equal-width vertical bands, crop a few pixels off the bottom
to remove the label strip, run rembg/U²-Net on each band as one figure.

We deliberately do NOT use connected-components on a color-distance mask
anymore. That approach had two known failure modes we hit in real-world use:

  1. **Lighting/scene bleed across figures** (e.g. a fireplace painted behind
     pose 1 reaches into pose 2's foreground in the mask) — two figures
     merge into one bbox; we get 4 sprites instead of 5 and the rest of
     the expression mapping shifts.

  2. **Head-body disconnection** when a character wears a white shirt on the
     white background (e.g. Musa in story 5). The shirt is indistinguishable
     from the background in the mask, so the face becomes an isolated island
     connected to the torso only via the thin slice of neck skin. The
     morphological close can't bridge it; the head component falls below
     the area threshold and gets filtered out. Result: every sprite of that
     character is headless from the neck down.

Vertical-band slicing is immune to both: every band contains exactly one
whole figure top-to-bottom, and rembg's U²-Net does the foreground extraction
inside the band without any color-distance heuristic.

Trade-off: this assumes the model produces 5 evenly-spaced figures. Our
prompt asks for that explicitly ("equal spacing between each pose, clear
gap between figures") so it holds in practice.
"""

import io
import zipfile
from typing import List, Tuple

from PIL import Image
from rembg import new_session, remove

# Lazy-init the rembg ONNX session once per process (model is ~150MB,
# downloaded on first use; subsequent inferences are ~0.5-2s per sprite on CPU).
_REMBG_SESSION = None

# Crop this many pixels off the bottom of the sheet before slicing, to remove
# the optional "ANGRY / SAD / ..." label strip Nano Banana sometimes prints.
DEFAULT_LABEL_STRIP_PX = 60

# Number of poses we expect on every sheet.
DEFAULT_N_POSES = 5


def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        _REMBG_SESSION = new_session("u2net")
    return _REMBG_SESSION


def _slice_into_bands(
    sheet: Image.Image,
    n: int = DEFAULT_N_POSES,
    label_strip_px: int = DEFAULT_LABEL_STRIP_PX,
) -> List[Tuple[int, Image.Image]]:
    """Return [(index, band_image), ...] — n equal-width vertical bands of the
    sheet, with the bottom label strip cropped off."""
    W, H = sheet.size
    H_eff = max(1, H - label_strip_px)
    band_w = W // n
    bands = []
    for i in range(n):
        x0 = i * band_w
        x1 = (i + 1) * band_w if i < n - 1 else W
        bands.append((i, sheet.crop((x0, 0, x1, H_eff))))
    return bands


def extract_sprites_from_sheet(
    image_bytes: bytes,
    n_poses: int = DEFAULT_N_POSES,
    label_strip_px: int = DEFAULT_LABEL_STRIP_PX,
) -> bytes:
    """Extract sprites from a sprite sheet and return them as a zip file.

    Args:
        image_bytes: PNG/JPEG sprite-sheet bytes.
        n_poses: Number of figures left-to-right. Default 5.
        label_strip_px: Pixels to crop off the bottom before slicing.

    Returns:
        Zip-file bytes containing `sprite_1.png` .. `sprite_N.png`, in
        left-to-right order. Each is RGBA with a semantically-segmented alpha
        (transparent background).
    """
    sheet = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if sheet.size[0] < n_poses * 10 or sheet.size[1] < 50:
        raise ValueError(f"sheet too small to slice: {sheet.size}")

    session = _get_rembg_session()
    sprite_buffers: List[Tuple[str, bytes]] = []
    for i, band in _slice_into_bands(sheet, n_poses, label_strip_px):
        cutout = remove(band, session=session)
        buf = io.BytesIO()
        cutout.save(buf, format="PNG")
        sprite_buffers.append((f"sprite_{i + 1}.png", buf.getvalue()))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in sprite_buffers:
            zf.writestr(filename, data)
    return zip_buffer.getvalue()
