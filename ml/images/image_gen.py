"""Image generation via Google Gemini (Nano Banana family) + Imagen.

Three guardrails keep development cheap and predictable:

1. Content-addressed cache — same prompt + model + reference images returns the
   cached PNG instantly, no API call.
2. Hard budget cap — every real call logs to .image_costs.jsonl; once cumulative
   cost would exceed IMAGE_BUDGET_USD (default $5), generation raises before
   spending anything.
3. Mock mode — set IMAGE_MOCK=1 to return a labelled placeholder PNG with no
   API call, for plumbing/dev.

Use `generate_image(prompt, model=..., ref_images=...) -> bytes` (PNG bytes).
Inspect spend with `python3 -m ml.images.image_gen`.
"""

import hashlib
import io
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Approximate per-image costs in USD. Verify against your actual Google billing.
COST_USD = {
    "gemini-3-pro-image-preview": 0.15,        # Nano Banana Pro
    "gemini-3.1-flash-image-preview": 0.04,    # Nano Banana 2
    "gemini-2.5-flash-image": 0.04,            # Nano Banana
    "gemini-2.5-flash-preview-image": 0.04,
    "imagen-4.0-generate-001": 0.04,
    "imagen-4.0-fast-generate-001": 0.02,
    "imagen-4.0-ultra-generate-001": 0.06,
}
DEFAULT_MODEL = "gemini-3-pro-image-preview"

ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
CACHE_DIR = ROOT / ".image_cache"
LEDGER = ROOT / ".image_costs.jsonl"
CACHE_DIR.mkdir(exist_ok=True)


def _budget_cap() -> float:
    return float(os.getenv("IMAGE_BUDGET_USD", "5.00"))


def _is_mock() -> bool:
    return os.getenv("IMAGE_MOCK", "").lower() in ("1", "true", "yes")


def _spent_so_far() -> float:
    if not LEDGER.exists():
        return 0.0
    total = 0.0
    for line in LEDGER.read_text().splitlines():
        try:
            total += json.loads(line).get("cost", 0.0)
        except json.JSONDecodeError:
            continue
    return total


def _cache_key(prompt: str, model: str, ref_images: Optional[List[bytes]]) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(prompt.encode())
    for img in ref_images or []:
        h.update(img)
    return h.hexdigest()[:16]


def _placeholder(prompt: str, model: str) -> bytes:
    """A diagonal-striped PNG with the prompt overlaid — used in mock mode."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1024, 1024), (28, 20, 48))
    draw = ImageDraw.Draw(img)
    for i in range(-1024, 2048, 80):
        draw.line([(i, 0), (i + 1024, 1024)], fill=(38, 28, 64), width=18)
    draw.text((40, 40), f"[MOCK · {model}]", fill=(220, 200, 240))
    # naive word-wrap
    line, lines = "", []
    for word in prompt.split():
        if len(line) + len(word) > 60:
            lines.append(line); line = word
        else:
            line = f"{line} {word}".strip()
    if line: lines.append(line)
    for i, l in enumerate(lines[:20]):
        draw.text((40, 100 + i * 26), l, fill=(180, 180, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _log_call(model: str, prompt: str, cost: float, elapsed: float, cache_key: str):
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "cost": round(cost, 4),
        "elapsed_s": round(elapsed, 1),
        "cache_key": cache_key,
        "prompt_preview": prompt[:120],
    }
    with LEDGER.open("a") as f:
        f.write(json.dumps(row) + "\n")


class BudgetExceeded(RuntimeError):
    pass


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ref_images: Optional[List[bytes]] = None,
) -> bytes:
    """Generate an image, going through cache → mock → budget → real API.

    Returns PNG bytes. Raises BudgetExceeded if a real call would exceed the cap.
    """
    key = _cache_key(prompt, model, ref_images)
    cached = CACHE_DIR / f"{key}.png"
    if cached.exists():
        return cached.read_bytes()

    if _is_mock():
        data = _placeholder(prompt, model)
        cached.write_bytes(data)
        return data

    cost_est = COST_USD.get(model, 0.15)
    spent = _spent_so_far()
    budget = _budget_cap()
    if spent + cost_est > budget:
        raise BudgetExceeded(
            f"image generation would exceed cap: spent ${spent:.2f} + "
            f"estimate ${cost_est:.2f} > cap ${budget:.2f}. "
            f"Set IMAGE_BUDGET_USD higher or use IMAGE_MOCK=1."
        )

    # Real API call.
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Try .env as a fallback (the FastAPI app uses pydantic-settings).
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("'\"")
                    os.environ["GEMINI_API_KEY"] = api_key
                    break
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set (env or .env)")

    client = genai.Client(api_key=api_key)
    contents: list = [prompt]
    for ref in ref_images or []:
        contents.append(types.Part.from_bytes(data=ref, mime_type="image/png"))

    t0 = time.time()
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    elapsed = time.time() - t0

    image_bytes = None
    for part in resp.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            image_bytes = part.inline_data.data
            break
    if not image_bytes:
        raise RuntimeError(
            f"no image in response (parts: {[type(p).__name__ for p in resp.candidates[0].content.parts]})"
        )

    cached.write_bytes(image_bytes)
    _log_call(model, prompt, cost_est, elapsed, key)

    new_total = _spent_so_far()
    print(
        f"[image: ${cost_est:.2f} | session total ${new_total:.2f} / ${budget:.2f} budget | {elapsed:.1f}s]"
    )
    return image_bytes


def summary():
    """Print a cost summary from the ledger."""
    if not LEDGER.exists() or not LEDGER.read_text().strip():
        print("no image calls logged yet")
        return
    rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    total = sum(r.get("cost", 0) for r in rows)
    print(f"total spent: ${total:.2f} across {len(rows)} calls (cap ${_budget_cap():.2f})")
    by_model: dict = {}
    for r in rows:
        m = r["model"]
        by_model.setdefault(m, {"n": 0, "cost": 0.0})
        by_model[m]["n"] += 1
        by_model[m]["cost"] += r.get("cost", 0)
    for m, s in sorted(by_model.items()):
        print(f"  {m}: {s['n']} calls, ${s['cost']:.2f}")


if __name__ == "__main__":
    summary()
