from __future__ import annotations

"""Strict production release gate for Semantic ABI.

A clean semantic diff is necessary but not sufficient. Production promotion can also
require the v0.5 certified attestation, which binds conformance, contract adequacy,
risk certification and the exact candidate execution state.
"""

from dataclasses import dataclass
from typing import Any, Sequence

from .attestation_v1 import SemanticProtocolAttestation
from .change_control import ReleasePolicy, SemanticChangeReport, compare_protocol_audits
from .contracts import SemanticContract
from .protocol_v1 import ProtocolAuditResult


@dataclass(slots=True)
class ProductionReleaseReport:
    change: SemanticChangeReport
    attestation_digest: str | None
    attestation_bound: bool
    certification_evidence_bound: bool
    attestation_deployment_eligible: bool
    deployment_eligible: bool
    blockers: tuple[str, ...]

    def to_dict(self, *, include_clauses: bool = True) -> dict[str, Any]:
        return {
            "format": "semantic-abi-production-release",
            "format_version": 1,
            "deployment_eligible": self.deployment_eligible,
            "blockers": list(self.blockers),
            "attestation": {
                "digest": self.attestation_digest,
                "bound_to_candidate": self.attestation_bound,
                "certification_evidence_bound": self.certification_evidence_bound,
                "deployment_eligible": self.attestation_deployment_eligible,
            },
            "change": self.change.to_dict(include_clauses=include_clauses),
        }

    def to_markdown(self, *, max_rows: int = 20) -> str:
        verdict = "PASS" if self.deployment_eligible else "BLOCK"
        lines = [
            f"# Semantic ABI production release — {verdict}",
            "",
            f"- Change-control gate: {'PASS' if self.change.deployment_eligible else 'BLOCK'}",
            f"- Attestation bound to candidate: {'yes' if self.attestation_bound else 'no'}",
            f"- Certification evidence rebound: {'yes' if self.certification_evidence_bound else 'no'}",
            f"- Certified attestation: {'PASS' if self.attestation_deployment_eligible else 'BLOCK'}",
        ]
        if self.blockers:
            lines.extend(["", "## Release blockers"])
            lines.extend(f"- {blocker}" for blocker in self.blockers)
        lines.extend(["", self.change.to_markdown(max_rows=max_rows).rstrip()])
        return "\n".join(lines) + "\n"


def attestation_matches_audit(attestation: SemanticProtocolAttestation, candidate: ProtocolAuditResult) -> tuple[bool, tuple[str, ...]]:
    mismatches: list[str] = []
    expected = {
        "contract_digest": candidate.report.contract_digest,
        "oracle_manifest_digest": candidate.snapshot.manifest.digest,
        "plan_digest": candidate.plan.digest,
        "snapshot_digest": candidate.snapshot.digest,
        "protocol_audit_digest": candidate.digest,
    }
    for field, value in expected.items():
        if str(getattr(attestation, field)) != str(value):
            mismatches.append(f"attestation {field} does not match candidate audit")
    if bool(attestation.hard_pass) != bool(candidate.report.hard_pass):
        mismatches.append("attestation hard_pass does not match candidate audit")
    if int(attestation.missing_clauses) != int(candidate.report.missing_clauses):
        mismatches.append("attestation missing_clauses does not match candidate audit")
    return not mismatches, tuple(mismatches)


def attestation_matches_certification_evidence(
    attestation: SemanticProtocolAttestation,
    *,
    conformance_digest: str,
    conformance_passed: bool,
    adequacy_digest: str,
    adequacy_status: str,
    risk_certificate_digest: str,
    risk_certified: bool,
) -> tuple[bool, tuple[str, ...]]:
    """Verify that an attestation references independently recomputed evidence."""

    mismatches: list[str] = []
    expected = {
        "conformance_digest": str(conformance_digest),
        "adequacy_digest": str(adequacy_digest),
        "adequacy_status": str(adequacy_status),
        "risk_certificate_digest": str(risk_certificate_digest),
    }
    for field, value in expected.items():
        if str(getattr(attestation, field)) != value:
            mismatches.append(f"attestation {field} does not match recomputed certification evidence")
    if bool(attestation.conformance_passed) != bool(conformance_passed):
        mismatches.append("attestation conformance_passed does not match recomputed certification evidence")
    if bool(attestation.risk_certified) != bool(risk_certified):
        mismatches.append("attestation risk_certified does not match recomputed certification evidence")
    return not mismatches, tuple(mismatches)


def evaluate_production_release(
    contract: SemanticContract,
    baseline: ProtocolAuditResult,
    candidate: ProtocolAuditResult,
    *,
    attestation: SemanticProtocolAttestation | None,
    change_policy: ReleasePolicy | None = None,
    require_certified_attestation: bool = True,
    certification_evidence_mismatches: Sequence[str] = (),
) -> ProductionReleaseReport:
    change = compare_protocol_audits(contract, baseline, candidate, policy=change_policy)
    blockers = list(change.blockers)
    bound = False
    evidence_bound = not certification_evidence_mismatches
    attestation_eligible = False
    attestation_digest: str | None = None

    if attestation is None:
        evidence_bound = False
        if require_certified_attestation:
            blockers.append("candidate has no certified Semantic Protocol Attestation")
    else:
        attestation_digest = attestation.digest
        bound, mismatches = attestation_matches_audit(attestation, candidate)
        blockers.extend(mismatches)
        blockers.extend(str(value) for value in certification_evidence_mismatches)
        attestation_eligible = bool(bound and evidence_bound and attestation.deployment_eligible)
        if require_certified_attestation and not attestation_eligible:
            blockers.append("candidate attestation is not deployment-eligible with recomputed certification evidence")

    return ProductionReleaseReport(
        change=change,
        attestation_digest=attestation_digest,
        attestation_bound=bound,
        certification_evidence_bound=evidence_bound,
        attestation_deployment_eligible=attestation_eligible,
        deployment_eligible=bool(change.deployment_eligible and (attestation_eligible or not require_certified_attestation)),
        blockers=tuple(dict.fromkeys(blockers)),
    )
