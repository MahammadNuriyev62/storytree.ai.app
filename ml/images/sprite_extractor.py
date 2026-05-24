import cv2
import numpy as np
import zipfile
from PIL import Image
import io

from rembg import new_session, remove

# Lazy-init the rembg ONNX session once per process (model is ~150MB,
# downloaded on first use; subsequent inferences are ~0.5–2s per sprite on CPU).
_REMBG_SESSION = None


def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        _REMBG_SESSION = new_session("u2net")
    return _REMBG_SESSION


def extract_sprites_from_sheet(image_bytes: bytes) -> bytes:
    """
    Extract sprites from a sprite sheet and return them as a zip file.

    Args:
        image_bytes: The sprite sheet image as bytes

    Returns:
        Zip file containing extracted sprites as bytes
    """
    # Convert bytes to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    sheet = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if sheet is None:
        raise ValueError("Invalid image data")

    sheet_lab = cv2.cvtColor(sheet, cv2.COLOR_BGR2LAB)
    H, W = sheet.shape[:2]

    # Detect background color from borders
    border = 20
    border_pixels = np.vstack(
        [
            sheet_lab[:border, :, :].reshape(-1, 3),
            sheet_lab[-border:, :, :].reshape(-1, 3),
            sheet_lab[:, :border, :].reshape(-1, 3),
            sheet_lab[:, -border:, :].reshape(-1, 3),
        ]
    )
    bg_mean = border_pixels.mean(axis=0)

    # Calculate distance from background
    dist = np.linalg.norm(sheet_lab - bg_mean, axis=2)
    dist_norm = (dist / dist.max() * 255).astype(np.uint8)

    # Threshold and morphological operations
    _, mask0 = cv2.threshold(dist_norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask0 = cv2.morphologyEx(
        mask0,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        iterations=2,
    )

    # Find connected components (sprite boxes)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask0)
    boxes = [
        (x, y, w, h)
        for (_, x, y, w, h, area) in [(i, *stats[i]) for i in range(1, num)]
        if area > 8000  # Minimum area threshold
    ]
    boxes.sort(key=lambda b: b[0])  # Sort by x-coordinate

    # Extract individual sprites
    sprite_buffers = []

    # Asymmetric padding into the surrounding sheet background:
    #   - generous on top  -> protect hats, hair, raised arms
    #   - minimal on bottom -> avoid catching label text ("1. ANGRY" etc.) below
    #   - moderate on sides -> protect outstretched arms / props
    pad_top, pad_bottom, pad_side = 30, 5, 20

    session = _get_rembg_session()

    for idx, (x, y, w, h) in enumerate(boxes, 1):
        # Pad the connected-component bbox so rembg sees a bit of surrounding
        # background — improves edge quality. Asymmetric pad keeps label text
        # below the figure out of the ROI.
        x0 = max(0, x - pad_side)
        y0 = max(0, y - pad_top)
        x1 = min(W, x + w + pad_side)
        y1 = min(H, y + h + pad_bottom)
        roi_bgr = sheet[y0:y1, x0:x1]

        # rembg expects a PIL image (or bytes); return is RGBA PIL with a
        # semantically-segmented alpha — no more GrabCut color-confusion, so
        # hallucinated props (e.g. a white wall the model invented) drop out.
        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
        cutout = remove(Image.fromarray(roi_rgb), session=session)

        img_buffer = io.BytesIO()
        cutout.save(img_buffer, format="PNG")
        sprite_buffers.append((f"sprite_{idx}.png", img_buffer.getvalue()))

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in sprite_buffers:
            zf.writestr(filename, data)

    return zip_buffer.getvalue()
