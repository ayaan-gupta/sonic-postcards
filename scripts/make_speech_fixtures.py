"""Records the speech fixtures for the rejection tests. macOS only (uses `say`).

    api/.venv/bin/python scripts/make_speech_fixtures.py

The outputs are committed under api/tests/fixtures/speech so the tests run
anywhere. The containers mirror what browsers really upload: Chrome and
Firefox record Opus in WebM, Safari records AAC in MP4.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path

import av
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.audio.clip import decode  # noqa: E402
from app.fixtures import synth  # noqa: E402

OUT = ROOT / "api" / "tests" / "fixtures" / "speech"
RATE = 48_000

MONOLOGUE = (
    "I am standing at the corner by the bakery and I thought I would describe what is going on. "
    "A woman just walked past with two dogs, the lights changed, and somebody across the road is waving. "
    "It has been a long day and I am mostly thinking about dinner, to be honest with you."
)
CHAT = (
    "So anyway, I told him the meeting was moved to Thursday, and he said that was fine. "
    "Then he asked whether we still needed the big room, and I said probably not, there are only four of us. "
    "We can sort the rest out tomorrow morning."
)


def say(text: str, voice: str, rate_wpm: int = 175) -> np.ndarray:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "speech.aiff"
        subprocess.run(["say", "-v", voice, "-r", str(rate_wpm), "-o", str(path), text], check=True)
        return decode(path.read_bytes(), rate=RATE, max_seconds=30.0)


def fit(samples: np.ndarray, seconds: float) -> np.ndarray:
    length = int(seconds * RATE)
    if samples.size >= length:
        return samples[:length]
    return np.concatenate([samples, np.zeros(length - samples.size, dtype=np.float32)])


def encode(samples: np.ndarray, container: str, codec: str, bit_rate: int) -> bytes:
    buffer = io.BytesIO()
    with av.open(buffer, mode="w", format=container) as out:
        stream = out.add_stream(codec, rate=RATE)
        stream.bit_rate = bit_rate
        stream.layout = "mono"
        pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(pcm, format="s16", layout="mono")
        frame.sample_rate = RATE
        resampler = av.AudioResampler(format=stream.format, layout="mono", rate=RATE, frame_size=stream.frame_size or 960)
        for chunk in resampler.resample(frame):
            out.mux(stream.encode(chunk))
        for chunk in resampler.resample(None):
            out.mux(stream.encode(chunk))
        out.mux(stream.encode(None))
    return buffer.getvalue()


def upsample(samples: np.ndarray, src_rate: int) -> np.ndarray:
    x = np.arange(int(samples.size * RATE / src_rate)) * src_rate / RATE
    return np.interp(x, np.arange(samples.size), samples).astype(np.float32)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rain = np.resize(upsample(synth.rain(3), synth.RATE), int(10.5 * RATE))  # tiled to the fixture length

    monologue = fit(say(MONOLOGUE, "Samantha"), 10.5)
    (OUT / "monologue_chrome.webm").write_bytes(encode(monologue, "webm", "libopus", 32_000))

    chat = fit(say(CHAT, "Daniel"), 10.5)
    (OUT / "chat_safari.m4a").write_bytes(encode(chat, "mp4", "aac", 48_000))

    # Speech in the foreground with rain behind it: still mostly speech.
    over_rain = fit(say(MONOLOGUE, "Karen"), 10.5)
    mixed = over_rain * 0.8 + rain[: over_rain.size] * 0.12
    (OUT / "speech_over_rain.webm").write_bytes(encode(mixed, "webm", "libopus", 32_000))

    # Rain with two words called out once: not mostly speech, must be accepted.
    hello = say("Hello there.", "Samantha")
    ambient = rain.copy() * 0.6
    ambient[int(4.0 * RATE) : int(4.0 * RATE) + hello.size] += hello * 0.25
    (OUT / "rain_with_a_hello.webm").write_bytes(encode(ambient, "webm", "libopus", 32_000))

    for path in sorted(OUT.iterdir()):
        print(f"{path.name}: {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
