"""Minimal WAV writing for fixtures and tests. Reading goes through PyAV like everything else."""

from __future__ import annotations

import io
import wave

import numpy as np


def wav_bytes(samples: np.ndarray, rate: int) -> bytes:
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return buffer.getvalue()
