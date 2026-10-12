"""Step 1 of the pipeline: any browser recording in, a 10 s mono clip out.

Decoding uses PyAV, which carries its own FFmpeg libraries, so nothing has to
be installed on the host. Two renditions come out of the same samples:

- analysis: exactly 160,000 float32 samples at 16 kHz, the tagger's input
- playback: a 64 kbit/s mono MP3 at 32 kHz, the only audio that is stored

16 kHz is what the model wants but it makes rain sound like a telephone, so
the stored clip keeps twice the bandwidth.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from fractions import Fraction

import av
import numpy as np
from av.audio.resampler import AudioResampler

ANALYSIS_RATE = 16_000
PLAYBACK_RATE = 32_000
TARGET_RMS_DBFS = -23.0
MAX_GAIN_DB = 36.0
SILENCE_RMS_DBFS = -62.0
PEAK_CEILING = 0.89  # about -1 dBFS


class ClipError(ValueError):
    """The upload cannot become a postcard. `code` is stable; `message` is shown to people."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Clip:
    analysis: np.ndarray  # float32, 16 kHz mono, exactly clip_seconds long
    playback_mp3: bytes
    source_seconds: float
    gain_db: float


def decode(data: bytes, *, rate: int, max_seconds: float) -> np.ndarray:
    """Decode any container FFmpeg understands to mono float32 at `rate`."""
    try:
        container = av.open(io.BytesIO(data), mode="r")
    except (av.error.FFmpegError, ValueError, IndexError) as exc:
        raise ClipError("unreadable_audio", "We could not read that recording. Please try again.") from exc
    with container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise ClipError("unreadable_audio", "That file has no audio in it.")
        resampler = AudioResampler(format="flt", layout="mono", rate=rate)
        limit = int(max_seconds * rate)
        chunks: list[np.ndarray] = []
        total = 0
        try:
            for frame in container.decode(stream):
                if not isinstance(frame, av.AudioFrame):
                    continue
                for out in resampler.resample(frame):
                    block = out.to_ndarray().reshape(-1)
                    chunks.append(block)
                    total += block.size
                if total >= limit:
                    break
            if total < limit:
                for out in resampler.resample(None):
                    chunks.append(out.to_ndarray().reshape(-1))
        except (av.error.FFmpegError, ValueError) as exc:
            if not chunks:
                raise ClipError("unreadable_audio", "We could not read that recording. Please try again.") from exc
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32, copy=False)[:limit]


def rms_dbfs(samples: np.ndarray) -> float:
    if samples.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    return 20.0 * float(np.log10(max(rms, 1e-6)))


def fit_length(samples: np.ndarray, length: int, rate: int) -> np.ndarray:
    """Trim to `length`, or pad the tail with silence after a short fade out."""
    if samples.size >= length:
        return samples[:length].copy()
    out = np.zeros(length, dtype=np.float32)
    out[: samples.size] = samples
    fade = min(samples.size, rate // 50)
    if fade:
        out[samples.size - fade : samples.size] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return out


def loudness_gain(samples: np.ndarray) -> float:
    """Linear gain that brings the clip to the target loudness without clipping."""
    level = rms_dbfs(samples)
    gain_db = min(TARGET_RMS_DBFS - level, MAX_GAIN_DB)
    gain = float(10.0 ** (gain_db / 20.0))
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak * gain > PEAK_CEILING:
        gain = PEAK_CEILING / peak
    return gain


def encode_mp3(samples: np.ndarray, rate: int, *, bit_rate: int = 64_000) -> bytes:
    buffer = io.BytesIO()
    with av.open(buffer, mode="w", format="mp3") as out:
        stream = out.add_stream("libmp3lame", rate=rate)
        stream.bit_rate = bit_rate
        stream.layout = "mono"
        stream.time_base = Fraction(1, rate)
        pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(pcm, format="s16", layout="mono")
        frame.sample_rate = rate
        frame.pts = 0
        resampler = AudioResampler(format=stream.format, layout="mono", rate=rate, frame_size=stream.frame_size or 1152)
        for chunk in resampler.resample(frame):
            out.mux(stream.encode(chunk))
        for chunk in resampler.resample(None):
            out.mux(stream.encode(chunk))
        out.mux(stream.encode(None))
    return buffer.getvalue()


def prepare_clip(data: bytes, *, clip_seconds: float = 10.0, min_seconds: float = 8.0) -> Clip:
    """Decode, trim, level and encode an upload. Raises ClipError with a message for the user."""
    wide = decode(data, rate=PLAYBACK_RATE, max_seconds=clip_seconds)
    source_seconds = wide.size / PLAYBACK_RATE
    if source_seconds < min_seconds:
        raise ClipError(
            "too_short",
            f"That recording is {source_seconds:.1f} seconds long. A postcard needs the full {clip_seconds:.0f}.",
        )
    wide = fit_length(wide, int(clip_seconds * PLAYBACK_RATE), PLAYBACK_RATE)
    wide = wide - float(np.mean(wide))  # remove DC offset from cheap microphones
    if rms_dbfs(wide) < SILENCE_RMS_DBFS:
        raise ClipError("silent", "We could not hear anything. Check your microphone and try again.")

    gain = loudness_gain(wide)
    wide = wide * gain

    # Same samples at 16 kHz for the tagger. Decimating by two after a
    # windowed-sinc low pass is exact enough and keeps both renditions aligned.
    analysis = _halve_rate(wide)
    analysis = fit_length(analysis, int(clip_seconds * ANALYSIS_RATE), ANALYSIS_RATE)
    # Dropping everything above 8 kHz can take 3 dB off a hissy clip, so level this copy again.
    analysis = analysis * loudness_gain(analysis)
    return Clip(
        analysis=analysis.astype(np.float32),
        playback_mp3=encode_mp3(wide, PLAYBACK_RATE),
        source_seconds=source_seconds,
        gain_db=20.0 * float(np.log10(max(gain, 1e-9))),
    )


def _halve_rate(samples: np.ndarray, taps: int = 127) -> np.ndarray:
    n = np.arange(taps) - (taps - 1) / 2.0
    kernel = 0.5 * np.sinc(0.5 * n) * np.hamming(taps)  # cutoff at a quarter of the input rate
    kernel /= kernel.sum()
    return np.convolve(samples, kernel, mode="same")[::2].astype(np.float32)
