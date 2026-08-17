from __future__ import annotations

"""Static compatibility preflight between a compiled contract and an oracle manifest."""

from dataclasses import dataclass
from typing import Any, Mapping

from .protocol_v1 import ContractExecutionPlan, OracleManifest


@dataclass(slots=True, frozen=True)
class PlanCompatibilityIssue:
    code: str
    message: str
    context: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "context": dict(self.context)}


@dataclass(slots=True, frozen=True)
class PlanCompatibilityReport:
    plan_digest: str
    oracle_manifest_digest: str
    compatible: bool
    issues: tuple[PlanCompatibilityIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-plan-compatibility",
            "format_version": 1,
            "plan_digest": self.plan_digest,
            "oracle_manifest_digest": self.oracle_manifest_digest,
            "compatible": self.compatible,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _prefix_allowed(object_id: str, declared: Any) -> bool:
    if declared is None:
        return True
    prefixes = tuple(str(x) for x in declared)
    return any(object_id.startswith(prefix) for prefix in prefixes)


def check_plan_compatibility(plan: ContractExecutionPlan, manifest: OracleManifest) -> PlanCompatibilityReport:
    """Fail fast before sending an unsupported contract plan to a provider.

    Providers may optionally declare typed namespaces in manifest metadata:
    ``score_anchor_prefixes``, ``score_candidate_prefixes``, and
    ``neighbor_anchor_prefixes``. Absence means the provider does not impose a
    protocol-level namespace restriction.
    """
    capabilities = set(manifest.capabilities)
    issues: list[PlanCompatibilityIssue] = []
    if plan.object_ids and "contains_many" not in capabilities:
        issues.append(PlanCompatibilityIssue("missing-capability", "plan requires contains_many", {"capability": "contains_many"}))
    if plan.score_pairs and "score_many" not in capabilities:
        issues.append(PlanCompatibilityIssue("missing-capability", "plan requires score_many", {"capability": "score_many"}))
    if plan.neighbor_requests and "neighbors_many" not in capabilities:
        issues.append(PlanCompatibilityIssue("missing-capability", "plan requires neighbors_many", {"capability": "neighbors_many"}))

    metadata = manifest.metadata
    score_anchor_prefixes = metadata.get("score_anchor_prefixes")
    score_candidate_prefixes = metadata.get("score_candidate_prefixes")
    neighbor_anchor_prefixes = metadata.get("neighbor_anchor_prefixes")
    for pair in plan.score_pairs:
        if not _prefix_allowed(pair.anchor, score_anchor_prefixes):
            issues.append(PlanCompatibilityIssue("unsupported-score-anchor", "score anchor is outside provider-declared namespace", {"anchor": pair.anchor}))
        if not _prefix_allowed(pair.candidate, score_candidate_prefixes):
            issues.append(PlanCompatibilityIssue("unsupported-score-candidate", "score candidate is outside provider-declared namespace", {"candidate": pair.candidate}))
    for request in plan.neighbor_requests:
        if not _prefix_allowed(request.anchor, neighbor_anchor_prefixes):
            issues.append(PlanCompatibilityIssue("unsupported-neighbor-anchor", "neighbor anchor is outside provider-declared namespace", {"anchor": request.anchor, "k": request.k}))

    return PlanCompatibilityReport(plan.digest, manifest.digest, not issues, tuple(issues))
