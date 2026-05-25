"""Regression tests for `ml/images/sprite_extractor.py`.

These tests guard against the two extractor bugs we've actually shipped and
later had to dig out:

  1. **Headless sprites** — when a character wears something close to the
     background colour (e.g. a white shirt on a white sheet), the connected-
     components extractor disconnected their face from their body, the head
     blob fell below the area threshold, and every extracted sprite for that
     character was cropped from the neck down. Reproducer: Musa from story 5.

  2. **Merged adjacent figures** — when prop or lighting language bridged
     two figures in the colour-distance mask (e.g. a fireplace painted
     behind one pose, or a hand resting on a bar), connected-components
     returned 4 bboxes instead of 5 and the expression mapping shifted
     by one. Reproducer: Hannah's first sheet in story 4.

Fixtures live in `tests/fixtures/` — real sprite sheets we generated via
Nano Banana Pro and committed for reproducibility. The tests are slow
(rembg/U²-Net is CPU-only, ~1-2s per sprite) so all together they take
~15-30s. They run by default — protecting the extractor is worth it.

What we assert per fixture:
  * Exactly 5 sprites returned (counts), named sprite_1..sprite_5
  * Each sprite has visible content in the TOP 15% (catches headless bug)
  * Each sprite has visible content in the BOTTOM 15% (catches footless bug)
  * Each sprite has alpha channel + transparent corners (catches "rembg
    didn't run" or "background kept as white")
  * No two sprites are byte-identical (catches accidental duplication)
  * Each sprite has reasonable dimensions (not collapsed to a few px)

If you "improve" the extractor and break any of these, the test name
tells you what regression you re-introduced.
"""

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from ml.images.sprite_extractor import extract_sprites_from_sheet

FIXTURES = Path(__file__).parent / "fixtures"

# Each fixture pairs a sprite-sheet PNG with a short note on what edge case
# it documents. Add new fixtures here when you find another failure mode.
SHEETS = [
    pytest.param(
        FIXTURES / "sheet_musa_white_shirt_on_white.png",
        id="musa_white_shirt_on_white_bg",
    ),
    pytest.param(
        FIXTURES / "sheet_iwan_anime_with_prop.png",
        id="iwan_anime_one_pose_with_stone_prop",
    ),
]


def _extract(sheet_path: Path) -> list[Image.Image]:
    """Run the extractor on one fixture; return RGBA PIL images in order."""
    sheet_bytes = sheet_path.read_bytes()
    zip_bytes = extract_sprites_from_sheet(sheet_bytes)
    sprites: list[Image.Image] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in sorted(zf.namelist()):
            sprites.append(Image.open(io.BytesIO(zf.read(name))).convert("RGBA"))
    return sprites


def _has_content(img: Image.Image, y_start_frac: float, y_end_frac: float) -> bool:
    """Are there any non-transparent pixels in the band [y_start, y_end) of img?"""
    W, H = img.size
    y0 = int(H * y_start_frac)
    y1 = int(H * y_end_frac)
    band = img.crop((0, y0, W, y1))
    alpha = band.split()[-1]
    return alpha.getextrema()[1] > 0  # max alpha > 0 means at least one visible pixel


def _corner_is_transparent(img: Image.Image, alpha_threshold: int = 20) -> bool:
    """Every corner pixel has alpha below `alpha_threshold` — proxy for
    'rembg removed the bg.' Threshold rather than ==0 because rembg/U²-Net
    sometimes leaves a faint feathered edge a few alpha units above zero
    (observed alpha=7 in the bottom-right of one fixture sprite)."""
    W, H = img.size
    a = img.split()[-1]
    for x in (0, W - 1):
        for y in (0, H - 1):
            if a.getpixel((x, y)) >= alpha_threshold:
                return False
    return True


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_returns_five_named_sprites(sheet_path):
    """The extractor returns exactly 5 sprites in sprite_1..sprite_5 order."""
    sheet_bytes = sheet_path.read_bytes()
    zip_bytes = extract_sprites_from_sheet(sheet_bytes)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = sorted(zf.namelist())
    assert names == [f"sprite_{i}.png" for i in range(1, 6)], names


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_every_sprite_has_a_head(sheet_path):
    """Top 15% of every sprite has at least one non-transparent pixel.

    Guards against the Musa regression (white shirt on white bg disconnected
    the face component; the bbox covered only the body; every sprite was
    headless from the neck down).
    """
    sprites = _extract(sheet_path)
    for i, sprite in enumerate(sprites, 1):
        assert _has_content(sprite, 0.0, 0.15), (
            f"sprite_{i}.png from {sheet_path.name} has no content in the top "
            "15% — head missing (extractor probably dropped the head as a "
            "small disconnected component)"
        )


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_every_sprite_has_feet(sheet_path):
    """Bottom 15% of every sprite has visible content."""
    sprites = _extract(sheet_path)
    for i, sprite in enumerate(sprites, 1):
        assert _has_content(sprite, 0.85, 1.0), (
            f"sprite_{i}.png from {sheet_path.name} has no content in the "
            "bottom 15% — feet missing (probably over-aggressive label-strip "
            "crop or bottom padding regression)"
        )


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_corners_are_transparent(sheet_path):
    """The background was actually removed (alpha=0 at every corner)."""
    sprites = _extract(sheet_path)
    for i, sprite in enumerate(sprites, 1):
        assert sprite.mode == "RGBA", f"sprite_{i}.png is not RGBA"
        assert _corner_is_transparent(sprite), (
            f"sprite_{i}.png from {sheet_path.name} has opaque corners — "
            "rembg either didn't run or the bg colour wasn't extracted"
        )


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_sprites_are_unique(sheet_path):
    """No two sprites are byte-identical.

    Guards against the case where the extractor returns N<5 and the caller
    fills missing slots by duplicating one (which is what auto_gen.py does
    today, but THAT logic should only fire on bad sheets — never on the
    clean fixtures here).
    """
    sheet_bytes = sheet_path.read_bytes()
    zip_bytes = extract_sprites_from_sheet(sheet_bytes)
    seen: set[bytes] = set()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in sorted(zf.namelist()):
            data = zf.read(name)
            assert data not in seen, f"{name} duplicates a previous sprite"
            seen.add(data)


@pytest.mark.parametrize("sheet_path", SHEETS)
def test_sprites_have_reasonable_dimensions(sheet_path):
    """Each sprite is wider than 100px and taller than 300px.

    Catches degenerate slicing (e.g. accidentally splitting into 50 bands)
    and over-aggressive bottom cropping.
    """
    sprites = _extract(sheet_path)
    for i, sprite in enumerate(sprites, 1):
        W, H = sprite.size
        assert W >= 100, f"sprite_{i}.png from {sheet_path.name} is too narrow: {W}px"
        assert H >= 300, f"sprite_{i}.png from {sheet_path.name} is too short: {H}px"
