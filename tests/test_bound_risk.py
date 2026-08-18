import json

import pytest

from semantic_atlas.certification_io import BoundRiskCertificate
from semantic_atlas.risk_control import RiskCertificate


def _certificate():
    return RiskCertificate(
        target_risk=0.1,
        delta=0.05,
        threshold=0.2,
        empirical_risk=0.01,
        upper_risk_bound=0.08,
        accepted_calibration=100,
        certification_size=100,
        total_events=200,
        estimated_coverage=0.5,
        candidate_count=3,
        certified=True,
        method="test",
        reason="fixture",
    )


def test_bound_risk_round_trip_requires_matching_contract_and_candidate(tmp_path):
    artifact = BoundRiskCertificate(
        certificate=_certificate(),
        contract_digest="contract-a",
        oracle_manifest_digest="candidate-a",
        calibration_evidence_digest="events-a",
    )
    path = tmp_path / "risk.json"
    artifact.save(path)

    loaded = BoundRiskCertificate.load(
        path,
        contract_digest="contract-a",
        oracle_manifest_digest="candidate-a",
    )
    assert loaded == artifact
    assert loaded.digest == artifact.digest

    with pytest.raises(ValueError, match="different Semantic Contract"):
        BoundRiskCertificate.load(path, contract_digest="contract-b")
    with pytest.raises(ValueError, match="different candidate oracle manifest"):
        BoundRiskCertificate.load(path, oracle_manifest_digest="candidate-b")


def test_bound_risk_binding_tamper_is_detected(tmp_path):
    artifact = BoundRiskCertificate(
        certificate=_certificate(),
        contract_digest="contract-a",
        oracle_manifest_digest="candidate-a",
        calibration_evidence_digest="events-a",
    )
    path = tmp_path / "risk.json"
    artifact.save(path)

    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["artifact"]["binding"]["oracle_manifest_digest"] = "candidate-b"
    path.write_text(json.dumps(envelope), encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        BoundRiskCertificate.load(path)
