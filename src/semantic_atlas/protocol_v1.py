from __future__ import annotations

"""Semantic ABI Oracle Protocol v1.

The established SemanticOracle API was designed around in-process experiments
and uses the word ``similarity``. Real retrievers are often directional and
remote: BM25 scores query->document, ColBERT/MaxSim is asymmetric, graph
traversal can be typed, and a provider may expose only ranking behavior.

Protocol v1 models ``score(anchor, candidate)`` explicitly and compiles a
SemanticContract into a deduplicated batch plan. No coordinates, symmetry, or
shared representation space are assumed.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from .contracts import (
    ClauseResult,
    ContractReport,
    MutualNeighborClause,
    NeighborClause,
    SemanticContract,
    TripletClause,
)

_EPS = 1e-12


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class OracleManifest:
    implementation_id: str
    implementation_kind: str = "other"
    score_semantics: str = "arbitrary"
    score_directionality: str = "unknown"
    deterministic: bool = True
    capabilities: tuple[str, ...] = ("contains_many", "score_many", "neighbors_many")
    metadata: Mapping[str, Any] = field(default_factory=dict)
    protocol: str = "semantic-abi-oracle"
    protocol_version: int = 1

    def __post_init__(self) -> None:
        if self.protocol != "semantic-abi-oracle" or self.protocol_version != 1:
            raise ValueError("unsupported Semantic ABI oracle protocol")
        if self.score_directionality not in {"symmetric", "asymmetric", "unknown"}:
            raise ValueError("invalid score directionality")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "protocol_version": self.protocol_version,
            "implementation_id": self.implementation_id,
            "implementation_kind": self.implementation_kind,
            "score_semantics": self.score_semantics,
            "score_directionality": self.score_directionality,
            "deterministic": self.deterministic,
            "capabilities": list(self.capabilities),
            "metadata": dict(self.metadata),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OracleManifest":
        return cls(
            implementation_id=str(payload["implementation_id"]),
            implementation_kind=str(payload.get("implementation_kind", "other")),
            score_semantics=str(payload.get("score_semantics", "arbitrary")),
            score_directionality=str(payload.get("score_directionality", "unknown")),
            deterministic=bool(payload.get("deterministic", True)),
            capabilities=tuple(str(x) for x in payload.get("capabilities", ("contains_many", "score_many", "neighbors_many"))),
            metadata=dict(payload.get("metadata", {})),
            protocol=str(payload.get("protocol", "semantic-abi-oracle")),
            protocol_version=int(payload.get("protocol_version", 1)),
        )


@dataclass(slots=True, frozen=True, order=True)
class ScorePair:
    anchor: str
    candidate: str

    def to_dict(self) -> dict[str, str]:
        return {"anchor": self.anchor, "candidate": self.candidate}


@dataclass(slots=True, frozen=True, order=True)
class NeighborRequest:
    anchor: str
    k: int

    def __post_init__(self) -> None:
        if self.k <= 0:
            raise ValueError("k must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {"anchor": self.anchor, "k": self.k}


@runtime_checkable
class BatchSemanticOracleV1(Protocol):
    manifest: OracleManifest

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]: ...
    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]: ...
    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]: ...


class LegacyOracleBatchAdapter:
    """Compatibility shim for the pre-v1 in-process SemanticOracle API."""

    def __init__(self, oracle: Any, *, implementation_kind: str = "legacy") -> None:
        self.oracle = oracle
        self.manifest = OracleManifest(
            implementation_id=str(getattr(oracle, "implementation", "legacy-oracle")),
            implementation_kind=implementation_kind,
            score_semantics="legacy-similarity",
            score_directionality="unknown",
            metadata={"adapter": "LegacyOracleBatchAdapter"},
        )

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        return {x: bool(self.oracle.contains(x)) for x in object_ids}

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        fn = getattr(self.oracle, "score", None) or self.oracle.similarity
        return {pair: float(fn(pair.anchor, pair.candidate)) for pair in pairs}

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        return {req: tuple(self.oracle.neighbors(req.anchor, req.k))[: req.k] for req in requests}


@dataclass(slots=True, frozen=True)
class ContractExecutionPlan:
    contract_digest: str
    clause_count: int
    object_ids: tuple[str, ...]
    score_pairs: tuple[ScorePair, ...]
    neighbor_requests: tuple[NeighborRequest, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-execution-plan",
            "format_version": 1,
            "contract_digest": self.contract_digest,
            "clause_count": self.clause_count,
            "object_ids": list(self.object_ids),
            "score_pairs": [x.to_dict() for x in self.score_pairs],
            "neighbor_requests": [x.to_dict() for x in self.neighbor_requests],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(slots=True, frozen=True)
class OracleExecutionStats:
    contains_batch_calls: int
    score_batch_calls: int
    neighbor_batch_calls: int
    object_checks: int
    score_pairs: int
    neighbor_requests: int

    @property
    def transport_round_trips(self) -> int:
        return self.contains_batch_calls + self.score_batch_calls + self.neighbor_batch_calls

    def to_dict(self) -> dict[str, int]:
        return {
            "contains_batch_calls": self.contains_batch_calls,
            "score_batch_calls": self.score_batch_calls,
            "neighbor_batch_calls": self.neighbor_batch_calls,
            "transport_round_trips": self.transport_round_trips,
            "object_checks": self.object_checks,
            "score_pairs": self.score_pairs,
            "neighbor_requests": self.neighbor_requests,
        }


@dataclass(slots=True, frozen=True)
class OracleSnapshot:
    manifest: OracleManifest
    plan_digest: str
    contains_map: Mapping[str, bool]
    scores: Mapping[ScorePair, float]
    neighborhoods: Mapping[NeighborRequest, tuple[str, ...]]
    stats: OracleExecutionStats

    def contains(self, object_id: str) -> bool:
        return bool(self.contains_map.get(object_id, False))

    def score(self, anchor: str, candidate: str) -> float:
        return float(self.scores[ScorePair(anchor, candidate)])

    def neighbors(self, anchor: str, k: int) -> tuple[str, ...]:
        exact = NeighborRequest(anchor, int(k))
        if exact in self.neighborhoods:
            return tuple(self.neighborhoods[exact])[:k]
        larger = sorted((x for x in self.neighborhoods if x.anchor == anchor and x.k >= k), key=lambda x: x.k)
        if not larger:
            raise KeyError((anchor, k))
        return tuple(self.neighborhoods[larger[0]])[:k]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-oracle-snapshot",
            "format_version": 1,
            "oracle_manifest": self.manifest.to_dict(),
            "oracle_manifest_digest": self.manifest.digest,
            "plan_digest": self.plan_digest,
            "contains": dict(self.contains_map),
            "scores": [{**pair.to_dict(), "score": score} for pair, score in sorted(self.scores.items())],
            "neighborhoods": [{**req.to_dict(), "neighbors": list(values)} for req, values in sorted(self.neighborhoods.items())],
            "stats": self.stats.to_dict(),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


def compile_contract(contract: SemanticContract) -> ContractExecutionPlan:
    """Compile clauses to the minimal deduplicated oracle operation set."""
    object_ids: set[str] = set()
    pairs: set[ScorePair] = set()
    neighbors: set[NeighborRequest] = set()
    for clause in contract.clauses:
        object_ids.update(clause.objects)
        if isinstance(clause, TripletClause):
            pairs.add(ScorePair(clause.anchor, clause.positive))
            pairs.add(ScorePair(clause.anchor, clause.negative))
        elif isinstance(clause, NeighborClause):
            neighbors.add(NeighborRequest(clause.anchor, max(1, int(clause.candidate_k or len(clause.expected) or 1))))
        elif isinstance(clause, MutualNeighborClause):
            k = max(1, int(clause.k))
            neighbors.add(NeighborRequest(clause.left, k))
            neighbors.add(NeighborRequest(clause.right, k))
        else:
            raise TypeError(f"unsupported clause: {type(clause)!r}")
    return ContractExecutionPlan(contract.digest, len(contract.clauses), tuple(sorted(object_ids)), tuple(sorted(pairs)), tuple(sorted(neighbors)))


def execute_contract_plan(plan: ContractExecutionPlan, oracle: BatchSemanticOracleV1) -> OracleSnapshot:
    """Execute a plan with at most one call per operation family."""
    raw_contains = dict(oracle.contains_many(plan.object_ids)) if plan.object_ids else {}
    contains = {x: bool(raw_contains.get(x, False)) for x in plan.object_ids}
    pairs = tuple(x for x in plan.score_pairs if contains.get(x.anchor, False) and contains.get(x.candidate, False))
    raw_scores = dict(oracle.score_many(pairs)) if pairs else {}
    scores: dict[ScorePair, float] = {}
    for pair in pairs:
        value = float(raw_scores[pair])
        if not math.isfinite(value):
            raise ValueError(f"non-finite oracle score: {pair}")
        scores[pair] = value
    requests = tuple(x for x in plan.neighbor_requests if contains.get(x.anchor, False))
    raw_neighbors = dict(oracle.neighbors_many(requests)) if requests else {}
    neighborhoods = {x: tuple(str(v) for v in raw_neighbors.get(x, ()))[: x.k] for x in requests}
    stats = OracleExecutionStats(int(bool(plan.object_ids)), int(bool(pairs)), int(bool(requests)), len(plan.object_ids), len(pairs), len(requests))
    return OracleSnapshot(oracle.manifest, plan.digest, contains, scores, neighborhoods, stats)


def audit_snapshot(contract: SemanticContract, snapshot: OracleSnapshot) -> ContractReport:
    """Audit from a directional protocol snapshot using established clause semantics."""
    results: list[ClauseResult] = []
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    total = earned = 0.0
    missing = 0
    hard_pass = True

    def register(result: ClauseResult) -> None:
        nonlocal total, earned, hard_pass
        results.append(result)
        total += result.weight
        earned += result.weight * result.score
        if result.hard and not result.passed:
            hard_pass = False
        loss = 1.0 - result.score
        for pos, object_id in enumerate(result.objects):
            factor = 1.0 if pos == 0 else 0.35
            num[object_id] = num.get(object_id, 0.0) + result.weight * factor * loss
            den[object_id] = den.get(object_id, 0.0) + result.weight * factor

    common = {"oracle": snapshot.manifest.implementation_id, "oracle_manifest_digest": snapshot.manifest.digest, "protocol": "semantic-abi-oracle", "protocol_version": 1}
    for i, clause in enumerate(contract.clauses):
        if any(not snapshot.contains(x) for x in clause.objects):
            missing += 1
            if clause.hard:
                hard_pass = False
            continue
        weight = max(0.0, float(clause.weight))
        if isinstance(clause, TripletClause):
            delta = snapshot.score(clause.anchor, clause.positive) - snapshot.score(clause.anchor, clause.negative)
            passed = delta >= clause.margin
            scale = max(0.05, abs(clause.margin) + 0.10)
            score = 1.0 if passed else max(0.0, min(0.499999, 0.5 + 0.5 * math.tanh((delta - clause.margin) / scale)))
            register(ClauseResult(i, clause.kind, score, passed, clause.hard, weight, clause.objects, {**common, "delta": delta, "required_margin": clause.margin}))
        elif isinstance(clause, NeighborClause):
            k = max(1, int(clause.candidate_k or len(clause.expected) or 1))
            got, expected = set(snapshot.neighbors(clause.anchor, k)), set(clause.expected)
            recall = 1.0 if not expected else len(got & expected) / len(expected)
            passed = recall >= clause.min_recall
            score = 1.0 if passed else max(0.0, min(1.0, recall / max(clause.min_recall, _EPS)))
            register(ClauseResult(i, clause.kind, score, passed, clause.hard, weight, clause.objects, {**common, "recall": recall, "required_recall": clause.min_recall, "candidate_k": k}))
        elif isinstance(clause, MutualNeighborClause):
            left = set(snapshot.neighbors(clause.left, clause.k)); right = set(snapshot.neighbors(clause.right, clause.k))
            directions = int(clause.right in left) + int(clause.left in right)
            register(ClauseResult(i, clause.kind, directions / 2.0, directions == 2, clause.hard, weight, clause.objects, {**common, "reciprocal_directions": directions, "k": clause.k}))
        else:
            raise TypeError(f"unsupported clause: {type(clause)!r}")
    risk = {x: max(0.0, min(1.0, num.get(x, 0.0) / max(den.get(x, 0.0), _EPS))) for x in den}
    return ContractReport(contract.name, contract.digest, snapshot.manifest.implementation_id, 0.0 if total <= 0 else earned / total, hard_pass, results, risk, len(results), missing)


@dataclass(slots=True, frozen=True)
class ProtocolAuditResult:
    plan: ContractExecutionPlan
    snapshot: OracleSnapshot
    report: ContractReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-protocol-audit",
            "format_version": 1,
            "plan_digest": self.plan.digest,
            "snapshot_digest": self.snapshot.digest,
            "oracle_manifest_digest": self.snapshot.manifest.digest,
            "contract_digest": self.report.contract_digest,
            "implementation": self.report.implementation,
            "score": self.report.score,
            "hard_pass": self.report.hard_pass,
            "evaluated_clauses": self.report.evaluated_clauses,
            "missing_clauses": self.report.missing_clauses,
            "violated_clauses": len(self.report.violated),
            "execution": self.snapshot.stats.to_dict(),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


def audit_contract_v1(contract: SemanticContract, oracle: BatchSemanticOracleV1 | Any) -> ProtocolAuditResult:
    if not isinstance(getattr(oracle, "manifest", None), OracleManifest):
        oracle = LegacyOracleBatchAdapter(oracle)
    plan = compile_contract(contract)
    snapshot = execute_contract_plan(plan, oracle)
    return ProtocolAuditResult(plan, snapshot, audit_snapshot(contract, snapshot))
