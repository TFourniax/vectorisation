from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from .contracts import ContractReport, MutualNeighborClause, NeighborClause, SemanticContract, TripletClause

_EPS = 1e-12


def _normalize(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), _EPS)


@dataclass(slots=True, frozen=True)
class ContractCoverage:
    total_vectors: int
    referenced_objects: int
    present_referenced_objects: int
    object_coverage: float
    clause_count: int
    triplet_clauses: int
    neighbor_clauses: int
    mutual_neighbor_clauses: int
    mean_clause_degree: float
    max_clause_degree: int


@dataclass(slots=True, frozen=True)
class LocalSemanticRisk:
    risk: float
    interpolated_risk: float
    support: float
    nearest_similarity: float
    effective_neighbors: float
    support_distance: float
    reference_radius: float


def contract_coverage(contract: SemanticContract, vectors: Mapping[str, np.ndarray]) -> ContractCoverage:
    """Describe how much of the logical corpus is actually constrained.

    A high contract score over a tiny fraction of objects must not be mistaken
    for broad semantic coverage. This diagnostic is intentionally coordinate-
    independent except for the caller-provided universe of logical IDs.
    """

    referenced: set[str] = set()
    degree: dict[str, int] = {}
    triplets = neighbors = mutual = 0
    for clause in contract.clauses:
        if isinstance(clause, TripletClause):
            triplets += 1
        elif isinstance(clause, NeighborClause):
            neighbors += 1
        elif isinstance(clause, MutualNeighborClause):
            mutual += 1
        for object_id in clause.objects:
            referenced.add(object_id)
            degree[object_id] = degree.get(object_id, 0) + 1
    present = referenced & set(vectors)
    total = len(vectors)
    return ContractCoverage(
        total_vectors=total,
        referenced_objects=len(referenced),
        present_referenced_objects=len(present),
        object_coverage=0.0 if total == 0 else len(present) / total,
        clause_count=len(contract.clauses),
        triplet_clauses=triplets,
        neighbor_clauses=neighbors,
        mutual_neighbor_clauses=mutual,
        mean_clause_degree=0.0 if not degree else float(np.mean(list(degree.values()))),
        max_clause_degree=max(degree.values(), default=0),
    )


def estimate_local_semantic_risk(
    report: ContractReport,
    query: np.ndarray,
    vectors: Mapping[str, np.ndarray],
    *,
    k: int = 8,
    support_quantile: float = 0.90,
    temperature: float = 0.08,
) -> LocalSemanticRisk:
    """Interpolate contract risk while penalizing out-of-support queries.

    The reference radius is estimated from landmark-to-landmark nearest-neighbor
    distances. A query farther from the contract landmarks than that empirical
    radius receives an exponential support penalty. Final risk is at least
    ``1-support``; therefore an apparently low-risk but unsupported region
    naturally becomes abstention-prone.

    This is a geometric support diagnostic, not a distribution-shift theorem.
    The statistical rollout certificate must still be calibrated on held-out
    deployment-like cases.
    """

    candidates = [(object_id, vectors[object_id]) for object_id in report.object_risk if object_id in vectors]
    if not candidates:
        return LocalSemanticRisk(1.0, 1.0, 0.0, -1.0, 0.0, 2.0, 0.0)

    ids = [object_id for object_id, _ in candidates]
    matrix = _normalize(np.vstack([vector for _, vector in candidates]))
    q = _normalize(np.asarray(query, dtype=np.float32))[0]
    if q.shape[0] != matrix.shape[1]:
        raise ValueError("query dimensionality differs from contract landmark dimensionality")

    sims = matrix @ q
    take = min(max(1, int(k)), len(ids))
    chosen = np.argsort(-sims)[:take]
    top_sims = sims[chosen]
    weights = np.exp((top_sims - np.max(top_sims)) / max(float(temperature), 1e-4))
    weights /= max(float(np.sum(weights)), _EPS)
    interpolated = float(np.sum(weights * np.asarray([report.object_risk[ids[int(i)]] for i in chosen], dtype=np.float64)))
    effective_neighbors = float(1.0 / max(float(np.sum(weights * weights)), _EPS))

    nearest_similarity = float(np.max(sims))
    query_distance = max(0.0, 1.0 - nearest_similarity)

    if len(matrix) <= 1:
        reference_radius = 0.10
    else:
        pairwise = matrix @ matrix.T
        np.fill_diagonal(pairwise, -np.inf)
        nearest_landmark_similarity = np.max(pairwise, axis=1)
        landmark_distances = np.maximum(0.0, 1.0 - nearest_landmark_similarity)
        reference_radius = float(np.quantile(landmark_distances, float(np.clip(support_quantile, 0.50, 0.99))))
        reference_radius = max(reference_radius, 1e-3)

    excess = max(0.0, query_distance - reference_radius)
    support = float(np.exp(-excess / reference_radius))
    risk = float(np.clip(max(interpolated, 1.0 - support), 0.0, 1.0))
    return LocalSemanticRisk(
        risk=risk,
        interpolated_risk=float(np.clip(interpolated, 0.0, 1.0)),
        support=float(np.clip(support, 0.0, 1.0)),
        nearest_similarity=nearest_similarity,
        effective_neighbors=effective_neighbors,
        support_distance=query_distance,
        reference_radius=reference_radius,
    )
