import pytest

from semantic_atlas.acquisition import AcquisitionPolicy, PreferenceEvidence, RelevantSetEvidence, forge_contract
from semantic_atlas.review import ReviewDecision, apply_review_decisions, build_review_bundle


def _review_policy():
    return AcquisitionPolicy(
        auto_promote_confidence=0.99,
        review_confidence=0.50,
        min_effective_support=10.0,
    )


def test_review_bundle_preserves_neighbor_clause_semantics_and_acceptance_lineage():
    evidence = [
        RelevantSetEvidence(
            "q:invoice",
            ("doc:invoice", "doc:billing-policy"),
            candidate_k=5,
            min_recall=0.5,
            source="human_judgment",
            confidence=0.9,
            event_id="judgment-1",
        )
    ]
    acquired = forge_contract(evidence, name="support", version="1", policy=_review_policy())
    assert acquired.contract.clauses == []
    assert len(acquired.review_queue) == 1

    bundle = build_review_bundle(acquired, evidence)
    proposal = bundle.proposals[0]
    assert proposal.suggested_clause["candidate_k"] == 5
    assert proposal.suggested_clause["min_recall"] == 0.5
    assert proposal.suggested_clause["expected"] == ["doc:billing-policy", "doc:invoice"]

    applied = apply_review_decisions(
        acquired.contract,
        bundle,
        [ReviewDecision(proposal.proposal_id, "accept", reviewer="expert")],
        version="2",
    )

    assert applied.accepted == 1
    assert applied.unresolved == 0
    assert applied.contract.parent_digest == acquired.contract.digest
    assert len(applied.contract.clauses) == 1
    clause = applied.contract.clauses[0]
    assert clause.candidate_k == 5
    assert clause.min_recall == 0.5
    assert clause.hard is False
    assert applied.contract.metadata["review_bundle_digest"] == bundle.digest


def test_hard_review_requires_explicit_authorization():
    evidence = [
        PreferenceEvidence(
            "q:delete",
            "doc:gdpr",
            "doc:newsletter",
            confidence=0.9,
            event_id="judgment-1",
        )
    ]
    acquired = forge_contract(evidence, policy=_review_policy())
    bundle = build_review_bundle(acquired, evidence)
    proposal = bundle.proposals[0]
    decision = ReviewDecision(proposal.proposal_id, "accept", hard=True)

    with pytest.raises(ValueError, match="allow_hard=True"):
        apply_review_decisions(acquired.contract, bundle, [decision], version="2")

    applied = apply_review_decisions(
        acquired.contract,
        bundle,
        [decision],
        version="2",
        allow_hard=True,
    )
    assert applied.contract.clauses[0].hard is True


def test_review_bundle_rejects_wrong_parent_and_duplicate_decisions():
    evidence = [PreferenceEvidence("q", "a", "b", confidence=0.9, event_id="j1")]
    acquired = forge_contract(evidence, policy=_review_policy())
    bundle = build_review_bundle(acquired, evidence)
    proposal_id = bundle.proposals[0].proposal_id

    other = forge_contract([], name="other").contract
    with pytest.raises(ValueError, match="does not belong"):
        apply_review_decisions(other, bundle, [], version="2")

    decision = ReviewDecision(proposal_id, "reject")
    with pytest.raises(ValueError, match="duplicate review decision"):
        apply_review_decisions(acquired.contract, bundle, [decision, decision], version="2")
