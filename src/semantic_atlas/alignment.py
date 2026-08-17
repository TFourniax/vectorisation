from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Sequence

import numpy as np

from .geometry import cosine_matrix, normalize

_EPS = 1e-9


@dataclass(slots=True)
class LinearTransition:
    source_mean: np.ndarray
    target_mean: np.ndarray
    matrix: np.ndarray
    scale: float
    source_centroid: np.ndarray
    quality: float
    support: int
    radius: float = 1.0
    validation_quality: float | None = None
    validation_support: int = 0

    def map(self, vector: np.ndarray) -> np.ndarray:
        x = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if x.shape[1] != self.matrix.shape[0]:
            raise ValueError("source vector dimensionality does not match transition")
        y = self.scale * ((x - self.source_mean) @ self.matrix) + self.target_mean
        return normalize(y)[0]


@dataclass(slots=True)
class TransitionDiagnostics:
    n: int
    mean_pair_cosine: float
    p10_pair_cosine: float
    pair_recall_at_1: float
    neighborhood_jaccard: float
    held_out: bool = False
    n_train: int = 0

    @property
    def confidence(self) -> float:
        c = 0.55 * max(0.0, self.mean_pair_cosine) + 0.45 * self.neighborhood_jaccard
        return float(np.clip(c, 0.0, 1.0))


@dataclass(slots=True)
class TransportedVector:
    vector: np.ndarray
    confidence: float
    chart_ids: tuple[int, ...]


@dataclass(slots=True)
class RoutedTransport:
    vector: np.ndarray
    confidence: float
    path: tuple[str, ...]
    chart_ids: tuple[int, ...]


def _fit_procrustes(source: np.ndarray, target: np.ndarray) -> LinearTransition:
    x = normalize(np.asarray(source, dtype=np.float32))
    y = normalize(np.asarray(target, dtype=np.float32))
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
        raise ValueError("source and target anchors must be paired 2-D arrays")
    if len(x) < 2:
        raise ValueError("at least two paired anchors are required")

    mx = x.mean(axis=0, keepdims=True)
    my = y.mean(axis=0, keepdims=True)
    xc = x - mx
    yc = y - my
    cross = xc.T @ yc
    u, singular, vt = np.linalg.svd(cross, full_matrices=False)
    matrix = (u @ vt).astype(np.float32)
    denom = float(np.sum(xc * xc))
    scale = float(np.sum(singular) / max(denom, _EPS))
    mapped = normalize(scale * (xc @ matrix) + my)
    quality = float(np.mean(np.sum(mapped * y, axis=1)))
    centroid = normalize(x.mean(axis=0, keepdims=True))[0]
    distance = 1.0 - cosine_matrix(x, centroid.reshape(1, -1))[:, 0]
    radius = float(np.max(distance)) * 1.05
    radius = max(radius, 1e-4)
    return LinearTransition(
        source_mean=mx[0].astype(np.float32),
        target_mean=my[0].astype(np.float32),
        matrix=matrix,
        scale=scale,
        source_centroid=centroid.astype(np.float32),
        quality=float(np.clip(quality, -1.0, 1.0)),
        support=len(x),
        radius=radius,
    )


def _knn_sets(vectors: np.ndarray, k: int) -> list[set[int]]:
    x = normalize(vectors)
    n = len(x)
    if n <= 1:
        return [set() for _ in range(n)]
    sims = x @ x.T
    np.fill_diagonal(sims, -np.inf)
    take = max(1, min(int(k), n - 1))
    order = np.argsort(-sims, axis=1)[:, :take]
    return [set(map(int, row)) for row in order]


def _mean_jaccard(a: list[set[int]], b: list[set[int]]) -> float:
    values: list[float] = []
    for left, right in zip(a, b):
        union = left | right
        values.append(1.0 if not union else len(left & right) / len(union))
    return float(np.mean(values)) if values else 0.0


def _copy_local_calibration(train_maps: Sequence[LinearTransition], serving_maps: Sequence[LinearTransition]) -> None:
    if not train_maps or not serving_maps:
        return
    train_centroids = np.vstack([m.source_centroid for m in train_maps])
    for model in serving_maps:
        sims = cosine_matrix(model.source_centroid.reshape(1, -1), train_centroids)[0]
        source = train_maps[int(np.argmax(sims))]
        model.validation_quality = source.validation_quality
        model.validation_support = source.validation_support


class TransitionAtlas:
    """Piecewise coordinate transition with held-out, locality-aware risk."""

    def __init__(
        self,
        source_space: str,
        target_space: str,
        global_map: LinearTransition,
        local_maps: Sequence[LinearTransition],
        fit_diagnostics: TransitionDiagnostics,
        temperature: float = 0.08,
    ) -> None:
        self.source_space = source_space
        self.target_space = target_space
        self.global_map = global_map
        self.local_maps = list(local_maps)
        self.fit_diagnostics = fit_diagnostics
        self.temperature = max(0.001, float(temperature))

    @property
    def confidence(self) -> float:
        return self.fit_diagnostics.confidence

    @staticmethod
    def _fit_components(
        x: np.ndarray,
        y: np.ndarray,
        *,
        chart_size: int,
        chart_overlap: float,
        min_chart_anchors: int,
    ) -> tuple[LinearTransition, list[LinearTransition]]:
        global_map = _fit_procrustes(x, y)
        target_charts = max(1, int(np.ceil(len(x) / max(2, int(chart_size)))))
        seeds = [0]
        min_dist = 1.0 - cosine_matrix(x, x[0:1])[:, 0]
        for _ in range(1, target_charts):
            idx = int(np.argmax(min_dist))
            seeds.append(idx)
            d = 1.0 - cosine_matrix(x, x[idx : idx + 1])[:, 0]
            min_dist = np.minimum(min_dist, d)

        local_maps: list[LinearTransition] = []
        take = min(
            len(x),
            max(
                int(min_chart_anchors),
                int(math.ceil(max(2, chart_size) * max(1.0, chart_overlap))),
            ),
        )
        for seed in seeds:
            dist = 1.0 - cosine_matrix(x, x[seed : seed + 1])[:, 0]
            members = np.argsort(dist)[:take]
            if len(members) >= 2:
                local_maps.append(_fit_procrustes(x[members], y[members]))
        return global_map, local_maps

    @staticmethod
    def _calibrate_local_maps(
        local_maps: Sequence[LinearTransition], source_validation: np.ndarray, target_validation: np.ndarray
    ) -> None:
        if not local_maps or len(source_validation) == 0:
            return
        centroids = np.vstack([m.source_centroid for m in local_maps])
        assignment = np.argmax(cosine_matrix(source_validation, centroids), axis=1)
        for cid, model in enumerate(local_maps):
            members = np.where(assignment == cid)[0]
            model.validation_support = int(len(members))
            if len(members) == 0:
                model.validation_quality = None
                continue
            mapped = np.vstack([model.map(source_validation[i]) for i in members])
            pair_cosine = np.sum(mapped * target_validation[members], axis=1)
            model.validation_quality = float(np.clip(np.quantile(pair_cosine, 0.10), 0.0, 1.0))

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
        validation_fraction: float = 0.2,
        validation_seed: int = 17,
    ) -> "TransitionAtlas":
        x = normalize(np.asarray(source_anchors, dtype=np.float32))
        y = normalize(np.asarray(target_anchors, dtype=np.float32))
        if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
            raise ValueError("source and target anchors must be paired 2-D arrays")
        if len(x) < 2:
            raise ValueError("at least two paired anchors are required")

        use_holdout = len(x) >= 10 and validation_fraction > 0.0
        diagnostics: TransitionDiagnostics
        train_local_maps: list[LinearTransition] = []
        if use_holdout:
            rng = np.random.default_rng(int(validation_seed))
            perm = rng.permutation(len(x))
            val_n = max(
                2,
                min(len(x) - 2, int(round(len(x) * min(0.45, validation_fraction)))),
            )
            val_idx, train_idx = perm[:val_n], perm[val_n:]
            g_train, train_local_maps = cls._fit_components(
                x[train_idx],
                y[train_idx],
                chart_size=chart_size,
                chart_overlap=chart_overlap,
                min_chart_anchors=min_chart_anchors,
            )
            evaluator = cls(
                source_space,
                target_space,
                g_train,
                train_local_maps,
                TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0),
                temperature,
            )
            diagnostics = evaluator.evaluate(
                x[val_idx], y[val_idx], k=min(10, max(1, val_n - 1))
            )
            diagnostics.held_out = True
            diagnostics.n_train = len(train_idx)
            cls._calibrate_local_maps(train_local_maps, x[val_idx], y[val_idx])
        else:
            diagnostics = TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0, False, len(x))

        global_map, local_maps = cls._fit_components(
            x,
            y,
            chart_size=chart_size,
            chart_overlap=chart_overlap,
            min_chart_anchors=min_chart_anchors,
        )
        if use_holdout:
            _copy_local_calibration(train_local_maps, local_maps)
        serving = cls(source_space, target_space, global_map, local_maps, diagnostics, temperature)
        if not use_holdout:
            diagnostics = serving.evaluate(x, y, k=min(10, max(1, len(x) - 1)))
            diagnostics.held_out = False
            diagnostics.n_train = len(x)
            serving.fit_diagnostics = diagnostics
        return serving

    def _model_risk_confidence(self, model: LinearTransition, similarity_to_centroid: float) -> float:
        distance = max(0.0, 1.0 - float(similarity_to_centroid))
        radius = max(float(model.radius), 1e-4)
        outside = max(0.0, distance - radius)
        support_decay = math.exp(-outside / max(radius, 0.02))

        if model.validation_quality is not None:
            quality = float(np.clip(model.validation_quality, 0.0, 1.0))
            support_factor = 1.0 - math.exp(-max(0, model.validation_support) / 3.0)
            calibration = quality * (0.55 + 0.45 * support_factor)
        else:
            calibration = 0.65 * float(np.clip((model.quality + 1.0) / 2.0, 0.0, 1.0))
        return float(np.clip(calibration * support_decay, 0.0, 1.0))

    def map(self, vector: np.ndarray, *, probes: int = 2) -> TransportedVector:
        q = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        if q.shape[0] != self.global_map.matrix.shape[0]:
            raise ValueError("source vector dimensionality does not match transition")

        if not self.local_maps:
            similarity = float(cosine_matrix(q.reshape(1, -1), self.global_map.source_centroid.reshape(1, -1))[0, 0])
            local_conf = self._model_risk_confidence(self.global_map, similarity)
            return TransportedVector(
                self.global_map.map(q),
                float(np.clip(self.confidence * local_conf, 0.0, 1.0)),
                (),
            )

        centroids = np.vstack([m.source_centroid for m in self.local_maps])
        sims = cosine_matrix(q.reshape(1, -1), centroids)[0]
        chosen = np.argsort(-sims)[: max(1, min(int(probes), len(self.local_maps)))]
        max_sim = float(np.max(sims[chosen]))
        mapped: list[np.ndarray] = []
        weights: list[float] = []
        local_conf: list[float] = []
        for cid in chosen:
            model = self.local_maps[int(cid)]
            quality = float(np.clip((model.quality + 1.0) / 2.0, 0.0, 1.0))
            weight = math.exp((float(sims[int(cid)]) - max_sim) / self.temperature) * max(quality, 0.001)
            mapped.append(model.map(q))
            weights.append(weight)
            local_conf.append(self._model_risk_confidence(model, float(sims[int(cid)])))

        w = np.asarray(weights, dtype=np.float64)
        w = w / max(float(np.sum(w)), _EPS)
        blended = normalize(np.sum(np.vstack(mapped) * w[:, None], axis=0, keepdims=True))[0]
        query_local_confidence = float(np.sum(w * np.asarray(local_conf)))
        confidence = self.confidence * query_local_confidence
        return TransportedVector(
            blended,
            float(np.clip(confidence, 0.0, 1.0)),
            tuple(map(int, chosen)),
        )

    def evaluate(self, source: np.ndarray, target: np.ndarray, *, k: int = 10) -> TransitionDiagnostics:
        x = normalize(np.asarray(source, dtype=np.float32))
        y = normalize(np.asarray(target, dtype=np.float32))
        if len(x) != len(y):
            raise ValueError("evaluation arrays must be paired")
        if len(x) == 0:
            return TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0)
        mapped = np.vstack([self.map(v).vector for v in x])
        pair_cos = np.sum(mapped * y, axis=1)
        cross = cosine_matrix(mapped, y)
        recall1 = float(np.mean(np.argmax(cross, axis=1) == np.arange(len(x))))
        take = min(max(1, int(k)), max(1, len(x) - 1))
        jac = _mean_jaccard(_knn_sets(mapped, take), _knn_sets(y, take)) if len(x) > 1 else 1.0
        return TransitionDiagnostics(
            n=len(x),
            mean_pair_cosine=float(np.mean(pair_cos)),
            p10_pair_cosine=float(np.quantile(pair_cos, 0.1)),
            pair_recall_at_1=recall1,
            neighborhood_jaccard=jac,
        )


class TransitionGraph:
    def __init__(self) -> None:
        self.transitions: dict[tuple[str, str], TransitionAtlas] = {}

    def add(self, transition: TransitionAtlas) -> None:
        self.transitions[transition.source_space, transition.target_space] = transition

    def route(self, source: str, target: str, *, max_hops: int = 4) -> tuple[str, ...]:
        if source == target:
            return (source,)
        outgoing: dict[str, list[TransitionAtlas]] = {}
        for tr in self.transitions.values():
            outgoing.setdefault(tr.source_space, []).append(tr)
        heap: list[tuple[float, int, str, tuple[str, ...]]] = [(0.0, 0, source, (source,))]
        best: dict[tuple[str, int], float] = {(source, 0): 0.0}
        while heap:
            cost, hops, node, path = heapq.heappop(heap)
            if node == target:
                return path
            if hops >= max_hops:
                continue
            for tr in outgoing.get(node, []):
                confidence = max(0.0001, tr.confidence)
                edge_cost = -math.log(confidence) + 0.025
                new_cost = cost + edge_cost
                key = (tr.target_space, hops + 1)
                if new_cost + 1e-12 < best.get(key, float("inf")):
                    best[key] = new_cost
                    heapq.heappush(
                        heap,
                        (new_cost, hops + 1, tr.target_space, path + (tr.target_space,)),
                    )
        return ()

    def path_confidence(self, path: Sequence[str]) -> float:
        if len(path) <= 1:
            return 1.0
        confidence = 1.0
        for a, b in zip(path, path[1:]):
            confidence *= max(0.0, self.transitions[a, b].confidence)
        return float(np.clip(confidence, 0.0, 1.0))

    def transport(self, vector: np.ndarray, path: Sequence[str]) -> TransportedVector:
        if not path:
            raise ValueError("transport path is empty")
        current = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        confidence = 1.0
        chart_ids: list[int] = []
        for a, b in zip(path, path[1:]):
            moved = self.transitions[a, b].map(current)
            current = moved.vector
            confidence *= moved.confidence
            chart_ids.extend(moved.chart_ids)
        return TransportedVector(
            current,
            float(np.clip(confidence, 0.0, 1.0)),
            tuple(chart_ids),
        )

    def transport_best(
        self,
        vector: np.ndarray,
        source: str,
        target: str,
        *,
        max_hops: int = 4,
    ) -> RoutedTransport | None:
        """Choose the highest-confidence route at the actual query location."""
        q = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        if source == target:
            return RoutedTransport(q, 1.0, (source,), ())

        outgoing: dict[str, list[TransitionAtlas]] = {}
        for tr in self.transitions.values():
            outgoing.setdefault(tr.source_space, []).append(tr)

        best_result: RoutedTransport | None = None
        stack: list[tuple[str, np.ndarray, float, tuple[str, ...], tuple[int, ...]]] = [
            (source, q, 1.0, (source,), ())
        ]
        while stack:
            node, current, confidence, path, charts = stack.pop()
            hops = len(path) - 1
            if node == target:
                candidate = RoutedTransport(current, confidence, path, charts)
                if best_result is None or candidate.confidence > best_result.confidence:
                    best_result = candidate
                continue
            if hops >= max_hops:
                continue
            for tr in outgoing.get(node, []):
                nxt = tr.target_space
                if nxt in path:
                    continue
                moved = tr.map(current)
                new_confidence = confidence * moved.confidence
                if best_result is not None and new_confidence <= best_result.confidence:
                    continue
                stack.append(
                    (
                        nxt,
                        moved.vector,
                        float(np.clip(new_confidence, 0.0, 1.0)),
                        path + (nxt,),
                        charts + moved.chart_ids,
                    )
                )
        return best_result

    def cycle_consistency(self, cycle: Sequence[str], vectors: np.ndarray) -> dict[str, float]:
        if len(cycle) < 2 or cycle[0] != cycle[-1]:
            raise ValueError("cycle must contain at least one edge and end at its start")
        original = normalize(np.asarray(vectors, dtype=np.float32))
        returned = np.vstack([self.transport(v, cycle).vector for v in original])
        if returned.shape != original.shape:
            raise ValueError("cycle returned to an incompatible dimensionality")
        cos = np.sum(original * returned, axis=1)
        return {
            "mean_cosine": float(np.mean(cos)),
            "p10_cosine": float(np.quantile(cos, 0.1)),
            "mean_cycle_error": float(np.mean(1.0 - cos)),
        }
