"""Four limited palettes, one per time of day. Gouache posters live on few colours."""

from __future__ import annotations

from dataclasses import dataclass

from app.postcard.paint import RGB, hex_rgb


@dataclass(frozen=True)
class Palette:
    sky: tuple[RGB, RGB, RGB, RGB]  # top to horizon
    sun: RGB
    cloud: RGB
    far: RGB
    mid: RGB
    near: RGB
    ground: RGB
    path: RGB
    dark: RGB
    light: RGB
    accent: RGB
    water: RGB
    foam: RGB
    walls: tuple[RGB, RGB, RGB, RGB]
    roof: RGB
    window: RGB
    is_dark: bool


def _p(a: str, b: str, c: str, d: str) -> tuple[RGB, RGB, RGB, RGB]:
    return (hex_rgb(a), hex_rgb(b), hex_rgb(c), hex_rgb(d))


PALETTES: dict[str, Palette] = {
    "dawn": Palette(
        sky=_p("#8fb0c2", "#c9c3cf", "#f2c9a8", "#f8e2bd"),
        sun=hex_rgb("#f6a56a"), cloud=hex_rgb("#fbeada"), far=hex_rgb("#b3a6c4"), mid=hex_rgb("#8389ad"),
        near=hex_rgb("#56688d"), ground=hex_rgb("#d9a77c"), path=hex_rgb("#f1d3a9"), dark=hex_rgb("#2c3550"),
        light=hex_rgb("#fff3d2"), accent=hex_rgb("#e2583a"), water=hex_rgb("#93b9c6"), foam=hex_rgb("#f4ede0"),
        walls=_p("#f3dcc2", "#e7b99a", "#c9a3b4", "#a9b9c9"),
        roof=hex_rgb("#b5674f"), window=hex_rgb("#59678a"), is_dark=False,
    ),
    "day": Palette(
        sky=_p("#4a9cc0", "#73b6cf", "#a6d2d9", "#e3eeda"),
        sun=hex_rgb("#f8d368"), cloud=hex_rgb("#fdf6e4"), far=hex_rgb("#86b5ad"), mid=hex_rgb("#559b82"),
        near=hex_rgb("#2f7262"), ground=hex_rgb("#e6c684"), path=hex_rgb("#f5e3b6"), dark=hex_rgb("#1f3b4d"),
        light=hex_rgb("#fff8df"), accent=hex_rgb("#e2583a"), water=hex_rgb("#2f86a8"), foam=hex_rgb("#f6f1e1"),
        walls=_p("#f6ead0", "#f0c98f", "#e59f7a", "#b9d3cf"),
        roof=hex_rgb("#c8614a"), window=hex_rgb("#33586b"), is_dark=False,
    ),
    "dusk": Palette(
        sky=_p("#4d4276", "#93507e", "#d9634a", "#f3a85c"),
        sun=hex_rgb("#fbe09b"), cloud=hex_rgb("#e98e6c"), far=hex_rgb("#7d5183"), mid=hex_rgb("#583b6a"),
        near=hex_rgb("#342c55"), ground=hex_rgb("#46365c"), path=hex_rgb("#8a5a78"), dark=hex_rgb("#1c1b3b"),
        light=hex_rgb("#ffe39c"), accent=hex_rgb("#ffb347"), water=hex_rgb("#6f4f93"), foam=hex_rgb("#f6c08a"),
        walls=_p("#6c4a7a", "#8a5676", "#4c3d6c", "#a8607a"),
        roof=hex_rgb("#2c2850"), window=hex_rgb("#ffd98a"), is_dark=True,
    ),
    "night": Palette(
        sky=_p("#101c40", "#172a57", "#21386b", "#31507f"),
        sun=hex_rgb("#f5f0d8"), cloud=hex_rgb("#3a5387"), far=hex_rgb("#26386a"), mid=hex_rgb("#1b2b55"),
        near=hex_rgb("#132043"), ground=hex_rgb("#17264c"), path=hex_rgb("#2c4172"), dark=hex_rgb("#0a1128"),
        light=hex_rgb("#ffe08f"), accent=hex_rgb("#f2c14e"), water=hex_rgb("#1c3b6d"), foam=hex_rgb("#7f9ccb"),
        walls=_p("#22366a", "#2b4279", "#1c2d5a", "#33487c"),
        roof=hex_rgb("#0e1836"), window=hex_rgb("#ffd97a"), is_dark=True,
    ),
}
