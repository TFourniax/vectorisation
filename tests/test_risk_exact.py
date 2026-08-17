import numpy as np

from semantic_atlas.risk_control import CalibrationEvent, bernoulli_kl_upper_bound
from semantic_atlas.risk_exact import exact_binomial_upper_bound, calibrate_semantic_risk_preregistered


def test_exact_binomial_upper_bound_matches_known_zero_failure_case():
    losses = np.zeros(100, dtype=np.float64)
    upper = exact_binomial_upper_bound(losses, delta=0.05)
    expected = 1.0 - 0.05 ** (1.0 / 100.0)
    assert abs(upper - expected) < 1e-8


def test_exact_fixed_rule_bound_is_tighter_than_chernoff_kl_on_scifact_sized_sample():
    losses = np.asarray([1.0] * 7 + [0.0] * 80, dtype=np.float64)
    exact = exact_binomial_upper_bound(losses, delta=0.10)
    kl = bernoulli_kl_upper_bound(losses, delta=0.10)
    assert 0.13 < exact < 0.132
    assert exact < kl


def test_preregistered_calibration_certifies_without_post_holdout_threshold_search():
    events = []
    for i in range(1200):
        proxy = i / 1199
        if proxy < 0.45:
            loss = 1.0 if i % 31 == 0 else 0.0
        else:
            loss = 1.0 if i % 3 == 0 else 0.0
        events.append(CalibrationEvent(proxy, loss))

    certificate = calibrate_semantic_risk_preregistered(
        events,
        target_risk=0.12,
        delta=0.05,
        threshold_candidates=10,
        min_selection=80,
        min_certification=100,
        seed=9,
    )

    assert certificate.method == "split-preregistered-exact-binomial"
    assert certificate.candidate_count == 1
    assert certificate.certified
    assert certificate.threshold is not None
    assert certificate.upper_risk_bound <= 0.12


def test_preregistered_calibration_abstains_when_sample_is_too_small():
    certificate = calibrate_semantic_risk_preregistered(
        [CalibrationEvent(0.1, 0.0) for _ in range(12)],
        min_selection=10,
        min_certification=10,
    )
    assert not certificate.certified
    assert certificate.threshold is None
    assert "insufficient" in certificate.reason
