import numpy as np

from semantic_atlas.contracts import ContractReport
from semantic_atlas.risk_control import (
    CalibrationEvent,
    CertifiedSemanticABIGate,
    RiskCertificate,
    bernoulli_kl_upper_bound,
    calibrate_semantic_risk,
)


def test_kl_upper_bound_is_above_empirical_loss_and_tightens_with_more_data():
    small = np.array([1.0] * 5 + [0.0] * 95)
    large = np.array([1.0] * 25 + [0.0] * 475)
    upper_small = bernoulli_kl_upper_bound(small, delta=0.05)
    upper_large = bernoulli_kl_upper_bound(large, delta=0.05)
    assert upper_small >= 0.05
    assert upper_large >= 0.05
    assert upper_large < upper_small


def test_calibration_certifies_only_low_risk_region():
    events = []
    # The low-proxy half has sparse failures; the high-proxy half fails often.
    for i in range(1200):
        proxy = i / 1199
        if proxy < 0.45:
            loss = 1.0 if i % 31 == 0 else 0.0
        else:
            loss = 1.0 if i % 3 == 0 else 0.0
        events.append(CalibrationEvent(proxy, loss))

    certificate = calibrate_semantic_risk(
        events,
        target_risk=0.12,
        delta=0.05,
        threshold_candidates=10,
        min_selection=80,
        min_certification=100,
        seed=9,
    )
    assert certificate.certified
    assert certificate.threshold is not None
    assert certificate.threshold < 0.60
    assert certificate.upper_risk_bound <= 0.12
    assert certificate.accepts(certificate.threshold)
    assert not certificate.accepts(min(1.0, certificate.threshold + 0.30))


def test_calibration_abstains_when_evidence_is_insufficient():
    certificate = calibrate_semantic_risk(
        [CalibrationEvent(0.1, 0.0) for _ in range(12)],
        min_selection=10,
        min_certification=10,
    )
    assert not certificate.certified
    assert certificate.threshold is None
    assert "insufficient" in certificate.reason


def test_certified_gate_accepts_safe_region_and_rejects_risky_region():
    report = ContractReport(
        contract_name="demo",
        contract_digest="abc",
        implementation="candidate",
        score=0.95,
        hard_pass=True,
        clause_results=[],
        object_risk={"safe": 0.02, "risky": 0.90},
        evaluated_clauses=0,
        missing_clauses=0,
    )
    landmarks = {
        "safe": np.array([1.0, 0.0], dtype=np.float32),
        "risky": np.array([0.0, 1.0], dtype=np.float32),
    }
    certificate = RiskCertificate(
        target_risk=0.10,
        delta=0.05,
        threshold=0.20,
        empirical_risk=0.03,
        upper_risk_bound=0.08,
        accepted_calibration=100,
        certification_size=150,
        total_events=300,
        estimated_coverage=2 / 3,
        candidate_count=5,
        certified=True,
        method="test",
        reason="test certificate",
    )
    gate = CertifiedSemanticABIGate({"candidate": (report, landmarks, certificate)})

    safe = gate.choose({"candidate": np.array([1.0, 0.0], dtype=np.float32)})
    risky = gate.choose({"candidate": np.array([0.0, 1.0], dtype=np.float32)})

    assert safe.accepted and safe.implementation == "candidate"
    assert safe.certificate_upper_risk == 0.08
    assert not risky.accepted
    assert "exceeds certified threshold" in risky.reason
