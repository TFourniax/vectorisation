"""Bridge change-control evidence into Semantic ABI linker certificates."""
from __future__ import annotations

from typing import Any, Mapping

from .change_control import CompatibilityReport, CompatibilityStatus
from .linker import CertificateVerdict, CompatibilityCertificate


def certificate_from_change_report(
    report: CompatibilityReport,
    *,
    baseline_component_id: str,
    candidate_component_id: str,
    issuer: str,
    issued_at: str,
    expires_at: str | None = None,
    environment_digest: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CompatibilityCertificate:
    """Promote only a non-breaking evidence report into a dependency certificate.

    This is the critical boundary between testing and linking: the dependency
    resolver cannot manufacture compatibility from generic benchmarks. A
    certificate is downstream of an executable Semantic ABI change report and
    carries that report's evidence digest and exact application contract digest.
    """

    if report.status == CompatibilityStatus.COMPATIBLE:
        verdict = CertificateVerdict.COMPATIBLE
    elif report.status == CompatibilityStatus.CONDITIONAL:
        verdict = CertificateVerdict.CONDITIONAL
    elif report.status in {
        CompatibilityStatus.BREAKING,
        CompatibilityStatus.INSUFFICIENT_EVIDENCE,
    }:
        raise ValueError(f"cannot certify report with status {report.status.value}")
    else:  # defensive against future enum expansion
        raise ValueError(f"unknown compatibility status: {report.status!r}")

    return CompatibilityCertificate(
        baseline_component_id=baseline_component_id,
        candidate_component_id=candidate_component_id,
        contract_digest=report.contract_digest,
        evidence_digest=report.evidence_digest,
        verdict=verdict,
        probe_coverage=report.probe_coverage,
        issuer=issuer,
        issued_at=issued_at,
        expires_at=expires_at,
        environment_digest=environment_digest,
        metadata=dict(metadata or {}),
    )
