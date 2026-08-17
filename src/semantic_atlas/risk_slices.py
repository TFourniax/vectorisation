from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .risk_control import CalibrationEvent, RiskCertificate, calibrate_semantic_risk


@dataclass(slots=True, frozen=True)
class SliceRiskPortfolio:
    """Global + semantic-slice finite-sample rollout certificates.

    ``delta`` is allocated across the global certificate and every observed
    slice via a simple union correction. A query carrying a known slice is
    accepted only when both the global certificate and that slice certificate
    accept its proxy risk. This prevents strong average performance from
    silently masking a weak domain/language/tenant slice.
    """

    global_certificate: RiskCertificate
    slice_certificates: Mapping[str, RiskCertificate]
    total_delta: float
    slice_field: str

    @property
    def certified_slices(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, cert in self.slice_certificates.items() if cert.certified))

    @property
    def uncertified_slices(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, cert in self.slice_certificates.items() if not cert.certified))

    def accepts(self, proxy_risk: float, *, group: str | None = None, require_group: bool = False) -> bool:
        if not self.global_certificate.accepts(proxy_risk):
            return False
        if group is None:
            return not require_group
        certificate = self.slice_certificates.get(group)
        return bool(certificate is not None and certificate.accepts(proxy_risk))

    def effective_upper_bound(self, *, group: str | None = None) -> float:
        upper = self.global_certificate.upper_risk_bound
        if group is None:
            return upper
        cert = self.slice_certificates.get(group)
        if cert is None:
            return 1.0
        return max(upper, cert.upper_risk_bound)


def calibrate_semantic_risk_by_slice(
    events: Sequence[CalibrationEvent],
    *,
    target_risk: float = 0.10,
    delta: float = 0.05,
    min_group_events: int = 60,
    selection_fraction: float = 0.5,
    threshold_candidates: int = 10,
    min_selection: int = 20,
    min_certification: int = 30,
    seed: int = 17,
    slice_field: str = "group",
) -> SliceRiskPortfolio:
    """Simultaneously certify global and per-group selective risk.

    The procedure uses a conservative union allocation of ``delta`` across the
    global certificate and all observed non-null groups. Each component then
    uses the split Chernoff/KL procedure from ``calibrate_semantic_risk``.
    Sparse groups are retained as explicit *uncertified* certificates instead
    of being dropped from the result.
    """

    rows = list(events)
    groups = sorted({row.group for row in rows if row.group is not None})
    family_size = 1 + len(groups)
    component_delta = delta / max(1, family_size)

    global_certificate = calibrate_semantic_risk(
        rows,
        target_risk=target_risk,
        delta=component_delta,
        selection_fraction=selection_fraction,
        threshold_candidates=threshold_candidates,
        min_selection=min_selection,
        min_certification=min_certification,
        seed=seed,
    )

    certificates: dict[str, RiskCertificate] = {}
    for offset, group in enumerate(groups, start=1):
        subset = [row for row in rows if row.group == group]
        if len(subset) < int(min_group_events):
            certificates[group] = RiskCertificate(
                target_risk=target_risk,
                delta=component_delta,
                threshold=None,
                empirical_risk=1.0,
                upper_risk_bound=1.0,
                accepted_calibration=0,
                certification_size=0,
                total_events=len(subset),
                estimated_coverage=0.0,
                candidate_count=0,
                certified=False,
                method="slice-split-chernoff-kl",
                reason=f"insufficient slice calibration events: {len(subset)} < {int(min_group_events)}",
            )
            continue
        cert = calibrate_semantic_risk(
            subset,
            target_risk=target_risk,
            delta=component_delta,
            selection_fraction=selection_fraction,
            threshold_candidates=threshold_candidates,
            min_selection=min(min_selection, max(2, len(subset) // 4)),
            min_certification=min(min_certification, max(2, len(subset) // 4)),
            seed=seed + offset,
        )
        certificates[group] = RiskCertificate(
            target_risk=cert.target_risk,
            delta=cert.delta,
            threshold=cert.threshold,
            empirical_risk=cert.empirical_risk,
            upper_risk_bound=cert.upper_risk_bound,
            accepted_calibration=cert.accepted_calibration,
            certification_size=cert.certification_size,
            total_events=cert.total_events,
            estimated_coverage=cert.estimated_coverage,
            candidate_count=cert.candidate_count,
            certified=cert.certified,
            method="slice-" + cert.method,
            reason=cert.reason,
        )

    return SliceRiskPortfolio(
        global_certificate=global_certificate,
        slice_certificates=certificates,
        total_delta=float(delta),
        slice_field=slice_field,
    )
