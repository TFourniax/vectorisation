from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

_EPS = 1e-12


def _normalize(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    norm = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norm, _EPS)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class TripletClause:
    """Ordinal semantic invariant: anchor must prefer positive over negative."""

    anchor: str
    positive: str
    negative: str
    margin: float = 0.0
    weight: float = 1.0
    hard: bool = False
    source: str = "contract"

    @property
    def kind(self) -> str:
        return "triplet"

    @property
    def objects(self) -> tuple[str, ...]:
        return (self.anchor, self.positive, self.negative)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "anchor": self.anchor,
            "positive": self.positive,
            "negative": self.negative,
            "margin": self.margin,
            "weight": self.weight,
            "hard": self.hard,
            "source": self.source,
        }


@dataclass(slots=True, frozen=True)
class NeighborClause:
    """A minimum fraction of a critical reference neighborhood must survive."""

    anchor: str
    expected: tuple[str, ...]
    min_recall: float = 0.6
    candidate_k: int | None = None
    weight: float = 1.0
    hard: bool = False
    source: str = "behavior"

    @property
    def kind(self) -> str:
        return "neighbor"

    @property
    def objects(self) -> tuple[str, ...]:
        return (self.anchor, *self.expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "anchor": self.anchor,
            "expected": list(self.expected),
            "min_recall": self.min_recall,
            "candidate_k": self.candidate_k,
            "weight": self.weight,
            "hard": self.hard,
            "source": self.source,
        }


@dataclass(slots=True, frozen=True)
class MutualNeighborClause:
    """A reciprocal semantic edge must remain reciprocal within top-k."""

    left: str
    right: str
    k: int = 10
    weight: float = 1.0
    hard: bool = False
    source: str = "behavior"

    @property
    def kind(self) -> str:
        return "mutual_neighbor"

    @property
    def objects(self) -> tuple[str, ...]:
        return (self.left, self.right)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "left": self.left,
            "right": self.right,
            "k": self.k,
            "weight": self.weight,
            "hard": self.hard,
            "source": self.source,
        }


Clause = TripletClause | NeighborClause | MutualNeighborClause


@dataclass(slots=True)
class ClauseResult:
    clause_index: int
    kind: str
    score: float
    passed: bool
    hard: bool
    weight: float
    objects: tuple[str, ...]
    detail: dict[str, Any]


@dataclass(slots=True)
class ContractReport:
    contract_name: str
    contract_digest: str
    implementation: str
    score: float
    hard_pass: bool
    clause_results: list[ClauseResult]
    object_risk: dict[str, float]
    evaluated_clauses: int
    missing_clauses: int

    @property
    def violated(self) -> list[ClauseResult]:
        return [result for result in self.clause_results if not result.passed]

    def certified_ids(self, *, max_risk: float = 0.15) -> set[str]:
        return {object_id for object_id, risk in self.object_risk.items() if risk <= max_risk}

    def certified_coverage(self, *, max_risk: float = 0.15) -> float:
        if not self.object_risk:
            return 0.0
        return len(self.certified_ids(max_risk=max_risk)) / len(self.object_risk)

    def top_risks(self, limit: int = 20) -> list[tuple[str, float]]:
        return sorted(self.object_risk.items(), key=lambda item: (-item[1], item[0]))[: max(0, int(limit))]

    def local_risk(self, query: np.ndarray, vectors: Mapping[str, np.ndarray], *, k: int = 8) -> float:
        candidates = [(object_id, vectors[object_id]) for object_id in self.object_risk if object_id in vectors]
        if not candidates:
            return 1.0
        ids = [item[0] for item in candidates]
        matrix = _normalize(np.vstack([item[1] for item in candidates]))
        q = _normalize(np.asarray(query, dtype=np.float32))[0]
        sims = matrix @ q
        take = min(max(1, int(k)), len(ids))
        chosen = np.argsort(-sims)[:take]
        weights = np.exp((sims[chosen] - np.max(sims[chosen])) / 0.08)
        weights /= max(float(np.sum(weights)), _EPS)
        return float(np.sum(weights * np.asarray([self.object_risk[ids[int(i)]] for i in chosen], dtype=np.float64)))


@dataclass(slots=True)
class SemanticContract:
    """Coordinate-free semantic ABI expressed as ID-level relational clauses."""

    name: str
    version: str
    clauses: list[Clause] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    parent_digest: str | None = None

    def add(self, clause: Clause) -> "SemanticContract":
        self.clauses.append(clause)
        return self

    def to_dict(self, *, include_created_at: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "format": "semantic-abi-contract",
            "format_version": 1,
            "name": self.name,
            "version": self.version,
            "parent_digest": self.parent_digest,
            "metadata": self.metadata,
            "clauses": [clause.to_dict() for clause in self.clauses],
        }
        if include_created_at:
            payload["created_at"] = self.created_at
        return payload

    @property
    def digest(self) -> str:
        return _sha256(self.to_dict(include_created_at=False))

    def audit(self, vectors: Mapping[str, np.ndarray], *, implementation: str = "candidate") -> ContractReport:
        ids = list(vectors)
        if not ids:
            return ContractReport(self.name, self.digest, implementation, 0.0, False, [], {}, 0, len(self.clauses))
        matrix = _normalize(np.vstack([vectors[object_id] for object_id in ids]))
        id_to_idx = {object_id: i for i, object_id in enumerate(ids)}
        similarities = matrix @ matrix.T
        np.fill_diagonal(similarities, -np.inf)

        results: list[ClauseResult] = []
        risk_numerator: dict[str, float] = {}
        risk_denominator: dict[str, float] = {}
        total_weight = 0.0
        earned_weight = 0.0
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

        for clause_index, clause in enumerate(self.clauses):
            if any(object_id not in id_to_idx for object_id in clause.objects):
                missing += 1
                if clause.hard:
                    hard_pass = False
                continue

            if isinstance(clause, TripletClause):
                anchor = id_to_idx[clause.anchor]
                positive = id_to_idx[clause.positive]
                negative = id_to_idx[clause.negative]
                delta = float((matrix[anchor] @ matrix[positive]) - (matrix[anchor] @ matrix[negative]))
                passed = delta >= clause.margin
                scale = max(0.05, abs(clause.margin) + 0.10)
                score = 1.0 if passed else float(np.clip(0.5 + 0.5 * np.tanh((delta - clause.margin) / scale), 0.0, 0.499999))
                register(ClauseResult(clause_index, clause.kind, score, passed, clause.hard, max(0.0, clause.weight), clause.objects, {"delta": delta, "required_margin": clause.margin}))
                continue

            if isinstance(clause, NeighborClause):
                anchor = id_to_idx[clause.anchor]
                candidate_k = clause.candidate_k or len(clause.expected)
                candidate_k = min(max(1, int(candidate_k)), max(1, len(ids) - 1))
                order = np.argsort(-similarities[anchor])[:candidate_k]
                got = {ids[int(i)] for i in order}
                expected = set(clause.expected)
                recall = 1.0 if not expected else len(expected & got) / len(expected)
                passed = recall >= clause.min_recall
                score = float(np.clip(recall / max(clause.min_recall, _EPS), 0.0, 1.0)) if not passed else 1.0
                register(ClauseResult(clause_index, clause.kind, score, passed, clause.hard, max(0.0, clause.weight), clause.objects, {"recall": recall, "required_recall": clause.min_recall, "candidate_k": candidate_k}))
                continue

            if isinstance(clause, MutualNeighborClause):
                left = id_to_idx[clause.left]
                right = id_to_idx[clause.right]
                take = min(max(1, int(clause.k)), max(1, len(ids) - 1))
                left_neighbors = set(np.argsort(-similarities[left])[:take].tolist())
                right_neighbors = set(np.argsort(-similarities[right])[:take].tolist())
                directions = int(right in left_neighbors) + int(left in right_neighbors)
                score = directions / 2.0
                passed = directions == 2
                register(ClauseResult(clause_index, clause.kind, score, passed, clause.hard, max(0.0, clause.weight), clause.objects, {"reciprocal_directions": directions, "k": take}))
                continue

            raise TypeError(f"unsupported clause: {type(clause)!r}")

        object_risk = {object_id: float(np.clip(risk_numerator.get(object_id, 0.0) / max(risk_denominator.get(object_id, 0.0), _EPS), 0.0, 1.0)) for object_id in risk_denominator}
        score = 0.0 if total_weight <= 0.0 else float(earned_weight / total_weight)
        return ContractReport(self.name, self.digest, implementation, score, hard_pass, results, object_risk, len(results), missing)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SemanticContract":
        if payload.get("format") != "semantic-abi-contract":
            raise ValueError("not a Semantic ABI contract")
        clauses: list[Clause] = []
        for raw in payload.get("clauses", []):
            kind = raw["kind"]
            if kind == "triplet":
                clauses.append(TripletClause(raw["anchor"], raw["positive"], raw["negative"], float(raw.get("margin", 0.0)), float(raw.get("weight", 1.0)), bool(raw.get("hard", False)), raw.get("source", "contract")))
            elif kind == "neighbor":
                clauses.append(NeighborClause(raw["anchor"], tuple(raw.get("expected", [])), float(raw.get("min_recall", 0.6)), raw.get("candidate_k"), float(raw.get("weight", 1.0)), bool(raw.get("hard", False)), raw.get("source", "behavior")))
            elif kind == "mutual_neighbor":
                clauses.append(MutualNeighborClause(raw["left"], raw["right"], int(raw.get("k", 10)), float(raw.get("weight", 1.0)), bool(raw.get("hard", False)), raw.get("source", "behavior")))
            else:
                raise ValueError(f"unknown clause kind: {kind}")
        return cls(name=str(payload["name"]), version=str(payload["version"]), clauses=clauses, metadata=dict(payload.get("metadata", {})), created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()), parent_digest=payload.get("parent_digest"))

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "SemanticContract":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass(slots=True, frozen=True)
class LedgerEntry:
    sequence: int
    contract_digest: str
    previous_entry_digest: str | None
    timestamp: str
    note: str
    entry_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {"sequence": self.sequence, "contract_digest": self.contract_digest, "previous_entry_digest": self.previous_entry_digest, "timestamp": self.timestamp, "note": self.note, "entry_digest": self.entry_digest}


class ContractLedger:
    """Tiny append-only hash chain for semantic schema history."""

    def __init__(self, entries: Sequence[LedgerEntry] | None = None) -> None:
        self.entries = list(entries or [])

    def append(self, contract: SemanticContract, *, note: str = "") -> LedgerEntry:
        previous = self.entries[-1].entry_digest if self.entries else None
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {"sequence": len(self.entries), "contract_digest": contract.digest, "previous_entry_digest": previous, "timestamp": timestamp, "note": note}
        entry = LedgerEntry(len(self.entries), contract.digest, previous, timestamp, note, _sha256(payload))
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        previous: str | None = None
        for expected_sequence, entry in enumerate(self.entries):
            if entry.sequence != expected_sequence or entry.previous_entry_digest != previous:
                return False
            payload = {"sequence": entry.sequence, "contract_digest": entry.contract_digest, "previous_entry_digest": entry.previous_entry_digest, "timestamp": entry.timestamp, "note": entry.note}
            if _sha256(payload) != entry.entry_digest:
                return False
            previous = entry.entry_digest
        return True

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for entry in self.entries:
                handle.write(_canonical_json(entry.to_dict()) + "\n")
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ContractLedger":
        entries: list[LedgerEntry] = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(LedgerEntry(**json.loads(line)))
        ledger = cls(entries)
        if not ledger.verify():
            raise ValueError("semantic contract ledger hash chain is invalid")
        return ledger


def capture_behavior_contract(vectors: Mapping[str, np.ndarray], *, name: str = "behavior", version: str = "1", anchors: Sequence[str] | None = None, k: int = 8, min_neighbor_recall: float = 0.5, triplets_per_anchor: int = 2, include_mutual: bool = True, max_mutual_edges: int = 1000, seed: int = 17) -> SemanticContract:
    """Freeze selected retrieval behavior without freezing coordinates."""
    ids = list(vectors)
    if len(ids) < 4:
        raise ValueError("at least four vectors are required")
    matrix = _normalize(np.vstack([vectors[object_id] for object_id in ids]))
    sims = matrix @ matrix.T
    np.fill_diagonal(sims, -np.inf)
    anchor_ids = list(anchors) if anchors is not None else ids
    rng = np.random.default_rng(int(seed))
    contract = SemanticContract(name=name, version=version, metadata={"builder": "capture_behavior_contract", "k": int(k)})
    id_to_idx = {object_id: i for i, object_id in enumerate(ids)}
    neighborhoods: dict[str, tuple[str, ...]] = {}
    for anchor_id in anchor_ids:
        if anchor_id not in id_to_idx:
            continue
        i = id_to_idx[anchor_id]
        order = np.argsort(-sims[i])
        take = min(max(1, int(k)), len(ids) - 1)
        neighbors = tuple(ids[int(j)] for j in order[:take])
        neighborhoods[anchor_id] = neighbors
        contract.add(NeighborClause(anchor_id, neighbors, min_recall=min_neighbor_recall, candidate_k=take, source="captured_behavior"))
        positives = order[:take]
        negative_pool = order[take : min(len(order), max(take + 1, take * 4))]
        if len(negative_pool) == 0:
            negative_pool = order[-take:]
        for _ in range(max(0, int(triplets_per_anchor))):
            positive = int(rng.choice(positives))
            negative = int(rng.choice(negative_pool))
            margin = max(0.0, float(sims[i, positive] - sims[i, negative]) * 0.20)
            contract.add(TripletClause(anchor_id, ids[positive], ids[negative], margin=margin, source="captured_behavior"))

    if include_mutual:
        seen: set[tuple[str, str]] = set()
        count = 0
        for left, neighbors in neighborhoods.items():
            for right in neighbors:
                if right not in neighborhoods or left not in neighborhoods[right]:
                    continue
                edge = tuple(sorted((left, right)))
                if edge in seen:
                    continue
                seen.add(edge)
                contract.add(MutualNeighborClause(edge[0], edge[1], k=k, source="captured_behavior"))
                count += 1
                if count >= max_mutual_edges:
                    break
            if count >= max_mutual_edges:
                break
    return contract


def contract_from_labels(vectors: Mapping[str, np.ndarray], labels: Mapping[str, Any], *, name: str = "application-semantics", version: str = "1", anchors: Sequence[str] | None = None, triplets_per_anchor: int = 3, hard: bool = False, seed: int = 17) -> SemanticContract:
    """Compile task semantics into hard-negative ordinal clauses.

    Labels are only one possible source. Production clauses can come from
    domain rules, human judgments, clicks, safety policy, ontology edges or
    curated examples.
    """
    ids = [object_id for object_id in vectors if object_id in labels]
    if len(ids) < 4:
        raise ValueError("at least four labelled vectors are required")
    matrix = _normalize(np.vstack([vectors[object_id] for object_id in ids]))
    sims = matrix @ matrix.T
    np.fill_diagonal(sims, -np.inf)
    anchor_ids = list(anchors) if anchors is not None else ids
    rng = np.random.default_rng(int(seed))
    contract = SemanticContract(name=name, version=version, metadata={"builder": "contract_from_labels", "semantics": "same-label ordinal preference"})
    id_to_idx = {object_id: i for i, object_id in enumerate(ids)}
    for anchor_id in anchor_ids:
        if anchor_id not in id_to_idx:
            continue
        i = id_to_idx[anchor_id]
        same = np.asarray([j for j, object_id in enumerate(ids) if j != i and labels[object_id] == labels[anchor_id]], dtype=int)
        different = np.asarray([j for j, object_id in enumerate(ids) if labels[object_id] != labels[anchor_id]], dtype=int)
        if len(same) == 0 or len(different) == 0:
            continue
        same = same[np.argsort(-sims[i, same])]
        different = different[np.argsort(-sims[i, different])]
        positive_pool = same[: min(len(same), max(4, triplets_per_anchor * 3))]
        negative_pool = different[: min(len(different), max(8, triplets_per_anchor * 6))]
        for _ in range(max(1, int(triplets_per_anchor))):
            positive = int(rng.choice(positive_pool))
            negative = int(rng.choice(negative_pool))
            contract.add(TripletClause(anchor_id, ids[positive], ids[negative], margin=0.0, weight=1.0, hard=hard, source="application_label"))
    return contract


@dataclass(slots=True, frozen=True)
class GateDecision:
    implementation: str | None
    accepted: bool
    local_risk: float
    utility: float
    reason: str


class SemanticABIGate:
    """Choose only implementations certified for the query's semantic region."""

    def __init__(self, implementations: Mapping[str, tuple[ContractReport, Mapping[str, np.ndarray]]], *, max_local_risk: float = 0.15, min_global_score: float = 0.80) -> None:
        self.implementations = dict(implementations)
        self.max_local_risk = float(np.clip(max_local_risk, 0.0, 1.0))
        self.min_global_score = float(np.clip(min_global_score, 0.0, 1.0))

    def choose(self, query_vectors: Mapping[str, np.ndarray], *, prefer: Sequence[str] = ()) -> GateDecision:
        preference = {name: len(prefer) - i for i, name in enumerate(prefer)}
        candidates: list[tuple[float, int, str, float]] = []
        rejected: list[str] = []
        for name, (report, landmarks) in self.implementations.items():
            if name not in query_vectors:
                rejected.append(f"{name}: no query vector")
                continue
            if not report.hard_pass:
                rejected.append(f"{name}: hard contract failure")
                continue
            if report.score < self.min_global_score:
                rejected.append(f"{name}: global score {report.score:.3f}")
                continue
            risk = report.local_risk(query_vectors[name], landmarks)
            if risk > self.max_local_risk:
                rejected.append(f"{name}: local risk {risk:.3f}")
                continue
            utility = report.score * (1.0 - risk)
            candidates.append((utility, preference.get(name, 0), name, risk))
        if not candidates:
            return GateDecision(None, False, 1.0, 0.0, "; ".join(rejected) or "no implementations")
        candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        utility, _, name, risk = candidates[0]
        return GateDecision(name, True, risk, utility, "certified semantic region")
