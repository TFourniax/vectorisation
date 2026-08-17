from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from .risk_control import CalibrationEvent, RiskCertificate

_EPS = 1e-12


def _binomial_cdf(k: int, n: int, p: float) -> float:
    """Stable Binomial(n, p) CDF up to k using log-sum-exp."""
    if n < 0 or k < 0:
        return 0.0
    if k >= n:
        return 1.0
    p = float(np.clip(p, 0.0, 1.0))
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0

    log_p = math.log(p)
    log_q = math.log1p(-p)
    logs = [
        math.lgamma(n + 1)
        - math.lgamma(i + 1)
        - math.lgamma(n - i + 1)
        + i * log_p
        + (n - i) * log_q
        for i in range(k + 1)
    ]
    peak = max(logs)
    return float(math.exp(peak) * sum(math.exp(value - peak) for value in logs))


def exact_binomial_upper_bound(losses: Sequence[float] | np.ndarray, *, delta: float) -> float:
    """One-sided exact Clopper-Pearson-style upper bound for Bernoulli risk.

    This inverts the binomial lower tail for a *fixed, pre-specified* selection
    rule. It is useful when a rollout threshold has been chosen on independent
    data and only one rule is certified on the holdout. It must not be used as
    if it corrected for choosing the best of many thresholds on the same
    certification sample.
    """
    x = np.asarray(losses, dtype=np.float64).reshape(-1)
    if len(x) == 0:
        return 1.0
    if np.any((x != 0.0) & (x != 1.0)):
        raise ValueError("exact binomial bound requires Bernoulli losses")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")

    n = len(x)
    failures = int(np.sum(x))
    if failures >= n:
        return 1.0

    lo = failures / n
    hi = 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        cdf = _binomial_cdf(failures, n, mid)
        if cdf > delta:
            lo = mid
        else:
            hi = mid
    return float(np.clip(hi, 0.0, 1.0))


def calibrate_semantic_risk_preregistered(
    events: Sequence[CalibrationEvent],
    *,
    target_risk: float = 0.10,
    delta: float = 0.05,
    selection_fraction: float = 0.5,
    threshold_candidates: int = 12,
    min_selection: int = 20,
    min_certification: int = 30,
    selection_risk_fraction: float = 0.75,
    seed: int = 17,
) -> RiskCertificate:
    """Certify one threshold selected before viewing certification labels.

    The selection split proposes proxy-risk quantiles and chooses the broadest
    rule whose empirical loss is below a stricter *selection budget*:
    ``target_risk * selection_risk_fraction``. The default 0.75 reserves room
    for finite-sample uncertainty; it is a candidate-selection heuristic, not a
    coverage guarantee. That single threshold is then frozen and evaluated on
    the independent certification split with an exact one-sided binomial bound.

    Because exactly one fixed rule is tested on certification data, no
    multiplicity correction is paid there. The trade-off versus
    ``calibrate_semantic_risk`` is that this procedure cannot inspect holdout
    labels and then fall back to another threshold. If the pre-registered rule
    fails, it abstains.

    This is a sample-efficiency baseline, not a claim to supersede
    Learn-Then-Test, selective conformal risk control, or adaptive methods.
    """
    if not 0.0 < target_risk < 1.0:
        raise ValueError("target_risk must be in (0, 1)")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")
    if not 0.1 <= selection_fraction <= 0.9:
        raise ValueError("selection_fraction must be in [0.1, 0.9]")
    if not 0.0 < selection_risk_fraction <= 1.0:
        raise ValueError("selection_risk_fraction must be in (0, 1]")

    rows = list(events)
    total = len(rows)
    minimum = int(min_selection) + int(min_certification)
    method = "split-preregistered-exact-binomial"
    if total < minimum:
        return RiskCertificate(
            target_risk, delta, None, 1.0, 1.0, 0, 0, total, 0.0, 0, False,
            method, f"insufficient calibration events: {total} < {minimum}",
        )

    rng = np.random.default_rng(int(seed))
    order = rng.permutation(total)
    selection_n = int(round(total * selection_fraction))
    selection_n = max(int(min_selection), min(total - int(min_certification), selection_n))
    selection = [rows[int(i)] for i in order[:selection_n]]
    certification = [rows[int(i)] for i in order[selection_n:]]

    selection_risk = np.asarray([row.proxy_risk for row in selection], dtype=np.float64)
    selection_loss = np.asarray([row.observed_loss for row in selection], dtype=np.float64)
    quantiles = np.linspace(
        1.0 / max(2, int(threshold_candidates)),
        1.0,
        max(2, int(threshold_candidates)),
    )
    thresholds = np.unique(np.quantile(selection_risk, quantiles))
    selection_budget = target_risk * float(selection_risk_fraction)

    plausible: list[float] = []
    for threshold in thresholds:
        mask = selection_risk <= threshold
        if int(np.sum(mask)) < int(min_selection):
            continue
        if float(np.mean(selection_loss[mask])) <= selection_budget:
            plausible.append(float(threshold))

    if not plausible:
        return RiskCertificate(
            target_risk, delta, None, 1.0, 1.0, 0, len(certification), total, 0.0, 0, False,
            method,
            f"selection split found no plausible threshold under internal risk budget {selection_budget:.6f}",
        )

    threshold = max(plausible)
    cert_risk = np.asarray([row.proxy_risk for row in certification], dtype=np.float64)
    cert_loss = np.asarray([row.observed_loss for row in certification], dtype=np.float64)
    mask = cert_risk <= threshold
    accepted = int(np.sum(mask))
    coverage = accepted / max(1, len(certification))
    if accepted < int(min_certification):
        return RiskCertificate(
            target_risk, delta, threshold, 1.0, 1.0, accepted, len(certification), total,
            float(coverage), 1, False, method,
            "pre-registered threshold has insufficient certification support",
        )

    selected_losses = cert_loss[mask]
    empirical = float(np.mean(selected_losses))
    upper = exact_binomial_upper_bound(selected_losses, delta=delta)
    certified = bool(upper <= target_risk)
    return RiskCertificate(
        target_risk, delta, threshold, empirical, upper, accepted, len(certification), total,
        float(coverage), 1, certified, method,
        (
            "pre-registered threshold certified on independent holdout"
            if certified
            else "pre-registered threshold exceeded the exact-binomial risk bound"
        ),
    )
