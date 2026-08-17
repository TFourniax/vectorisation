from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

import numpy as np

from .contracts import ContractReport
from .support import estimate_local_semantic_risk

_EPS = 1e-12


@dataclass(slots=True, frozen=True)
class CalibrationEvent:
    """Held-out observation used to calibrate a semantic rollout gate.

    ``proxy_risk`` is any pre-deployment score where lower means safer (for
    example a support-aware local Semantic ABI risk). ``observed_loss`` is the
    semantic failure observed on an independently judged calibration case and
    must be a Bernoulli value for the current KL certificate.
    """

    proxy_risk: float
    observed_loss: float
    object_id: str | None = None
    group: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.proxy_risk <= 1.0:
            raise ValueError("proxy_risk must be in [0, 1]")
        if self.observed_loss not in (0.0, 1.0):
            raise ValueError("observed_loss must be binary for KL certification")


@dataclass(slots=True, frozen=True)
class RiskCertificate:
    """Finite-sample certificate for a selective semantic rollout rule.

    The certificate is valid under independent calibration/deployment draws
    from the same distribution. Candidate thresholds are chosen on a selection
    split and simultaneously tested on an independent certification split.
    A union-corrected Chernoff/KL upper confidence bound controls the family of
    candidate thresholds.
    """

    target_risk: float
    delta: float
    threshold: float | None
    empirical_risk: float
    upper_risk_bound: float
    accepted_calibration: int
    certification_size: int
    total_events: int
    estimated_coverage: float
    candidate_count: int
    certified: bool
    method: str
    reason: str

    def accepts(self, proxy_risk: float) -> bool:
        return bool(self.certified and self.threshold is not None and proxy_risk <= self.threshold)


@dataclass(slots=True, frozen=True)
class CertifiedGateDecision:
    implementation: str | None
    accepted: bool
    local_risk: float
    utility: float
    certificate_upper_risk: float | None
    reason: str


def _bernoulli_kl(p: float, q: float) -> float:
    if p <= 0.0:
        return -math.log(max(1.0 - q, _EPS))
    if p >= 1.0:
        return -math.log(max(q, _EPS))
    q = float(np.clip(q, _EPS, 1.0 - _EPS))
    return p * math.log(p / q) + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))


def bernoulli_kl_upper_bound(losses: Sequence[float] | np.ndarray, *, delta: float) -> float:
    """One-sided Chernoff/KL upper confidence bound for Bernoulli risk."""

    x = np.asarray(losses, dtype=np.float64).reshape(-1)
    if len(x) == 0:
        return 1.0
    if np.any((x != 0.0) & (x != 1.0)):
        raise ValueError("KL bound requires Bernoulli losses")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")
    p = float(np.mean(x))
    if p >= 1.0:
        return 1.0
    budget = math.log(1.0 / delta) / len(x)
    lo, hi = p, 1.0 - _EPS
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if _bernoulli_kl(p, mid) <= budget:
            lo = mid
        else:
            hi = mid
    return float(np.clip(lo, 0.0, 1.0))


def calibrate_semantic_risk(
    events: Sequence[CalibrationEvent],
    *,
    target_risk: float = 0.10,
    delta: float = 0.05,
    selection_fraction: float = 0.5,
    threshold_candidates: int = 12,
    min_selection: int = 20,
    min_certification: int = 30,
    seed: int = 17,
) -> RiskCertificate:
    """Calibrate the broadest risk threshold that can be statistically certified.

    The calibration sample is split deterministically. The first split proposes
    a small family of thresholds; the second split certifies them with a
    Bonferroni/union correction. Because the threshold family is fixed before
    looking at certification outcomes, selecting the broadest passing threshold
    preserves the simultaneous confidence statement.

    This is deliberately conservative. Failure to certify means "insufficient
    evidence for this risk budget", not that the candidate representation is
    necessarily unsafe.
    """

    if not 0.0 < target_risk < 1.0:
        raise ValueError("target_risk must be in (0, 1)")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")
    if not 0.1 <= selection_fraction <= 0.9:
        raise ValueError("selection_fraction must be in [0.1, 0.9]")

    rows = list(events)
    total = len(rows)
    minimum = int(min_selection) + int(min_certification)
    if total < minimum:
        return RiskCertificate(
            target_risk, delta, None, 1.0, 1.0, 0, 0, total, 0.0, 0, False,
            "split-chernoff-kl", f"insufficient calibration events: {total} < {minimum}",
        )

    rng = np.random.default_rng(int(seed))
    order = rng.permutation(total)
    selection_n = int(round(total * selection_fraction))
    selection_n = max(int(min_selection), min(total - int(min_certification), selection_n))
    selection = [rows[int(i)] for i in order[:selection_n]]
    certification = [rows[int(i)] for i in order[selection_n:]]

    selection_risk = np.asarray([row.proxy_risk for row in selection], dtype=np.float64)
    selection_loss = np.asarray([row.observed_loss for row in selection], dtype=np.float64)
    quantiles = np.linspace(1.0 / max(2, int(threshold_candidates)), 1.0, max(2, int(threshold_candidates)))
    thresholds = np.unique(np.quantile(selection_risk, quantiles))

    candidates: list[float] = []
    for threshold in thresholds:
        mask = selection_risk <= threshold
        if int(np.sum(mask)) < int(min_selection):
            continue
        if float(np.mean(selection_loss[mask])) <= target_risk:
            candidates.append(float(threshold))

    if not candidates:
        return RiskCertificate(
            target_risk, delta, None, 1.0, 1.0, 0, len(certification), total, 0.0, 0, False,
            "split-chernoff-kl", "selection split found no plausible threshold",
        )

    cert_risk = np.asarray([row.proxy_risk for row in certification], dtype=np.float64)
    cert_loss = np.asarray([row.observed_loss for row in certification], dtype=np.float64)
    per_candidate_delta = delta / len(candidates)
    passing: list[tuple[int, float, float, float]] = []
    evaluated: list[tuple[int, float, float, float]] = []

    for threshold in candidates:
        mask = cert_risk <= threshold
        accepted = int(np.sum(mask))
        if accepted < int(min_certification):
            continue
        empirical = float(np.mean(cert_loss[mask]))
        upper = bernoulli_kl_upper_bound(cert_loss[mask], delta=per_candidate_delta)
        evaluated.append((accepted, threshold, empirical, upper))
        if upper <= target_risk:
            passing.append((accepted, threshold, empirical, upper))

    if not passing:
        if evaluated:
            accepted, threshold, empirical, upper = max(evaluated, key=lambda row: (row[0], row[1]))
            coverage = accepted / max(1, len(certification))
        else:
            accepted, threshold, empirical, upper, coverage = 0, None, 1.0, 1.0, 0.0
        return RiskCertificate(
            target_risk, delta, threshold, empirical, upper, accepted, len(certification), total,
            float(coverage), len(candidates), False, "split-chernoff-kl",
            "no candidate threshold met the certified semantic-risk budget",
        )

    accepted, threshold, empirical, upper = max(passing, key=lambda row: (row[0], row[1]))
    return RiskCertificate(
        target_risk, delta, threshold, empirical, upper, accepted, len(certification), total,
        accepted / max(1, len(certification)), len(candidates), True, "split-chernoff-kl",
        "certified on independent calibration split",
    )


class CertifiedSemanticABIGate:
    """Semantic ABI rollout gate using support-aware statistical certificates."""

    def __init__(
        self,
        implementations: Mapping[str, tuple[ContractReport, Mapping[str, np.ndarray], RiskCertificate]],
        *,
        min_global_score: float = 0.80,
    ) -> None:
        self.implementations = dict(implementations)
        self.min_global_score = float(np.clip(min_global_score, 0.0, 1.0))

    def choose(self, query_vectors: Mapping[str, np.ndarray], *, prefer: Sequence[str] = ()) -> CertifiedGateDecision:
        preference = {name: len(prefer) - i for i, name in enumerate(prefer)}
        candidates: list[tuple[float, int, str, float, float]] = []
        rejected: list[str] = []

        for name, (report, landmarks, certificate) in self.implementations.items():
            if name not in query_vectors:
                rejected.append(f"{name}: no query vector")
                continue
            if not report.hard_pass:
                rejected.append(f"{name}: hard contract failure")
                continue
            if report.score < self.min_global_score:
                rejected.append(f"{name}: global score {report.score:.3f}")
                continue
            if not certificate.certified or certificate.threshold is None:
                rejected.append(f"{name}: no statistical certificate")
                continue
            estimate = estimate_local_semantic_risk(report, query_vectors[name], landmarks)
            local_risk = estimate.risk
            if not certificate.accepts(local_risk):
                rejected.append(
                    f"{name}: support-aware local risk {local_risk:.3f} exceeds certified threshold "
                    f"{certificate.threshold:.3f} (support={estimate.support:.3f})"
                )
                continue
            utility = report.score * (1.0 - local_risk) * max(0.0, 1.0 - certificate.upper_risk_bound)
            candidates.append((utility, preference.get(name, 0), name, local_risk, certificate.upper_risk_bound))

        if not candidates:
            return CertifiedGateDecision(None, False, 1.0, 0.0, None, "; ".join(rejected) or "no implementations")

        candidates.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
        utility, _, name, local_risk, upper = candidates[0]
        return CertifiedGateDecision(name, True, local_risk, utility, upper, "statistically certified semantic region with contract support")
