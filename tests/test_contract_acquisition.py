from semantic_atlas.acquisition import (
    AcquisitionPolicy,
    PreferenceEvidence,
    RelevantSetEvidence,
    evidence_digest,
    evidence_from_trace,
    forge_contract,
)


def test_evidence_digest_is_order_independent():
    first = PreferenceEvidence("q:1", "doc:a", "doc:b", event_id="a")
    second = PreferenceEvidence("q:2", "doc:c", "doc:d", event_id="b")
    assert evidence_digest([first, second]) == evidence_digest([second, first])


def test_trace_click_only_prefers_clicked_over_skipped_above():
    evidence = evidence_from_trace(
        {
            "type": "trace",
            "anchor": "q:1",
            "results": ["doc:a", "doc:b", "doc:c"],
            "clicked": ["doc:b"],
            "event_id": "trace-1",
        }
    )
    pairs = {(event.preferred, event.rejected) for event in evidence if isinstance(event, PreferenceEvidence)}
    assert ("doc:b", "doc:a") in pairs
    assert ("doc:b", "doc:c") not in pairs


def test_contradictory_preferences_are_not_auto_promoted():
    evidence = []
    for index in range(4):
        evidence.append(PreferenceEvidence("q:1", "doc:a", "doc:b", source="human_judgment", event_id=f"a-{index}"))
        evidence.append(PreferenceEvidence("q:1", "doc:b", "doc:a", source="human_judgment", event_id=f"b-{index}"))
    result = forge_contract(evidence, name="conflict")
    assert len(result.contract.clauses) == 0
    assert result.report.conflict_count == 1
    assert result.report.review_count == 1
    assert result.review_queue[0].candidate.reason == "contradictory evidence"


def test_repeated_weak_behavior_can_promote_only_a_soft_clause():
    evidence = [
        PreferenceEvidence(
            "q:1",
            "doc:a",
            "doc:b",
            source="production_click",
            confidence=0.70,
            hard_eligible=False,
            event_id=f"click-{index}",
        )
        for index in range(12)
    ]
    result = forge_contract(evidence, name="behavior")
    assert result.report.promoted_count == 1
    assert len(result.contract.clauses) == 1
    assert result.contract.clauses[0].hard is False


def test_explicit_policy_can_be_promoted_as_hard_with_a_policy_override():
    policy = AcquisitionPolicy(
        auto_promote_confidence=0.70,
        min_effective_support=0.80,
        hard_confidence=0.70,
        hard_min_criticality=0.80,
    )
    evidence = [
        PreferenceEvidence(
            "q:overdose",
            "doc:emergency",
            "doc:marketing",
            source="policy",
            confidence=1.0,
            criticality=1.0,
            hard_eligible=True,
            event_id="medical-policy-1",
        )
    ]
    result = forge_contract(evidence, name="safety", policy=policy)
    assert result.report.promoted_count == 1
    assert result.contract.clauses[0].hard is True


def test_relevant_sets_compile_to_neighbor_clauses_after_support_accumulates():
    evidence = [
        RelevantSetEvidence(
            "q:delete-account",
            ("doc:gdpr-delete", "doc:identity-check"),
            candidate_k=5,
            min_recall=1.0,
            source="human_judgment",
            event_id=f"judgment-{index}",
        )
        for index in range(4)
    ]
    result = forge_contract(evidence, name="account")
    assert result.report.promoted_count == 1
    clause = result.contract.clauses[0]
    assert clause.anchor == "q:delete-account"
    assert set(clause.expected) == {"doc:gdpr-delete", "doc:identity-check"}
    assert clause.candidate_k == 5
