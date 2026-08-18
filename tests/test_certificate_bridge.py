import pytest

from semantic_atlas.certificate_bridge import certificate_from_change_report
from semantic_atlas.change_control import (
    ChangeFacet,
    ChangeKind,
    ChangeSet,
    Comparator,
    CompatibilityContract,
    CompatibilityRule,
    MeaningFrame,
    ProbeObservation,
    SystemRun,
    evaluate_change,
)
from semantic_atlas.linker import CertificateVerdict


def run(candidate_claims):
    contract = CompatibilityContract(
        name="component-slot",
        version="1",
        rules=(
            CompatibilityRule(
                "claim-preservation",
                "claims",
                Comparator.BASELINE_RECALL,
                threshold=1.0,
            ),
        ),
    )
    baseline = SystemRun(
        "component@old",
        "manifest-old",
        (
            ProbeObservation(
                "probe",
                "family",
                "canonical",
                MeaningFrame(claims=frozenset({"must-survive"})),
            ),
        ),
    )
    candidate = SystemRun(
        "component@new",
        "manifest-new",
        (
            ProbeObservation(
                "probe",
                "family",
                "canonical",
                MeaningFrame(claims=frozenset(candidate_claims)),
            ),
        ),
    )
    changes = ChangeSet(
        "component@old",
        "component@new",
        (ChangeFacet(ChangeKind.MODEL, "model"),),
    )
    return evaluate_change(contract, changes, baseline, candidate)


def test_compatible_report_becomes_evidence_bound_linker_certificate():
    report = run({"must-survive", "new-safe-claim"})

    certificate = certificate_from_change_report(
        report,
        baseline_component_id="component@old",
        candidate_component_id="component@new",
        issuer="semantic-abi-ci",
        issued_at="2026-08-18T08:00:00+00:00",
        environment_digest="prod-eu",
    )

    assert certificate.verdict == CertificateVerdict.COMPATIBLE
    assert certificate.contract_digest == report.contract_digest
    assert certificate.evidence_digest == report.evidence_digest
    assert certificate.probe_coverage == 1.0


def test_breaking_report_cannot_be_promoted_to_dependency_proof():
    report = run(set())

    with pytest.raises(ValueError, match="cannot certify"):
        certificate_from_change_report(
            report,
            baseline_component_id="component@old",
            candidate_component_id="component@new",
            issuer="semantic-abi-ci",
            issued_at="2026-08-18T08:00:00+00:00",
        )
