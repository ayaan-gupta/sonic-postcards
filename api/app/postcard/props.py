"""Things that stand in a scene: trees, houses, cars, boats, people, animals.

Each function draws one object with its feet at (x, y). `size` is a scale
factor; 1.0 suits the middle distance of a 1128 px wide picture.
"""

from __future__ import annotations

import math

from app.postcard.paint import RGB, Canvas, Point, mix
from app.postcard.palette import Palette


def cloud(c: Canvas, x: float, y: float, width: float, colour: RGB) -> None:
    """A poster cloud: flat base, three or four bumps on top."""
    height = width * 0.2
    c.rect(x - width / 2, y - height, x + width / 2, y, colour, 0.04)
    c.ellipse(x - width / 2, y - height / 2, height / 2, height / 2, colour, 0.04)
    c.ellipse(x + width / 2, y - height / 2, height / 2, height / 2, colour, 0.04)
    bumps = 3 if width < 170 else 4
    for i in range(bumps):
        t = (i + 0.5) / bumps
        radius = width * c.uniform(0.15, 0.24) * (1.0 - abs(t - 0.45) * 0.7)
        c.ellipse(x - width / 2 + width * t, y - height * 0.9, radius, radius * 0.86, colour, 0.04)


def round_tree(c: Canvas, x: float, y: float, size: float, p: Palette, *, lean: float = 0.0, crown: RGB | None = None) -> None:
    height = 92 * size
    top_x = x + lean * height
    c.line([(x, y), (x + lean * height * 0.5, y - height * 0.55)], p.dark, 7 * size)
    colour = crown or p.near
    c.blob(top_x - 16 * size, y - height * 0.62, 30 * size, 26 * size, mix(colour, p.dark, 0.22))
    c.blob(top_x + 14 * size, y - height * 0.7, 32 * size, 28 * size, colour)
    c.blob(top_x - 4 * size, y - height * 0.92, 28 * size, 24 * size, mix(colour, p.mid, 0.55))


def cypress(c: Canvas, x: float, y: float, size: float, p: Palette, *, lean: float = 0.0) -> None:
    height = 120 * size
    tip = (x + lean * height, y - height)
    c.poly(
        [(x - 13 * size, y), (x - 15 * size, y - height * 0.45), tip, (x + 15 * size + lean * 20, y - height * 0.45), (x + 13 * size, y)],
        mix(p.near, p.dark, 0.35),
    )


def pine(c: Canvas, x: float, y: float, size: float, p: Palette, *, lean: float = 0.0, colour: RGB | None = None) -> None:
    height = 130 * size
    tone = colour or mix(p.near, p.dark, 0.3)
    c.rect(x - 4 * size, y - height * 0.2, x + 4 * size, y, p.dark, 0.0)
    for i, (width, base, top) in enumerate(((46, 0.12, 0.52), (36, 0.4, 0.78), (25, 0.66, 1.0))):
        shift = lean * height * (0.2 + 0.3 * i)
        c.poly(
            [(x - width * size + shift * 0.5, y - height * base), (x + shift, y - height * top), (x + width * size + shift * 0.5, y - height * base)],
            mix(tone, p.light, 0.05 * i),
        )


def house(c: Canvas, x: float, y: float, width: float, height: float, p: Palette, wall: RGB, *, roof: str = "gable", shop: bool = False) -> None:
    """A townhouse standing on y, with its left wall at x."""
    c.rect(x, y - height, x + width, y, wall, 0.07)
    if roof == "gable":
        c.poly([(x - 5, y - height), (x + width / 2, y - height - width * 0.36), (x + width + 5, y - height)], p.roof)
    elif roof == "hip":
        c.poly([(x - 5, y - height), (x + width * 0.2, y - height - 34), (x + width * 0.8, y - height - 34), (x + width + 5, y - height)], p.roof)
    else:
        c.rect(x - 4, y - height - 10, x + width + 4, y - height, mix(wall, p.dark, 0.3), 0.04)
    # Windows: a regular grid; after dark most are lit and a few are not.
    columns = max(2, int(width // 34))
    rows = max(2, int((height - (56 if shop else 30)) // 46))
    pane_w, pane_h = 14.0, 24.0
    gap = (width - columns * pane_w) / (columns + 1)
    for row in range(rows):
        for col in range(columns):
            wx = x + gap + col * (pane_w + gap)
            wy = y - height + 20 + row * 46
            lit = p.is_dark and c.chance(0.7)
            pane = p.window if (lit or not p.is_dark) else mix(wall, p.dark, 0.5)
            c.rect(wx, wy, wx + pane_w, wy + pane_h, pane, 0.0)
            c.rect(wx - 2, wy + pane_h, wx + pane_w + 2, wy + pane_h + 3, mix(wall, p.dark, 0.25), 0.0)
    if shop:
        c.rect(x + 8, y - 44, x + width - 8, y, mix(wall, p.dark, 0.45), 0.03)
        c.rect(x + 14, y - 38, x + width - 14, y - 8, p.window if p.is_dark else mix(p.window, p.light, 0.25), 0.0)
        awning(c, x + 4, y - 46, width - 8, 16, p)
    else:
        door = x + width * (0.3 if c.chance(0.5) else 0.62)
        c.rect(door, y - 34, door + 18, y, mix(p.roof, p.dark, 0.3), 0.0)


def awning(c: Canvas, x: float, y: float, width: float, drop: float, p: Palette, *, stripes: tuple[RGB, RGB] | None = None) -> None:
    """A striped shop awning hanging from (x, y) to the right."""
    a, b = stripes or (p.accent, p.light)
    count = max(4, int(width // 16))
    step = width / count
    for i in range(count):
        colour = a if i % 2 == 0 else b
        c.poly([(x + i * step, y), (x + (i + 1) * step, y), (x + (i + 1) * step + 4, y + drop), (x + i * step - 4 + (4 if i else 0), y + drop)], colour, 0.03)
        c.ellipse(x + (i + 0.5) * step + 2, y + drop, step / 2, 4.5, colour, 0.0)


def lamp_post(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    height = 118 * size
    c.line([(x, y), (x, y - height)], p.dark, 4 * size)
    c.line([(x, y - height), (x + 14 * size, y - height - 6 * size)], p.dark, 3 * size)
    if p.is_dark:
        c.ellipse(x + 17 * size, y - height + 2 * size, 15 * size, 15 * size, mix(p.light, p.sky[2], 0.55), 0.0)
    c.ellipse(x + 17 * size, y - height + 2 * size, 7 * size, 8 * size, p.light if p.is_dark else mix(p.light, p.dark, 0.2), 0.0)


def car(c: Canvas, x: float, y: float, size: float, p: Palette, colour: RGB, *, facing: int = 1) -> None:
    """A small rounded saloon car. `facing` is 1 for right, -1 for left."""
    length, body, wheel = 118 * size, 30 * size, 12 * size
    left, right = x - length / 2, x + length / 2
    top = y - wheel * 0.7 - body
    c.rect(left + 8 * size, top, right - 8 * size, y - wheel * 0.7, colour)
    c.ellipse(left + 9 * size, (top + y - wheel * 0.7) / 2, 9 * size, body / 2, colour)
    c.ellipse(right - 9 * size, (top + y - wheel * 0.7) / 2, 9 * size, body / 2, colour)
    cab_l, cab_r = x - length * 0.24 - facing * 6 * size, x + length * 0.22 - facing * 6 * size
    c.poly([(cab_l - 12 * size, top + 2), (cab_l + 4 * size, top - 24 * size), (cab_r - 6 * size, top - 24 * size), (cab_r + 14 * size, top + 2)], colour)
    glass = p.light if p.is_dark else mix(p.sky[2], p.light, 0.5)
    c.poly([(cab_l - 2 * size, top), (cab_l + 8 * size, top - 18 * size), (x - 3 * size, top - 18 * size), (x - 3 * size, top)], glass, 0.0)
    c.poly([(x + 3 * size, top), (x + 3 * size, top - 18 * size), (cab_r - 9 * size, top - 18 * size), (cab_r + 4 * size, top)], glass, 0.0)
    for wx in (left + length * 0.22, right - length * 0.22):
        c.ellipse(wx, y - wheel, wheel, wheel, p.dark, 0.0)
        c.ellipse(wx, y - wheel, wheel * 0.42, wheel * 0.42, mix(p.light, p.dark, 0.35), 0.0)
    lamp = right - 5 * size if facing > 0 else left + 5 * size
    if p.is_dark:
        c.ellipse(lamp + facing * 3 * size, top + body * 0.45, 10 * size, 10 * size, mix(p.light, p.dark, 0.5), 0.0)
    c.ellipse(lamp, top + body * 0.45, 4.5 * size, 4.5 * size, p.light, 0.0)


def bus(c: Canvas, x: float, y: float, size: float, p: Palette, colour: RGB, *, facing: int = 1) -> None:
    length, body, wheel = 200 * size, 70 * size, 13 * size
    left, right, top = x - length / 2, x + length / 2, y - wheel * 0.7 - body
    c.rect(left, top + 8 * size, right, y - wheel * 0.7, colour)
    c.rect(left + 8 * size, top, right - 8 * size, top + 12 * size, colour)
    c.ellipse(left + 8 * size, top + 8 * size, 8 * size, 8 * size, colour)
    c.ellipse(right - 8 * size, top + 8 * size, 8 * size, 8 * size, colour)
    c.rect(left, top + body * 0.58, right, top + body * 0.66, p.light, 0.0)
    glass = p.light if p.is_dark else mix(p.sky[2], p.light, 0.5)
    panes = 6
    pane = (length - 26 * size) / panes
    for i in range(panes):
        c.rect(left + 13 * size + i * pane, top + 14 * size, left + 13 * size + (i + 1) * pane - 5 * size, top + body * 0.5, glass, 0.0)
    for wx in (left + length * 0.2, right - length * 0.2):
        c.ellipse(wx, y - wheel, wheel, wheel, p.dark, 0.0)
        c.ellipse(wx, y - wheel, wheel * 0.42, wheel * 0.42, mix(p.light, p.dark, 0.35), 0.0)
    lamp = right - 4 * size if facing > 0 else left + 4 * size
    c.ellipse(lamp, y - wheel * 0.7 - 12 * size, 4 * size, 4 * size, p.light, 0.0)


def walker(c: Canvas, x: float, y: float, size: float, p: Palette, coat: RGB, *, umbrella: RGB | None = None, stride: float = 1.0) -> None:
    """A small figure in a coat, mid step."""
    hip, shoulder, head = y - 30 * size, y - 64 * size, y - 73 * size
    c.line([(x - 2 * size, hip), (x - 8 * size * stride, y)], p.dark, 4.5 * size)
    c.line([(x + 2 * size, hip), (x + 9 * size * stride, y)], p.dark, 4.5 * size)
    c.poly([(x - 8 * size, shoulder), (x + 8 * size, shoulder), (x + 12 * size, hip + 4 * size), (x - 12 * size, hip + 4 * size)], coat)
    c.ellipse(x, shoulder + 1 * size, 8 * size, 5 * size, coat, 0.0)
    c.ellipse(x, head, 7.5 * size, 8 * size, mix(p.dark, p.roof, 0.35), 0.0)
    if umbrella is not None:
        c.line([(x + 9 * size, hip - 6 * size), (x + 9 * size, head - 26 * size)], p.dark, 2.2 * size)
        c.pie(x + 9 * size, head - 20 * size, 31 * size, 24 * size, 180, 360, umbrella)
        c.line([(x + 9 * size, head - 44 * size), (x + 9 * size, head - 50 * size)], p.dark, 2.2 * size)


def stall(c: Canvas, x: float, y: float, size: float, p: Palette, stripes: tuple[RGB, RGB]) -> None:
    """A market stall: two poles, a striped awning, a counter heaped with produce."""
    width, height = 132 * size, 104 * size
    left = x - width / 2
    c.line([(left + 6 * size, y), (left + 6 * size, y - height)], p.dark, 4 * size)
    c.line([(left + width - 6 * size, y), (left + width - 6 * size, y - height)], p.dark, 4 * size)
    c.rect(left + 2 * size, y - 40 * size, left + width - 2 * size, y, mix(p.roof, p.dark, 0.25))
    c.rect(left - 2 * size, y - 46 * size, left + width + 2 * size, y - 38 * size, mix(p.walls[0], p.dark, 0.1), 0.03)
    fruit = (p.accent, p.sun, mix(p.near, p.light, 0.25), p.walls[2])
    for i in range(int(width // (11 * size))):
        fx = left + 8 * size + i * 11 * size
        colour = fruit[(i // 3) % len(fruit)]
        c.ellipse(fx, y - 50 * size, 5.5 * size, 5.5 * size, colour, 0.0)
        if i % 2 == 0:
            c.ellipse(fx + 5 * size, y - 58 * size, 5.5 * size, 5.5 * size, colour, 0.0)
    c.poly([(left - 10 * size, y - height + 22 * size), (left + 4 * size, y - height - 4 * size), (left + width - 4 * size, y - height - 4 * size), (left + width + 10 * size, y - height + 22 * size)], stripes[0])
    awning(c, left - 10 * size, y - height + 4 * size, width + 20 * size, 20 * size, p, stripes=stripes)


def bunting(c: Canvas, start: Point, end: Point, sag: float, p: Palette) -> None:
    colours = (p.accent, p.light, p.sun, p.walls[3])
    flags = max(8, int(abs(end[0] - start[0]) // 34))
    points: list[Point] = []
    for i in range(flags + 1):
        t = i / flags
        points.append((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t + sag * 4 * t * (1 - t)))
    c.line(points, p.dark, 1.6)
    for i in range(flags):
        (x0, y0), (x1, y1) = points[i], points[i + 1]
        c.poly([(x0 + 2, y0), (x1 - 2, y1), ((x0 + x1) / 2, (y0 + y1) / 2 + 24)], colours[i % len(colours)], 0.03)


def cafe_table(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    """A parasol, a round table and two chairs. A cup steams on the table."""
    top = y - 128 * size
    c.line([(x, y), (x, top)], p.dark, 3.4 * size)
    wedges = 6
    for i in range(wedges):
        a0, a1 = 180 + i * 180 / wedges, 180 + (i + 1) * 180 / wedges
        c.pie(x, top + 30 * size, 78 * size, 34 * size, a0, a1, p.accent if i % 2 == 0 else p.light, 0.03)
    c.ellipse(x, y - 44 * size, 34 * size, 7 * size, p.light, 0.0)
    c.rect(x - 34 * size, y - 44 * size, x + 34 * size, y - 40 * size, mix(p.light, p.dark, 0.25), 0.0)
    for side in (-1, 1):
        cx = x + side * 54 * size
        c.line([(cx, y), (cx, y - 30 * size)], p.dark, 3 * size)
        c.line([(cx + side * 14 * size, y), (cx + side * 14 * size, y - 62 * size)], p.dark, 3 * size)
        c.line([(cx, y - 30 * size), (cx + side * 14 * size, y - 30 * size)], p.dark, 4 * size)
    c.rect(x + 8 * size, y - 56 * size, x + 20 * size, y - 46 * size, p.accent, 0.0)
    c.curve([(x + 14 * size, y - 60 * size), (x + 10 * size, y - 70 * size), (x + 17 * size, y - 78 * size), (x + 12 * size, y - 88 * size)], p.light, 2 * size)


def sheep(c: Canvas, x: float, y: float, size: float, p: Palette, *, facing: int = 1) -> None:
    wool = p.foam if p.is_dark else p.light
    for leg in (-13, -5, 6, 14):
        c.line([(x + leg * size, y), (x + leg * size, y - 16 * size)], p.dark, 3 * size)
    c.blob(x, y - 26 * size, 24 * size, 15 * size, wool, wobble=0.2)
    c.ellipse(x + facing * 24 * size, y - 30 * size, 8 * size, 7 * size, p.dark, 0.0)


def cow(c: Canvas, x: float, y: float, size: float, p: Palette, *, facing: int = 1) -> None:
    hide = p.foam if p.is_dark else p.light
    patch = mix(p.roof, p.dark, 0.4)
    for leg in (-24, -14, 14, 24):
        c.line([(x + leg * size, y), (x + leg * size, y - 26 * size)], patch, 4.5 * size)
    c.blob(x, y - 40 * size, 38 * size, 20 * size, hide, wobble=0.08)
    c.blob(x - facing * 10 * size, y - 44 * size, 13 * size, 9 * size, patch, wobble=0.3)
    c.blob(x + facing * 16 * size, y - 34 * size, 9 * size, 7 * size, patch, wobble=0.3)
    hx = x + facing * 42 * size
    c.ellipse(hx, y - 50 * size, 11 * size, 9 * size, hide, 0.0)
    c.ellipse(hx + facing * 7 * size, y - 46 * size, 6 * size, 5 * size, mix(p.accent, p.light, 0.5), 0.0)
    c.line([(hx - 6 * size, y - 58 * size), (hx - 10 * size, y - 65 * size)], p.dark, 2.4 * size)
    c.line([(hx + 5 * size, y - 58 * size), (hx + 9 * size, y - 65 * size)], p.dark, 2.4 * size)


def dog(c: Canvas, x: float, y: float, size: float, p: Palette, *, facing: int = 1) -> None:
    coat = mix(p.roof, p.dark, 0.2)
    for leg in (-15, -9, 10, 16):
        c.line([(x + leg * size, y), (x + leg * size, y - 18 * size)], coat, 4 * size)
    c.blob(x, y - 26 * size, 23 * size, 11 * size, coat, wobble=0.08)
    hx = x + facing * 24 * size
    c.ellipse(hx, y - 38 * size, 10 * size, 9 * size, coat, 0.0)
    c.poly([(hx + facing * 6 * size, y - 40 * size), (hx + facing * 19 * size, y - 36 * size), (hx + facing * 6 * size, y - 31 * size)], coat, 0.0)
    c.poly([(hx - facing * 6 * size, y - 44 * size), (hx - facing * 2 * size, y - 56 * size), (hx + facing * 3 * size, y - 44 * size)], p.dark, 0.0)
    c.curve([(x - facing * 22 * size, y - 30 * size), (x - facing * 31 * size, y - 40 * size), (x - facing * 29 * size, y - 52 * size)], coat, 4 * size)


def campfire(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    if p.is_dark:
        c.ellipse(x, y - 4 * size, 96 * size, 20 * size, mix(p.ground, p.accent, 0.3), 0.04)
    for i in range(3):
        c.blob(x - 14 * size - i * 13 * size, y - 96 * size - i * 34 * size, (15 + i * 5) * size, (11 + i * 4) * size, mix(p.cloud, p.sky[1], 0.25 + 0.2 * i), wobble=0.25)
    c.line([(x - 34 * size, y - 2 * size), (x + 30 * size, y - 14 * size)], mix(p.roof, p.dark, 0.5), 9 * size)
    c.line([(x + 34 * size, y - 2 * size), (x - 30 * size, y - 14 * size)], mix(p.roof, p.dark, 0.35), 9 * size)
    flame = (p.accent, p.sun, p.light)
    for i, scale in enumerate((1.0, 0.68, 0.36)):
        w, h = 27 * size * scale, 76 * size * scale
        c.poly(
            [(x - w, y - 12 * size), (x - w * 0.9, y - 12 * size - h * 0.45), (x - w * 0.25, y - 12 * size - h * 0.62), (x + w * 0.1, y - 12 * size - h),
             (x + w * 0.55, y - 12 * size - h * 0.6), (x + w * 0.95, y - 12 * size - h * 0.4), (x + w, y - 12 * size)],
            flame[i], 0.03,
        )
    for _ in range(9):
        c.ellipse(x + c.uniform(-46, 46) * size, y - c.uniform(70, 150) * size, 2.2 * size, 2.2 * size, p.sun, 0.0)


def guitar(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    """A guitar leaning on a stool."""
    wood = mix(p.accent, p.roof, 0.45)
    c.line([(x + 34 * size, y), (x + 34 * size, y - 40 * size)], p.dark, 4 * size)
    c.line([(x + 62 * size, y), (x + 62 * size, y - 40 * size)], p.dark, 4 * size)
    c.rect(x + 26 * size, y - 46 * size, x + 70 * size, y - 39 * size, mix(p.walls[0], p.dark, 0.15), 0.0)
    c.line([(x - 4 * size, y - 44 * size), (x + 30 * size, y - 122 * size)], mix(wood, p.dark, 0.5), 7 * size)
    c.rect(x + 25 * size, y - 136 * size, x + 38 * size, y - 118 * size, p.dark, 0.0)
    c.blob(x - 12 * size, y - 22 * size, 25 * size, 22 * size, wood, wobble=0.06)
    c.blob(x - 1 * size, y - 50 * size, 18 * size, 17 * size, wood, wobble=0.06)
    c.ellipse(x - 5 * size, y - 40 * size, 7 * size, 7 * size, p.dark, 0.0)


def music_note(c: Canvas, x: float, y: float, size: float, colour: RGB, *, double: bool = False) -> None:
    c.ellipse(x, y, 8 * size, 6 * size, colour, 0.0)
    c.line([(x + 7 * size, y), (x + 7 * size, y - 30 * size)], colour, 2.6 * size)
    if double:
        c.ellipse(x + 22 * size, y - 5 * size, 8 * size, 6 * size, colour, 0.0)
        c.line([(x + 29 * size, y - 5 * size), (x + 29 * size, y - 35 * size)], colour, 2.6 * size)
        c.line([(x + 7 * size, y - 30 * size), (x + 29 * size, y - 35 * size)], colour, 5 * size)
    else:
        c.curve([(x + 7 * size, y - 30 * size), (x + 16 * size, y - 24 * size), (x + 17 * size, y - 14 * size)], colour, 3 * size)


def bell_tower(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    """A campanile with an open belfry, a bell, and rings of sound."""
    half, height = 27 * size, 230 * size
    wall = mix(p.walls[0], p.far, 0.15)
    c.rect(x - half, y - height, x + half, y, wall)
    c.rect(x - half - 5 * size, y - height - 6 * size, x + half + 5 * size, y - height, mix(wall, p.dark, 0.3), 0.0)
    c.poly([(x - half - 5 * size, y - height - 6 * size), (x, y - height - 70 * size), (x + half + 5 * size, y - height - 6 * size)], p.roof)
    belfry = y - height + 20 * size
    c.rect(x - 15 * size, belfry + 14 * size, x + 15 * size, belfry + 56 * size, p.dark, 0.0)
    c.ellipse(x, belfry + 15 * size, 15 * size, 15 * size, p.dark, 0.0)
    c.pie(x, belfry + 40 * size, 12 * size, 22 * size, 180, 360, p.accent, 0.0)
    c.rect(x - 14 * size, belfry + 38 * size, x + 14 * size, belfry + 43 * size, p.accent, 0.0)
    c.ellipse(x, belfry + 47 * size, 3.5 * size, 3.5 * size, p.light, 0.0)
    for row in range(3):
        wy = y - height + 104 * size + row * 40 * size
        c.rect(x - 5 * size, wy, x + 5 * size, wy + 18 * size, mix(wall, p.dark, 0.55), 0.0)
    ring = p.light if p.is_dark else mix(p.light, p.sky[0], 0.15)
    for i in range(3):
        r = (42 + i * 20) * size
        c.arc(x, belfry + 36 * size, r, r, 150, 210, ring, 3 * size)
        c.arc(x, belfry + 36 * size, r, r, -30, 30, ring, 3 * size)


def crane(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    height, reach = 250 * size, 170 * size
    steel = p.accent
    c.line([(x - 7 * size, y), (x - 7 * size, y - height)], steel, 3.2 * size)
    c.line([(x + 7 * size, y), (x + 7 * size, y - height)], steel, 3.2 * size)
    steps = 9
    for i in range(steps):
        y0, y1 = y - height * i / steps, y - height * (i + 1) / steps
        c.line([(x - 7 * size, y0), (x + 7 * size, y1)], steel, 1.8 * size)
    top = y - height
    c.line([(x - 62 * size, top), (x + reach, top)], steel, 4 * size)
    c.line([(x, top - 34 * size), (x + reach, top)], steel, 2 * size)
    c.line([(x, top - 34 * size), (x - 62 * size, top)], steel, 2 * size)
    c.line([(x, top), (x, top - 34 * size)], steel, 3.2 * size)
    c.rect(x - 60 * size, top, x - 34 * size, top + 18 * size, p.dark, 0.0)
    c.rect(x - 2 * size, top - 2 * size, x + 20 * size, top + 16 * size, p.light, 0.0)
    hook = x + reach * 0.72
    c.line([(hook, top), (hook, top + 96 * size)], p.dark, 1.6 * size)
    c.rect(hook - 13 * size, top + 96 * size, hook + 13 * size, top + 112 * size, mix(p.walls[1], p.dark, 0.2), 0.0)


def sailboat(c: Canvas, x: float, y: float, size: float, p: Palette, sail: RGB) -> None:
    c.poly([(x - 38 * size, y - 12 * size), (x + 42 * size, y - 12 * size), (x + 28 * size, y), (x - 26 * size, y)], p.dark)
    c.line([(x, y - 12 * size), (x, y - 98 * size)], p.dark, 2.6 * size)
    c.poly([(x + 4 * size, y - 94 * size), (x + 40 * size, y - 20 * size), (x + 4 * size, y - 20 * size)], sail)
    c.poly([(x - 4 * size, y - 80 * size), (x - 4 * size, y - 20 * size), (x - 32 * size, y - 20 * size)], p.light if sail != p.light else p.foam)
    c.arc(x, y + 3 * size, 52 * size, 6 * size, 0, 180, p.foam, 2 * size)


def lighthouse(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    height = 150 * size
    top = y - height
    if p.is_dark:
        c.poly([(x, top - 12 * size), (x - 330 * size, top - 52 * size), (x - 330 * size, top + 6 * size)], mix(p.light, p.sky[1], 0.78), 0.0)
    c.poly([(x - 19 * size, y), (x - 12 * size, top), (x + 12 * size, top), (x + 19 * size, y)], p.light)
    for i in (1, 3):
        y0, y1 = y - height * i / 5, y - height * (i + 1) / 5
        w0, w1 = 19 - 7 * i / 5, 19 - 7 * (i + 1) / 5
        c.poly([(x - w0 * size, y0), (x - w1 * size, y1), (x + w1 * size, y1), (x + w0 * size, y0)], p.accent, 0.03)
    c.rect(x - 16 * size, top - 4 * size, x + 16 * size, top, p.dark, 0.0)
    c.rect(x - 9 * size, top - 20 * size, x + 9 * size, top - 4 * size, p.sun if p.is_dark else p.window, 0.0)
    c.poly([(x - 13 * size, top - 20 * size), (x, top - 36 * size), (x + 13 * size, top - 20 * size)], p.dark, 0.0)


def plane(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    """An airliner heading up and to the right, with a contrail."""
    body = p.light if not p.is_dark else p.foam
    tilt = -0.2
    def at(dx: float, dy: float) -> Point:
        return (x + (dx * math.cos(tilt) - dy * math.sin(tilt)) * size, y + (dx * math.sin(tilt) + dy * math.cos(tilt)) * size)
    trail = mix(body, p.sky[0], 0.35)
    c.line([at(-60, -5), at(-360, -3)], trail, 4 * size)
    c.line([at(-60, 7), at(-330, 11)], trail, 4 * size)
    c.poly([at(-58, 0), at(-74, -26), at(-60, -26), at(-36, -3)], p.accent, 0.0)
    c.poly([at(-6, 2), at(-34, 40), at(-18, 40), at(22, 4)], mix(body, p.dark, 0.2), 0.0)
    c.poly([at(-6, -2), at(-30, -34), at(-16, -34), at(20, -4)], mix(body, p.dark, 0.3), 0.0)
    c.line([at(-56, 0), at(50, 0)], body, 13 * size)
    c.line([at(-50, 4), at(46, 4)], mix(body, p.dark, 0.45), 4 * size)
    c.line([at(26, -2), at(44, -2)], p.window, 3 * size)


def firework(c: Canvas, x: float, y: float, radius: float, colours: tuple[RGB, RGB], *, ground: float) -> None:
    c.line([(x + c.uniform(-18, 18), ground), (x, y + radius * 0.5)], mix(colours[1], (40, 40, 70), 0.6), 1.6)
    rays = 16
    offset = c.uniform(0, math.tau)
    for i in range(rays):
        angle = offset + math.tau * i / rays
        long = i % 2 == 0
        r0, r1 = radius * 0.2, radius * (1.0 if long else 0.66)
        droop = radius * 0.1
        c.line([(x + math.cos(angle) * r0, y + math.sin(angle) * r0), (x + math.cos(angle) * r1, y + math.sin(angle) * r1 + droop)], colours[0] if long else colours[1], 3.2 if long else 2.4)
        c.ellipse(x + math.cos(angle) * (r1 + 9), y + math.sin(angle) * (r1 + 9) + droop * 1.4, 3.2, 3.2, colours[1] if long else colours[0], 0.0)
    c.ellipse(x, y, radius * 0.08, radius * 0.08, colours[1], 0.0)


def flying_bird(c: Canvas, x: float, y: float, span: float, colour: RGB) -> None:
    """The two-stroke bird every landscape painter uses."""
    dip = span * c.uniform(0.22, 0.42)
    width = max(1.6, span * 0.11)
    c.curve([(x - span, y - dip * 0.3), (x - span * 0.5, y - dip), (x, y)], colour, width, steps=6)
    c.curve([(x, y), (x + span * 0.5, y - dip), (x + span, y - dip * 0.3)], colour, width, steps=6)


def perched_bird(c: Canvas, x: float, y: float, size: float, colour: RGB, beak: RGB, *, facing: int = 1) -> None:
    c.poly([(x - facing * 8 * size, y - 9 * size), (x - facing * 27 * size, y - 1 * size), (x - facing * 9 * size, y - 3 * size)], colour, 0.0)
    c.ellipse(x, y - 11 * size, 12 * size, 10 * size, colour, 0.0)
    c.ellipse(x + facing * 9 * size, y - 21 * size, 7 * size, 7 * size, colour, 0.0)
    c.poly([(x + facing * 14 * size, y - 23 * size), (x + facing * 23 * size, y - 20 * size), (x + facing * 14 * size, y - 18 * size)], beak, 0.0)
    c.line([(x - 2 * size, y - 2 * size), (x - 2 * size, y + 2 * size)], colour, 1.6 * size)
    c.line([(x + 3 * size, y - 2 * size), (x + 3 * size, y + 2 * size)], colour, 1.6 * size)


def kite(c: Canvas, x: float, y: float, size: float, p: Palette, anchor: Point) -> None:
    w, h = 26 * size, 36 * size
    tail = [(x - 4 * size, y + h), (x - 26 * size, y + h + 34 * size), (x - 8 * size, y + h + 64 * size), (x - 34 * size, y + h + 96 * size)]
    string_colour = p.light if p.is_dark else p.dark
    c.curve([(x, y + h * 0.4), ((x + anchor[0]) / 2 + 40, (y + anchor[1]) / 2 + 30), anchor], string_colour, 1.4)
    c.curve(tail, string_colour, 1.6)
    for i, (tx, ty) in enumerate(tail[1:]):
        c.poly([(tx - 9 * size, ty - 5 * size), (tx + 9 * size, ty + 5 * size), (tx + 9 * size, ty - 5 * size), (tx - 9 * size, ty + 5 * size)], p.accent if i % 2 == 0 else p.sun, 0.0)
    c.poly([(x, y - h), (x + w, y), (x, y)], p.accent, 0.03)
    c.poly([(x, y - h), (x - w, y), (x, y)], mix(p.accent, p.light, 0.35), 0.03)
    c.poly([(x - w, y), (x, y + h), (x, y)], p.sun, 0.03)
    c.poly([(x + w, y), (x, y + h), (x, y)], mix(p.sun, p.accent, 0.5), 0.03)


def puddle(c: Canvas, x: float, y: float, width: float, p: Palette) -> None:
    c.ellipse(x, y, width, width * 0.2, mix(p.sky[2], p.ground, 0.35), 0.03)
    c.arc(x - width * 0.2, y, width * 0.36, width * 0.08, 0, 360, p.foam, 1.6)
    c.arc(x + width * 0.35, y + 1, width * 0.2, width * 0.045, 0, 360, p.foam, 1.4)


def fountain(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    stone = mix(p.walls[0], p.dark, 0.15)
    for side in (-1, 1):
        c.curve([(x, y - 92 * size), (x + side * 22 * size, y - 104 * size), (x + side * 44 * size, y - 60 * size), (x + side * 50 * size, y - 30 * size)], p.foam, 3.4 * size)
        c.curve([(x, y - 66 * size), (x + side * 14 * size, y - 74 * size), (x + side * 26 * size, y - 44 * size), (x + side * 29 * size, y - 30 * size)], p.foam, 2.6 * size)
    c.rect(x - 5 * size, y - 92 * size, x + 5 * size, y - 24 * size, stone, 0.0)
    c.ellipse(x, y - 64 * size, 24 * size, 6 * size, stone, 0.0)
    c.ellipse(x, y - 24 * size, 70 * size, 14 * size, p.water, 0.04)
    c.poly([(x - 70 * size, y - 24 * size), (x + 70 * size, y - 24 * size), (x + 62 * size, y), (x - 62 * size, y)], stone)
    c.arc(x, y - 24 * size, 70 * size, 14 * size, 0, 180, mix(stone, p.dark, 0.3), 2.4 * size)


def pond(c: Canvas, x: float, y: float, size: float, p: Palette) -> None:
    c.blob(x, y - 6 * size, 92 * size, 22 * size, p.water, wobble=0.1)
    for dx, w in ((-30, 30), (22, 22), (-4, 14)):
        c.arc(x + dx * size, y - 6 * size + dx * 0.05, w * size, w * 0.24 * size, 0, 360, p.foam, 1.8 * size)
    for i in range(7):
        rx = x + (62 + i * 6) * size
        c.line([(rx, y), (rx + c.uniform(-5, 8) * size, y - c.uniform(34, 62) * size)], mix(p.near, p.dark, 0.3), 2.4 * size)
    c.ellipse(x + 76 * size, y - 56 * size, 3.6 * size, 9 * size, mix(p.roof, p.dark, 0.3), 0.0)


def grass_tuft(c: Canvas, x: float, y: float, height: float, colour: RGB, *, lean: float = 0.0) -> None:
    for i in range(5):
        dx = (i - 2) * height * 0.11
        tip_x = x + dx * 2.4 + lean * height + c.uniform(-3, 3)
        tip_y = y - height * c.uniform(0.6, 1.0)
        c.poly([(x + dx - 2.2, y), (tip_x, tip_y), (x + dx + 2.2, y)], colour, 0.0)


def lightning(c: Canvas, x: float, top: float, bottom: float, colour: RGB) -> None:
    """The bolt everyone draws: two slanted strokes joined by a step."""
    height = bottom - top
    width = height * 0.34
    shape = ((0.5, 0.0), (0.95, 0.0), (0.62, 0.4), (0.9, 0.4), (0.18, 1.0), (0.42, 0.55), (0.12, 0.55))
    c.poly([(x + (px - 0.5) * width, top + py * height) for px, py in shape], colour, 0.0)
