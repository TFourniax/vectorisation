from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_EPS = 1e-9


def normalize(v: np.ndarray) -> np.ndarray:
    arr = np.asarray(v, dtype=np.float32)
    norm = np.linalg.norm(arr, axis=-1, keepdims=True)
    return arr / np.maximum(norm, _EPS)


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return normalize(a) @ normalize(b).T


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(normalize(np.asarray(a).reshape(1, -1))[0] @ normalize(np.asarray(b).reshape(1, -1))[0])


def cosine_distance_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return 1.0 - cosine_matrix(a, b)


def local_intrinsic_dimension(distances: np.ndarray) -> float:
    d = np.sort(np.asarray(distances, dtype=np.float64))
    d = d[d > _EPS]
    if d.size < 3:
        return 0.0
    r_k = d[-1]
    logs = np.log(np.maximum(r_k / d[:-1], 1.0 + _EPS))
    denom = float(np.sum(logs))
    return 0.0 if denom <= _EPS else float((d.size - 1) / denom)


def pca_basis(vectors: np.ndarray, max_dims: int = 3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(vectors, dtype=np.float32)
    mean = x.mean(axis=0)
    centered = x - mean
    if len(x) <= 1:
        basis = np.zeros((max_dims, x.shape[1]), dtype=np.float32)
        return mean, basis, np.zeros(max_dims, dtype=np.float32)
    _, s, vt = np.linalg.svd(centered, full_matrices=False)
    dims = min(max_dims, vt.shape[0])
    basis = np.zeros((max_dims, x.shape[1]), dtype=np.float32)
    basis[:dims] = vt[:dims]
    variance = np.zeros(max_dims, dtype=np.float32)
    if np.sum(s * s) > _EPS:
        variance[:dims] = (s[:dims] * s[:dims]) / np.sum(s * s)
    return mean.astype(np.float32), basis, variance


def project_local(vector: np.ndarray, mean: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return (np.asarray(vector, dtype=np.float32) - mean) @ basis.T


def csls_scores(query: np.ndarray, candidates: np.ndarray, candidate_density: np.ndarray, k: int = 10) -> np.ndarray:
    """Cross-domain-similarity-local-scaling-inspired score."""
    sims = cosine_matrix(np.asarray(query).reshape(1, -1), candidates)[0]
    take = max(1, min(k, sims.size))
    rq = float(np.mean(np.partition(sims, -take)[-take:]))
    return 2.0 * sims - rq - candidate_density


@dataclass(slots=True)
class RobustScale:
    lo: float
    hi: float

    @classmethod
    def fit(cls, values: np.ndarray) -> "RobustScale":
        arr = np.asarray(values, dtype=np.float32)
        if arr.size == 0:
            return cls(0.0, 1.0)
        lo, hi = np.quantile(arr, [0.05, 0.95])
        if abs(float(hi - lo)) < _EPS:
            hi = lo + 1.0
        return cls(float(lo), float(hi))

    def transform(self, values: np.ndarray) -> np.ndarray:
        return np.clip((np.asarray(values) - self.lo) / (self.hi - self.lo), 0.0, 1.0)
