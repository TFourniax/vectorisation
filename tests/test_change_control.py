from semantic_atlas.change_control import (
    ChangeFacet,
    ChangeKind,
    ChangeSet,
    Comparator,
    CompatibilityContract,
    CompatibilityRule,
    CompatibilityStatus,
    MeaningFrame,
    ProbeObservation,
    RolloutDecision,
    RuleScope,
    SystemRun,
    contract_from_dict,
    evaluate_change,
    report_to_dict,
)


def obs(probe_id, *, family="f1", variant="canonical", claims=(), retrieved=(), tools=(), effects=(), scores=None):
    return ProbeObservation(
        probe_id=probe_id,
        family_id=family,
        variant_id=variant,
        frame=MeaningFrame(
            claims=frozenset(claims),
            retrieved=frozenset(retrieved),
            tools=frozenset(tools),
            effects=frozenset(effects),
            scores=scores or {},
        ),
    )


def base_changes(*kinds):
    return ChangeSet(
        baseline_system="prod@1",
        candidate_system="candidate@2",
        facets=tuple(ChangeFacet(kind=k, name=k.value) for k in kinds),
    )


def test_model_swap_is_compatible_when_meaning_contract_survives():
    contract = CompatibilityContract(
        name="support-agent",
        version="1.0",
        rules=(
            CompatibilityRule(
                "claims",
                "claims",
                Comparator.BASELINE_RECALL,
                threshold=1.0,
                depends_on=(ChangeKind.MODEL,),
            ),
            CompatibilityRule("effects", "effects", Comparator.EXACT),
        ),
    )
    baseline = SystemRun("prod@1", "m1", (obs("p1", claims={"refund:30d"}, effects={"no-write"}),))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", claims={"refund:30d", "refund:method"}, effects={"no-write"}),))

    report = evaluate_change(contract, base_changes(ChangeKind.MODEL), baseline, candidate)

    assert report.status == CompatibilityStatus.COMPATIBLE
    assert report.rollout == RolloutDecision.ALLOW
    assert report.semantic_version_bump == "patch"
    assert report.hard_violations == ()


def test_breaking_claim_loss_blocks_release_and_localizes_change():
    contract = CompatibilityContract(
        name="legal-rag",
        version="1.0",
        rules=(
            CompatibilityRule(
                "claim-preservation",
                "claims",
                Comparator.BASELINE_RECALL,
                threshold=1.0,
                depends_on=(ChangeKind.RETRIEVER, ChangeKind.CORPUS),
            ),
        ),
    )
    baseline = SystemRun("prod@1", "m1", (obs("p1", claims={"a", "b"}),))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", claims={"a"}),))

    report = evaluate_change(
        contract,
        base_changes(ChangeKind.RETRIEVER, ChangeKind.MODEL),
        baseline,
        candidate,
    )

    assert report.status == CompatibilityStatus.BREAKING
    assert report.rollout == RolloutDecision.BLOCK
    assert report.semantic_version_bump == "major"
    assert report.hard_violations[0].observed == 0.5
    assert "retriever:retriever" in report.suspicious_facets
    assert "model:model" not in report.suspicious_facets


def test_metamorphic_rule_catches_semantic_instability_without_ground_truth():
    contract = CompatibilityContract(
        name="faq",
        version="1.0",
        rules=(
            CompatibilityRule(
                "paraphrase-invariance",
                "claims",
                Comparator.EXACT,
                scope=RuleScope.METAMORPHIC,
                depends_on=(ChangeKind.MODEL, ChangeKind.PROMPT),
            ),
            CompatibilityRule("baseline", "claims", Comparator.EXACT),
        ),
    )
    baseline = SystemRun(
        "prod@1",
        "m1",
        (
            obs("q-canon", family="q", variant="canonical", claims={"answer:a"}),
            obs("q-para", family="q", variant="paraphrase", claims={"answer:a"}),
        ),
    )
    candidate = SystemRun(
        "candidate@2",
        "m2",
        (
            obs("q-canon", family="q", variant="canonical", claims={"answer:a"}),
            obs("q-para", family="q", variant="paraphrase", claims={"answer:b"}),
        ),
    )

    report = evaluate_change(contract, base_changes(ChangeKind.MODEL), baseline, candidate)

    assert report.status == CompatibilityStatus.BREAKING
    assert any(w.rule_id == "paraphrase-invariance" for w in report.hard_violations)


def test_missing_probe_fails_closed_as_insufficient_evidence():
    contract = CompatibilityContract(
        name="rag",
        version="1.0",
        rules=(CompatibilityRule("claims", "claims", Comparator.EXACT),),
        minimum_probe_coverage=1.0,
    )
    baseline = SystemRun("prod@1", "m1", (obs("p1", claims={"a"}), obs("p2", claims={"b"}, family="f2")))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", claims={"a"}),))

    report = evaluate_change(contract, base_changes(ChangeKind.MODEL), baseline, candidate)

    assert report.status == CompatibilityStatus.INSUFFICIENT_EVIDENCE
    assert report.rollout == RolloutDecision.BLOCK
    assert report.probe_coverage == 0.5
    assert any("candidate_missing:p2" in item for item in report.missing_evidence)


def test_soft_regression_inside_budget_requests_canary():
    contract = CompatibilityContract(
        name="search",
        version="1.0",
        rules=(
            CompatibilityRule(
                "retrieval-overlap",
                "retrieved",
                Comparator.JACCARD,
                threshold=0.8,
                hard=False,
                weight=0.5,
            ),
        ),
        max_soft_regression_weight=0.5,
    )
    baseline = SystemRun("prod@1", "m1", (obs("p1", retrieved={"a", "b", "c"}),))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", retrieved={"a", "b", "x"}),))

    report = evaluate_change(contract, base_changes(ChangeKind.RETRIEVER), baseline, candidate)

    assert report.status == CompatibilityStatus.CONDITIONAL
    assert report.rollout == RolloutDecision.CANARY
    assert report.semantic_version_bump == "minor"


def test_numeric_rules_can_guard_cost_or_quality_surfaces():
    contract = CompatibilityContract(
        name="quality",
        version="1.0",
        rules=(
            CompatibilityRule("quality-floor", "score:groundedness", Comparator.NUMERIC_FLOOR, threshold=0.9),
            CompatibilityRule("cost-ceiling", "score:cost", Comparator.NUMERIC_CEILING, threshold=0.03, hard=False),
        ),
        max_soft_regression_weight=1.0,
    )
    baseline = SystemRun("prod@1", "m1", (obs("p1", scores={"groundedness": 0.95, "cost": 0.02}),))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", scores={"groundedness": 0.93, "cost": 0.04}),))

    report = evaluate_change(contract, base_changes(ChangeKind.MODEL), baseline, candidate)

    assert report.status == CompatibilityStatus.CONDITIONAL
    assert report.soft_violations[0].rule_id == "cost-ceiling"


def test_contract_loader_and_report_digest_are_deterministic():
    payload = {
        "name": "demo",
        "version": "1",
        "rules": [
            {
                "rule_id": "preserve",
                "target": "claims",
                "comparator": "baseline_recall",
                "threshold": 1.0,
                "depends_on": ["model"],
            }
        ],
    }
    contract = contract_from_dict(payload)
    baseline = SystemRun("prod@1", "m1", (obs("p1", claims={"a"}),))
    candidate = SystemRun("candidate@2", "m2", (obs("p1", claims={"a"}),))
    changes = base_changes(ChangeKind.MODEL)

    report1 = evaluate_change(contract, changes, baseline, candidate)
    report2 = evaluate_change(contract, changes, baseline, candidate)

    assert report1.evidence_digest == report2.evidence_digest
    assert report_to_dict(report1)["evidence_digest"] == report1.evidence_digest
