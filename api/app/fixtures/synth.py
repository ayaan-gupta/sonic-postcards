"""Ambient sounds synthesised from noise and sine waves.

There is no field recording in this repository. These clips stand in for
them in tests and in the demo seed: every one is a pure function of its seed,
so nothing binary has to be committed. Each is named after what the real
tagger hears in it, which is not always what it was first written to be.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

RATE = 32_000
SECONDS = 10.0


def _n(seconds: float = SECONDS) -> int:
    return int(seconds * RATE)


def _fft_filter(signal: np.ndarray, shape: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Filter by multiplying the spectrum with `shape(frequency_hz)`."""
    spectrum = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(signal.size, 1.0 / RATE)
    return np.fft.irfft(spectrum * shape(freqs), n=signal.size)


def _band(signal: np.ndarray, low: float, high: float, order: float = 4.0) -> np.ndarray:
    def shape(f: np.ndarray) -> np.ndarray:
        hp = 1.0 / (1.0 + (low / np.maximum(f, 1e-3)) ** (2 * order)) if low > 0 else 1.0
        lp = 1.0 / (1.0 + (f / high) ** (2 * order))
        return np.sqrt(hp * lp)

    return _fft_filter(signal, shape)


def _smooth_random(rng: np.random.Generator, n: int, rate_hz: float) -> np.ndarray:
    """A slow random curve between 0 and 1 with roughly `rate_hz` wiggles per second."""
    points = max(4, int(n / RATE * rate_hz) + 3)
    knots = rng.random(points)
    x = np.linspace(0, points - 1, n)
    left = np.floor(x).astype(int).clip(0, points - 2)
    t = x - left
    t = t * t * (3 - 2 * t)
    curve: np.ndarray = knots[left] * (1 - t) + knots[left + 1] * t
    return curve


def _norm(signal: np.ndarray, peak: float = 0.5) -> np.ndarray:
    top = float(np.max(np.abs(signal))) or 1.0
    return (signal / top * peak).astype(np.float32)


def rain(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _n()
    hiss = _band(rng.standard_normal(n), 900, 9000, 2) * (0.75 + 0.25 * _smooth_random(rng, n, 0.5))
    drops = np.zeros(n)
    for start in rng.integers(0, n - 400, size=2600):
        length = int(rng.integers(40, 220))
        drops[start : start + length] += rng.standard_normal(length) * np.exp(-np.arange(length) / (length / 4)) * rng.random()
    drops = _band(drops, 1500, 12000, 2)
    patter = _band(rng.standard_normal(n), 150, 600, 2) * 0.25
    return _norm(hiss + 1.6 * drops + patter)


def birds(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _n()
    out = _band(rng.standard_normal(n), 200, 3000, 1) * 0.01
    t_all = np.arange(n) / RATE
    for _ in range(int(rng.integers(30, 44))):
        start = rng.uniform(0, SECONDS - 0.6)
        base = rng.uniform(2400, 5200)
        notes = int(rng.integers(2, 7))
        for k in range(notes):
            t0 = start + k * rng.uniform(0.07, 0.13)
            dur = rng.uniform(0.04, 0.11)
            idx = (t_all >= t0) & (t_all < t0 + dur)
            tt = t_all[idx] - t0
            sweep = base * (1 + rng.uniform(-0.25, 0.45) * tt / dur) + 300 * np.sin(2 * np.pi * rng.uniform(25, 60) * tt)
            phase = 2 * np.pi * np.cumsum(sweep) / RATE
            env = np.sin(np.pi * tt / dur) ** 2
            out[idx] += env * (np.sin(phase) + 0.3 * np.sin(2 * phase)) * rng.uniform(0.3, 1.0)
    return _norm(out)


def traffic(seed: int = 0) -> np.ndarray:
    """Low rumble under a resonant band of noise that sweeps as something drives by.

    Written as a first attempt at wind. YAMNet calls it "Vehicle", so that is what it is.
    """
    rng = np.random.default_rng(seed)
    n = _n()
    gust = _smooth_random(rng, n, 0.7) ** 1.5
    low = _band(rng.standard_normal(n), 40, 420, 2) * (0.35 + gust)
    whistle = np.zeros(n)
    block = 2048
    noise = rng.standard_normal(n + block)
    centre = 500 + 900 * _smooth_random(rng, n, 0.5)
    for start in range(0, n - block, block // 2):
        f0 = float(centre[start])
        seg = _band(noise[start : start + block], f0 * 0.85, f0 * 1.15, 3)
        whistle[start : start + block] += seg * np.hanning(block)
    return _norm(low + 0.9 * whistle * (0.2 + gust))


def waves(seed: int = 0) -> np.ndarray:
    """Mid-band noise that swells and falls back every few seconds, with a slow flutter on top."""
    rng = np.random.default_rng(seed)
    n = _n()
    swell = 0.25 + 0.75 * _smooth_random(rng, n, 0.5) ** 1.5
    wash = _band(rng.standard_normal(n), 80, 700, 1.5) * swell * (0.7 + 0.3 * _smooth_random(rng, n, 3.0))
    undertow = _band(rng.standard_normal(n), 20, 120, 2) * swell * 0.6 * (0.4 + 0.6 * _smooth_random(rng, n, 12.0))
    return _norm(wash + undertow)


def wind(seed: int = 0) -> np.ndarray:
    """Wind is mostly the microphone being buffeted: noise below 250 Hz with a fast flutter."""
    rng = np.random.default_rng(seed)
    n = _n()
    gust = 0.2 + 0.8 * _smooth_random(rng, n, 1.2) ** 1.5
    return _norm(_band(rng.standard_normal(n), 20, 250, 2) * gust * (0.3 + 0.7 * _smooth_random(rng, n, 20.0)))


def stream(seed: int = 0) -> np.ndarray:
    """Four bands of noise, each flickering on its own, plus rising-pitch bubbles."""
    rng = np.random.default_rng(seed)
    n = _n()
    t_all = np.arange(n) / RATE
    out = np.zeros(n)
    for low, high in ((300, 900), (900, 2200), (2200, 5000), (5000, 10000)):
        out += _band(rng.standard_normal(n), low, high, 2) * (0.4 + 0.6 * _smooth_random(rng, n, 14.0)) * (1.0 if low < 3000 else 0.5)
    for _ in range(500):
        t0 = rng.uniform(0, SECONDS - 0.08)
        dur = rng.uniform(0.01, 0.04)
        i0 = int(t0 * RATE)
        i1 = i0 + int(dur * RATE)
        tt = t_all[i0:i1] - t0
        f = rng.uniform(600, 3000) * (1 + rng.uniform(0.3, 1.2) * tt / dur)
        out[i0:i1] += np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-tt / (dur / 3)) * rng.uniform(0.3, 1.0) * 1.5
    return _norm(out)


def chimes(seed: int = 0) -> np.ndarray:
    """Small bells: ten inharmonic partials per strike, a click at the attack, quick decay."""
    rng = np.random.default_rng(seed)
    n = _n()
    t = np.arange(n) / RATE
    out = _band(rng.standard_normal(n), 100, 2000, 1) * 0.003
    partials = ((0.5, 0.6, 0.25), (1.0, 1.0, 0.5), (1.2, 0.7, 0.7), (1.5, 0.5, 0.9), (2.0, 0.8, 1.0), (2.5, 0.35, 1.6),
                (3.0, 0.3, 2.0), (4.0, 0.25, 2.6), (5.33, 0.15, 3.4), (6.7, 0.1, 4.5))
    strike = 0.15
    while strike < SECONDS - 0.3:
        tt = np.clip(t - strike, 0, None)
        on = t >= strike
        for ratio, amp, damping in partials:
            out += on * amp * np.sin(2 * np.pi * 523.0 * ratio * (1 + rng.uniform(-0.004, 0.004)) * tt) * np.exp(-tt * 1.6 * damping)
        length = int(0.012 * RATE)
        i0 = int(strike * RATE)
        out[i0 : i0 + length] += _band(rng.standard_normal(length), 1500, 9000, 1) * np.exp(-np.arange(length) / (length / 3)) * 0.8
        strike += rng.uniform(0.5, 0.9)
    return _norm(out)


def crickets(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _n()
    t = np.arange(n) / RATE
    out = _band(rng.standard_normal(n), 200, 2500, 1) * 0.015
    for _ in range(5):
        carrier = rng.uniform(3900, 5200)
        pulse = rng.uniform(22, 34)
        chirp = rng.uniform(1.6, 2.6)
        phase = rng.uniform(0, 1)
        gate = ((t * chirp + phase) % 1.0) < 0.42
        pulses = np.clip(np.sin(2 * np.pi * pulse * t), 0, None) ** 2
        out += gate * pulses * np.sin(2 * np.pi * carrier * t) * rng.uniform(0.4, 1.0)
    return _norm(out)


def plucked_strings(seed: int = 0) -> np.ndarray:
    """A slow fingerpicked pattern, Karplus-Strong strings."""
    rng = np.random.default_rng(seed)
    n = _n()
    out = np.zeros(n)
    scale = [196.0, 220.0, 246.9, 293.7, 329.6, 392.0, 440.0, 493.9, 587.3]
    t0 = 0.1
    while t0 < SECONDS - 1.2:
        freq = float(rng.choice(scale))
        period = int(RATE / freq)
        length = int(1.6 * RATE)
        buf = rng.uniform(-1, 1, period)
        note = np.empty(length)
        for i in range(0, length, period):
            chunk = min(period, length - i)
            note[i : i + chunk] = buf[:chunk]
            buf = 0.996 * 0.5 * (buf + np.roll(buf, 1))
        i0 = int(t0 * RATE)
        end = min(n, i0 + length)
        out[i0:end] += note[: end - i0] * rng.uniform(0.5, 1.0)
        t0 += float(rng.choice([0.25, 0.25, 0.5]))
    return _norm(out)


def fire(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _n()
    roar = _band(rng.standard_normal(n), 60, 900, 1.5) * (0.5 + 0.5 * _smooth_random(rng, n, 3.0)) * 0.5
    crackle = np.zeros(n)
    for start in rng.integers(0, n - 300, size=420):
        length = int(rng.integers(20, 260))
        crackle[start : start + length] += rng.standard_normal(length) * np.exp(-np.arange(length) / (length / 6)) * rng.random() ** 2 * 3
    return _norm(roar + _band(crackle, 800, 9000, 1))


def thunderstorm(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _n()
    t = np.arange(n) / RATE
    out = rain(seed + 1000).astype(np.float64)
    for centre in (rng.uniform(1.5, 3.5), rng.uniform(6.0, 8.0)):
        env = np.where(t > centre, np.exp(-(t - centre) / 1.3), 0.0) * (0.6 + 0.4 * _smooth_random(rng, n, 6.0))
        out += 2.5 * env * _band(rng.standard_normal(n), 20, 180, 2)
    return _norm(out)


SOUNDS: dict[str, Callable[[int], np.ndarray]] = {
    "rain": rain,
    "birds": birds,
    "traffic": traffic,
    "waves": waves,
    "wind": wind,
    "stream": stream,
    "chimes": chimes,
    "crickets": crickets,
    "strings": plucked_strings,
    "fire": fire,
    "thunderstorm": thunderstorm,
}

# What YAMNet makes of each sound, measured. A test holds it to this.
EXPECTED_MOTIF: dict[str, str] = {
    "rain": "rain",
    "birds": "birds",
    "traffic": "traffic",
    "waves": "waves",
    "wind": "wind",
    "stream": "water",
    "chimes": "music",
    "crickets": "insects",
    "strings": "music",
    "fire": "fire",
    "thunderstorm": "storm",
}


def synthesise(kind: str, seed: int = 0) -> np.ndarray:
    """Ten seconds of `kind` at 32 kHz mono, float32 in [-1, 1]."""
    return SOUNDS[kind](seed)
