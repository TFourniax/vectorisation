from __future__ import annotations

"""Evidence-gated acquisition of Semantic ABI contracts from real system signals.

The forge deliberately does *not* treat current retrieval behavior as truth. It accepts
explicit policy, human judgments/corrections, relevant sets and cautious production
interaction evidence, aggregates contradictory signals, and only auto-promotes clauses
whose support clears a declared policy. Everything else is surfaced for review.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .contracts import NeighborClause, SemanticContract, TripletClause


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


DEFAULT_SOURCE_RELIABILITY: dict[str, float] = {
    "policy": 1.00,
    "human_correction": 1.00,
    "human_judgment": 0.95,
    "explicit_feedback": 0.90,
    "accepted_answer": 0.85,
    "user_selection": 0.75,
    "production_click": 0.45,
    "implicit_behavior": 0.35,
    "synthetic": 0.30,
    "captured_behavior": 0.15,
}


@dataclass(slots=True, frozen=True)
class PreferenceEvidence:
    """Evidence that ``anchor`` should prefer ``preferred`` over ``rejected``."""

    anchor: str
    preferred: str
    rejected: str
    source: str = "human_judgment"
    confidence: float = 1.0
    criticality: float = 0.0
    hard_eligible: bool = False
    event_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.anchor or not self.preferred or not self.rejected:
            raise ValueError("anchor/preferred/rejected must be non-empty logical IDs")
        if self.preferred == self.rejected:
            raise ValueError("preferred and rejected must differ")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if not 0.0 <= float(self.criticality) <= 1.0:
            raise ValueError("criticality must be within [0, 1]")

    @property
    def kind(self) -> str:
        return "preference"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.kind,
            "anchor": self.anchor,
            "preferred": self.preferred,
            "rejected": self.rejected,
            "source": self.source,
            "confidence": float(self.confidence),
            "criticality": float(self.criticality),
            "hard_eligible": bool(self.hard_eligible),
            "event_id": self.event_id,
            "provenance": dict(self.provenance),
        }


@dataclass(slots=True, frozen=True)
class RelevantSetEvidence:
    """Evidence that a set of logical objects must remain reachable for an anchor."""

    anchor: str
    relevant: tuple[str, ...]
    candidate_k: int | None = None
    min_recall: float = 0.6
    source: str = "human_judgment"
    confidence: float = 1.0
    criticality: float = 0.0
    hard_eligible: bool = False
    event_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.anchor:
            raise ValueError("anchor must be a non-empty logical ID")
        if not self.relevant or any(not item for item in self.relevant):
            raise ValueError("relevant must contain at least one logical ID")
        if not 0.0 < float(self.min_recall) <= 1.0:
            raise ValueError("min_recall must be within (0, 1]")
        if self.candidate_k is not None and int(self.candidate_k) <= 0:
            raise ValueError("candidate_k must be positive")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if not 0.0 <= float(self.criticality) <= 1.0:
            raise ValueError("criticality must be within [0, 1]")

    @property
    def kind(self) -> str:
        return "relevant_set"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.kind,
            "anchor": self.anchor,
            "relevant": list(self.relevant),
            "candidate_k": self.candidate_k,
            "min_recall": float(self.min_recall),
            "source": self.source,
            "confidence": float(self.confidence),
            "criticality": float(self.criticality),
            "hard_eligible": bool(self.hard_eligible),
            "event_id": self.event_id,
            "provenance": dict(self.provenance),
        }


Evidence = PreferenceEvidence | RelevantSetEvidence


@dataclass(slots=True, frozen=True)
class AcquisitionPolicy:
    """Declared promotion policy for inferred semantic requirements."""

    auto_promote_confidence: float = 0.85
    review_confidence: float = 0.60
    min_effective_support: float = 0.80
    hard_confidence: float = 0.98
    hard_min_criticality: float = 0.80
    opposition_ratio_review: float = 0.20
    max_review_items: int = 200
    source_reliability: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_SOURCE_RELIABILITY))

    def __post_init__(self) -> None:
        for value in (self.auto_promote_confidence, self.review_confidence, self.hard_confidence, self.hard_min_criticality, self.opposition_ratio_review):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("policy probabilities must be within [0, 1]")
        if self.review_confidence > self.auto_promote_confidence:
            raise ValueError("review_confidence cannot exceed auto_promote_confidence")
        if float(self.min_effective_support) < 0.0:
            raise ValueError("min_effective_support cannot be negative")
        if int(self.max_review_items) < 0:
            raise ValueError("max_review_items cannot be negative")

    def reliability(self, source: str) -> float:
        return _clip01(float(self.source_reliability.get(source, 0.50)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_promote_confidence": self.auto_promote_confidence,
            "review_confidence": self.review_confidence,
            "min_effective_support": self.min_effective_support,
            "hard_confidence": self.hard_confidence,
            "hard_min_criticality": self.hard_min_criticality,
            "opposition_ratio_review": self.opposition_ratio_review,
            "max_review_items": self.max_review_items,
            "source_reliability": dict(sorted(self.source_reliability.items())),
        }


@dataclass(slots=True, frozen=True)
class ClauseCandidate:
    kind: str
    key: tuple[str, ...]
    confidence: float
    effective_support: float
    opposition_support: float
    criticality: float
    hard_eligible: bool
    sources: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": list(self.key),
            "confidence": self.confidence,
            "effective_support": self.effective_support,
            "opposition_support": self.opposition_support,
            "criticality": self.criticality,
            "hard_eligible": self.hard_eligible,
            "sources": list(self.sources),
            "evidence_ids": list(self.evidence_ids),
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(slots=True, frozen=True)
class ReviewItem:
    candidate: ClauseCandidate
    priority: float

    def to_dict(self) -> dict[str, Any]:
        return {"priority": self.priority, **self.candidate.to_dict()}


@dataclass(slots=True, frozen=True)
class ContractAcquisitionReport:
    evidence_digest: str
    evidence_count: int
    source_counts: Mapping[str, int]
    candidate_count: int
    promoted_count: int
    review_count: int
    rejected_count: int
    conflict_count: int
    contract_digest: str
    estimated_review_minutes: float
    clauses_per_review_minute: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_digest": self.evidence_digest,
            "evidence_count": self.evidence_count,
            "source_counts": dict(sorted(self.source_counts.items())),
            "candidate_count": self.candidate_count,
            "promoted_count": self.promoted_count,
            "review_count": self.review_count,
            "rejected_count": self.rejected_count,
            "conflict_count": self.conflict_count,
            "contract_digest": self.contract_digest,
            "estimated_review_minutes": self.estimated_review_minutes,
            "clauses_per_review_minute": self.clauses_per_review_minute,
        }


@dataclass(slots=True)
class ContractAcquisitionResult:
    contract: SemanticContract
    report: ContractAcquisitionReport
    candidates: list[ClauseCandidate]
    review_queue: list[ReviewItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract.to_dict(),
            "report": self.report.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "review_queue": [item.to_dict() for item in self.review_queue],
        }


def _event_identity(event: Evidence) -> str:
    if event.event_id:
        return str(event.event_id)
    return _digest(event.to_dict())[:24]


def evidence_digest(evidence: Iterable[Evidence]) -> str:
    """Order-independent digest of acquisition inputs."""
    payload = sorted(_canonical_json(event.to_dict()) for event in evidence)
    return _digest(payload)


def _confidence_from_support(support: float, opposition: float) -> float:
    """Conservative Bayesian-style confidence with explicit evidence-mass damping.

    A small symmetric prior prevents a single weak event from looking certain; repeated
    independent evidence can accumulate, while contradictory evidence pulls confidence
    back toward 0.5.
    """

    support = max(0.0, float(support))
    opposition = max(0.0, float(opposition))
    mass = support + opposition
    if mass <= 0.0:
        return 0.5
    posterior = (0.25 + support) / (0.50 + mass)
    mass_factor = 1.0 - math.exp(-mass)
    directional = 0.5 + (posterior - 0.5) * mass_factor
    return _clip01(directional)


def _status_for(
    *,
    confidence: float,
    support: float,
    opposition: float,
    policy: AcquisitionPolicy,
) -> tuple[str, str]:
    total = support + opposition
    opposition_ratio = 0.0 if total <= 0.0 else opposition / total
    if opposition_ratio >= policy.opposition_ratio_review and opposition > 0.0:
        return "review", "contradictory evidence"
    if support >= policy.min_effective_support and confidence >= policy.auto_promote_confidence:
        return "promoted", "evidence threshold satisfied"
    if confidence >= policy.review_confidence or opposition > 0.0:
        return "review", "insufficient certainty for automatic promotion"
    return "rejected", "evidence too weak"


def _preference_candidates(evidence: Sequence[PreferenceEvidence], policy: AcquisitionPolicy) -> list[ClauseCandidate]:
    grouped: dict[tuple[str, str, str], list[PreferenceEvidence]] = {}
    for event in evidence:
        grouped.setdefault((event.anchor, event.preferred, event.rejected), []).append(event)

    candidates: list[ClauseCandidate] = []
    visited: set[tuple[str, str, str]] = set()
    for key in sorted(grouped):
        if key in visited:
            continue
        anchor, preferred, rejected = key
        opposite_key = (anchor, rejected, preferred)
        direct = grouped[key]
        opposite = grouped.get(opposite_key, [])
        visited.add(key)
        visited.add(opposite_key)

        def strength(events: Sequence[PreferenceEvidence]) -> float:
            return sum(_clip01(event.confidence) * policy.reliability(event.source) for event in events)

        direct_support = strength(direct)
        opposite_support = strength(opposite)

        # Emit the better-supported direction as the candidate. A true tie is stable by ID.
        if opposite_support > direct_support or (opposite_support == direct_support and opposite_key < key):
            key, opposite_key = opposite_key, key
            direct, opposite = opposite, direct
            direct_support, opposite_support = opposite_support, direct_support
            anchor, preferred, rejected = key

        confidence = _confidence_from_support(direct_support, opposite_support)
        status, reason = _status_for(confidence=confidence, support=direct_support, opposition=opposite_support, policy=policy)
        all_events = [*direct, *opposite]
        criticality = max((float(event.criticality) for event in all_events), default=0.0)
        hard_eligible = bool(direct) and all(event.hard_eligible for event in direct) and not opposite
        candidates.append(
            ClauseCandidate(
                kind="triplet",
                key=(anchor, preferred, rejected),
                confidence=confidence,
                effective_support=direct_support,
                opposition_support=opposite_support,
                criticality=criticality,
                hard_eligible=hard_eligible,
                sources=tuple(sorted({event.source for event in all_events})),
                evidence_ids=tuple(sorted(_event_identity(event) for event in all_events)),
                status=status,
                reason=reason,
            )
        )
    return candidates


def _relevant_set_candidates(evidence: Sequence[RelevantSetEvidence], policy: AcquisitionPolicy) -> list[tuple[ClauseCandidate, RelevantSetEvidence]]:
    grouped: dict[tuple[str, tuple[str, ...], int | None, float], list[RelevantSetEvidence]] = {}
    for event in evidence:
        relevant = tuple(sorted(set(event.relevant)))
        key = (event.anchor, relevant, event.candidate_k, float(event.min_recall))
        grouped.setdefault(key, []).append(event)

    output: list[tuple[ClauseCandidate, RelevantSetEvidence]] = []
    for key in sorted(grouped, key=lambda item: (item[0], item[1], item[2] or -1, item[3])):
        events = grouped[key]
        support = sum(_clip01(event.confidence) * policy.reliability(event.source) for event in events)
        confidence = _confidence_from_support(support, 0.0)
        status, reason = _status_for(confidence=confidence, support=support, opposition=0.0, policy=policy)
        criticality = max(float(event.criticality) for event in events)
        hard_eligible = all(event.hard_eligible for event in events)
        anchor, relevant, candidate_k, min_recall = key
        candidate = ClauseCandidate(
            kind="neighbor",
            key=(anchor, *relevant),
            confidence=confidence,
            effective_support=support,
            opposition_support=0.0,
            criticality=criticality,
            hard_eligible=hard_eligible,
            sources=tuple(sorted({event.source for event in events})),
            evidence_ids=tuple(sorted(_event_identity(event) for event in events)),
            status=status,
            reason=reason,
        )
        representative = RelevantSetEvidence(
            anchor=anchor,
            relevant=relevant,
            candidate_k=candidate_k,
            min_recall=min_recall,
            source="contract_forge",
            confidence=confidence,
            criticality=criticality,
            hard_eligible=hard_eligible,
        )
        output.append((candidate, representative))
    return output


def _should_be_hard(candidate: ClauseCandidate, policy: AcquisitionPolicy) -> bool:
    return bool(
        candidate.hard_eligible
        and candidate.opposition_support == 0.0
        and candidate.confidence >= policy.hard_confidence
        and candidate.criticality >= policy.hard_min_criticality
    )


def forge_contract(
    evidence: Sequence[Evidence],
    *,
    name: str = "application-semantics",
    version: str = "1",
    parent_digest: str | None = None,
    policy: AcquisitionPolicy | None = None,
    estimated_seconds_per_review: float = 20.0,
) -> ContractAcquisitionResult:
    """Infer a reviewable Semantic Contract from heterogeneous evidence.

    The returned contract contains *only* auto-promoted clauses. Ambiguous, weak or
    contradictory candidates are retained in ``review_queue`` rather than silently
    becoming application truth.
    """

    policy = policy or AcquisitionPolicy()
    preference = [event for event in evidence if isinstance(event, PreferenceEvidence)]
    relevant_sets = [event for event in evidence if isinstance(event, RelevantSetEvidence)]

    candidates = _preference_candidates(preference, policy)
    relevant_candidates = _relevant_set_candidates(relevant_sets, policy)
    candidates.extend(candidate for candidate, _ in relevant_candidates)
    candidates.sort(key=lambda item: (item.kind, item.key))

    input_digest = evidence_digest(evidence)
    source_counts: dict[str, int] = {}
    for event in evidence:
        source_counts[event.source] = source_counts.get(event.source, 0) + 1

    contract = SemanticContract(
        name=name,
        version=version,
        parent_digest=parent_digest,
        metadata={
            "builder": "contract_forge_v1",
            "evidence_digest": input_digest,
            "evidence_count": len(evidence),
            "source_counts": dict(sorted(source_counts.items())),
            "acquisition_policy": policy.to_dict(),
        },
    )

    relevant_by_key = {candidate.key: event for candidate, event in relevant_candidates}
    for candidate in candidates:
        if candidate.status != "promoted":
            continue
        hard = _should_be_hard(candidate, policy)
        weight = 0.25 + 0.75 * candidate.confidence
        source = "contract_forge:" + "+".join(candidate.sources)
        if candidate.kind == "triplet":
            anchor, preferred, rejected = candidate.key
            contract.add(TripletClause(anchor, preferred, rejected, margin=0.0, weight=weight, hard=hard, source=source))
        elif candidate.kind == "neighbor":
            event = relevant_by_key[candidate.key]
            contract.add(
                NeighborClause(
                    event.anchor,
                    tuple(event.relevant),
                    min_recall=event.min_recall,
                    candidate_k=event.candidate_k,
                    weight=weight,
                    hard=hard,
                    source=source,
                )
            )

    review_queue = [
        ReviewItem(
            candidate=candidate,
            priority=(2.0 * candidate.criticality) + (1.0 - abs(candidate.confidence - policy.auto_promote_confidence)) + min(1.0, candidate.opposition_support),
        )
        for candidate in candidates
        if candidate.status == "review"
    ]
    review_queue.sort(key=lambda item: (-item.priority, item.candidate.kind, item.candidate.key))
    review_queue = review_queue[: policy.max_review_items]

    promoted = sum(candidate.status == "promoted" for candidate in candidates)
    review = sum(candidate.status == "review" for candidate in candidates)
    rejected = sum(candidate.status == "rejected" for candidate in candidates)
    conflicts = sum(candidate.opposition_support > 0.0 for candidate in candidates)
    review_minutes = review * max(0.0, float(estimated_seconds_per_review)) / 60.0
    clauses_per_minute = 0.0 if review_minutes <= 0.0 else promoted / review_minutes
    report = ContractAcquisitionReport(
        evidence_digest=input_digest,
        evidence_count=len(evidence),
        source_counts=source_counts,
        candidate_count=len(candidates),
        promoted_count=promoted,
        review_count=review,
        rejected_count=rejected,
        conflict_count=conflicts,
        contract_digest=contract.digest,
        estimated_review_minutes=review_minutes,
        clauses_per_review_minute=clauses_per_minute,
    )
    return ContractAcquisitionResult(contract=contract, report=report, candidates=candidates, review_queue=review_queue)


def _preference_from_payload(payload: Mapping[str, Any]) -> PreferenceEvidence:
    return PreferenceEvidence(
        anchor=str(payload["anchor"]),
        preferred=str(payload["preferred"]),
        rejected=str(payload["rejected"]),
        source=str(payload.get("source", "human_judgment")),
        confidence=float(payload.get("confidence", 1.0)),
        criticality=float(payload.get("criticality", 0.0)),
        hard_eligible=bool(payload.get("hard_eligible", False)),
        event_id=None if payload.get("event_id") is None else str(payload["event_id"]),
        provenance=dict(payload.get("provenance", {})),
    )


def _relevant_set_from_payload(payload: Mapping[str, Any]) -> RelevantSetEvidence:
    return RelevantSetEvidence(
        anchor=str(payload["anchor"]),
        relevant=tuple(str(item) for item in payload.get("relevant", [])),
        candidate_k=None if payload.get("candidate_k") is None else int(payload["candidate_k"]),
        min_recall=float(payload.get("min_recall", 0.6)),
        source=str(payload.get("source", "human_judgment")),
        confidence=float(payload.get("confidence", 1.0)),
        criticality=float(payload.get("criticality", 0.0)),
        hard_eligible=bool(payload.get("hard_eligible", False)),
        event_id=None if payload.get("event_id") is None else str(payload["event_id"]),
        provenance=dict(payload.get("provenance", {})),
    )


def evidence_from_trace(payload: Mapping[str, Any]) -> list[PreferenceEvidence | RelevantSetEvidence]:
    """Cautiously derive evidence from one production retrieval trace.

    Click evidence only compares a clicked result with *skipped results ranked above it*,
    which is substantially safer than assuming every non-clicked result is negative.
    Explicit selections/negatives can carry stronger evidence. Baseline ranking alone
    never becomes a contract.
    """

    anchor = str(payload["anchor"])
    results = tuple(str(item) for item in payload.get("results", []))
    clicks = tuple(str(item) for item in payload.get("clicked", []))
    selected = tuple(str(item) for item in payload.get("selected", []))
    explicit_negative = tuple(str(item) for item in payload.get("explicit_negative", []))
    event_id = None if payload.get("event_id") is None else str(payload["event_id"])
    provenance = dict(payload.get("provenance", {}))
    criticality = float(payload.get("criticality", 0.0))

    output: list[PreferenceEvidence | RelevantSetEvidence] = []
    rank = {object_id: index for index, object_id in enumerate(results)}

    for clicked in clicks:
        if clicked not in rank:
            continue
        for skipped in results[: rank[clicked]]:
            if skipped in clicks or skipped in selected:
                continue
            output.append(
                PreferenceEvidence(
                    anchor,
                    clicked,
                    skipped,
                    source="production_click",
                    confidence=float(payload.get("click_confidence", 0.70)),
                    criticality=criticality,
                    hard_eligible=False,
                    event_id=f"{event_id}:click:{clicked}>{skipped}" if event_id else None,
                    provenance=provenance,
                )
            )

    preferred_explicit = selected or clicks
    for preferred in preferred_explicit:
        for rejected in explicit_negative:
            if preferred == rejected:
                continue
            output.append(
                PreferenceEvidence(
                    anchor,
                    preferred,
                    rejected,
                    source="user_selection" if preferred in selected else "explicit_feedback",
                    confidence=float(payload.get("selection_confidence", 0.95 if preferred in selected else 0.85)),
                    criticality=criticality,
                    hard_eligible=False,
                    event_id=f"{event_id}:explicit:{preferred}>{rejected}" if event_id else None,
                    provenance=provenance,
                )
            )

    accepted_sources = tuple(str(item) for item in payload.get("accepted_sources", []))
    if accepted_sources:
        output.append(
            RelevantSetEvidence(
                anchor,
                accepted_sources,
                candidate_k=int(payload.get("candidate_k", max(1, len(accepted_sources)))),
                min_recall=float(payload.get("min_recall", 1.0)),
                source="accepted_answer",
                confidence=float(payload.get("accepted_sources_confidence", 0.90)),
                criticality=criticality,
                hard_eligible=False,
                event_id=f"{event_id}:accepted-sources" if event_id else None,
                provenance=provenance,
            )
        )
    return output


def evidence_from_payload(payload: Mapping[str, Any]) -> list[Evidence]:
    kind = str(payload.get("type", "preference"))
    if kind == "preference":
        return [_preference_from_payload(payload)]
    if kind == "relevant_set":
        return [_relevant_set_from_payload(payload)]
    if kind == "trace":
        return list(evidence_from_trace(payload))
    if kind == "policy":
        patched = dict(payload)
        patched["source"] = "policy"
        patched["hard_eligible"] = bool(payload.get("hard_eligible", True))
        patched["confidence"] = float(payload.get("confidence", 1.0))
        patched["criticality"] = float(payload.get("criticality", 1.0))
        return [_preference_from_payload(patched)]
    raise ValueError(f"unknown acquisition evidence type: {kind}")


def load_evidence_jsonl(path: str | Path) -> list[Evidence]:
    events: list[Evidence] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("JSONL row must be an object")
            events.extend(evidence_from_payload(payload))
        except Exception as exc:
            raise ValueError(f"invalid acquisition evidence at line {line_number}: {exc}") from exc
    return events


def save_review_queue(items: Sequence[ReviewItem], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(_canonical_json(item.to_dict()) for item in items) + ("\n" if items else ""), encoding="utf-8")
    return output
