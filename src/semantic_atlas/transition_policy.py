from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .alignment import RoutedTransport, TransitionAtlas, TransportedVector
from .geometry import normalize


@dataclass(slots=True, frozen=True)
class TransitionValidation:
    mode: str
    local_score: float
    global_score: float
    local_pair_cosine: float
    global_pair_cosine: float
    local_neighborhood_jaccard: float
    global_neighborhood_jaccard: float
    validation_size: int
    min_local_gain: float

    @property
    def selected_score(self) -> float:
        return self.local_score if self.mode == "local" else self.global_score

    @property
    def local_gain(self) -> float:
        return self.local_score - self.global_score


def _knn_sets(vectors: np.ndarray, k: int) -> list[set[int]]:
    x = normalize(np.asarray(vectors, dtype=np.float32))
    if len(x) <= 1:
        return [set() for _ in range(len(x))]
    sims = x @ x.T
    np.fill_diagonal(sims, -np.inf)
    take = max(1, min(int(k), len(x) - 1))
    order = np.argsort(-sims, axis=1)[:, :take]
    return [set(map(int, row)) for row in order]


def _jaccard_neighbors(a: np.ndarray, b: np.ndarray, k: int) -> float:
    left, right = _knn_sets(a, k), _knn_sets(b, k)
    values = []
    for x, y in zip(left, right):
        union = x | y
        values.append(1.0 if not union else len(x & y) / len(union))
    return float(np.mean(values)) if values else 0.0


def _score(mapped: np.ndarray, target: np.ndarray, k: int) -> tuple[float, float, float]:
    mapped = normalize(np.asarray(mapped, dtype=np.float32))
    target = normalize(np.asarray(target, dtype=np.float32))
    pair_cos = float(np.mean(np.sum(mapped * target, axis=1)))
    jac = _jaccard_neighbors(mapped, target, k) if len(mapped) > 1 else 1.0
    score = 0.70 * max(0.0, pair_cos) + 0.30 * jac
    return float(score), pair_cos, jac


class EvidenceGatedTransition:
    """Use local transition complexity only when held-out anchors justify it.

    This wrapper deliberately treats a global map as the baseline. A local
    atlas is selected only when it improves a fixed held-out quality score by
    at least ``min_local_gain``. The final serving atlas is then refit on all
    paired anchors, but the global/local decision remains frozen from the
    independent selection split.

    The class implements the small interface expected by ``TransitionGraph``:
    ``source_space``, ``target_space``, ``confidence`` and ``map``.
    """

    def __init__(self, atlas: TransitionAtlas, validation: TransitionValidation) -> None:
        self.atlas = atlas
        self.validation = validation
        self.source_space = atlas.source_space
        self.target_space = atlas.target_space

    @property
    def confidence(self) -> float:
        return float(np.clip(self.validation.selected_score, 0.0, 1.0))

    @classmethod
    def fit(
        cls,
        source_space: str,
        target_space: str,
        source_anchors: np.ndarray,
        target_anchors: np.ndarray,
        *,
        chart_size: int = 32,
        chart_overlap: float = 1.5,
        min_chart_anchors: int = 8,
        temperature: float = 0.08,
        selection_fraction: float = 0.20,
        selection_seed: int = 43,
        min_local_gain: float = 0.02,
    ) -> "EvidenceGatedTransition":
        x = normalize(np.asarray(source_anchors, dtype=np.float32))
        y = normalize(np.asarray(target_anchors, dtype=np.float32))
        if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
            raise ValueError("source and target anchors must be paired 2-D arrays")
        if len(x) < 10:
            serving = TransitionAtlas.fit(
                source_space,
                target_space,
                x,
                y,
                chart_size=chart_size,
                chart_overlap=chart_overlap,
                min_chart_anchors=min_chart_anchors,
                temperature=temperature,
            )
            validation = TransitionValidation("global", 0.0, serving.confidence, 0.0, serving.fit_diagnostics.mean_pair_cosine, 0.0, serving.fit_diagnostics.neighborhood_jaccard, 0, float(min_local_gain))
            return cls(serving, validation)

        rng = np.random.default_rng(int(selection_seed))
        order = rng.permutation(len(x))
        val_n = max(4, min(len(x) - 4, int(round(len(x) * float(np.clip(selection_fraction, 0.10, 0.45))))))
        val_idx, train_idx = order[:val_n], order[val_n:]

        selector = TransitionAtlas.fit(
            source_space,
            target_space,
            x[train_idx],
            y[train_idx],
            chart_size=chart_size,
            chart_overlap=chart_overlap,
            min_chart_anchors=min_chart_anchors,
            temperature=temperature,
            validation_fraction=0.0,
        )
        local_mapped = np.vstack([selector.map(vector).vector for vector in x[val_idx]])
        global_mapped = np.vstack([selector.global_map.map(vector) for vector in x[val_idx]])
        k = min(10, max(1, val_n - 1))
        local_score, local_cos, local_jac = _score(local_mapped, y[val_idx], k)
        global_score, global_cos, global_jac = _score(global_mapped, y[val_idx], k)
        mode = "local" if local_score >= global_score + float(min_local_gain) else "global"

        serving = TransitionAtlas.fit(
            source_space,
            target_space,
            x,
            y,
            chart_size=chart_size,
            chart_overlap=chart_overlap,
            min_chart_anchors=min_chart_anchors,
            temperature=temperature,
        )
        validation = TransitionValidation(
            mode=mode,
            local_score=local_score,
            global_score=global_score,
            local_pair_cosine=local_cos,
            global_pair_cosine=global_cos,
            local_neighborhood_jaccard=local_jac,
            global_neighborhood_jaccard=global_jac,
            validation_size=val_n,
            min_local_gain=float(min_local_gain),
        )
        return cls(serving, validation)

    def map_local(self, vector: np.ndarray, *, probes: int = 2) -> TransportedVector:
        return self.atlas.map(vector, probes=probes)

    def map_global(self, vector: np.ndarray) -> TransportedVector:
        q = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        return TransportedVector(self.atlas.global_map.map(q), self.confidence, ())

    def map(self, vector: np.ndarray, *, probes: int = 2) -> TransportedVector:
        if self.validation.mode == "local":
            moved = self.map_local(vector, probes=probes)
            return TransportedVector(moved.vector, min(moved.confidence, self.confidence), moved.chart_ids)
        return self.map_global(vector)
