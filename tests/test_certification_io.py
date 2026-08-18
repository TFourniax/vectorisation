import json

import pytest

from semantic_atlas.adequacy import ContractAdequacyEvidence, ContractAdequacyRequirements, assess_contract_adequacy
from semantic_atlas.certification_io import (
    assess_adequacy_spec,
    load_adequacy_report,
    load_risk_certificate,
    risk_certificate_digest,
    save_adequacy_report,
    save_risk_certificate,
)
from semantic_atlas.risk_control import RiskCertificate


def _risk(certified=True):
    return RiskCertificate(
        target_risk=0.10,
        delta=0.05,
        threshold=0.2 if certified else None,
        empirical_risk=0.01 if certified else 1.0,
        upper_risk_bound=0.08 if certified else 1.0,
        accepted_calibration=100 if certified else 0,
        certification_size=100,
        total_events=200,
        estimated_coverage=0.5 if certified else 0.0,
        candidate_count=4,
        certified=certified,
        method="test",
        reason="fixture",
    )


def test_risk_certificate_round_trip_and_tamper_detection(tmp_path):
    path = tmp_path / "risk.json"
    certificate = _risk()
    save_risk_certificate(certificate, path)

    loaded = load_risk_certificate(path)
    assert loaded == certificate
    assert risk_certificate_digest(loaded) == risk_certificate_digest(certificate)

    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["certificate"]["upper_risk_bound"] = 0.99
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_risk_certificate(path)


def test_adequacy_report_is_recomputed_and_bound_to_contract(tmp_path):
    report = assess_contract_adequacy(
        ContractAdequacyEvidence(contract_digest="abc", object_coverage=0.95, heldout_cases=500),
        ContractAdequacyRequirements(min_object_coverage=0.90, min_heldout_cases=100),
    )
    path = tmp_path / "adequacy.json"
    save_adequacy_report(report, path)

    loaded = load_adequacy_report(path, contract_digest="abc")
    assert loaded.status == "adequate"
    assert loaded.digest == report.digest

    with pytest.raises(ValueError, match="different Semantic Contract"):
        load_adequacy_report(path, contract_digest="different")


def test_adequacy_spec_does_not_treat_missing_evidence_as_pass(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "evidence": {"contract_digest": "abc", "object_coverage": 0.99},
                "requirements": {"min_object_coverage": 0.9, "min_heldout_cases": 100},
            }
        ),
        encoding="utf-8",
    )

    report = assess_adequacy_spec(spec, contract_digest="abc")

    assert report.status == "insufficient_evidence"
    states = {check.name: check.state for check in report.checks}
    assert states["object_coverage"] == "pass"
    assert states["heldout_cases"] == "missing"
