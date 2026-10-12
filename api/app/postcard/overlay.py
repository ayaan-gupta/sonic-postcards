"""The postcard template: paper border, caption, stamp and postmark.

Everything with letters in it is drawn here, by code, from the stored facts.
An image model never gets to spell the city or the date. The stamp picture
and the blank postmark are artwork files (delivered or interim); the stamp
value, the postmark lettering and the caption are set in bundled fonts.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.audio.motifs import MOTIF_BY_SLUG
from app.postcard import interim
from app.postcard.art import load_rgba
from app.postcard.brief import PostcardBrief
from app.postcard.paint import RGB, hex_rgb

FONT_DIR = Path(__file__).resolve().parent.parent / "fonts"
CARD_SIZE = (1200, 840)
ART_BOX = (36, 36, 1164, 676)  # left, top, right, bottom

PAPER = hex_rgb("#f6f0e1")
INK = hex_rgb("#1d2440")
MUTED = hex_rgb("#6b6f80")
ACCENT = hex_rgb("#e2583a")

_TIME_WORD = {"dawn": "EARLY MORNING", "day": "DAYTIME", "dusk": "EVENING", "night": "NIGHT"}
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


@lru_cache(maxsize=32)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


DISPLAY = "BebasNeue-Regular.ttf"
SCRIPT = "Yellowtail-Regular.ttf"
TYPEWRITER = "SpecialElite-Regular.ttf"


def printable(text: str, face: ImageFont.FreeTypeFont) -> str:
    """Drop characters the font cannot draw, so a caption never shows empty boxes.

    Pillow does not expose the font's character map, but every missing
    character renders as the same "not defined" glyph, so compare against one
    that is certainly missing.
    """
    missing = face.getmask("\uffff")
    blank = (bytes(missing), missing.size)

    def drawable(ch: str) -> bool:
        if ch == " ":
            return True
        mask = face.getmask(ch)
        return mask.getbbox() is not None and (bytes(mask), mask.size) != blank

    return " ".join("".join(ch for ch in text if drawable(ch)).split())


def format_date(brief: PostcardBrief) -> str:
    d = brief.local_date
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def spaced_width(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, tracking: float) -> float:
    return sum(draw.textlength(ch, font=face) for ch in text) + tracking * max(0, len(text) - 1)


def draw_spaced(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, face: ImageFont.FreeTypeFont, fill: RGB, tracking: float, *, anchor_right: bool = False) -> float:
    """Text with letter spacing. Returns the width drawn."""
    width = spaced_width(draw, text, face, tracking)
    x = xy[0] - width if anchor_right else xy[0]
    for ch in text:
        draw.text((x, xy[1]), ch, font=face, fill=fill)
        x += draw.textlength(ch, font=face) + tracking
    return width


def fit_font(draw: ImageDraw.ImageDraw, text: str, name: str, size: int, max_width: float, tracking: float = 0.0, minimum: int = 22) -> ImageFont.FreeTypeFont:
    while size > minimum and spaced_width(draw, text, font(name, size), tracking) > max_width:
        size -= 2
    return font(name, size)


def draw_arc_text(target: Image.Image, text: str, face: ImageFont.FreeTypeFont, centre: tuple[float, float], radius: float, fill: tuple[int, int, int, int], *, top: bool = True, spread: float = 150.0) -> None:
    """Set text along a circle, upright at the top or readable along the bottom."""
    if not text:
        return
    measure = ImageDraw.Draw(target)
    widths = [measure.textlength(ch, font=face) for ch in text]
    gap = face.size * 0.12
    total = sum(widths) + gap * (len(text) - 1)
    arc = min(math.radians(spread), total / radius)
    used = 0.0
    for ch, width in zip(text, widths, strict=True):
        middle = (used + width / 2) / total if total else 0.5
        offset = (middle - 0.5) * arc
        angle = -math.pi / 2 + offset if top else math.pi / 2 - offset
        used += width + gap
        if ch == " ":
            continue
        box = int(face.size * 2.2)
        glyph = Image.new("RGBA", (box, box), (0, 0, 0, 0))
        ImageDraw.Draw(glyph).text((box / 2, box / 2), ch, font=face, fill=fill, anchor="mm")
        turn = -math.degrees(angle) - 90 if top else -math.degrees(angle) + 90
        glyph = glyph.rotate(turn, resample=Image.Resampling.BICUBIC)
        x = centre[0] + radius * math.cos(angle) - box / 2
        y = centre[1] + radius * math.sin(angle) - box / 2
        target.alpha_composite(glyph, (round(x), round(y)))


def _fit_art(art: Image.Image) -> Image.Image:
    """Centre-crop any provider's picture to the art window."""
    left, top, right, bottom = ART_BOX
    width, height = right - left, bottom - top
    scale = max(width / art.width, height / art.height)
    resized = art.convert("RGB").resize((max(width, round(art.width * scale)), max(height, round(art.height * scale))), Image.Resampling.LANCZOS)
    x, y = (resized.width - width) // 2, (resized.height - height) // 2
    return resized.crop((x, y, x + width, y + height))


def _paper(size: tuple[int, int]) -> Image.Image:
    rng = np.random.default_rng(11)
    base = np.empty((size[1], size[0], 3), dtype=np.float32)
    base[:] = PAPER
    base += rng.normal(0.0, 1.6, size=(size[1], size[0], 1)).astype(np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def _stamp(assets_dir: Path, motif: str) -> Image.Image:
    return load_rgba(assets_dir, f"stamps/{motif}.png") or interim.draw_stamp(motif if motif in MOTIF_BY_SLUG else "hum")


def _postmark(assets_dir: Path) -> Image.Image:
    return load_rgba(assets_dir, "postmark/ring.png") or interim.draw_postmark()


def compose_postcard(art: Image.Image, brief: PostcardBrief, assets_dir: Path) -> Image.Image:
    """Art plus template: the finished 1200 x 840 postcard."""
    card = _paper(CARD_SIZE)
    left, top, right, bottom = ART_BOX
    card.paste(_fit_art(art), (left, top))
    draw = ImageDraw.Draw(card)
    draw.rectangle([left - 1, top - 1, right, bottom], outline=(*INK, 70), width=1)

    # Stamp, top right, set slightly crooked like a real one.
    motif = brief.motifs[0] if brief.motifs else "hum"
    stamp_w, stamp_h = 150, 186
    stamp = _stamp(assets_dir, motif).resize((stamp_w, stamp_h), Image.Resampling.LANCZOS)
    stamp_draw = ImageDraw.Draw(stamp)
    draw_spaced(stamp_draw, (15, stamp_h - 33), "SONIC POST", font(DISPLAY, 15), INK, 1.2)
    stamp_draw.text((stamp_w - 14, stamp_h - 36), "10s", font=font(DISPLAY, 20), fill=ACCENT, anchor="ra")
    tilt = 2.6 if brief.seed % 2 == 0 else -2.2
    stamp = stamp.rotate(tilt, resample=Image.Resampling.BICUBIC, expand=True)
    stamp_x, stamp_y = right - stamp.width - 20, top + 18
    shadow = Image.new("RGBA", stamp.size, (20, 24, 40, 0))
    shadow.putalpha(stamp.getchannel("A").point(lambda a: a * 70 // 255))
    card.alpha_composite(shadow, (stamp_x + 3, stamp_y + 4))
    card.alpha_composite(stamp, (stamp_x, stamp_y))

    # Postmark: blank artwork tinted with ink, then the lettering.
    mark = _postmark(assets_dir)
    mark_h = 190
    mark = mark.resize((round(mark.width * mark_h / mark.height), mark_h), Image.Resampling.LANCZOS)
    ring_radius = mark_h / 2
    layer = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    mark_x, mark_y = stamp_x - 150, top + 44
    layer.alpha_composite(mark, (mark_x, mark_y))
    centre = (mark_x + ring_radius, mark_y + ring_radius)
    ink = (*INK, 235)
    city_face = font(DISPLAY, 25)
    city = printable(brief.place_name.upper(), city_face)[:22] or "SOMEWHERE"
    draw_arc_text(layer, city, city_face, centre, ring_radius * 0.79, ink, top=True)
    draw_arc_text(layer, _TIME_WORD[brief.time_of_day], font(DISPLAY, 19), centre, ring_radius * 0.8, ink, top=False, spread=120)
    mark_draw = ImageDraw.Draw(layer)
    d = brief.local_date
    mark_draw.text(centre, f"{d.day} {_MONTHS[d.month - 1]}", font=font(DISPLAY, 36), fill=ink, anchor="ms")
    mark_draw.text((centre[0], centre[1] + 6), str(d.year), font=font(DISPLAY, 24), fill=ink, anchor="mt")
    layer = layer.rotate(-7 if tilt > 0 else 6, resample=Image.Resampling.BICUBIC, center=centre)
    alpha = np.asarray(layer.getchannel("A"), dtype=np.float32) * 0.86
    layer.putalpha(Image.fromarray(alpha.astype(np.uint8), "L"))
    card.alpha_composite(layer)

    # Caption strip.
    draw = ImageDraw.Draw(card)
    strip_top = bottom
    title_face = font(DISPLAY, 70)
    title = printable(brief.place_name.upper(), title_face) or "SOMEWHERE"
    tags = "  ·  ".join(MOTIF_BY_SLUG[m].name.upper() for m in brief.motifs if m in MOTIF_BY_SLUG)
    tag_face = font(DISPLAY, 30)
    tags_width = spaced_width(draw, tags, tag_face, 2.4)
    title_face = fit_font(draw, title, DISPLAY, 70, (right - left) - tags_width - 60, tracking=3.0, minimum=34)
    draw.text((left + 2, strip_top + 12), "Sounds of", font=font(SCRIPT, 40), fill=ACCENT)
    draw_spaced(draw, (left, strip_top + 58), title, title_face, INK, 3.0)
    draw_spaced(draw, (right, strip_top + 62), tags, tag_face, INK, 2.4, anchor_right=True)
    where = printable((brief.country_name or "").upper(), font(TYPEWRITER, 19))
    line = "  ·  ".join(part for part in (where, format_date(brief)) if part)
    draw.text((right, strip_top + 104), line, font=font(TYPEWRITER, 19), fill=MUTED, anchor="ra")
    return card.convert("RGB")
