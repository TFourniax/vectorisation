from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

import numpy as np

from .contracts import ClauseResult, ContractReport, MutualNeighborClause, NeighborClause, SemanticContract, TripletClause

_EPS = 1e-12


@runtime_checkable
class SemanticOracle(Protocol):
    """Minimal behavior interface required to audit a Semantic ABI contract.

    The contract never asks how a representation is stored. Dense vectors,
    sparse search, graphs, hybrid rankers or remote retrieval services can all
    implement this protocol as long as they expose stable logical IDs,
    pairwise semantic affinity and ranked neighborhoods.
    """

    implementation: str

    def contains(self, object_id: str) -> bool: ...

    def similarity(self, left: str, right: str) -> float: ...

    def neighbors(self, anchor: str, k: int) -> Sequence[str]: ...


class DenseVectorOracle:
    """Cosine-backed adapter preserving the historical dense-vector behavior."""

    def __init__(self, vectors: Mapping[str, np.ndarray], *, implementation: str = "dense-vector") -> None:
        self.implementation = implementation
        self.ids = list(vectors)
        self.id_to_idx = {object_id: i for i, object_id in enumerate(self.ids)}
        if self.ids:
            matrix = np.vstack([np.asarray(vectors[object_id], dtype=np.float32).reshape(-1) for object_id in self.ids])
            norm = np.linalg.norm(matrix, axis=1, keepdims=True)
            self.matrix = matrix / np.maximum(norm, _EPS)
            self.similarities = self.matrix @ self.matrix.T
            np.fill_diagonal(self.similarities, -np.inf)
        else:
            self.matrix = np.empty((0, 0), dtype=np.float32)
            self.similarities = np.empty((0, 0), dtype=np.float32)

    def contains(self, object_id: str) -> bool:
        return object_id in self.id_to_idx

    def similarity(self, left: str, right: str) -> float:
        if left == right:
            return 1.0
        return float(self.similarities[self.id_to_idx[left], self.id_to_idx[right]])

    def neighbors(self, anchor: str, k: int) -> Sequence[str]:
        if len(self.ids) <= 1:
            return ()
        idx = self.id_to_idx[anchor]
        take = min(max(1, int(k)), len(self.ids) - 1)
        order = np.argsort(-self.similarities[idx])[:take]
        return tuple(self.ids[int(i)] for i in order)


@dataclass(slots=True)
class CallbackSemanticOracle:
    """Small adapter for graph/sparse/remote systems without vector exposure."""

    object_ids: frozenset[str]
    similarity_fn: Callable[[str, str], float]
    neighbors_fn: Callable[[str, int], Sequence[str]]
    implementation: str = "callback-oracle"

    def contains(self, object_id: str) -> bool:
        return object_id in self.object_ids

    def similarity(self, left: str, right: str) -> float:
        return float(self.similarity_fn(left, right))

    def neighbors(self, anchor: str, k: int) -> Sequence[str]:
        return tuple(self.neighbors_fn(anchor, int(k)))[: max(0, int(k))]


def evaluate_contract_clause(
    contract: SemanticContract,
    oracle: SemanticOracle,
    clause_index: int,
    *,
    implementation: str | None = None,
) -> ClauseResult | None:
    """Evaluate one contract clause while preserving its original clause index.

    ``None`` means at least one logical object required by the clause is absent
    from the oracle. Full audits retain their historical missing-clause
    semantics; progressive audit policies may deliberately treat missing soft
    clauses more conservatively.
    """
    index = int(clause_index)
    if index < 0 or index >= len(contract.clauses):
        raise IndexError(index)
    clause = contract.clauses[index]
    if any(not oracle.contains(object_id) for object_id in clause.objects):
        return None

    label = implementation or getattr(oracle, "implementation", "semantic-oracle")
    weight = max(0.0, float(clause.weight))
    if isinstance(clause, TripletClause):
        delta = float(oracle.similarity(clause.anchor, clause.positive) - oracle.similarity(clause.anchor, clause.negative))
        passed = delta >= clause.margin
        scale = max(0.05, abs(clause.margin) + 0.10)
        score = 1.0 if passed else float(np.clip(0.5 + 0.5 * np.tanh((delta - clause.margin) / scale), 0.0, 0.499999))
        return ClauseResult(index, clause.kind, score, passed, clause.hard, weight, clause.objects, {"delta": delta, "required_margin": clause.margin, "oracle": label})

    if isinstance(clause, NeighborClause):
        candidate_k = clause.candidate_k or len(clause.expected)
        candidate_k = max(1, int(candidate_k))
        got = set(oracle.neighbors(clause.anchor, candidate_k))
        expected = set(clause.expected)
        recall = 1.0 if not expected else len(expected & got) / len(expected)
        passed = recall >= clause.min_recall
        score = float(np.clip(recall / max(clause.min_recall, _EPS), 0.0, 1.0)) if not passed else 1.0
        return ClauseResult(index, clause.kind, score, passed, clause.hard, weight, clause.objects, {"recall": recall, "required_recall": clause.min_recall, "candidate_k": candidate_k, "oracle": label})

    if isinstance(clause, MutualNeighborClause):
        left_neighbors = set(oracle.neighbors(clause.left, clause.k))
        right_neighbors = set(oracle.neighbors(clause.right, clause.k))
        directions = int(clause.right in left_neighbors) + int(clause.left in right_neighbors)
        score = directions / 2.0
        passed = directions == 2
        return ClauseResult(index, clause.kind, score, passed, clause.hard, weight, clause.objects, {"reciprocal_directions": directions, "k": int(clause.k), "oracle": label})

    raise TypeError(f"unsupported clause: {type(clause)!r}")


def audit_contract(
    contract: SemanticContract,
    oracle: SemanticOracle,
    *,
    implementation: str | None = None,
) -> ContractReport:
    """Audit coordinate-free Semantic ABI clauses against any semantic oracle."""

    label = implementation or getattr(oracle, "implementation", "semantic-oracle")
    results: list[ClauseResult] = []
    risk_numerator: dict[str, float] = {}
    risk_denominator: dict[str, float] = {}
    total_weight = earned_weight = 0.0
    missing = 0
    hard_pass = True

    def register(result: ClauseResult) -> None:
        nonlocal total_weight, earned_weight, hard_pass
        results.append(result)
        total_weight += result.weight
        earned_weight += result.weight * result.score
        if result.hard and not result.passed:
            hard_pass = False
        loss = 1.0 - result.score
        for position, object_id in enumerate(result.objects):
            factor = 1.0 if position == 0 else 0.35
            risk_numerator[object_id] = risk_numerator.get(object_id, 0.0) + result.weight * factor * loss
            risk_denominator[object_id] = risk_denominator.get(object_id, 0.0) + result.weight * factor

    for clause_index, clause in enumerate(contract.clauses):
        result = evaluate_contract_clause(contract, oracle, clause_index, implementation=label)
        if result is None:
            missing += 1
            if clause.hard:
                hard_pass = False
            continue
        register(result)

    object_risk = {
        object_id: float(np.clip(risk_numerator.get(object_id, 0.0) / max(risk_denominator.get(object_id, 0.0), _EPS), 0.0, 1.0))
        for object_id in risk_denominator
    }
    score = 0.0 if total_weight <= 0.0 else float(earned_weight / total_weight)
    return ContractReport(contract.name, contract.digest, label, score, hard_pass, results, object_risk, len(results), missing)
