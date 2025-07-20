import cv2
import numpy as np
import zipfile
from PIL import Image
import io


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

    for idx, (x, y, w, h) in enumerate(boxes, 1):
        roi = sheet[y : y + h, x : x + w].copy()
        mask = np.zeros(roi.shape[:2], np.uint8)
        margin = 15

        # Set probable background and foreground regions
        mask[:margin, :] = cv2.GC_PR_BGD
        mask[-margin:, :] = cv2.GC_PR_BGD
        mask[:, :margin] = cv2.GC_PR_BGD
        mask[:, -margin:] = cv2.GC_PR_BGD
        mask[margin : h - margin, margin : w - margin] = cv2.GC_PR_FGD

        # Apply GrabCut algorithm
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        cv2.grabCut(roi, mask, None, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)

        # Create alpha channel
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(
            np.uint8
        )

        # Refine mask with morphological operations
        k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, k3, iterations=1)
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, k3, iterations=1)

        # Convert to RGBA
        rgba = cv2.cvtColor(roi, cv2.COLOR_BGR2RGBA)
        rgba[:, :, 3] = alpha

        # Save to buffer
        img_buffer = io.BytesIO()
        Image.fromarray(rgba).save(img_buffer, format="PNG")
        sprite_buffers.append((f"sprite_{idx}.png", img_buffer.getvalue()))

    # Create zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, data in sprite_buffers:
            zf.writestr(filename, data)

    return zip_buffer.getvalue()
