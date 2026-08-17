from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
from .alignment import TransitionAtlas
from .core import AtlasIndex, SearchPolicy
from .geometry import normalize

@dataclass(slots=True)
class DriftPoint:
    id: str
    aligned_cosine: float
    vector_change: float
    neighborhood_churn: float
    drift_score: float

@dataclass(slots=True)
class DriftReport:
    points: list[DriftPoint]
    mean_drift: float
    median_drift: float
    mean_aligned_cosine: float

    def top(self, limit: int=20) -> list[DriftPoint]:
        return sorted(self.points, key=lambda p: (-p.drift_score, p.id))[:max(0, int(limit))]

def _neighbors(index: AtlasIndex, record_id: str, k: int) -> set[str]:
    idx = index._id_to_idx[record_id]
    vector = index.vectors[idx]
    policy = SearchPolicy(top_k=max(2, int(k) + 1), diversify=0.0)
    return {hit.id for hit in index.search(vector, policy=policy) if hit.id != record_id}

def compare_indexes(before: AtlasIndex, after: AtlasIndex, *, transition: TransitionAtlas | None=None, ids: Sequence[str] | None=None, k: int=10, topology_weight: float=0.6) -> DriftReport:
    if not before.charts and before.records:
        before.build()
    if not after.charts and after.records:
        after.build()
    common = set(before._id_to_idx) & set(after._id_to_idx)
    selected = list(ids) if ids is not None else sorted(common)
    selected = [rid for rid in selected if rid in common]
    if not selected:
        return DriftReport([], 0.0, 0.0, 0.0)
    tw = float(np.clip(topology_weight, 0.0, 1.0))
    points: list[DriftPoint] = []
    for rid in selected:
        old = before.vectors[before._id_to_idx[rid]]
        new = after.vectors[after._id_to_idx[rid]]
        if transition is not None:
            aligned = transition.map(old).vector
        else:
            if old.shape != new.shape:
                raise ValueError('different dimensions require an explicit transition')
            aligned = normalize(old.reshape(1, -1))[0]
        cosine = float(np.clip(aligned @ normalize(new.reshape(1, -1))[0], -1.0, 1.0))
        vector_change = float(np.clip(1.0 - cosine, 0.0, 1.0))
        left = _neighbors(before, rid, k)
        right = _neighbors(after, rid, k)
        union = left | right
        agreement = 1.0 if not union else len(left & right) / len(union)
        churn = 1.0 - agreement
        score = tw * churn + (1.0 - tw) * vector_change
        points.append(DriftPoint(rid, cosine, vector_change, float(churn), float(score)))
    scores = np.asarray([p.drift_score for p in points], dtype=np.float32)
    cosines = np.asarray([p.aligned_cosine for p in points], dtype=np.float32)
    return DriftReport(points=points, mean_drift=float(np.mean(scores)), median_drift=float(np.median(scores)), mean_aligned_cosine=float(np.mean(cosines)))
