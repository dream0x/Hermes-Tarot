"""FLUX-driven tarot card renderer.

Each card is generated with a deck-wide *style anchor* prepended to the
per-card art prompt, so all 78 cards look like one cohesive deck. Results
are cached on disk by `(card_id, reversed_)` so demos run instantly.

Cost: ~$0.025 per FLUX [schnell] call (fal.ai default). The 22 Major
Arcana pre-warm is ~$0.55. Each fresh reading of 3 cards is ~$0.075.

Run:
    python -m tarot.render --test the-fool         # one card, force re-render
    python -m tarot.render --prewarm-major         # build the cache
"""
from __future__ import annotations

import argparse
import hashlib
import os
import time
from pathlib import Path

import fal_client
import requests
from PIL import Image, ImageDraw, ImageFont

from config import cfg
from ratelimit import record_spend
from tarot import deck as deck_mod

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TITLE_FONT_PATH = ASSETS / "EBGaramond.ttf"

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Style anchor: hand-tuned, kept in one place so all cards share it.
# IMPORTANT: aggressively suppress hallucinated card titles. FLUX schnell
# tends to invent card-name text in the bottom band — we kill it via the
# positive prompt because schnell ignores negatives.
DECK_STYLE = (
    "ornate hand-painted tarot card illustration in the Rider-Waite-Smith tradition, "
    "art-nouveau line work, muted indigo and antique gold palette with deep crimson accents, "
    "soft volumetric lighting, painterly textures, "
    "thin gilt border running uniformly around all four edges with only small abstract glyphs at the corners, "
    "the painted scene extends fully to the inner border on all sides including the bottom, "
    "absolutely no rectangular title cartouche, no banner, no caption strip, no name plate, "
    "no readable text anywhere, no letters, no inscription, "
    "vertical portrait orientation, mystical and quietly dramatic mood"
)
NEGATIVE = (
    "text, letters, words, captions, banner, title, cartouche, watermark, signature, logo, "
    "modern photo, photorealism, anime, cropped subject"
)

# Per-call cost estimate (used for global $-spend tracking).
# FLUX [dev] on fal.ai is ~ $0.025 per image at 1024px and respects the
# prompt much better than [schnell] (which hallucinates titles in cartouches).
COST_PER_IMAGE_USD = 0.025

# fal.ai model id. We use FLUX [dev] for prompt fidelity (schnell hallucinates
# card-name text in the bottom band even with strong negative prompts).
MODEL_ID = os.environ.get("FAL_MODEL_ID", "fal-ai/flux/dev")


def _ensure_fal_creds() -> None:
    if not cfg.fal_key:
        raise RuntimeError("FAL_KEY not set in env")
    # fal-client reads FAL_KEY from env; set it explicitly in case load order differs.
    os.environ["FAL_KEY"] = cfg.fal_key


def _cache_key(card_id: str, reversed_: bool) -> Path:
    suffix = "-R" if reversed_ else ""
    return CACHE_DIR / f"{card_id}{suffix}.png"


def _build_prompt(card_id: str, art_fragment: str, reversed_: bool) -> str:
    card = deck_mod.by_id(card_id)
    arcana_tag = "major arcana" if card.arcana == "major" else f"minor arcana, suit of {card.suit}"
    reversal_tag = ", composition rotated 180 degrees, inverted card" if reversed_ else ""
    return (
        f"{DECK_STYLE}, depicting {art_fragment}, "
        f"{arcana_tag}, archetypal symbolism, mystical{reversal_tag}"
    )


def _download(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


def _overlay_title(path: Path, card_name: str, reversed_: bool = False) -> None:
    """Cover FLUX's hallucinated bottom-band title with a clean parchment
    cartouche containing the *real* card name in EB Garamond. Also masks any
    top-band glyph FLUX may have stuck in. In-place edit.

    Tuned for 768x1024 portrait_4_3 outputs.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    draw = ImageDraw.Draw(im)

    # Sample colors from the existing border for a coherent overlay.
    # Pixel (8, h//2) is reliably inside the left gold border.
    gold = im.getpixel((8, h // 2))
    # Inner cartouche uses a slightly lighter parchment.
    parchment = tuple(min(255, int(c * 1.05)) for c in gold)
    ink = (28, 22, 16)

    # --- Bottom title cartouche ---
    band_h = int(h * 0.085)
    band_top = h - band_h - int(h * 0.01)
    pad_x = int(w * 0.10)
    rect = (pad_x, band_top, w - pad_x, band_top + band_h)
    draw.rectangle(rect, fill=parchment, outline=gold, width=3)
    # Inner thin border for that classic two-line cartouche look
    inner = (rect[0] + 4, rect[1] + 4, rect[2] - 4, rect[3] - 4)
    draw.rectangle(inner, outline=gold, width=1)

    # Title text — fit to band. Reversed indicator is the 180° rotation
    # applied later, not text decoration (which would itself flip).
    title = card_name.upper()
    inner_w = inner[2] - inner[0] - 24
    inner_h = inner[3] - inner[1] - 12
    # Binary-search the largest font size that fits horizontally + vertically
    lo, hi, best = 8, 96, 8
    font_path = str(TITLE_FONT_PATH) if TITLE_FONT_PATH.exists() else None
    while lo <= hi:
        mid = (lo + hi) // 2
        font = ImageFont.truetype(font_path, mid) if font_path else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), title, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= inner_w and th <= inner_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
        if not font_path:
            break
    font = ImageFont.truetype(font_path, best) if font_path else ImageFont.load_default()
    bbox = draw.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # Center in band
    tx = inner[0] + (inner[2] - inner[0] - tw) // 2 - bbox[0]
    ty = inner[1] + (inner[3] - inner[1] - th) // 2 - bbox[1]
    draw.text((tx, ty), title, font=font, fill=ink)

    im.save(path, format="PNG", optimize=True)


def render_card(
    card_id: str,
    art_fragment: str | None = None,
    *,
    reversed_: bool = False,
    force: bool = False,
) -> Path:
    """Return a path to a PNG of the card. Uses on-disk cache."""
    import logging as _lg
    _flux_log = _lg.getLogger("mnemos.flux")
    cache = _cache_key(card_id, reversed_)
    if cache.exists() and not force:
        _flux_log.info("MNEMOS_EVENT flux model=cache card=%s reversed=%s cost_usd=0",
                       card_id, reversed_)
        return cache

    _flux_log.info("MNEMOS_EVENT flux model=%s card=%s reversed=%s cost_usd=%.4f",
                   MODEL_ID, card_id, reversed_, COST_PER_IMAGE_USD)
    _ensure_fal_creds()
    if art_fragment is None:
        art_fragment = deck_mod.by_id(card_id).art_prompt

    prompt = _build_prompt(card_id, art_fragment, reversed_)
    seed = int(hashlib.sha256(card_id.encode()).hexdigest()[:12], 16)

    # fal-client subscribe = blocking call until ready.
    # Step counts: schnell=4, dev=28, pro=auto. We default to dev's sweet spot.
    steps = 4 if "schnell" in MODEL_ID else 28
    result = fal_client.subscribe(
        MODEL_ID,
        arguments={
            "prompt": prompt,
            "image_size": "portrait_4_3",  # 768x1024-ish
            "num_inference_steps": steps,
            "num_images": 1,
            "enable_safety_checker": False,
            "seed": seed,
            "guidance_scale": 4.5,         # dev sweet spot for prompt fidelity
        },
        with_logs=False,
    )
    images = result.get("images") or []
    if not images:
        raise RuntimeError(f"FLUX returned no images for {card_id}: {result}")
    url = images[0]["url"]
    _download(url, cache)
    # Always overlay the *correct* card name; FLUX's title cartouche is wrong.
    card = deck_mod.by_id(card_id)
    _overlay_title(cache, card.name, reversed_=reversed_)
    # For reversed cards, rotate the entire composed image 180° — that's how a
    # real reversed tarot card looks: the artwork upside down, the title cartouche
    # at the top when held normally. The reader recognises it instantly.
    if reversed_:
        from PIL import Image as _PI
        im = _PI.open(cache).convert("RGB").rotate(180, expand=False)
        im.save(cache, format="PNG", optimize=True)
    record_spend(COST_PER_IMAGE_USD, "fal")
    return cache


def prewarm_major(force: bool = False) -> int:
    """Render all 22 Major Arcana into the cache (one-time)."""
    n = 0
    for card in deck_mod.MAJOR:
        path = _cache_key(card.id, False)
        if path.exists() and not force:
            continue
        print(f"  rendering {card.name} ...", flush=True)
        t0 = time.time()
        render_card(card.id, card.art_prompt, reversed_=False, force=force)
        dt = time.time() - t0
        print(f"     -> {path.name} ({dt:.1f}s)")
        n += 1
    return n


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--test", type=str, help="card id, e.g. 'the-fool'")
    p.add_argument("--reversed", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--prewarm-major", action="store_true")
    args = p.parse_args()

    if args.test:
        path = render_card(args.test, reversed_=args.reversed, force=args.force)
        print(f"OK {path}  ({path.stat().st_size//1024} KB)")
    if args.prewarm_major:
        n = prewarm_major(force=args.force)
        print(f"prewarmed {n} Major Arcana into {CACHE_DIR}")
    if not (args.test or args.prewarm_major):
        p.print_help()
