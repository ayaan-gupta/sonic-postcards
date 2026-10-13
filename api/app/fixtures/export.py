"""Writes fixture clips as WAV files, for feeding a browser's fake microphone.

    python -m app.fixtures.export <directory>

Chromium can play a WAV file into getUserMedia, which is how the end-to-end
script and the demo recording get real audio through the real recorder.
"""

from __future__ import annotations

import sys
from pathlib import Path

from app.audio.clip import decode
from app.audio.wav import wav_bytes
from app.fixtures import synth

SPEECH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "speech" / "monologue_chrome.webm"


def export(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for kind in ("birds", "waves", "rain", "crickets"):
        path = directory / f"{kind}.wav"
        path.write_bytes(wav_bytes(synth.synthesise(kind, 7), synth.RATE))
        written.append(path)
    if SPEECH.is_file():
        path = directory / "speech.wav"
        path.write_bytes(wav_bytes(decode(SPEECH.read_bytes(), rate=48_000, max_seconds=12.0), 48_000))
        written.append(path)
    return written


if __name__ == "__main__":
    for item in export(Path(sys.argv[1] if len(sys.argv) > 1 else ".run/fixtures")):
        print(item)
