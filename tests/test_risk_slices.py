from semantic_atlas.risk_control import CalibrationEvent
from semantic_atlas.risk_slices import calibrate_semantic_risk_by_slice


def make_group(name, n, period, base=0.05):
    rows = []
    for i in range(n):
        proxy = base + 0.5 * (i / max(1, n - 1))
        loss = 1.0 if i % period == 0 else 0.0
        rows.append(CalibrationEvent(proxy, loss, group=name))
    return rows


def test_slice_portfolio_does_not_hide_bad_group_behind_good_average():
    events = make_group("good", 600, 40) + make_group("bad", 120, 2)
    portfolio = calibrate_semantic_risk_by_slice(
        events,
        target_risk=0.15,
        delta=0.10,
        min_group_events=80,
        min_selection=30,
        min_certification=40,
        threshold_candidates=6,
        seed=3,
    )

    assert "good" in portfolio.certified_slices
    assert "bad" in portfolio.uncertified_slices
    good_cert = portfolio.slice_certificates["good"]
    assert good_cert.threshold is not None
    assert portfolio.accepts(min(0.1, good_cert.threshold), group="good")
    assert not portfolio.accepts(0.1, group="bad")


def test_sparse_slice_is_explicitly_uncertified():
    events = make_group("large", 400, 50) + make_group("rare", 12, 50)
    portfolio = calibrate_semantic_risk_by_slice(
        events,
        target_risk=0.20,
        delta=0.10,
        min_group_events=60,
        min_selection=20,
        min_certification=30,
        seed=7,
    )
    assert "rare" in portfolio.uncertified_slices
    assert portfolio.slice_certificates["rare"].threshold is None
    assert not portfolio.accepts(0.0, group="rare")
