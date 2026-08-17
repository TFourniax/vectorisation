from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

_EPS = 1e-12


def _normalize(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), _EPS)


def _aligned(ids: Sequence[str], vectors: Mapping[str, np.ndarray]) -> np.ndarray:
    return _normalize(np.vstack([vectors[object_id] for object_id in ids]))


def _neighbor_rows(matrix: np.ndarray, k: int) -> np.ndarray:
    sims = matrix @ matrix.T
    np.fill_diagonal(sims, -np.inf)
    take = max(1, min(int(k), max(1, len(matrix) - 1)))
    if len(matrix) <= 1:
        return np.empty((len(matrix), 0), dtype=int)
    return np.argsort(-sims, axis=1)[:, :take]


@dataclass(slots=True, frozen=True)
class ObjectSemanticDiff:
    object_id: str
    neighbor_jaccard: float
    neighbor_churn: float
    top1_changed: bool
    reciprocal_retention: float
    severity: float
    old_neighbors: tuple[str, ...]
    new_neighbors: tuple[str, ...]


@dataclass(slots=True)
class RepresentationDiff:
    shared_objects: int
    k: int
    mean_neighbor_jaccard: float
    mean_neighbor_churn: float
    top1_change_rate: float
    mean_reciprocal_retention: float
    objects: list[ObjectSemanticDiff]

    @property
    def most_changed(self) -> list[ObjectSemanticDiff]:
        return sorted(self.objects, key=lambda row: (-row.severity, row.object_id))


@dataclass(slots=True, frozen=True)
class ContractQuestion:
    anchor_id: str
    option_a: str
    option_b: str
    old_preference: str
    new_preference: str
    old_margin: float
    new_margin: float
    disagreement: float
    anchor_severity: float
    priority: float

    def as_prompt(self) -> str:
        return (
            f"For semantic object {self.anchor_id!r}, which is genuinely closer/relevant: "
            f"{self.option_a!r} or {self.option_b!r}? "
            f"The previous representation prefers {self.old_preference!r}; "
            f"the candidate prefers {self.new_preference!r}."
        )


def semantic_diff(
    old_vectors: Mapping[str, np.ndarray],
    new_vectors: Mapping[str, np.ndarray],
    *,
    k: int = 10,
) -> RepresentationDiff:
    """Compare representation topology without assuming coordinate alignment."""

    ids = sorted(set(old_vectors) & set(new_vectors))
    if len(ids) < 2:
        return RepresentationDiff(len(ids), int(k), 1.0, 0.0, 0.0, 1.0, [])
    old = _aligned(ids, old_vectors)
    new = _aligned(ids, new_vectors)
    old_n = _neighbor_rows(old, k)
    new_n = _neighbor_rows(new, k)
    id_by_idx = np.asarray(ids, dtype=object)

    old_sets = [set(map(int, row)) for row in old_n]
    new_sets = [set(map(int, row)) for row in new_n]
    old_recip = [set(j for j in row if i in old_sets[j]) for i, row in enumerate(old_sets)]
    new_recip = [set(j for j in row if i in new_sets[j]) for i, row in enumerate(new_sets)]

    rows: list[ObjectSemanticDiff] = []
    for i, object_id in enumerate(ids):
        union = old_sets[i] | new_sets[i]
        jaccard = 1.0 if not union else len(old_sets[i] & new_sets[i]) / len(union)
        churn = 1.0 - jaccard
        top1_changed = bool(len(old_n[i]) and len(new_n[i]) and old_n[i, 0] != new_n[i, 0])
        reciprocal_union = old_recip[i] | new_recip[i]
        reciprocal_retention = 1.0 if not reciprocal_union else len(old_recip[i] & new_recip[i]) / len(reciprocal_union)
        severity = float(np.clip(0.55 * churn + 0.25 * float(top1_changed) + 0.20 * (1.0 - reciprocal_retention), 0.0, 1.0))
        rows.append(
            ObjectSemanticDiff(
                object_id=object_id,
                neighbor_jaccard=float(jaccard),
                neighbor_churn=float(churn),
                top1_changed=top1_changed,
                reciprocal_retention=float(reciprocal_retention),
                severity=severity,
                old_neighbors=tuple(str(x) for x in id_by_idx[old_n[i]]),
                new_neighbors=tuple(str(x) for x in id_by_idx[new_n[i]]),
            )
        )

    return RepresentationDiff(
        shared_objects=len(ids),
        k=min(int(k), len(ids) - 1),
        mean_neighbor_jaccard=float(np.mean([row.neighbor_jaccard for row in rows])),
        mean_neighbor_churn=float(np.mean([row.neighbor_churn for row in rows])),
        top1_change_rate=float(np.mean([row.top1_changed for row in rows])),
        mean_reciprocal_retention=float(np.mean([row.reciprocal_retention for row in rows])),
        objects=rows,
    )


def propose_contract_questions(
    old_vectors: Mapping[str, np.ndarray],
    new_vectors: Mapping[str, np.ndarray],
    *,
    limit: int = 50,
    k: int = 10,
    min_disagreement: float = 0.02,
) -> list[ContractQuestion]:
    """Mine high-value human questions from cross-representation disagreement.

    For each changed anchor we compare its old and new top-1 neighbors. The
    question is valuable when the two coordinate systems reverse that pairwise
    preference. This does not decide which representation is correct; it turns
    disagreement into a reviewable ordinal judgment that can become a future
    ``TripletClause`` after human/domain validation.
    """

    ids = sorted(set(old_vectors) & set(new_vectors))
    if len(ids) < 3 or limit <= 0:
        return []
    old = _aligned(ids, old_vectors)
    new = _aligned(ids, new_vectors)
    old_n = _neighbor_rows(old, max(1, k))
    new_n = _neighbor_rows(new, max(1, k))
    diff = semantic_diff(old_vectors, new_vectors, k=k)
    severity = {row.object_id: row.severity for row in diff.objects}

    questions: list[ContractQuestion] = []
    for i, anchor_id in enumerate(ids):
        old_top = int(old_n[i, 0])
        new_top = int(new_n[i, 0])
        if old_top == new_top:
            continue
        old_a = float(old[i] @ old[old_top])
        old_b = float(old[i] @ old[new_top])
        new_a = float(new[i] @ new[old_top])
        new_b = float(new[i] @ new[new_top])
        old_margin = old_a - old_b
        new_margin = new_b - new_a
        if old_margin <= 0.0 or new_margin <= 0.0:
            continue
        disagreement = float(min(old_margin, new_margin))
        if disagreement < min_disagreement:
            continue
        anchor_severity = severity.get(anchor_id, 0.0)
        priority = float(disagreement * (0.4 + 0.6 * anchor_severity))
        questions.append(
            ContractQuestion(
                anchor_id=anchor_id,
                option_a=ids[old_top],
                option_b=ids[new_top],
                old_preference=ids[old_top],
                new_preference=ids[new_top],
                old_margin=old_margin,
                new_margin=new_margin,
                disagreement=disagreement,
                anchor_severity=anchor_severity,
                priority=priority,
            )
        )

    questions.sort(key=lambda row: (-row.priority, row.anchor_id))
    return questions[: int(limit)]
