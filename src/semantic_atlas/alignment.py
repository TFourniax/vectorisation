from __future__ import annotations
from dataclasses import dataclass
import heapq
import math
from typing import Iterable, Sequence
import numpy as np
from .geometry import cosine_matrix, normalize
_EPS = 1e-09

@dataclass(slots=True)
class LinearTransition:
    source_mean: np.ndarray
    target_mean: np.ndarray
    matrix: np.ndarray
    scale: float
    source_centroid: np.ndarray
    quality: float
    support: int

    def map(self, vector: np.ndarray) -> np.ndarray:
        x = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if x.shape[1] != self.matrix.shape[0]:
            raise ValueError('source vector dimensionality does not match transition')
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

def _fit_procrustes(source: np.ndarray, target: np.ndarray) -> LinearTransition:
    x = normalize(np.asarray(source, dtype=np.float32))
    y = normalize(np.asarray(target, dtype=np.float32))
    if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
        raise ValueError('source and target anchors must be paired 2-D arrays')
    if len(x) < 2:
        raise ValueError('at least two paired anchors are required')
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
    return LinearTransition(source_mean=mx[0].astype(np.float32), target_mean=my[0].astype(np.float32), matrix=matrix, scale=scale, source_centroid=centroid.astype(np.float32), quality=float(np.clip(quality, -1.0, 1.0)), support=len(x))

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

class TransitionAtlas:

    def __init__(self, source_space: str, target_space: str, global_map: LinearTransition, local_maps: Sequence[LinearTransition], fit_diagnostics: TransitionDiagnostics, temperature: float=0.08) -> None:
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
    def _fit_components(x: np.ndarray, y: np.ndarray, *, chart_size: int, chart_overlap: float, min_chart_anchors: int) -> tuple[LinearTransition, list[LinearTransition]]:
        global_map = _fit_procrustes(x, y)
        target_charts = max(1, int(np.ceil(len(x) / max(2, int(chart_size)))))
        seeds = [0]
        min_dist = 1.0 - cosine_matrix(x, x[0:1])[:, 0]
        for _ in range(1, target_charts):
            idx = int(np.argmax(min_dist))
            seeds.append(idx)
            d = 1.0 - cosine_matrix(x, x[idx:idx + 1])[:, 0]
            min_dist = np.minimum(min_dist, d)
        local_maps: list[LinearTransition] = []
        take = min(len(x), max(int(min_chart_anchors), int(math.ceil(max(2, chart_size) * max(1.0, chart_overlap)))))
        for seed in seeds:
            dist = 1.0 - cosine_matrix(x, x[seed:seed + 1])[:, 0]
            members = np.argsort(dist)[:take]
            if len(members) >= 2:
                local_maps.append(_fit_procrustes(x[members], y[members]))
        return (global_map, local_maps)

    @classmethod
    def fit(cls, source_space: str, target_space: str, source_anchors: np.ndarray, target_anchors: np.ndarray, *, chart_size: int=32, chart_overlap: float=1.5, min_chart_anchors: int=8, temperature: float=0.08, validation_fraction: float=0.2, validation_seed: int=17) -> 'TransitionAtlas':
        x = normalize(np.asarray(source_anchors, dtype=np.float32))
        y = normalize(np.asarray(target_anchors, dtype=np.float32))
        if x.ndim != 2 or y.ndim != 2 or len(x) != len(y):
            raise ValueError('source and target anchors must be paired 2-D arrays')
        if len(x) < 2:
            raise ValueError('at least two paired anchors are required')
        use_holdout = len(x) >= 10 and validation_fraction > 0.0
        diagnostics: TransitionDiagnostics
        if use_holdout:
            rng = np.random.default_rng(int(validation_seed))
            perm = rng.permutation(len(x))
            val_n = max(2, min(len(x) - 2, int(round(len(x) * min(0.45, validation_fraction)))))
            val_idx, train_idx = (perm[:val_n], perm[val_n:])
            g_train, l_train = cls._fit_components(x[train_idx], y[train_idx], chart_size=chart_size, chart_overlap=chart_overlap, min_chart_anchors=min_chart_anchors)
            evaluator = cls(source_space, target_space, g_train, l_train, TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0), temperature)
            diagnostics = evaluator.evaluate(x[val_idx], y[val_idx], k=min(10, max(1, val_n - 1)))
            diagnostics.held_out = True
            diagnostics.n_train = len(train_idx)
        else:
            diagnostics = TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0, False, len(x))
        global_map, local_maps = cls._fit_components(x, y, chart_size=chart_size, chart_overlap=chart_overlap, min_chart_anchors=min_chart_anchors)
        serving = cls(source_space, target_space, global_map, local_maps, diagnostics, temperature)
        if not use_holdout:
            diagnostics = serving.evaluate(x, y, k=min(10, max(1, len(x) - 1)))
            diagnostics.held_out = False
            diagnostics.n_train = len(x)
            serving.fit_diagnostics = diagnostics
        return serving

    def map(self, vector: np.ndarray, *, probes: int=2) -> TransportedVector:
        q = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        if q.shape[0] != self.global_map.matrix.shape[0]:
            raise ValueError('source vector dimensionality does not match transition')
        if not self.local_maps:
            return TransportedVector(self.global_map.map(q), self.confidence, ())
        if len(self.local_maps) == 1:
            return TransportedVector(self.local_maps[0].map(q), self.confidence, (0,))
        centroids = np.vstack([m.source_centroid for m in self.local_maps])
        sims = cosine_matrix(q.reshape(1, -1), centroids)[0]
        chosen = np.argsort(-sims)[:max(1, min(int(probes), len(self.local_maps)))]
        max_sim = float(np.max(sims[chosen]))
        mapped: list[np.ndarray] = []
        weights: list[float] = []
        local_conf: list[float] = []
        for cid in chosen:
            model = self.local_maps[int(cid)]
            locality = float(np.clip((sims[int(cid)] + 1.0) / 2.0, 0.0, 1.0))
            quality = float(np.clip((model.quality + 1.0) / 2.0, 0.0, 1.0))
            weight = math.exp((float(sims[int(cid)]) - max_sim) / self.temperature) * max(quality, 0.001)
            mapped.append(model.map(q))
            weights.append(weight)
            local_conf.append(quality * (0.35 + 0.65 * locality))
        w = np.asarray(weights, dtype=np.float64)
        w = w / max(float(np.sum(w)), _EPS)
        blended = normalize(np.sum(np.vstack(mapped) * w[:, None], axis=0, keepdims=True))[0]
        confidence = float(np.sum(w * np.asarray(local_conf)))
        confidence *= max(0.2, self.confidence)
        return TransportedVector(blended, float(np.clip(confidence, 0.0, 1.0)), tuple(map(int, chosen)))

    def evaluate(self, source: np.ndarray, target: np.ndarray, *, k: int=10) -> TransitionDiagnostics:
        x = normalize(np.asarray(source, dtype=np.float32))
        y = normalize(np.asarray(target, dtype=np.float32))
        if len(x) != len(y):
            raise ValueError('evaluation arrays must be paired')
        if len(x) == 0:
            return TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0)
        mapped = np.vstack([self.map(v).vector for v in x]) if self.local_maps else np.vstack([self.global_map.map(v) for v in x])
        pair_cos = np.sum(mapped * y, axis=1)
        cross = cosine_matrix(mapped, y)
        recall1 = float(np.mean(np.argmax(cross, axis=1) == np.arange(len(x))))
        take = min(max(1, int(k)), max(1, len(x) - 1))
        jac = _mean_jaccard(_knn_sets(mapped, take), _knn_sets(y, take)) if len(x) > 1 else 1.0
        return TransitionDiagnostics(n=len(x), mean_pair_cosine=float(np.mean(pair_cos)), p10_pair_cosine=float(np.quantile(pair_cos, 0.1)), pair_recall_at_1=recall1, neighborhood_jaccard=jac)

class TransitionGraph:

    def __init__(self) -> None:
        self.transitions: dict[tuple[str, str], TransitionAtlas] = {}

    def add(self, transition: TransitionAtlas) -> None:
        self.transitions[transition.source_space, transition.target_space] = transition

    def route(self, source: str, target: str, *, max_hops: int=4) -> tuple[str, ...]:
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
                if new_cost + 1e-12 < best.get(key, float('inf')):
                    best[key] = new_cost
                    heapq.heappush(heap, (new_cost, hops + 1, tr.target_space, path + (tr.target_space,)))
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
            raise ValueError('transport path is empty')
        current = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        confidence = 1.0
        chart_ids: list[int] = []
        for a, b in zip(path, path[1:]):
            moved = self.transitions[a, b].map(current)
            current = moved.vector
            confidence *= moved.confidence
            chart_ids.extend(moved.chart_ids)
        return TransportedVector(current, float(np.clip(confidence, 0.0, 1.0)), tuple(chart_ids))

    def cycle_consistency(self, cycle: Sequence[str], vectors: np.ndarray) -> dict[str, float]:
        if len(cycle) < 2 or cycle[0] != cycle[-1]:
            raise ValueError('cycle must contain at least one edge and end at its start')
        original = normalize(np.asarray(vectors, dtype=np.float32))
        returned = np.vstack([self.transport(v, cycle).vector for v in original])
        if returned.shape != original.shape:
            raise ValueError('cycle returned to an incompatible dimensionality')
        cos = np.sum(original * returned, axis=1)
        return {'mean_cosine': float(np.mean(cos)), 'p10_cosine': float(np.quantile(cos, 0.1)), 'mean_cycle_error': float(np.mean(1.0 - cos))}
