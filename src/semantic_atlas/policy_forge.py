from __future__ import annotations

"""Normative policy layer for Contract Forge.

A declared application policy is not a popularity vote.  Runtime clicks, selections and
other empirical evidence may reveal that production behavior conflicts with policy, but
they must never be able to overturn the policy itself.  This module keeps the original
Contract Forge as the empirical learner and composes an explicit normative layer above
it.
"""

from dataclasses import replace
from typing import Sequence

from .acquisition import (
    AcquisitionPolicy,
    ClauseCandidate,
    ContractAcquisitionReport,
    ContractAcquisitionResult,
    Evidence,
    PreferenceEvidence,
    RelevantSetEvidence,
    evidence_digest,
    forge_contract,
)
from .contracts import NeighborClause, SemanticContract, TripletClause


class PolicyConflictError(ValueError):
    """Raised when two explicit policies make mutually incompatible declarations."""


def _is_policy(event: Evidence) -> bool:
    return str(event.source) == "policy"


def _policy_preference_key(event: PreferenceEvidence) -> tuple[str, frozenset[str]]:
    return event.anchor, frozenset((event.preferred, event.rejected))


def _validate_policy_consistency(events: Sequence[Evidence]) -> None:
    directions: dict[tuple[str, frozenset[str]], tuple[str, str]] = {}
    for event in events:
        if not isinstance(event, PreferenceEvidence):
            continue
        key = _policy_preference_key(event)
        direction = (event.preferred, event.rejected)
        previous = directions.get(key)
        if previous is not None and previous != direction:
            raise PolicyConflictError(
                "contradictory normative policies for "
                f"anchor={event.anchor!r}: {previous[0]!r}>{previous[1]!r} and "
                f"{direction[0]!r}>{direction[1]!r}"
            )
        directions[key] = direction


def _policy_clauses(events: Sequence[Evidence], policy: AcquisitionPolicy):
    clauses = []
    seen_preferences: set[tuple[str, str, str]] = set()
    seen_sets: set[tuple[str, tuple[str, ...], int | None, float]] = set()
    for event in events:
        hard = bool(event.hard_eligible and float(event.criticality) >= policy.hard_min_criticality)
        if isinstance(event, PreferenceEvidence):
            key = (event.anchor, event.preferred, event.rejected)
            if key in seen_preferences:
                continue
            seen_preferences.add(key)
            clauses.append(
                TripletClause(
                    event.anchor,
                    event.preferred,
                    event.rejected,
                    margin=0.0,
                    weight=max(0.25, float(event.confidence)),
                    hard=hard,
                    source="policy",
                )
            )
        elif isinstance(event, RelevantSetEvidence):
            relevant = tuple(sorted(set(event.relevant)))
            key = (event.anchor, relevant, event.candidate_k, float(event.min_recall))
            if key in seen_sets:
                continue
            seen_sets.add(key)
            clauses.append(
                NeighborClause(
                    event.anchor,
                    relevant,
                    min_recall=event.min_recall,
                    candidate_k=event.candidate_k,
                    weight=max(0.25, float(event.confidence)),
                    hard=hard,
                    source="policy",
                )
            )
    return clauses


def _preference_direction(clause: TripletClause) -> tuple[str, str, str]:
    return clause.anchor, clause.positive, clause.negative


def forge_contract_with_policies(
    evidence: Sequence[Evidence],
    *,
    name: str = "application-semantics",
    version: str = "1",
    parent_digest: str | None = None,
    policy: AcquisitionPolicy | None = None,
    estimated_seconds_per_review: float = 20.0,
) -> ContractAcquisitionResult:
    """Forge a contract while treating explicit policies as normative truth.

    Policy-vs-policy contradiction fails closed.  Empirical evidence can be surfaced as
    conflicting provenance, but an opposite empirical clause is never allowed to replace
    or coexist with the normative direction.
    """

    policy = policy or AcquisitionPolicy()
    policy_events = [event for event in evidence if _is_policy(event)]
    empirical_events = [event for event in evidence if not _is_policy(event)]
    _validate_policy_consistency(policy_events)

    empirical = forge_contract(
        empirical_events,
        name=name,
        version=version,
        parent_digest=parent_digest,
        policy=policy,
        estimated_seconds_per_review=estimated_seconds_per_review,
    )
    normative_clauses = _policy_clauses(policy_events, policy)

    normative_directions = {
        _preference_direction(clause)
        for clause in normative_clauses
        if isinstance(clause, TripletClause)
    }
    normative_pairs = {
        (anchor, frozenset((preferred, rejected)))
        for anchor, preferred, rejected in normative_directions
    }

    kept_empirical = []
    suppressed_empirical = 0
    for clause in empirical.contract.clauses:
        if isinstance(clause, TripletClause):
            pair = (clause.anchor, frozenset((clause.positive, clause.negative)))
            if pair in normative_pairs:
                suppressed_empirical += 1
                continue
        kept_empirical.append(clause)

    source_counts: dict[str, int] = {}
    for event in evidence:
        source_counts[event.source] = source_counts.get(event.source, 0) + 1

    contract = SemanticContract(
        name=name,
        version=version,
        parent_digest=parent_digest,
        metadata={
            **dict(empirical.contract.metadata),
            "builder": "contract_forge_v2_normative",
            "evidence_digest": evidence_digest(evidence),
            "evidence_count": len(evidence),
            "source_counts": dict(sorted(source_counts.items())),
            "normative_policy_events": len(policy_events),
            "normative_clauses": len(normative_clauses),
            "empirical_clauses_suppressed_by_policy": suppressed_empirical,
        },
    )
    for clause in normative_clauses:
        contract.add(clause)
    for clause in kept_empirical:
        contract.add(clause)

    policy_candidates: list[ClauseCandidate] = []
    for clause in normative_clauses:
        if isinstance(clause, TripletClause):
            key = (clause.anchor, clause.positive, clause.negative)
            kind = "triplet"
        else:
            key = (clause.anchor, *clause.expected)
            kind = "neighbor"
        policy_candidates.append(
            ClauseCandidate(
                kind=kind,
                key=tuple(key),
                confidence=1.0,
                effective_support=1.0,
                opposition_support=0.0,
                criticality=1.0 if clause.hard else 0.0,
                hard_eligible=bool(clause.hard),
                sources=("policy",),
                evidence_ids=(),
                status="promoted",
                reason="normative policy",
            )
        )

    candidates = [*policy_candidates, *empirical.candidates]
    promoted_count = len(normative_clauses) + sum(
        candidate.status == "promoted" for candidate in empirical.candidates
    ) - suppressed_empirical
    review_count = sum(candidate.status == "review" for candidate in empirical.candidates)
    rejected_count = sum(candidate.status == "rejected" for candidate in empirical.candidates)
    conflict_count = empirical.report.conflict_count + suppressed_empirical
    review_minutes = empirical.report.estimated_review_minutes
    clauses_per_minute = 0.0 if review_minutes <= 0.0 else max(0, promoted_count) / review_minutes

    report = ContractAcquisitionReport(
        evidence_digest=evidence_digest(evidence),
        evidence_count=len(evidence),
        source_counts=source_counts,
        candidate_count=len(candidates),
        promoted_count=max(0, promoted_count),
        review_count=review_count,
        rejected_count=rejected_count,
        conflict_count=conflict_count,
        contract_digest=contract.digest,
        estimated_review_minutes=review_minutes,
        clauses_per_review_minute=clauses_per_minute,
    )
    return ContractAcquisitionResult(
        contract=contract,
        report=report,
        candidates=candidates,
        review_queue=empirical.review_queue,
    )
