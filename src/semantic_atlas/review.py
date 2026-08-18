from __future__ import annotations

"""Auditable human-review workflow for Contract Forge.

A review queue must be a reproducible artifact, not a UI side effect.  The bundle below
captures the exact proposed clause semantics required to make a decision later; review
decisions are hashed and the resulting contract links back to the auto-generated parent
contract.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .acquisition import (
    ContractAcquisitionResult,
    Evidence,
    PreferenceEvidence,
    RelevantSetEvidence,
    _event_identity,
)
from .contracts import NeighborClause, SemanticContract, TripletClause


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class ReviewProposal:
    proposal_id: str
    candidate_kind: str
    key: tuple[str, ...]
    confidence: float
    criticality: float
    sources: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    suggested_clause: Mapping[str, Any]
    priority: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "candidate_kind": self.candidate_kind,
            "key": list(self.key),
            "confidence": self.confidence,
            "criticality": self.criticality,
            "sources": list(self.sources),
            "evidence_ids": list(self.evidence_ids),
            "suggested_clause": dict(self.suggested_clause),
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReviewProposal":
        return cls(
            proposal_id=str(payload["proposal_id"]),
            candidate_kind=str(payload["candidate_kind"]),
            key=tuple(str(x) for x in payload.get("key", ())),
            confidence=float(payload["confidence"]),
            criticality=float(payload.get("criticality", 0.0)),
            sources=tuple(str(x) for x in payload.get("sources", ())),
            evidence_ids=tuple(str(x) for x in payload.get("evidence_ids", ())),
            suggested_clause=dict(payload["suggested_clause"]),
            priority=float(payload.get("priority", 0.0)),
        )


@dataclass(slots=True)
class ReviewBundle:
    parent_contract_digest: str
    evidence_digest: str
    proposals: list[ReviewProposal]
    format: str = "semantic-abi-review-bundle"
    format_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "format_version": self.format_version,
            "parent_contract_digest": self.parent_contract_digest,
            "evidence_digest": self.evidence_digest,
            "proposals": [proposal.to_dict() for proposal in self.proposals],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> "ReviewBundle":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("format") != "semantic-abi-review-bundle" or int(payload.get("format_version", 0)) != 1:
            raise ValueError("unsupported Semantic ABI review bundle")
        return cls(
            parent_contract_digest=str(payload["parent_contract_digest"]),
            evidence_digest=str(payload["evidence_digest"]),
            proposals=[ReviewProposal.from_dict(row) for row in payload.get("proposals", ())],
        )


@dataclass(slots=True, frozen=True)
class ReviewDecision:
    proposal_id: str
    decision: str
    hard: bool = False
    reviewer: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.decision not in {"accept", "reject"}:
            raise ValueError("review decision must be 'accept' or 'reject'")
        if self.decision == "reject" and self.hard:
            raise ValueError("a rejected proposal cannot be marked hard")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "decision": self.decision,
            "hard": self.hard,
            "reviewer": self.reviewer,
            "reason": self.reason,
        }


@dataclass(slots=True)
class ReviewApplicationResult:
    contract: SemanticContract
    accepted: int
    rejected: int
    unresolved: int
    decision_digest: str
    bundle_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_digest": self.contract.digest,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "unresolved": self.unresolved,
            "decision_digest": self.decision_digest,
            "bundle_digest": self.bundle_digest,
        }


def _proposal_id(candidate_kind: str, key: Sequence[str], evidence_ids: Sequence[str], suggested_clause: Mapping[str, Any]) -> str:
    return _digest(
        {
            "candidate_kind": candidate_kind,
            "key": list(key),
            "evidence_ids": sorted(str(x) for x in evidence_ids),
            "suggested_clause": dict(suggested_clause),
        }
    )


def build_review_bundle(result: ContractAcquisitionResult, evidence: Sequence[Evidence]) -> ReviewBundle:
    by_id = {_event_identity(event): event for event in evidence}
    proposals: list[ReviewProposal] = []
    for item in result.review_queue:
        candidate = item.candidate
        matched = [by_id[value] for value in candidate.evidence_ids if value in by_id]
        if len(matched) != len(candidate.evidence_ids):
            missing = sorted(set(candidate.evidence_ids) - set(by_id))
            raise ValueError(f"review candidate evidence is incomplete: {missing[:3]}")
        if candidate.kind == "triplet":
            anchor, preferred, rejected = candidate.key
            suggested = {
                "kind": "triplet",
                "anchor": anchor,
                "positive": preferred,
                "negative": rejected,
                "margin": 0.0,
                "weight": 0.25 + 0.75 * candidate.confidence,
            }
        elif candidate.kind == "neighbor":
            relevant_events = [event for event in matched if isinstance(event, RelevantSetEvidence)]
            if not relevant_events:
                raise ValueError("neighbor review proposal lacks RelevantSetEvidence")
            signatures = {
                (
                    event.anchor,
                    tuple(sorted(set(event.relevant))),
                    event.candidate_k,
                    float(event.min_recall),
                )
                for event in relevant_events
            }
            if len(signatures) != 1:
                raise ValueError("neighbor review proposal has ambiguous semantics")
            anchor, relevant, candidate_k, min_recall = next(iter(signatures))
            suggested = {
                "kind": "neighbor",
                "anchor": anchor,
                "expected": list(relevant),
                "candidate_k": candidate_k,
                "min_recall": min_recall,
                "weight": 0.25 + 0.75 * candidate.confidence,
            }
        else:
            raise ValueError(f"unsupported review candidate kind: {candidate.kind}")
        proposal_id = _proposal_id(candidate.kind, candidate.key, candidate.evidence_ids, suggested)
        proposals.append(
            ReviewProposal(
                proposal_id=proposal_id,
                candidate_kind=candidate.kind,
                key=tuple(candidate.key),
                confidence=float(candidate.confidence),
                criticality=float(candidate.criticality),
                sources=tuple(candidate.sources),
                evidence_ids=tuple(candidate.evidence_ids),
                suggested_clause=suggested,
                priority=float(item.priority),
            )
        )
    proposals.sort(key=lambda row: (-row.priority, row.proposal_id))
    return ReviewBundle(
        parent_contract_digest=result.contract.digest,
        evidence_digest=result.report.evidence_digest,
        proposals=proposals,
    )


def load_review_decisions_jsonl(path: str | Path) -> list[ReviewDecision]:
    output: list[ReviewDecision] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            output.append(
                ReviewDecision(
                    proposal_id=str(payload["proposal_id"]),
                    decision=str(payload["decision"]),
                    hard=bool(payload.get("hard", False)),
                    reviewer=None if payload.get("reviewer") is None else str(payload["reviewer"]),
                    reason=str(payload.get("reason", "")),
                )
            )
        except Exception as exc:
            raise ValueError(f"invalid review decision at line {line_number}: {exc}") from exc
    return output


def _clause_from_proposal(proposal: ReviewProposal, *, hard: bool):
    raw = proposal.suggested_clause
    source = "human_review:" + "+".join(proposal.sources)
    if raw["kind"] == "triplet":
        return TripletClause(
            str(raw["anchor"]),
            str(raw["positive"]),
            str(raw["negative"]),
            margin=float(raw.get("margin", 0.0)),
            weight=float(raw.get("weight", 1.0)),
            hard=hard,
            source=source,
        )
    if raw["kind"] == "neighbor":
        return NeighborClause(
            str(raw["anchor"]),
            tuple(str(x) for x in raw.get("expected", ())),
            min_recall=float(raw.get("min_recall", 0.6)),
            candidate_k=None if raw.get("candidate_k") is None else int(raw["candidate_k"]),
            weight=float(raw.get("weight", 1.0)),
            hard=hard,
            source=source,
        )
    raise ValueError(f"unsupported reviewed clause kind: {raw.get('kind')!r}")


def apply_review_decisions(
    parent: SemanticContract,
    bundle: ReviewBundle,
    decisions: Sequence[ReviewDecision],
    *,
    version: str,
    allow_hard: bool = False,
) -> ReviewApplicationResult:
    if parent.digest != bundle.parent_contract_digest:
        raise ValueError("review bundle does not belong to the supplied parent contract")
    proposals = {proposal.proposal_id: proposal for proposal in bundle.proposals}
    seen: dict[str, ReviewDecision] = {}
    for decision in decisions:
        if decision.proposal_id not in proposals:
            raise ValueError(f"unknown review proposal: {decision.proposal_id}")
        if decision.proposal_id in seen:
            raise ValueError(f"duplicate review decision: {decision.proposal_id}")
        if decision.hard and not allow_hard:
            raise ValueError("hard promotion requires allow_hard=True")
        seen[decision.proposal_id] = decision

    decision_payload = [seen[key].to_dict() for key in sorted(seen)]
    decision_digest = _digest(decision_payload)
    accepted = [decision for decision in seen.values() if decision.decision == "accept"]
    rejected = [decision for decision in seen.values() if decision.decision == "reject"]
    unresolved = len(proposals) - len(seen)

    contract = SemanticContract(
        name=parent.name,
        version=str(version),
        parent_digest=parent.digest,
        metadata={
            **dict(parent.metadata),
            "builder": "contract_review_v1",
            "review_bundle_digest": bundle.digest,
            "review_decision_digest": decision_digest,
            "review_accepted": len(accepted),
            "review_rejected": len(rejected),
            "review_unresolved": unresolved,
        },
    )
    for clause in parent.clauses:
        contract.add(clause)
    for decision in accepted:
        contract.add(_clause_from_proposal(proposals[decision.proposal_id], hard=decision.hard))

    return ReviewApplicationResult(
        contract=contract,
        accepted=len(accepted),
        rejected=len(rejected),
        unresolved=unresolved,
        decision_digest=decision_digest,
        bundle_digest=bundle.digest,
    )
