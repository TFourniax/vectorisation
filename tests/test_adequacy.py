from semantic_atlas.adequacy import (
    ContractAdequacyEvidence,
    ContractAdequacyRequirements,
    assess_contract_adequacy,
)


def test_adequacy_is_separate_from_missing_evidence():
    evidence = ContractAdequacyEvidence(
        contract_digest="abc",
        object_coverage=0.72,
        mutation_kill_rate=1.0,
    )
    requirements = ContractAdequacyRequirements(
        min_object_coverage=0.60,
        min_mutation_kill_rate=0.90,
        min_predictive_correlation=0.70,
    )
    report = assess_contract_adequacy(evidence, requirements)
    assert report.status == "insufficient_evidence"
    assert not report.adequate
    assert [check.state for check in report.checks] == ["pass", "pass", "missing"]


def test_adequacy_can_fail_even_when_some_axes_are_strong():
    evidence = ContractAdequacyEvidence(
        contract_digest="abc",
        object_coverage=0.90,
        mutation_kill_rate=1.0,
        predictive_correlation=0.62,
        baseline_predictive_correlation=0.68,
        heldout_cases=500,
        datasets=3,
    )
    requirements = ContractAdequacyRequirements(
        min_object_coverage=0.75,
        min_mutation_kill_rate=0.90,
        min_predictive_correlation=0.65,
        min_predictive_lift_over_baseline=0.0,
        min_heldout_cases=300,
        min_datasets=3,
    )
    report = assess_contract_adequacy(evidence, requirements)
    assert report.status == "failed"
    assert evidence.predictive_lift_over_baseline is not None
    assert evidence.predictive_lift_over_baseline < 0.0
    assert {check.name: check.state for check in report.checks}["predictive_correlation"] == "fail"
    assert {check.name: check.state for check in report.checks}["predictive_lift_over_baseline"] == "fail"


def test_adequacy_requires_an_explicit_policy_and_has_stable_digest():
    evidence = ContractAdequacyEvidence(
        contract_digest="abc",
        object_coverage=0.8,
        predictive_correlation=0.9,
        baseline_predictive_correlation=0.7,
        heldout_cases=600,
        datasets=4,
        fault_families=5,
    )
    requirements = ContractAdequacyRequirements(
        min_object_coverage=0.5,
        min_predictive_correlation=0.8,
        min_predictive_lift_over_baseline=0.1,
        min_heldout_cases=500,
        min_datasets=3,
        min_fault_families=4,
    )
    first = assess_contract_adequacy(evidence, requirements)
    second = assess_contract_adequacy(evidence, requirements)
    assert first.status == "adequate"
    assert first.digest == second.digest

    try:
        assess_contract_adequacy(evidence, ContractAdequacyRequirements())
    except ValueError as exc:
        assert "at least one explicit requirement" in str(exc)
    else:
        raise AssertionError("an adequacy policy without requirements must not pass")
