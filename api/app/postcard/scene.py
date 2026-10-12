"""The built-in postcard painter. No network, no model: just composition rules.

The strongest motif picks the setting (a street, a meadow, a coast, a river
valley, a railway viaduct, a market square). Every motif then adds the thing
that makes its sound: rain falls, a bell tower rings, a flock crosses the
sky. The time of day picks the palette and decides whether the windows are
lit.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from PIL import Image

from app.postcard import props
from app.postcard.brief import PostcardBrief
from app.postcard.paint import RGB, Canvas, Point, mix, smooth
from app.postcard.palette import PALETTES, Palette

ART_SIZE = (1128, 640)

SETTING_FOR_MOTIF: dict[str, str] = {
    "rain": "street",
    "storm": "meadow",
    "water": "river",
    "waves": "coast",
    "wind": "meadow",
    "birds": "meadow",
    "insects": "meadow",
    "animals": "meadow",
    "traffic": "street",
    "train": "railway",
    "aircraft": "meadow",
    "bells": "square",
    "music": "square",
    "market": "square",
    "cafe": "square",
    "footsteps": "street",
    "fire": "meadow",
    "fireworks": "coast",
    "works": "street",
    "hum": "meadow",
}

Slot = tuple[float, float, float]  # x, y of the feet, scale


@dataclass
class Scene:
    c: Canvas
    p: Palette
    brief: PostcardBrief
    motifs: list[str]
    setting: str
    horizon: float = 0.0
    lean: float = 0.0
    wet: bool = False
    stormy: bool = False
    slots: list[Slot] = field(default_factory=list)
    towers: list[Slot] = field(default_factory=list)
    lanes: list[Slot] = field(default_factory=list)  # where vehicles drive
    boats: list[Slot] = field(default_factory=list)  # open water
    perches: list[tuple[Point, Point]] = field(default_factory=list)  # wires and rails
    ground_colour: RGB = (0, 0, 0)
    canal: bool = False

    def has(self, motif: str) -> bool:
        return motif in self.motifs

    def weight(self, motif: str) -> float:
        """1.3 for the main motif, 1.0 for the second, 0.8 for the third."""
        index = self.motifs.index(motif) if motif in self.motifs else 2
        return (1.3, 1.0, 0.8)[min(index, 2)]

    def take(self) -> Slot | None:
        return self.slots.pop(0) if self.slots else None

    def label_has(self, *names: str) -> bool:
        return any(name in self.brief.labels[:6] for name in names)


# -- sky -------------------------------------------------------------------------


def paint_sky(s: Scene) -> None:
    c, p = s.c, s.p
    sky = list(p.sky)
    if s.stormy:
        sky = [mix(colour, p.dark, 0.3 if not p.is_dark else 0.12) for colour in sky]
    elif s.wet:
        grey = mix(p.far, p.cloud, 0.5)
        sky = [mix(colour, grey, 0.45) for colour in sky]
    c.rect(-20, -20, c.w + 20, c.h + 20, sky[0], 0.06)
    for i, fraction in enumerate((0.36, 0.62, 0.84)):
        c.ridge(s.horizon * fraction, 7, sky[i + 1], bumps=1.4, roughness=0.6, texture=0.06)

    overcast = s.wet or s.stormy
    time = s.brief.time_of_day
    if time == "night":
        star = mix(p.sun, sky[0], 0.25)
        for _ in range(70):
            x, y = c.uniform(0, c.w), c.uniform(0, s.horizon * 0.9)
            r = c.uniform(0.9, 2.2)
            if not overcast or c.chance(0.25):
                c.ellipse(x, y, r, r, star, 0.0)
        if not overcast:
            mx, my = c.w * 0.2, s.horizon * 0.3
            c.ellipse(mx, my, 50, 50, mix(sky[0], p.sun, 0.14), 0.03)
            c.ellipse(mx, my, 33, 33, p.sun, 0.04)
            c.ellipse(mx + 14, my - 8, 28, 28, mix(sky[0], p.sun, 0.14), 0.0)
    elif not overcast:
        if time == "day":
            sx, sy, r = c.w * 0.24, s.horizon * 0.3, 36.0
        elif time == "dawn":
            sx, sy, r = c.w * 0.3, s.horizon - 14, 62.0
        else:
            sx, sy, r = c.w * 0.36, s.horizon - 30, 70.0
        c.ellipse(sx, sy, r * 1.5, r * 1.5, mix(sky[2 if time != "day" else 0], p.sun, 0.3), 0.03)
        c.ellipse(sx, sy, r, r, p.sun, 0.04)

    storm_cloud = mix(p.cloud, p.dark, 0.5) if not p.is_dark else mix(p.cloud, p.sky[3], 0.4)
    cloud_colour = storm_cloud if s.stormy else (mix(p.cloud, p.far, 0.45) if s.wet else p.cloud)
    cloudy = s.brief.weather in ("cloudy", "fog", "drizzle", "rain", "snow", "storm") or overcast
    count = 5 if cloudy else 2
    for i in range(count):
        x = c.w * (0.1 + 0.8 * (i + c.uniform(0.1, 0.9)) / count) * 0.8
        # Leave the top of the sky clear when something has to fly through it.
        y = s.horizon * (c.uniform(0.46, 0.7) if s.has("aircraft") or s.has("fireworks") else c.uniform(0.2, 0.62))
        props.cloud(c, x, y, c.uniform(120, 240) * (1.25 if cloudy else 1.0), cloud_colour)
    if s.stormy:
        c.rect(-20, -20, c.w + 20, s.horizon * 0.22, storm_cloud, 0.07)
        for i in range(7):
            props.cloud(c, c.w * (i + 0.5) / 7 + c.uniform(-30, 30), s.horizon * c.uniform(0.34, 0.46), c.uniform(240, 330), storm_cloud)


def paint_sky_accents(s: Scene) -> None:
    c, p = s.c, s.p
    if s.has("fireworks"):
        pairs = ((p.accent, p.light), (p.light, p.sun), (p.foam, p.accent))
        strength = s.weight("fireworks")
        spots = ((0.42, 0.34, 96), (0.62, 0.22, 74), (0.3, 0.16, 58), (0.54, 0.5, 50))
        for i, (fx, fy, radius) in enumerate(spots[: 4 if strength > 1.1 else 2]):
            props.firework(c, c.w * fx, s.horizon * fy + 20, radius * min(strength, 1.15), pairs[i % 3], ground=s.horizon)
    if s.has("aircraft"):
        strength = s.weight("aircraft")
        props.plane(c, c.w * 0.52, s.horizon * 0.2, 0.9 * strength, p)
    if s.stormy:
        flash = p.light if p.is_dark else p.sun
        props.lightning(c, c.w * c.uniform(0.4, 0.54), s.horizon * 0.42, s.horizon + 8, flash)


# -- shared middle-distance pieces -----------------------------------------------


def paint_towers(s: Scene) -> None:
    """Things that stand on the skyline: the bell tower, the crane, a far train."""
    c, p = s.c, s.p
    spots = list(s.towers)
    for motif in s.motifs:
        if motif == "bells" and spots:
            x, y, scale = spots.pop(0)
            props.bell_tower(c, x, y, scale * (0.85 + 0.2 * s.weight("bells")), p)
        elif motif == "works" and spots:
            x, y, scale = spots.pop(0)
            props.crane(c, x, y, scale * (0.8 + 0.2 * s.weight("works")), p)
            frame = mix(p.walls[1], p.dark, 0.25)
            for i in range(4):
                c.line([(x + 60 + i * 26, y), (x + 60 + i * 26, y - 120 * scale)], frame, 2.4)
            for j in range(4):
                c.line([(x + 60, y - 30 * j * scale - 30), (x + 138, y - 30 * j * scale - 30)], frame, 2.4)


def far_train(s: Scene, y: float, scale: float = 0.55) -> None:
    c, p = s.c, s.p
    c.rect(-20, y, c.w + 20, y + 5, mix(p.mid, p.dark, 0.4), 0.0)
    train(s, c.w * 0.36, y, scale)


def train(s: Scene, x: float, y: float, scale: float) -> None:
    """A steam locomotive pulling three carriages to the right, front at x."""
    c, p = s.c, s.p
    carriage = 96 * scale
    for i in range(3):
        left = x - (i + 1) * (carriage + 6 * scale) - 70 * scale
        c.rect(left, y - 34 * scale, left + carriage, y - 6 * scale, p.accent if i % 2 == 0 else mix(p.accent, p.dark, 0.25))
        c.rect(left, y - 38 * scale, left + carriage, y - 33 * scale, p.dark, 0.0)
        for w in range(4):
            wx = left + 10 * scale + w * 21 * scale
            c.rect(wx, y - 28 * scale, wx + 13 * scale, y - 17 * scale, p.window if p.is_dark else p.light, 0.0)
        for wheel in (0.2, 0.8):
            c.ellipse(left + carriage * wheel, y - 5 * scale, 6 * scale, 6 * scale, p.dark, 0.0)
    left = x - 70 * scale
    c.rect(left, y - 30 * scale, left + 58 * scale, y - 6 * scale, p.dark)
    c.ellipse(left + 58 * scale, y - 18 * scale, 9 * scale, 12 * scale, p.dark, 0.0)
    c.rect(left - 4 * scale, y - 44 * scale, left + 22 * scale, y - 6 * scale, mix(p.dark, p.accent, 0.3))
    c.rect(left + 40 * scale, y - 46 * scale, left + 49 * scale, y - 30 * scale, p.dark, 0.0)
    for wheel in (0.14, 0.5, 0.86):
        c.ellipse(left + 58 * scale * wheel, y - 6 * scale, 7.5 * scale, 7.5 * scale, mix(p.dark, p.accent, 0.45), 0.0)
    smoke = mix(p.cloud, p.sky[1], 0.15)
    for i in range(6):
        c.blob(left + 44 * scale - i * 48 * scale, y - (60 + i * 15) * scale, (14 + i * 6) * scale, (11 + i * 4) * scale, smoke, wobble=0.22)


def waves_on(s: Scene, top: float, bottom: float, *, density: float = 1.0) -> None:
    """Short curled strokes that get bigger and further apart towards the viewer."""
    c, p = s.c, s.p
    rows = max(3, int((bottom - top) / 26))
    for row in range(rows):
        t = (row + 0.5) / rows
        y = top + (bottom - top) * t**1.3
        width = 18 + 54 * t
        count = int((6 + 5 * (1 - t)) * density)
        for i in range(count):
            x = c.w * (i + c.uniform(0.1, 0.9)) / count
            c.curve([(x - width, y + 3), (x - width * 0.4, y - 5 - 4 * t), (x + width * 0.1, y), (x + width, y + 2)], p.foam, 2.2 + 2.4 * t, steps=6)


# -- settings --------------------------------------------------------------------


def setting_meadow(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    sea = s.has("waves") or s.has("fireworks")
    if sea:
        c.rect(-20, s.horizon - 8, w + 20, s.horizon + 80, p.water, 0.06)
        waves_on(s, s.horizon + 4, s.horizon + 50, density=0.7)
        props.sailboat(c, w * 0.4, s.horizon + 26, 0.5, p, p.light)
        c.ridge(s.horizon + 4, 30, p.far, bumps=1.2, roughness=0.3, bottom=s.horizon + 90)
    else:
        c.ridge(s.horizon - 26, 30, p.far, bumps=2.4)
    if s.has("train") and s.motifs[0] != "train":
        far_train(s, s.horizon + 6)
    edge = c.ridge(s.horizon + 26, 22, p.mid, bumps=2.0)
    s.towers = [(w * 0.63, s.horizon + 26, 0.62), (w * 0.82, s.horizon + 30, 0.55)]
    for i in range(9):
        x = w * (0.04 + 0.92 * (i + c.uniform(0.2, 0.8)) / 9)
        y = _edge_y(edge, x) + 4
        if abs(x - w * 0.63) < 46:
            continue
        if c.chance(0.4):
            props.cypress(c, x, y, c.uniform(0.34, 0.5), p, lean=s.lean)
        else:
            props.round_tree(c, x, y, c.uniform(0.36, 0.52), p, lean=s.lean)
    paint_towers(s)
    c.ridge(h * 0.7, 16, p.near, bumps=1.6)
    field_colour = mix(p.ground, p.near, 0.18)
    c.ridge(h * 0.79, 10, field_colour, bumps=1.3)
    s.ground_colour = field_colour
    # A path that winds up from the bottom edge and narrows away.
    left = [(w * 0.5, h + 20), (w * 0.56, h * 0.93), (w * 0.47, h * 0.86), (w * 0.535, h * 0.8)]
    right = [(w * 0.535, h * 0.8), (w * 0.55, h * 0.8), (w * 0.52, h * 0.86), (w * 0.66, h * 0.93), (w * 0.68, h + 20)]
    c.poly(smooth(left, 6) + smooth(right, 6), p.path, 0.05)
    props.round_tree(c, w * 0.9, h * 0.84, 1.5, p, lean=s.lean, crown=mix(p.near, p.dark, 0.3))
    if c.chance(0.6):
        props.cypress(c, w * 0.045, h * 0.83, 1.2, p, lean=s.lean)
    # A fence along the left field gives birds somewhere to sit.
    rail_y = h * 0.855
    for i in range(6):
        fx = w * 0.1 + i * 46
        c.line([(fx, rail_y + 26), (fx, rail_y - 6)], p.dark, 4)
    c.line([(w * 0.1 - 10, rail_y), (w * 0.1 + 240, rail_y + 4)], p.dark, 2.6)
    c.line([(w * 0.1 - 10, rail_y + 13), (w * 0.1 + 240, rail_y + 17)], p.dark, 2.6)
    s.perches = [((w * 0.1, rail_y - 4), (w * 0.1 + 230, rail_y))]
    for _ in range(26):
        gx, gy = c.uniform(0, w), c.uniform(h * 0.82, h * 0.99)
        if w * 0.44 < gx < w * 0.7:
            continue
        props.grass_tuft(c, gx, gy, c.uniform(10, 20), mix(field_colour, p.dark, 0.3), lean=s.lean)
    s.slots = [(w * 0.33, h * 0.94, 1.0), (w * 0.76, h * 0.95, 0.95), (w * 0.2, h * 0.97, 0.9)]
    s.lanes = []


def _edge_y(edge: list[Point], x: float) -> float:
    return min(edge, key=lambda point: abs(point[0] - x))[1]


def setting_street(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    base = h * 0.68
    if s.has("train") and s.motifs[0] != "train":
        far_train(s, s.horizon - 10, 0.5)
    # Far skyline in one flat tone.
    x = -10.0
    while x < w + 10:
        width = c.uniform(44, 96)
        c.rect(x, s.horizon - c.uniform(30, 150), x + width, base, p.far, 0.05)
        x += width
    s.towers = [(w * 0.3, base - 70, 1.12), (w * 0.62, base - 70, 1.0)]
    paint_towers(s)
    # A row of townhouses, shop fronts under some of them.
    x = -30.0
    roofs = ("gable", "flat", "hip", "flat")
    index = 0
    while x < w + 10:
        width = c.uniform(92, 150)
        height = c.uniform(150, 250)
        props.house(c, x, base, width, height, p, p.walls[index % 4], roof=roofs[int(c.rng.integers(0, 4))], shop=c.chance(0.45))
        x += width + c.uniform(0, 5)
        index += 1
    pavement = mix(p.path, p.ground, 0.2)
    c.rect(-20, base, w + 20, h * 0.755, pavement, 0.05)
    c.rect(-20, h * 0.75, w + 20, h * 0.762, mix(pavement, p.dark, 0.3), 0.0)
    s.canal = (s.has("water") or s.has("waves")) and not s.has("traffic")
    if s.canal:
        c.rect(-20, h * 0.762, w + 20, h + 20, p.water, 0.07)
        waves_on(s, h * 0.79, h * 0.99, density=0.55)
        props.sailboat(c, w * 0.68, h * 0.9, 0.85, p, p.accent)
        s.boats = [(w * 0.3, h * 0.93, 0.7)]
    else:
        road = mix(p.dark, p.far, 0.35) if not p.is_dark else mix(p.dark, p.mid, 0.5)
        c.rect(-20, h * 0.762, w + 20, h + 20, road, 0.08)
        for i in range(9):
            c.rect(i * 140 - 20, h * 0.872, i * 140 + 50, h * 0.882, mix(p.light, road, 0.35), 0.0)
        s.lanes = [(w * 0.3, h * 0.865, 1.0), (w * 0.72, h * 0.985, 1.25), (w * 0.86, h * 0.865, 1.0)]
    s.ground_colour = pavement
    for lx in (w * 0.13, w * 0.52, w * 0.9):
        props.lamp_post(c, lx, h * 0.752, 1.0, p)
    wire_y = base - 215
    c.line([(-10, wire_y + 8), (w * 0.5, wire_y + 30), (w + 10, wire_y)], p.dark, 1.6)
    s.perches = [((w * 0.08, wire_y + 12), (w * 0.46, wire_y + 28))]
    s.slots = [(w * 0.4, h * 0.752, 0.86), (w * 0.68, h * 0.752, 0.86), (w * 0.24, h * 0.752, 0.82), (w * 0.8, h * 0.752, 0.8)]


def setting_square(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    base = h * 0.62
    x = -10.0
    while x < w + 10:
        width = c.uniform(50, 100)
        c.rect(x, s.horizon - c.uniform(120, 210), x + width, base, p.far, 0.05)
        x += width
    s.towers = [(w * 0.5, base - 40, 1.0), (w * 0.24, base - 40, 0.9)]
    paint_towers(s)
    x = -40.0
    index = 0
    while x < w + 10:
        width = c.uniform(130, 190)
        gap = w * 0.42 < x + width / 2 < w * 0.6 and (s.has("bells") or s.has("works"))
        if not gap:
            props.house(c, x, base, width, c.uniform(190, 270), p, p.walls[index % 4], roof=("hip", "flat", "gable")[index % 3], shop=True)
        x += width + 2
        index += 1
    plaza = mix(p.path, p.ground, 0.12)
    c.rect(-20, base, w + 20, h + 20, plaza, 0.07)
    s.ground_colour = plaza
    joint = mix(plaza, p.dark, 0.14)
    for i in range(-6, 14):
        c.line([(w * 0.5 + (i - 3.5) * 46, base), (w * 0.5 + (i - 3.5) * 190, h + 10)], joint, 1.6)
    for t in (0.08, 0.22, 0.42, 0.7):
        c.line([(-10, base + (h - base) * t), (w + 10, base + (h - base) * t)], joint, 1.6)
    s.canal = (s.has("water") or s.has("waves")) and not s.has("traffic")
    if s.canal:
        c.rect(-20, h * 0.93, w + 20, h + 20, p.water, 0.06)
        c.rect(-20, h * 0.918, w + 20, h * 0.935, mix(plaza, p.dark, 0.35), 0.0)
        waves_on(s, h * 0.95, h * 1.0, density=0.5)
    for lx in (w * 0.06, w * 0.94):
        props.lamp_post(c, lx, base + 14, 1.15, p)
    s.perches = [((w * 0.62, base - 228), (w * 0.9, base - 214))]
    c.line([(w * 0.56, base - 232), (w + 10, base - 208)], p.dark, 1.6)
    s.slots = [(w * 0.36, h * 0.86, 1.2), (w * 0.66, h * 0.88, 1.2), (w * 0.14, h * 0.82, 1.05), (w * 0.87, h * 0.82, 1.0)]
    s.lanes = [(w * 0.5, h * 0.98, 1.1)]


def setting_coast(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    c.rect(-20, s.horizon, w + 20, h + 20, p.water, 0.08)
    c.ridge(s.horizon + 30, 4, mix(p.water, p.sky[3], 0.0), bumps=1.0, texture=0.0, bottom=s.horizon + 31)
    c.rect(-20, s.horizon, w + 20, s.horizon + 26, mix(p.water, p.sky[3], 0.35), 0.05)
    # An island on the left and a headland with a lighthouse on the right.
    c.poly(smooth([(w * 0.05, s.horizon + 2), (w * 0.12, s.horizon - 24), (w * 0.2, s.horizon - 30), (w * 0.3, s.horizon + 2)], 6), p.far)
    if s.has("train") and s.motifs[0] != "train":
        far_train(s, s.horizon + 2, 0.45)
    head = [(w * 0.56, s.horizon + 4), (w * 0.66, s.horizon - 30), (w * 0.8, s.horizon - 54), (w * 0.93, s.horizon - 60), (w + 20, s.horizon - 44), (w + 20, s.horizon + 60), (w * 0.7, s.horizon + 34)]
    c.poly(smooth(head, 6), p.mid)
    s.towers = [(w * 0.66, s.horizon - 20, 0.6)]
    paint_towers(s)
    props.lighthouse(c, w * 0.86, s.horizon - 52, 0.8, p)
    waves_on(s, s.horizon + 44, h * 0.8, density=1.0 + 0.5 * s.weight("waves"))
    s.boats = [(w * 0.34, s.horizon + 62, 0.7), (w * 0.57, s.horizon + 112, 0.95)]
    for bx, by, scale in s.boats[: 2 if s.has("waves") else 1]:
        props.sailboat(c, bx, by, scale, p, p.accent if scale > 0.8 else p.light)
    # The beach sweeps in from the lower left.
    shore = smooth([(-20, h * 0.74), (w * 0.2, h * 0.76), (w * 0.46, h * 0.83), (w * 0.74, h * 0.9), (w + 20, h * 0.93)], 8)
    c.line([(x, y - 6) for x, y in shore], p.foam, 13)
    c.poly([(-20, h + 20), *shore, (w + 20, h + 20)], p.ground, 0.07)
    s.ground_colour = p.ground
    for _ in range(12):
        gx = c.uniform(0, w * 0.3)
        props.grass_tuft(c, gx, c.uniform(h * 0.93, h), c.uniform(14, 26), mix(p.near, p.ground, 0.3), lean=s.lean)
    s.slots = [(w * 0.3, h * 0.94, 1.0), (w * 0.56, h * 0.97, 0.95), (w * 0.12, h * 0.9, 0.9)]
    s.perches = []


def setting_river(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    peaks = c.ridge(s.horizon, 62, p.far, bumps=3.4, roughness=0.7)
    snow = p.light if not p.is_dark else p.foam
    for px, py in peaks[6::9]:
        if py < s.horizon - 20:
            c.poly([(px - 26, py + 24), (px, py - 2), (px + 28, py + 26), (px + 10, py + 18), (px - 4, py + 28)], snow, 0.03)
    if s.has("train") and s.motifs[0] != "train":
        far_train(s, s.horizon + 52, 0.5)
    edge = c.ridge(s.horizon + 74, 20, p.mid, bumps=2.2)
    for i in range(16):
        x = w * (i + c.uniform(0.1, 0.9)) / 16
        props.pine(c, x, _edge_y(edge, x) + 8, c.uniform(0.38, 0.6), p, lean=s.lean)
    s.towers = [(w * 0.8, s.horizon + 80, 0.6)]
    paint_towers(s)
    bank = mix(p.near, p.ground, 0.12)
    c.ridge(h * 0.66, 12, bank, bumps=1.5)
    s.ground_colour = bank
    # The river: narrow where it leaves the trees, wide at the bottom edge.
    left = smooth([(w * 0.5, h * 0.62), (w * 0.44, h * 0.7), (w * 0.52, h * 0.79), (w * 0.3, h * 0.9), (w * 0.2, h + 20)], 8)
    right = smooth([(w * 0.8, h + 20), (w * 0.78, h * 0.9), (w * 0.66, h * 0.79), (w * 0.56, h * 0.7), (w * 0.55, h * 0.62)], 8)
    c.poly(left + right, p.water, 0.08)
    for _ in range(22):
        t = c.uniform(0.1, 1.0)
        y = h * (0.64 + 0.36 * t)
        centre = w * (0.52 - 0.03 * math.sin(t * 5) + 0.0 * t)
        half = 12 + 150 * t**1.6
        x = centre + c.uniform(-half, half) * 0.8
        length = 10 + 34 * t
        c.curve([(x - length, y + 2), (x, y - 2 - 2 * t), (x + length, y + 3)], p.foam, 1.6 + 2.6 * t, steps=5)
    for rx, ry, size in ((w * 0.46, h * 0.86, 1.0), (w * 0.62, h * 0.95, 1.3), (w * 0.53, h * 0.75, 0.6)):
        c.blob(rx, ry, 26 * size, 14 * size, mix(p.dark, p.far, 0.3), wobble=0.2)
        c.arc(rx, ry + 8 * size, 34 * size, 9 * size, 10, 170, p.foam, 2.6 * size)
    for x, y, size in ((w * 0.06, h * 0.9, 1.6), (w * 0.16, h * 0.82, 1.1), (w * 0.94, h * 0.92, 1.7), (w * 0.86, h * 0.8, 1.0)):
        props.pine(c, x, y, size, p, lean=s.lean, colour=mix(p.near, p.dark, 0.45))
    s.slots = [(w * 0.24, h * 0.95, 0.95), (w * 0.86, h * 0.985, 0.9)]
    s.boats = [(w * 0.5, h * 0.97, 0.0)]
    s.perches = []


def setting_railway(s: Scene) -> None:
    c, p, h, w = s.c, s.p, s.c.h, s.c.w
    c.ridge(s.horizon - 30, 34, p.far, bumps=2.6)
    c.ridge(s.horizon + 60, 26, p.mid, bumps=1.8)
    s.towers = [(w * 0.84, s.horizon + 50, 0.55)]
    paint_towers(s)
    # The viaduct: a deck, piers, and the stone between each pair of piers.
    deck = s.horizon + 8
    floor = h * 0.8
    stone = mix(p.cloud, p.far, 0.35)
    span = 126.0
    spring = deck + 58
    x = -span * 0.4
    while x < w + span:
        c.rect(x - 11, deck, x + 11, floor, stone, 0.06)
        arc: list[Point] = [(x + 11, deck + 12)]
        cx, radius = x + span / 2, span / 2 - 11
        for i in range(13):
            angle = math.pi * i / 12
            arc.append((cx - radius * math.cos(angle), spring - radius * 0.86 * math.sin(angle)))
        arc.append((x + span - 11, deck + 12))
        c.poly(arc, stone, 0.06)
        x += span
    c.rect(-20, deck - 4, w + 20, deck + 14, mix(stone, p.dark, 0.18), 0.05)
    c.rect(-20, deck - 9, w + 20, deck - 4, p.dark, 0.0)
    train(s, w * 0.74, deck - 8, 1.0 * (0.8 + 0.25 * s.weight("train")))
    edge = c.ridge(h * 0.76, 14, p.near, bumps=1.7)
    for i in range(7):
        x = w * (i + c.uniform(0.1, 0.9)) / 7
        props.round_tree(c, x, _edge_y(edge, x) + 6, c.uniform(0.5, 0.8), p, lean=s.lean)
    field_colour = mix(p.ground, p.near, 0.18)
    c.ridge(h * 0.84, 9, field_colour, bumps=1.2)
    s.ground_colour = field_colour
    for _ in range(22):
        props.grass_tuft(c, c.uniform(0, w), c.uniform(h * 0.87, h * 0.99), c.uniform(10, 20), mix(field_colour, p.dark, 0.3), lean=s.lean)
    s.slots = [(w * 0.3, h * 0.96, 1.0), (w * 0.7, h * 0.97, 0.95)]
    s.perches = []


SETTINGS: dict[str, tuple[float, Callable[[Scene], None]]] = {
    "meadow": (0.55, setting_meadow),
    "street": (0.56, setting_street),
    "square": (0.5, setting_square),
    "coast": (0.5, setting_coast),
    "river": (0.4, setting_river),
    "railway": (0.5, setting_railway),
}


# -- things on the ground --------------------------------------------------------


def _needs_ground(s: Scene, motif: str) -> bool:
    if motif in ("market", "cafe", "footsteps", "animals", "fire", "music"):
        return True
    if motif == "water":
        return s.setting not in ("river", "coast") and not s.canal
    if motif == "rain":
        return s.motifs[0] == "rain" and s.setting in ("street", "square")
    return False


def paint_ground_accents(s: Scene) -> None:
    c, p = s.c, s.p
    coats = (p.accent, p.walls[1], mix(p.far, p.dark, 0.3), p.walls[2])

    if s.has("traffic"):
        strength = s.weight("traffic")
        colours = (p.accent, p.walls[1] if not p.is_dark else p.far, p.sun)
        if not s.lanes:
            # No road in this setting: lay a lane along the bottom edge.
            c.ridge(c.h * 0.93, 5, mix(p.dark, p.far, 0.4), bumps=1.0, texture=0.07)
            s.lanes = [(c.w * 0.62, c.h * 0.995, 1.0), (c.w * 0.22, c.h * 0.995, 0.95)]
            s.slots = [slot for slot in s.slots if slot[1] < c.h * 0.9][:1]
        for i, (x, y, scale) in enumerate(s.lanes[: 3 if strength > 1.1 else 2]):
            facing = 1 if i % 2 == 0 else -1
            if i == 1 and (s.label_has("Bus", "Truck") or strength > 1.1):
                props.bus(c, x, y, scale * 0.9, p, colours[1], facing=facing)
            else:
                props.car(c, x, y, scale, p, colours[i % 3], facing=facing)

    # Every motif that stands on the ground gets one spot, in order of strength.
    # Whatever is left over goes to the main motif.
    wanting = [m for m in s.motifs if _needs_ground(s, m)]
    spots: dict[str, list[Slot]] = {m: [] for m in wanting}
    for motif in wanting:
        slot = s.take()
        if slot:
            spots[motif].append(slot)
    if wanting and wanting[0] == s.motifs[0]:
        while s.slots and len(spots[wanting[0]]) < 3:
            spots[wanting[0]].append(s.slots.pop(0))
    # Paint back to front so nearer things overlap farther ones.
    order = sorted(((slot, motif, i) for motif, slots in spots.items() for i, slot in enumerate(slots)), key=lambda item: item[0][1])

    for (x, y, scale), motif, i in order:
        strength = s.weight(motif)
        if motif == "market":
            stripes = ((p.accent, p.light), (p.sun, p.light), (mix(p.near, p.light, 0.2), p.light))
            if i == 2:
                props.walker(c, x, y, scale * 0.95, p, coats[1])
            else:
                props.stall(c, x, y, scale * 0.95, p, stripes[i % 3])
        elif motif == "cafe":
            if i == 0:
                props.cafe_table(c, x, y, scale * 0.9, p)
            else:
                props.walker(c, x, y, scale * 0.95, p, coats[i])
        elif motif == "footsteps":
            props.walker(c, x, y, scale * 1.05, p, coats[i % 4], umbrella=p.accent if s.wet and i == 0 else None)
            for k in range(5):
                c.ellipse(x - 26 - k * 22, y + (5 if k % 2 else -1), 5, 2.4, mix(s.ground_colour, p.dark, 0.3), 0.0)
        elif motif == "animals":
            if i > 0 and strength < 1.1:
                continue
            if s.label_has("Dog", "Bark", "Bow-wow", "Howl", "Yip", "Growling", "Canidae, dogs, wolves", "Domestic animals, pets"):
                props.dog(c, x, y, scale * 1.25, p, facing=1 if i % 2 == 0 else -1)
            elif s.label_has("Cattle, bovinae", "Moo", "Cowbell", "Livestock, farm animals, working animals"):
                props.cow(c, x, y, scale * 1.05, p, facing=1 if i % 2 == 0 else -1)
            else:
                props.sheep(c, x, y, scale * 1.2, p)
                props.sheep(c, x + 66 * scale, y - 14, scale * 0.95, p, facing=-1)
        elif motif == "fire":
            if i == 0:
                props.campfire(c, x, y, scale * strength, p)
        elif motif == "music":
            if i == 0:
                props.guitar(c, x, y, scale * (0.8 + 0.2 * strength), p)
                ink = p.light if p.is_dark else p.dark
                for k in range(5 if strength > 1.1 else 3):
                    props.music_note(c, x + 50 * scale + k * 44 * scale, y - 150 * scale - k * 34 * scale + 16 * math.sin(k * 2.1), scale * (0.9 + 0.12 * k), ink, double=k % 2 == 1)
            elif i == 1:
                props.walker(c, x, y, scale * 0.95, p, coats[2])
        elif motif == "water":
            if i == 0:
                (props.fountain if s.setting in ("street", "square") else props.pond)(c, x, y, scale * strength, p)
        elif motif == "rain":
            props.walker(c, x, y, scale * 1.05, p, coats[(i + 1) % 4], umbrella=(p.accent, p.sun, p.light)[i % 3])

    if s.wet:
        for i in range(4):
            x = c.w * (0.14 + 0.24 * i + c.uniform(-0.04, 0.04))
            props.puddle(c, x, c.h * c.uniform(0.9, 0.98), c.uniform(44, 80), p)


# -- things in front of everything -----------------------------------------------


def paint_overlays(s: Scene) -> None:
    c, p = s.c, s.p
    ink = mix(p.dark, p.sky[0], 0.15) if not p.is_dark else mix(p.foam, p.sky[1], 0.2)

    if s.has("birds"):
        strength = s.weight("birds")
        flock = int(7 * strength)
        fx, fy = c.w * c.uniform(0.3, 0.5), s.horizon * c.uniform(0.28, 0.45)
        for i in range(flock):
            span = c.uniform(9, 17) * strength
            props.flying_bird(c, fx + (i % 4) * 46 + c.uniform(-14, 14) - i * 9, fy + (i // 4) * 30 + c.uniform(-12, 12) + (i % 4) * 9, span, ink)
        if strength > 1.1:
            props.flying_bird(c, c.w * 0.16, s.horizon * 0.62, 30, ink)
        if s.perches:
            (x0, y0), (x1, y1) = s.perches[0]
            count = 4 if strength > 1.1 else 2
            body = p.dark if not p.is_dark else mix(p.dark, p.foam, 0.3)
            for i in range(count):
                t = (i + 0.5 + c.uniform(-0.2, 0.2)) / count
                props.perched_bird(c, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 1.0 if strength > 1.1 else 0.85, body, p.accent, facing=1 if i % 3 else -1)

    if s.has("insects"):
        strength = s.weight("insects")
        blade = mix(p.near, p.dark, 0.45)
        for i in range(int(46 * strength)):
            x = c.uniform(-10, c.w + 10)
            height = c.uniform(40, 110) * (0.7 + 0.3 * strength)
            c.poly([(x - 4, c.h + 5), (x + s.lean * height + c.uniform(-16, 16), c.h - height), (x + 4, c.h + 5)], blade if i % 3 else mix(blade, p.near, 0.5), 0.0)
        for _ in range(8):
            x = c.uniform(0, c.w)
            top = c.h - c.uniform(70, 120)
            c.line([(x, c.h), (x + 5, top)], blade, 2.4)
            c.ellipse(x + 5, top - 9, 4.5, 12, mix(p.roof, p.dark, 0.2), 0.0)
        glow = p.light if p.is_dark else p.sun
        halo = mix(p.light, p.near, 0.55) if p.is_dark else mix(p.sun, s.ground_colour, 0.5)
        for _ in range(int(16 * strength)):
            x, y = c.uniform(0, c.w), c.uniform(s.horizon + 30, c.h - 26)
            c.ellipse(x, y, 7, 7, halo, 0.0)
            c.ellipse(x, y, 3, 3, glow, 0.0)

    if s.has("wind"):
        strength = s.weight("wind")
        stroke = p.foam if p.is_dark else p.light
        for _ in range(int(6 * strength)):
            x, y = c.uniform(-40, c.w * 0.7), c.uniform(s.horizon * 0.3, c.h * 0.86)
            length = c.uniform(150, 280)
            c.curve([(x, y), (x + length * 0.3, y - 16), (x + length * 0.62, y + 8), (x + length * 0.86, y - 22), (x + length, y - 12)], stroke, 3.0, steps=8)
            c.arc(x + length + 6, y - 22, 13, 11, 200, 520, stroke, 3.0)
        leaves = (p.accent, p.sun, mix(p.near, p.light, 0.2))
        for i in range(int(16 * strength)):
            x, y = c.uniform(0, c.w), c.uniform(s.horizon * 0.5, c.h * 0.92)
            angle = c.uniform(-0.8, 0.3)
            dx, dy = math.cos(angle) * 10, math.sin(angle) * 10
            c.poly([(x - dx, y - dy), (x - dy * 0.45, y + dx * 0.45), (x + dx, y + dy), (x + dy * 0.45, y - dx * 0.45)], leaves[i % 3], 0.0)
        if strength > 1.1 or len(s.motifs) == 1:
            props.kite(c, c.w * 0.46, s.horizon * 0.34, 1.25, p, (c.w * 0.3, c.h * 0.9))

    if s.wet or s.stormy:
        streak = mix(p.light, p.sky[1], 0.3) if not p.is_dark else mix(p.foam, p.sky[2], 0.35)
        heavy = s.stormy or s.weight("rain") > 1.1
        for _ in range(240 if heavy else 130):
            x, y = c.uniform(-60, c.w + 20), c.uniform(-20, c.h)
            length = c.uniform(22, 46)
            c.line([(x, y), (x - length * 0.34 + s.lean * 20, y + length)], streak, 1.7)

    if s.brief.weather == "snow":
        for _ in range(170):
            r = c.uniform(1.6, 4.2)
            c.ellipse(c.uniform(0, c.w), c.uniform(0, c.h), r, r, p.light if not p.is_dark else p.foam, 0.0)
    if s.brief.weather == "fog":
        mist = mix(p.sky[3], p.cloud, 0.5)
        for i in range(4):
            y = s.horizon + 10 + i * 34 + c.uniform(-8, 8)
            x0 = c.uniform(-80, c.w * 0.4)
            c.line([(x0, y), (x0 + c.uniform(c.w * 0.4, c.w * 0.8), y + c.uniform(-4, 4))], mist, c.uniform(9, 16))


# -- entry point -----------------------------------------------------------------


def paint_scene(brief: PostcardBrief, size: tuple[int, int] = ART_SIZE) -> Image.Image:
    """Paint the art for a brief. Same brief, same picture."""
    motifs = [m for m in brief.motifs if m in SETTING_FOR_MOTIF][:3] or ["hum"]
    palette = PALETTES[brief.time_of_day]
    canvas = Canvas(ART_SIZE[0], ART_SIZE[1], brief.seed)
    setting = SETTING_FOR_MOTIF[motifs[0]]
    horizon, painter = SETTINGS[setting]
    scene = Scene(
        c=canvas,
        p=palette,
        brief=brief,
        motifs=motifs,
        setting=setting,
        horizon=ART_SIZE[1] * horizon,
        lean=0.22 if "wind" in motifs else (0.1 if "storm" in motifs else 0.0),
        wet="rain" in motifs or brief.weather in ("rain", "drizzle"),
        stormy="storm" in motifs or brief.weather == "storm",
    )
    paint_sky(scene)
    paint_sky_accents(scene)
    painter(scene)
    paint_ground_accents(scene)
    paint_overlays(scene)
    image = canvas.finish()
    if image.size != size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image
