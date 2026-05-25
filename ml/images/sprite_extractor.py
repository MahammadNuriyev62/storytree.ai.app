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

import cv2
import numpy as np
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


def _crop_to_content(rgba: Image.Image, alpha_threshold: int = 10, pad: int = 6) -> Image.Image:
    """Crop the image to the bounding box of its non-transparent content.

    Nano Banana doesn't always center the figure within its band, so naive
    fixed-width slicing produces sprites with the character pushed left or
    right and lots of empty space on the other side. The SPA's
    bottom-anchor positioning hides that visually, but it inflates file
    size and makes the sprite read as off-balance in any tool that shows
    the PNG's natural bounds. Trim to the alpha bbox with a small padding.
    """
    arr = np.array(rgba)
    if arr.shape[-1] != 4:
        return rgba
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > alpha_threshold)
    if len(ys) == 0:
        return rgba
    y0 = max(0, int(ys.min()) - pad)
    y1 = min(arr.shape[0], int(ys.max()) + pad + 1)
    x0 = max(0, int(xs.min()) - pad)
    x1 = min(arr.shape[1], int(xs.max()) + pad + 1)
    return Image.fromarray(arr[y0:y1, x0:x1])


def _drop_adjacent_band_intrusions(
    rgba: Image.Image, alpha_threshold: int = 30
) -> Image.Image:
    """Keep the main figure + anything horizontally overlapping with it.

    rembg/U²-Net produces a clean foreground mask, but anti-aliased
    transitions (a bishop sleeve narrowing to the wrist, a head joined
    by the thin slice of neck) can break the figure into multiple
    connected components. A naive "keep the largest" drops the body's
    sleeves, head, or other limbs whenever they happen to be disjoint
    in the mask. Observed on Vera (story 6) — her bishop sleeves were
    dropped, leaving only her narrow torso-and-skirt strip.

    The fix: find the largest component (the figure's body), then keep
    every other component whose horizontal bbox overlaps with it.
    Components horizontally separated from the body are almost always
    intrusions from an adjacent pose's band — those get dropped.
    """
    arr = np.array(rgba)
    if arr.shape[-1] != 4:
        return rgba
    mask = (arr[:, :, 3] > alpha_threshold).astype(np.uint8)
    n_comp, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n_comp <= 2:
        return rgba

    # stats columns: LEFT, TOP, WIDTH, HEIGHT, AREA
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    lx0 = int(stats[largest, cv2.CC_STAT_LEFT])
    lx1 = lx0 + int(stats[largest, cv2.CC_STAT_WIDTH])

    keep = np.zeros_like(mask, dtype=bool)
    for i in range(1, n_comp):
        cx0 = int(stats[i, cv2.CC_STAT_LEFT])
        cx1 = cx0 + int(stats[i, cv2.CC_STAT_WIDTH])
        # Overlap if the x-intervals intersect at all.
        if i == largest or (cx0 < lx1 and cx1 > lx0):
            keep |= labels == i

    arr[:, :, 3] = arr[:, :, 3] * keep
    return Image.fromarray(arr)


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
        cutout = _crop_to_content(_drop_adjacent_band_intrusions(remove(band, session=session)))
        buf = io.BytesIO()
        cutout.save(buf, format="PNG")
        sprite_buffers.append((f"sprite_{i + 1}.png", buf.getvalue()))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in sprite_buffers:
            zf.writestr(filename, data)
    return zip_buffer.getvalue()
