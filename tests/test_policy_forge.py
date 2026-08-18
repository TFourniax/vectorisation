import pytest

from semantic_atlas.acquisition import AcquisitionPolicy, PreferenceEvidence
from semantic_atlas.contracts import TripletClause
from semantic_atlas.policy_forge import PolicyConflictError, forge_contract_with_policies


def test_single_explicit_policy_promotes_immediately_and_becomes_hard():
    evidence = [
        PreferenceEvidence(
            "q:overdose",
            "doc:emergency",
            "doc:marketing",
            source="policy",
            confidence=1.0,
            criticality=1.0,
            hard_eligible=True,
            event_id="policy-1",
        )
    ]

    result = forge_contract_with_policies(evidence, name="medical")

    assert len(result.contract.clauses) == 1
    clause = result.contract.clauses[0]
    assert isinstance(clause, TripletClause)
    assert clause.positive == "doc:emergency"
    assert clause.negative == "doc:marketing"
    assert clause.hard is True
    assert clause.source == "policy"
    assert result.report.promoted_count == 1


def test_behavioral_votes_cannot_reverse_normative_policy():
    evidence = [
        PreferenceEvidence(
            "q:delete",
            "doc:gdpr",
            "doc:newsletter",
            source="policy",
            confidence=1.0,
            criticality=1.0,
            hard_eligible=True,
        )
    ]
    evidence.extend(
        PreferenceEvidence(
            "q:delete",
            "doc:newsletter",
            "doc:gdpr",
            source="production_click",
            confidence=1.0,
            event_id=f"click-{index}",
        )
        for index in range(100)
    )

    result = forge_contract_with_policies(evidence, name="support")
    directions = [
        (clause.positive, clause.negative)
        for clause in result.contract.clauses
        if isinstance(clause, TripletClause)
    ]

    assert ("doc:gdpr", "doc:newsletter") in directions
    assert ("doc:newsletter", "doc:gdpr") not in directions
    assert result.contract.metadata["empirical_clauses_suppressed_by_policy"] >= 1


def test_contradictory_explicit_policies_fail_closed():
    evidence = [
        PreferenceEvidence("q", "a", "b", source="policy", hard_eligible=True),
        PreferenceEvidence("q", "b", "a", source="policy", hard_eligible=True),
    ]

    with pytest.raises(PolicyConflictError):
        forge_contract_with_policies(evidence)


def test_non_normative_evidence_still_uses_empirical_thresholds():
    evidence = [
        PreferenceEvidence("q", "a", "b", source="production_click", confidence=0.7)
    ]

    result = forge_contract_with_policies(
        evidence,
        policy=AcquisitionPolicy(auto_promote_confidence=0.85, min_effective_support=0.8),
    )

    assert result.contract.clauses == []
