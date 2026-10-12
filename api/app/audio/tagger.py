"""Steps 2 to 4 of the pipeline: labels, a speech probability and an embedding.

The tagger is YAMNet (MobileNet v1 trained on AudioSet, 521 classes, Apache
2.0), run from its TFLite file with LiteRT. It was chosen over PANNs because
the whole thing is a 16 MB file and a 13 MB wheel that installs on Apple
Silicon and Linux arm64 with Python 3.12, where PANNs brings PyTorch and a
checkpoint of 80 to 320 MB. One call on a 10 s clip gives 20 frames of class
scores and 20 embeddings of 1,024 numbers, which is the layer just before
the classifier.
"""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
EMBEDDING_DIM = 1024

# AudioSet classes that mean a person is talking. "Speech" is the parent, so
# it is nearly always the largest, but a whisper or a child can outscore it.
SPEECH_CLASSES = ("Speech", "Child speech, kid speaking", "Conversation", "Narration, monologue", "Whispering")


@dataclass(frozen=True)
class Label:
    name: str
    score: float


@dataclass(frozen=True)
class Tagging:
    labels: list[Label]  # every class above the floor, best first
    speech_probability: float
    embedding: np.ndarray  # float32, unit length, EMBEDDING_DIM long


class AudioTagger(Protocol):
    def tag(self, samples: np.ndarray) -> Tagging: ...


class YamnetTagger:
    """YAMNet through LiteRT. Thread safe: the interpreter is guarded by a lock."""

    def __init__(self, model_path: Path | None = None, class_map_path: Path | None = None) -> None:
        from ai_edge_litert.interpreter import Interpreter

        model = model_path or DATA_DIR / "yamnet.tflite"
        class_map = class_map_path or DATA_DIR / "yamnet_class_map.csv"
        with class_map.open(newline="", encoding="utf-8") as handle:
            self.class_names: list[str] = [row["display_name"] for row in csv.DictReader(handle)]
        self._speech_index = [self.class_names.index(name) for name in SPEECH_CLASSES]
        self._interpreter = Interpreter(model_path=str(model))
        self._input = self._interpreter.get_input_details()[0]["index"]
        outputs = self._interpreter.get_output_details()
        self._scores = next(o["index"] for o in outputs if o["shape"][-1] == len(self.class_names))
        self._embeddings = next(o["index"] for o in outputs if o["shape"][-1] == EMBEDDING_DIM)
        self._length = 0
        self._lock = threading.Lock()

    def frames(self, samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Per-frame class scores (frames x 521) and embeddings (frames x 1024)."""
        wave = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1)
        with self._lock:
            if wave.size != self._length:
                self._interpreter.resize_tensor_input(self._input, [wave.size], strict=False)
                self._interpreter.allocate_tensors()
                self._length = wave.size
            self._interpreter.set_tensor(self._input, wave)
            self._interpreter.invoke()
            scores = self._interpreter.get_tensor(self._scores).copy()
            embeddings = self._interpreter.get_tensor(self._embeddings).copy()
        return scores, embeddings

    def tag(self, samples: np.ndarray, *, floor: float = 0.02, limit: int = 12) -> Tagging:
        scores, embeddings = self.frames(samples)
        clip_scores = scores.mean(axis=0)
        order = np.argsort(clip_scores)[::-1][:limit]
        labels = [
            Label(name=self.class_names[i], score=round(float(clip_scores[i]), 4))
            for i in order
            if clip_scores[i] >= floor
        ]
        return Tagging(
            labels=labels,
            speech_probability=speech_probability(scores, self._speech_index),
            embedding=pool_embedding(embeddings),
        )


def speech_probability(frame_scores: np.ndarray, speech_index: list[int]) -> float:
    """Share of the clip that is someone talking.

    Per frame, take the strongest of the speech classes; then average over
    the frames. A clip that is speech for 7 of its 10 seconds scores about
    0.7, a passing "hello" in a rain recording scores about 0.1.
    """
    if frame_scores.size == 0:
        return 0.0
    per_frame = frame_scores[:, speech_index].max(axis=1)
    return round(float(np.clip(per_frame.mean(), 0.0, 1.0)), 4)


def pool_embedding(frame_embeddings: np.ndarray) -> np.ndarray:
    """Mean over frames, scaled to unit length so cosine distance is a dot product."""
    pooled = frame_embeddings.mean(axis=0).astype(np.float32)
    norm = float(np.linalg.norm(pooled))
    if norm == 0.0:
        return pooled
    return pooled / norm
