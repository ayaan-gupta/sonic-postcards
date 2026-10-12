"""A small gouache painter on top of Pillow.

Shapes are filled with flat opaque colour, the way gouache goes down. Three
things make the result read as paint instead of vector art:

- every shape carries its own brush texture, cut off at its edge, because
  each area was "painted" separately (an id buffer records who owns a pixel)
- the whole picture is pushed around by a slow noise field, so no edge is
  ruler straight
- paper grain on top

Everything is driven by one seeded generator, so a brief always paints the
same picture.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from PIL import Image, ImageDraw

RGB = tuple[int, int, int]
Point = tuple[float, float]

SS = 2  # supersampling factor


def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def _noise(rng: np.random.Generator, width: int, height: int, cells_x: int, cells_y: int) -> np.ndarray:
    """Smooth noise in [-1, 1]: a coarse random grid blown up with bicubic interpolation."""
    grid = rng.random((max(2, cells_y), max(2, cells_x))).astype(np.float32)
    image = Image.fromarray((grid * 255).astype(np.uint8), "L").resize((width, height), Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32) / 127.5 - 1.0


class Canvas:
    """Draw in art pixels; the canvas works at twice that and scales down at the end."""

    def __init__(self, width: int, height: int, seed: int, *, wobble: float = 1.0) -> None:
        self.w = width
        self.h = height
        self.wobble = wobble  # how unsteady the hand is; small pictures want less
        self.rng = np.random.default_rng(seed)
        self._image = Image.new("RGB", (width * SS, height * SS), (255, 255, 255))
        self._ids = Image.new("L", (width * SS, height * SS), 0)
        self._draw = ImageDraw.Draw(self._image)
        self._id_draw = ImageDraw.Draw(self._ids)
        self._next_id = 1
        self._amps: list[float] = [0.0]

    # -- helpers -----------------------------------------------------------------

    def _shape_id(self, texture: float) -> int:
        """Shapes cycle through 255 ids; neighbours never share one, which is all that matters."""
        if texture <= 0:
            return 0
        shape_id = self._next_id
        self._next_id = shape_id % 255 + 1
        if shape_id < len(self._amps):
            self._amps[shape_id] = texture
        else:
            self._amps.append(texture)
        return shape_id

    @staticmethod
    def _scale(points: Sequence[Point]) -> list[Point]:
        return [(x * SS, y * SS) for x, y in points]

    def uniform(self, low: float, high: float) -> float:
        return float(self.rng.uniform(low, high))

    def chance(self, probability: float) -> bool:
        return bool(self.rng.random() < probability)

    def pick(self, options: Sequence[RGB]) -> RGB:
        return options[int(self.rng.integers(0, len(options)))]

    # -- primitives --------------------------------------------------------------

    def poly(self, points: Sequence[Point], colour: RGB, texture: float = 0.06) -> None:
        if len(points) < 3:
            return
        scaled = self._scale(points)
        self._draw.polygon(scaled, fill=colour)
        self._id_draw.polygon(scaled, fill=self._shape_id(texture))

    def rect(self, x0: float, y0: float, x1: float, y1: float, colour: RGB, texture: float = 0.06) -> None:
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], colour, texture)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, colour: RGB, texture: float = 0.05) -> None:
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._draw.ellipse(box, fill=colour)
        self._id_draw.ellipse(box, fill=self._shape_id(texture))

    def pie(self, cx: float, cy: float, rx: float, ry: float, start: float, end: float, colour: RGB, texture: float = 0.05) -> None:
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._draw.pieslice(box, start, end, fill=colour)
        self._id_draw.pieslice(box, start, end, fill=self._shape_id(texture))

    def line(self, points: Sequence[Point], colour: RGB, width: float, texture: float = 0.0) -> None:
        """A stroke with round ends and joints."""
        scaled = self._scale(points)
        w = max(1, round(width * SS))
        shape_id = self._shape_id(texture)
        self._draw.line(scaled, fill=colour, width=w, joint="curve")
        self._id_draw.line(scaled, fill=shape_id, width=w, joint="curve")
        if w >= 3:
            r = w / 2
            for x, y in (scaled[0], scaled[-1]):
                self._draw.ellipse([x - r, y - r, x + r, y + r], fill=colour)
                self._id_draw.ellipse([x - r, y - r, x + r, y + r], fill=shape_id)

    def arc(self, cx: float, cy: float, rx: float, ry: float, start: float, end: float, colour: RGB, width: float) -> None:
        box = [(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS]
        self._draw.arc(box, start, end, fill=colour, width=max(1, round(width * SS)))

    def curve(self, points: Sequence[Point], colour: RGB, width: float, steps: int = 12) -> None:
        """A smooth stroke through the given points (Catmull-Rom)."""
        self.line(smooth(points, steps), colour, width)

    def blob(self, cx: float, cy: float, rx: float, ry: float, colour: RGB, *, wobble: float = 0.12, points: int = 14, texture: float = 0.06) -> None:
        """An ellipse drawn by an unsteady hand."""
        outline: list[Point] = []
        phase = self.uniform(0, math.tau)
        for i in range(points):
            angle = math.tau * i / points
            radius = 1.0 + wobble * math.sin(angle * 3 + phase) * 0.6 + wobble * self.uniform(-0.5, 0.5)
            outline.append((cx + math.cos(angle) * rx * radius, cy + math.sin(angle) * ry * radius))
        self.poly(smooth(outline + outline[:1], 4), colour, texture)

    def ridge(self, y: float, amplitude: float, colour: RGB, *, bumps: float = 3.0, roughness: float = 0.35, texture: float = 0.07, bottom: float | None = None) -> list[Point]:
        """A band with a rolling top edge from the left side to the right. Returns the edge."""
        edge = self.ridge_line(y, amplitude, bumps=bumps, roughness=roughness)
        floor = self.h + 20 if bottom is None else bottom
        self.poly([(-20, floor), *edge, (self.w + 20, floor)], colour, texture)
        return edge

    def ridge_line(self, y: float, amplitude: float, *, bumps: float = 3.0, roughness: float = 0.35) -> list[Point]:
        phases = [self.uniform(0, math.tau) for _ in range(3)]
        edge: list[Point] = []
        steps = 72
        for i in range(steps + 1):
            x = -20 + (self.w + 40) * i / steps
            t = i / steps
            value = (
                math.sin(t * math.tau * bumps * 0.5 + phases[0])
                + roughness * math.sin(t * math.tau * bumps * 1.7 + phases[1])
                + roughness * 0.5 * math.sin(t * math.tau * bumps * 4.1 + phases[2])
            )
            edge.append((x, y - amplitude * value / (1 + roughness * 1.5)))
        return edge

    # -- finishing ---------------------------------------------------------------

    def finish(self, *, full_size: bool = False) -> Image.Image:
        """Texture, wobble and grain. `full_size` keeps the working resolution (twice the art size)."""
        width, height = self._image.size
        rng = self.rng
        pixels = np.asarray(self._image, dtype=np.float32)
        ids = np.asarray(self._ids)

        # Brush texture, per shape: long streaks in three directions, sampled at
        # an offset that belongs to the shape.
        streaks = _noise(rng, width, height, width // 90, height // 5) * 0.65 + _noise(rng, width, height, width // 30, height // 3) * 0.35
        fields = np.stack([streaks, np.rot90(np.rot90(streaks)), _noise(rng, width, height, width // 9, height // 70)])
        count = 256
        amps = np.zeros(count, dtype=np.float32)
        amps[: len(self._amps)] = self._amps
        which = rng.integers(0, 3, size=count)
        which[rng.random(count) < 0.6] = 0  # most strokes run along the horizon
        off_y = rng.integers(0, height, size=count)
        off_x = rng.integers(0, width, size=count)
        yy, xx = np.indices((height, width), dtype=np.int32)
        sample_y = (yy + off_y[ids]) % height
        sample_x = (xx + off_x[ids]) % width
        tone = fields[which[ids], sample_y, sample_x] * amps[ids]
        # A lighter value shift per shape so that two shapes of one colour still separate.
        tone += (rng.random(count).astype(np.float32)[ids] - 0.5) * amps[ids] * 0.5
        pixels = pixels * (1.0 + tone[..., None])

        # Unsteady hand: move every pixel by a slow field plus a little jitter at the edges.
        reach = SS * self.wobble
        slow_x = _noise(rng, width, height, 9, 6) * 3.2 * reach + _noise(rng, width, height, 46, 30) * 1.1 * reach
        slow_y = _noise(rng, width, height, 9, 6) * 3.2 * reach + _noise(rng, width, height, 46, 30) * 1.1 * reach
        jitter = rng.integers(-1, 2, size=(2, height, width))
        src_y = np.clip(yy + slow_y.astype(np.int32) + jitter[0], 0, height - 1)
        src_x = np.clip(xx + slow_x.astype(np.int32) + jitter[1], 0, width - 1)
        pixels = pixels[src_y, src_x]

        image = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8), "RGB")
        out_w, out_h = (width, height) if full_size else (self.w, self.h)
        if not full_size:
            image = image.resize((out_w, out_h), Image.Resampling.LANCZOS)

        # Paper: fine grain shared by the three channels, and a soft tooth pattern.
        small = np.asarray(image, dtype=np.float32)
        grain = rng.normal(0.0, 2.6, size=(out_h, out_w)).astype(np.float32)
        tooth = _noise(rng, out_w, out_h, out_w // 3, out_h // 3) * 2.2
        papered = small + (grain + tooth)[..., None]
        # Gouache dries matte: lift the darkest darks a touch.
        papered = 10.0 + papered * (245.0 / 255.0)
        return Image.fromarray(np.clip(papered, 0, 255).astype(np.uint8), "RGB")


def smooth(points: Sequence[Point], steps: int = 8) -> list[Point]:
    """Catmull-Rom spline through the points."""
    if len(points) < 3:
        return list(points)
    pts = [points[0], *points, points[-1]]
    out: list[Point] = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(
                (
                    0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                    0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
                )
            )
    out.append(points[-1])
    return out
