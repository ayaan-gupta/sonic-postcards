"""Interim design-time art, drawn in code with the same painter as the postcards.

Every file here is also requested as real artwork in assets/prompts.md. Until
that arrives these keep the product looking finished. `scripts/draw_interim.py`
writes them to assets/interim.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from app.audio.motifs import MOTIFS
from app.postcard import props
from app.postcard.brief import PostcardBrief
from app.postcard.paint import RGB, Canvas, hex_rgb, mix
from app.postcard.palette import PALETTES, Palette
from app.postcard.scene import paint_scene

PAPER = hex_rgb("#f6f0e1")
INK = hex_rgb("#1d2440")
ACCENT = hex_rgb("#e2583a")

STAMP_SIZE = (300, 372)  # drawn at twice the size it is shown


def _seed(name: str) -> int:
    return sum(ord(ch) * (i + 1) for i, ch in enumerate(name)) % 100_000


def _stamp_picture(motif: str, width: int, height: int) -> Image.Image:
    """The little painting inside a stamp: one object on a two-colour ground."""
    night = motif in ("insects", "fireworks", "fire")
    p: Palette = PALETTES["night" if night else ("dusk" if motif in ("bells", "music") else "day")]
    c = Canvas(width, height, _seed(motif), wobble=0.35)
    c.rect(-5, -5, width + 5, height + 5, p.sky[1], 0.07)
    c.ridge(height * 0.34, 5, p.sky[2], bumps=1.0)
    ground = height * 0.8
    cx = width / 2
    if motif in ("waves",):
        c.rect(-5, height * 0.56, width + 5, height + 5, p.water, 0.07)
        for i in range(4):
            y = height * (0.66 + 0.09 * i)
            c.curve([(10, y), (cx - 20, y - 6), (cx + 10, y + 2), (width - 10, y - 4)], p.foam, 2.6)
        props.sailboat(c, cx, height * 0.66, 0.95, p, p.accent)
    else:
        c.ridge(ground, 4, mix(p.ground, p.near, 0.15) if motif not in ("traffic", "footsteps", "works", "cafe", "market", "music", "bells") else mix(p.path, p.ground, 0.2), bumps=1.0)
    foot = height * 0.9
    if motif == "rain":
        props.cloud(c, cx, height * 0.3, 96, mix(p.cloud, p.far, 0.45))
        props.walker(c, cx - 6, foot, 1.15, p, p.dark, umbrella=p.accent)
        for _ in range(26):
            x, y = c.uniform(0, width), c.uniform(height * 0.3, height * 0.95)
            c.line([(x, y), (x - 5, y + 16)], p.light, 1.8)
    elif motif == "storm":
        props.cloud(c, cx, height * 0.34, 112, mix(p.cloud, p.dark, 0.5))
        props.lightning(c, cx + 4, height * 0.36, height * 0.86, p.sun)
    elif motif == "water":
        props.fountain(c, cx, foot, 0.72, p)
    elif motif == "wind":
        props.kite(c, cx + 14, height * 0.36, 0.95, p, (cx - 40, foot))
        c.curve([(8, height * 0.62), (cx - 20, height * 0.56), (cx + 6, height * 0.66), (width - 30, height * 0.58)], p.light, 2.6)
    elif motif == "birds":
        c.line([(0, height * 0.62), (width, height * 0.58)], p.dark, 2)
        props.perched_bird(c, cx - 8, height * 0.6, 2.1, p.dark, p.accent)
        props.flying_bird(c, width * 0.74, height * 0.22, 13, p.dark)
        props.flying_bird(c, width * 0.56, height * 0.14, 9, p.dark)
    elif motif == "insects":
        for i in range(16):
            x = width * (i + 0.5) / 16
            c.poly([(x - 3, height), (x + c.uniform(-8, 8), height * c.uniform(0.5, 0.74)), (x + 3, height)], mix(p.near, p.dark, 0.3), 0.0)
        for x, y in ((0.3, 0.42), (0.62, 0.3), (0.72, 0.56), (0.42, 0.62), (0.2, 0.22)):
            c.ellipse(width * x, height * y, 9, 9, mix(p.light, p.sky[1], 0.5), 0.0)
            c.ellipse(width * x, height * y, 4, 4, p.light, 0.0)
    elif motif == "animals":
        props.sheep(c, cx - 8, foot, 1.5, p)
    elif motif == "traffic":
        c.rect(-5, height * 0.84, width + 5, height + 5, mix(p.dark, p.far, 0.35), 0.06)
        props.car(c, cx, height * 0.95, 0.92, p, p.accent)
    elif motif == "train":
        c.rect(-5, foot, width + 5, foot + 4, p.dark, 0.0)
        s_brief = PostcardBrief("stamp-train", ["train"], [], "day", "", None, date(2026, 1, 1))
        from app.postcard.scene import Scene, train  # local import: scene imports props, not this module

        train(Scene(c=c, p=p, brief=s_brief, motifs=["train"], setting="railway"), width + 44, foot, 0.8)
    elif motif == "aircraft":
        props.plane(c, cx + 10, height * 0.42, 0.72, p)
    elif motif == "bells":
        c.pie(cx, height * 0.56, 34, 50, 180, 360, p.accent)
        c.rect(cx - 42, height * 0.54, cx + 42, height * 0.6, p.accent, 0.03)
        c.ellipse(cx, height * 0.64, 8, 8, p.light, 0.0)
        c.line([(cx, height * 0.2), (cx, height * 0.3)], p.dark, 4)
        for i in range(2):
            r = 56 + i * 16
            c.arc(cx, height * 0.5, r, r, 150, 200, p.light, 3)
            c.arc(cx, height * 0.5, r, r, -20, 30, p.light, 3)
    elif motif == "music":
        props.music_note(c, cx - 26, height * 0.6, 2.2, p.light, double=True)
    elif motif == "market":
        props.stall(c, cx, foot, 0.78, p, (p.accent, p.light))
    elif motif == "cafe":
        c.rect(cx - 24, height * 0.5, cx + 20, height * 0.72, p.light)
        c.arc(cx + 24, height * 0.6, 12, 10, -90, 90, p.light, 4)
        c.ellipse(cx - 2, height * 0.76, 40, 7, p.accent, 0.03)
        c.curve([(cx - 8, height * 0.44), (cx - 14, height * 0.36), (cx - 2, height * 0.28), (cx - 8, height * 0.18)], p.light, 3)
        c.curve([(cx + 8, height * 0.44), (cx + 2, height * 0.36), (cx + 14, height * 0.28), (cx + 8, height * 0.18)], p.light, 3)
    elif motif == "footsteps":
        props.walker(c, cx, foot, 1.3, p, p.accent)
    elif motif == "fire":
        props.campfire(c, cx, foot, 0.85, p)
    elif motif == "fireworks":
        props.firework(c, cx, height * 0.4, 44, (p.accent, p.light), ground=height)
    elif motif == "works":
        props.crane(c, cx - 22, foot, 0.48, p)
    elif motif == "hum":
        c.ellipse(cx, height * 0.4, 24, 24, p.sun)
        c.ridge(height * 0.62, 12, p.far, bumps=1.6)
        c.ridge(height * 0.72, 9, p.mid, bumps=1.2)
    return c.finish(full_size=True)


def draw_stamp(motif: str) -> Image.Image:
    """A perforated stamp with a painting of the motif. The bottom band is left for the value."""
    width, height = STAMP_SIZE
    stamp = Image.new("RGBA", (width, height), (*PAPER, 255))
    margin = 26
    band = 44
    picture = _stamp_picture(motif, (width - 2 * margin) // 2, (height - 2 * margin - band) // 2)
    stamp.paste(picture, (margin, margin))
    draw = ImageDraw.Draw(stamp)
    draw.rectangle([margin - 3, margin - 3, width - margin + 2, height - margin - band + 2], outline=(*INK, 255), width=3)
    # Perforations: bite half circles out of all four edges.
    mask = Image.new("L", (width, height), 255)
    bite = ImageDraw.Draw(mask)
    radius, pitch = 9, 30
    for i in range(width // pitch + 1):
        x = i * pitch + (width % pitch) / 2
        bite.ellipse([x - radius, -radius, x + radius, radius], fill=0)
        bite.ellipse([x - radius, height - radius, x + radius, height + radius], fill=0)
    for i in range(height // pitch + 1):
        y = i * pitch + (height % pitch) / 2
        bite.ellipse([-radius, y - radius, radius, y + radius], fill=0)
        bite.ellipse([width - radius, y - radius, width + radius, y + radius], fill=0)
    stamp.putalpha(mask)
    return stamp


def draw_postmark() -> Image.Image:
    """Blank postmark: two rings and six wavy cancellation lines, ink on transparent."""
    width, height = 760, 400
    scale = 2
    layer = Image.new("L", (width * scale, height * scale), 0)
    draw = ImageDraw.Draw(layer)
    cx, cy, outer, inner = 200 * scale, 200 * scale, 184 * scale, 122 * scale
    draw.ellipse([cx - outer, cy - outer, cx + outer, cy + outer], outline=255, width=7 * scale)
    draw.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], outline=255, width=4 * scale)
    for i in range(6):
        y0 = (86 + i * 46) * scale
        points = []
        for step in range(0, 81):
            x = (392 + step * 4.5) * scale
            points.append((x, y0 + math.sin(step / 80 * math.tau * 3.2) * 13 * scale))
        draw.line(points, fill=255, width=6 * scale, joint="curve")
    layer = layer.resize((width, height), Image.Resampling.LANCZOS)
    # A rubber stamp never prints evenly: knock ink out with two scales of noise.
    rng = np.random.default_rng(7)
    coarse = Image.fromarray((rng.random((height // 14, width // 14)) * 255).astype(np.uint8), "L").resize((width, height), Image.Resampling.BICUBIC)
    fine = Image.fromarray((rng.random((height, width)) * 255).astype(np.uint8), "L")
    alpha = np.asarray(layer, dtype=np.float32) / 255.0
    wear = np.clip(0.55 + np.asarray(coarse, dtype=np.float32) / 255.0 * 0.6, 0, 1) * np.where(np.asarray(fine) < 26, 0.25, 1.0)
    alpha = np.clip(alpha * wear, 0, 1)
    out = Image.new("RGBA", (width, height), (*INK, 0))
    out.putalpha(Image.fromarray((alpha * 255).astype(np.uint8), "L"))
    return out


def draw_logo(size: int = 512, *, maskable: bool = False) -> Image.Image:
    """The mark: a red stamp whose picture is a sound wave."""
    scale = 2
    full = size * scale
    image = Image.new("RGBA", (full, full), (*ACCENT, 255) if maskable else (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    inset = full * (0.2 if maskable else 0.06)
    body = [inset, inset, full - inset, full - inset]
    if not maskable:
        draw.rounded_rectangle(body, radius=full * 0.1, fill=(*ACCENT, 255))
        side = full - 2 * inset
        radius = side * 0.035
        count = 9
        for i in range(count):
            t = inset + side * (i + 0.5) / count
            for x, y in ((t, inset), (t, full - inset), (inset, t), (full - inset, t)):
                draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=(0, 0, 0, 0))
    frame = inset + (full - 2 * inset) * 0.13
    draw.rounded_rectangle([frame, frame, full - frame, full - frame], radius=full * 0.03, outline=(*PAPER, 255), width=max(2, round(full * 0.014)))
    bars = (0.22, 0.46, 0.8, 0.56, 1.0, 0.62, 0.34)
    area = full - 2 * frame
    bar_w = area * 0.07
    gap = (area * 0.76 - bar_w * len(bars)) / (len(bars) - 1)
    x = frame + area * 0.12
    for value in bars:
        half = area * 0.3 * value
        draw.rounded_rectangle([x, full / 2 - half, x + bar_w, full / 2 + half], radius=bar_w / 2, fill=(*PAPER, 255))
        x += bar_w + gap
    return image.resize((size, size), Image.Resampling.LANCZOS)


def _vignette(brief: PostcardBrief, size: tuple[int, int], *, arch: bool) -> Image.Image:
    """A scene cut into an arched window or a rounded card, on transparent."""
    art = paint_scene(brief)
    width, height = size
    scale = max(width / art.width, height / art.height)
    art = art.resize((round(art.width * scale), round(art.height * scale)), Image.Resampling.LANCZOS)
    left, top = (art.width - width) // 2, (art.height - height) // 2
    art = art.crop((left, top, left + width, top + height)).convert("RGBA")
    mask = Image.new("L", (width * 2, height * 2), 0)
    draw = ImageDraw.Draw(mask)
    if arch:
        draw.pieslice([0, 0, width * 2, height * 1.6], 180, 360, fill=255)
        draw.rounded_rectangle([0, height * 0.8 - 1, width * 2, height * 2], radius=56, fill=255, corners=(False, False, True, True))
    else:
        draw.rounded_rectangle([0, 0, width * 2, height * 2], radius=72, fill=255)
    art.putalpha(mask.resize((width, height), Image.Resampling.LANCZOS))
    return art


def _pin(image: Image.Image, x: float, y: float, size: float, colour: RGB = ACCENT) -> None:
    draw = ImageDraw.Draw(image)
    draw.polygon([(x - size * 0.62, y - size * 1.2), (x + size * 0.62, y - size * 1.2), (x, y)], fill=(*colour, 255))
    draw.ellipse([x - size * 0.8, y - size * 2.3, x + size * 0.8, y - size * 0.7], fill=(*colour, 255))
    draw.ellipse([x - size * 0.3, y - size * 1.8, x + size * 0.3, y - size * 1.2], fill=(*PAPER, 255))


def draw_illustrations() -> dict[str, Image.Image]:
    """Onboarding and empty-state pictures, keyed by path under assets/interim."""
    day = date(2026, 6, 21)

    def brief(name: str, motifs: list[str], time: str) -> PostcardBrief:
        return PostcardBrief(name, motifs, [], time, "", None, day)  # type: ignore[arg-type]

    out: dict[str, Image.Image] = {}
    listen = _vignette(brief("onboarding-listen-4", ["birds", "cafe"], "day"), (720, 540), arch=True)
    out["onboarding/listen.png"] = listen
    place = _vignette(brief("onboarding-place-2", ["waves", "birds"], "dawn"), (720, 540), arch=True)
    _pin(place, 360, 330, 46)
    out["onboarding/place.png"] = place
    out["onboarding/send.png"] = _vignette(brief("onboarding-send-3", ["train", "wind"], "dusk"), (720, 540), arch=True)
    out["empty/quiet.png"] = _vignette(brief("empty-quiet-1", ["hum"], "night"), (560, 360), arch=False)
    out["empty/hush.png"] = _vignette(brief("empty-hush-5", ["cafe", "market"], "dusk"), (560, 360), arch=False)
    return out


def stamp_motifs() -> list[str]:
    return [motif.slug for motif in MOTIFS]


def subtract_alpha(image: Image.Image, mask: Image.Image) -> Image.Image:
    """Utility for callers that need to punch a shape out of an RGBA image."""
    alpha = ImageChops.multiply(image.getchannel("A"), ImageChops.invert(mask))
    image.putalpha(alpha)
    return image
