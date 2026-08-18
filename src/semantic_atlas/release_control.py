from __future__ import annotations

"""Strict production release gate for Semantic ABI.

A clean semantic diff is necessary but not sufficient. Production promotion can also
require the v0.5 certified attestation, which binds conformance, contract adequacy,
risk certification and the exact candidate execution state.
"""

from dataclasses import dataclass
from typing import Any

from .attestation_v1 import SemanticProtocolAttestation
from .change_control import ReleasePolicy, SemanticChangeReport, compare_protocol_audits
from .contracts import SemanticContract
from .protocol_v1 import ProtocolAuditResult


@dataclass(slots=True)
class ProductionReleaseReport:
    change: SemanticChangeReport
    attestation_digest: str | None
    attestation_bound: bool
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
            f"- Attestation bound: {'yes' if self.attestation_bound else 'no'}",
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


def evaluate_production_release(
    contract: SemanticContract,
    baseline: ProtocolAuditResult,
    candidate: ProtocolAuditResult,
    *,
    attestation: SemanticProtocolAttestation | None,
    change_policy: ReleasePolicy | None = None,
    require_certified_attestation: bool = True,
) -> ProductionReleaseReport:
    change = compare_protocol_audits(contract, baseline, candidate, policy=change_policy)
    blockers = list(change.blockers)
    bound = False
    attestation_eligible = False
    attestation_digest: str | None = None

    if attestation is None:
        if require_certified_attestation:
            blockers.append("candidate has no certified Semantic Protocol Attestation")
    else:
        attestation_digest = attestation.digest
        bound, mismatches = attestation_matches_audit(attestation, candidate)
        blockers.extend(mismatches)
        attestation_eligible = bool(bound and attestation.deployment_eligible)
        if require_certified_attestation and not attestation_eligible:
            blockers.append("candidate attestation is not deployment-eligible")

    return ProductionReleaseReport(
        change=change,
        attestation_digest=attestation_digest,
        attestation_bound=bound,
        attestation_deployment_eligible=attestation_eligible,
        deployment_eligible=bool(change.deployment_eligible and (attestation_eligible or not require_certified_attestation)),
        blockers=tuple(dict.fromkeys(blockers)),
    )
