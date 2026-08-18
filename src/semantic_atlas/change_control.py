from __future__ import annotations

"""Backend-independent semantic release diffs and deployment gates.

This is the product-level equivalent of ``git diff`` for a Semantic Contract.  It
compares two Protocol-v1 audit results clause by clause and never assumes that the two
implementations share coordinates, a distance metric, or even the same retrieval
algebra.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping

from .contracts import ClauseResult, SemanticContract
from .protocol_v1 import ProtocolAuditResult


def _clip_nonnegative(value: float) -> float:
    return max(0.0, float(value))


@dataclass(slots=True, frozen=True)
class ClauseDelta:
    clause_index: int
    kind: str
    hard: bool
    objects: tuple[str, ...]
    status: str
    baseline_present: bool
    candidate_present: bool
    baseline_passed: bool | None
    candidate_passed: bool | None
    baseline_score: float | None
    candidate_score: float | None
    score_delta: float | None

    @property
    def is_regression(self) -> bool:
        return self.status in {"regressed", "new_missing"}

    @property
    def is_hard_regression(self) -> bool:
        return self.hard and self.is_regression

    def to_dict(self) -> dict[str, Any]:
        return {
            "clause_index": self.clause_index,
            "kind": self.kind,
            "hard": self.hard,
            "objects": list(self.objects),
            "status": self.status,
            "baseline_present": self.baseline_present,
            "candidate_present": self.candidate_present,
            "baseline_passed": self.baseline_passed,
            "candidate_passed": self.candidate_passed,
            "baseline_score": self.baseline_score,
            "candidate_score": self.candidate_score,
            "score_delta": self.score_delta,
        }


@dataclass(slots=True, frozen=True)
class ReleasePolicy:
    """Declared semantic deployment policy.

    Defaults are intentionally conservative: no newly missing clauses, no newly failing
    clauses, and no hard-clause failure in the candidate.  ``max_score_drop`` allows a
    caller to tolerate a small aggregate soft-score movement while still blocking every
    newly failing clause.
    """

    min_candidate_score: float = 0.0
    max_score_drop: float = 0.0
    allow_soft_regressions: int = 0
    require_no_new_missing: bool = True
    require_absolute_hard_pass: bool = True
    allow_existing_hard_failures: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.min_candidate_score) <= 1.0:
            raise ValueError("min_candidate_score must be within [0, 1]")
        if float(self.max_score_drop) < 0.0:
            raise ValueError("max_score_drop cannot be negative")
        if int(self.allow_soft_regressions) < 0:
            raise ValueError("allow_soft_regressions cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_candidate_score": self.min_candidate_score,
            "max_score_drop": self.max_score_drop,
            "allow_soft_regressions": self.allow_soft_regressions,
            "require_no_new_missing": self.require_no_new_missing,
            "require_absolute_hard_pass": self.require_absolute_hard_pass,
            "allow_existing_hard_failures": self.allow_existing_hard_failures,
        }


@dataclass(slots=True)
class SemanticChangeReport:
    contract_digest: str
    baseline_implementation: str
    candidate_implementation: str
    baseline_manifest_digest: str
    candidate_manifest_digest: str
    baseline_score: float
    candidate_score: float
    score_delta: float
    deltas: list[ClauseDelta]
    deployment_eligible: bool
    blockers: tuple[str, ...] = ()
    policy: ReleasePolicy = field(default_factory=ReleasePolicy)

    @property
    def regressions(self) -> list[ClauseDelta]:
        return [row for row in self.deltas if row.is_regression]

    @property
    def hard_regressions(self) -> list[ClauseDelta]:
        return [row for row in self.deltas if row.is_hard_regression]

    @property
    def soft_regressions(self) -> list[ClauseDelta]:
        return [row for row in self.regressions if not row.hard]

    @property
    def improvements(self) -> list[ClauseDelta]:
        return [row for row in self.deltas if row.status in {"fixed", "improved", "restored"}]

    @property
    def new_missing(self) -> list[ClauseDelta]:
        return [row for row in self.deltas if row.status == "new_missing"]

    def to_dict(self, *, include_clauses: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "format": "semantic-abi-change-report",
            "format_version": 1,
            "contract_digest": self.contract_digest,
            "baseline": {
                "implementation": self.baseline_implementation,
                "manifest_digest": self.baseline_manifest_digest,
                "score": self.baseline_score,
            },
            "candidate": {
                "implementation": self.candidate_implementation,
                "manifest_digest": self.candidate_manifest_digest,
                "score": self.candidate_score,
            },
            "score_delta": self.score_delta,
            "summary": {
                "clauses": len(self.deltas),
                "regressions": len(self.regressions),
                "hard_regressions": len(self.hard_regressions),
                "soft_regressions": len(self.soft_regressions),
                "improvements": len(self.improvements),
                "new_missing": len(self.new_missing),
            },
            "deployment_eligible": self.deployment_eligible,
            "blockers": list(self.blockers),
            "policy": self.policy.to_dict(),
        }
        if include_clauses:
            payload["clauses"] = [row.to_dict() for row in self.deltas]
        return payload

    def to_markdown(self, *, max_rows: int = 20) -> str:
        verdict = "PASS" if self.deployment_eligible else "BLOCK"
        lines = [
            f"## Semantic ABI change control — {verdict}",
            "",
            f"- Contract: `{self.contract_digest}`",
            f"- Baseline: `{self.baseline_implementation}` — {self.baseline_score:.4f}",
            f"- Candidate: `{self.candidate_implementation}` — {self.candidate_score:.4f}",
            f"- Score delta: {self.score_delta:+.4f}",
            f"- Regressions: **{len(self.regressions)}** ({len(self.hard_regressions)} hard)",
            f"- Improvements: **{len(self.improvements)}**",
            f"- Newly missing clauses: **{len(self.new_missing)}**",
        ]
        if self.blockers:
            lines.extend(["", "### Blockers"])
            lines.extend(f"- {value}" for value in self.blockers)
        important = sorted(
            self.regressions,
            key=lambda row: (not row.hard, row.status != "new_missing", row.clause_index),
        )[: max(0, int(max_rows))]
        if important:
            lines.extend(["", "### Regressions", "", "| # | Severity | Status | Objects |", "|---:|---|---|---|"])
            for row in important:
                severity = "HARD" if row.hard else "soft"
                objects = " → ".join(f"`{item}`" for item in row.objects)
                lines.append(f"| {row.clause_index} | {severity} | {row.status} | {objects} |")
        return "\n".join(lines) + "\n"


def _result_map(result: ProtocolAuditResult) -> Mapping[int, ClauseResult]:
    return {int(row.clause_index): row for row in result.report.clause_results}


def compare_protocol_audits(
    contract: SemanticContract,
    baseline: ProtocolAuditResult,
    candidate: ProtocolAuditResult,
    *,
    policy: ReleasePolicy | None = None,
    score_epsilon: float = 1e-9,
) -> SemanticChangeReport:
    """Compare two executions of the *same* contract and evaluate a release gate."""

    policy = policy or ReleasePolicy()
    if baseline.report.contract_digest != contract.digest or candidate.report.contract_digest != contract.digest:
        raise ValueError("both audits must execute the supplied contract digest")

    old = _result_map(baseline)
    new = _result_map(candidate)
    rows: list[ClauseDelta] = []
    epsilon = _clip_nonnegative(score_epsilon)

    for index, clause in enumerate(contract.clauses):
        before = old.get(index)
        after = new.get(index)
        if before is None and after is None:
            status = "missing_both"
        elif before is not None and after is None:
            status = "new_missing"
        elif before is None and after is not None:
            status = "restored"
        else:
            assert before is not None and after is not None
            if before.passed and not after.passed:
                status = "regressed"
            elif not before.passed and after.passed:
                status = "fixed"
            else:
                delta = float(after.score - before.score)
                if delta > epsilon:
                    status = "improved"
                elif delta < -epsilon:
                    status = "degraded"
                else:
                    status = "unchanged"
        score_delta = None if before is None or after is None else float(after.score - before.score)
        rows.append(
            ClauseDelta(
                clause_index=index,
                kind=clause.kind,
                hard=bool(clause.hard),
                objects=tuple(clause.objects),
                status=status,
                baseline_present=before is not None,
                candidate_present=after is not None,
                baseline_passed=None if before is None else bool(before.passed),
                candidate_passed=None if after is None else bool(after.passed),
                baseline_score=None if before is None else float(before.score),
                candidate_score=None if after is None else float(after.score),
                score_delta=score_delta,
            )
        )

    score_delta = float(candidate.report.score - baseline.report.score)
    hard_regressions = [row for row in rows if row.is_hard_regression]
    soft_regressions = [row for row in rows if row.is_regression and not row.hard]
    new_missing = [row for row in rows if row.status == "new_missing"]
    blockers: list[str] = []

    if hard_regressions:
        blockers.append(f"{len(hard_regressions)} new hard-clause regression(s)")
    if policy.require_no_new_missing and new_missing:
        blockers.append(f"{len(new_missing)} newly missing clause(s)")
    if len(soft_regressions) > int(policy.allow_soft_regressions):
        blockers.append(
            f"{len(soft_regressions)} soft regression(s) exceed allowance {int(policy.allow_soft_regressions)}"
        )
    if candidate.report.score < float(policy.min_candidate_score):
        blockers.append(
            f"candidate score {candidate.report.score:.6f} below minimum {policy.min_candidate_score:.6f}"
        )
    if -score_delta > float(policy.max_score_drop) + epsilon:
        blockers.append(
            f"aggregate score drop {-score_delta:.6f} exceeds allowance {policy.max_score_drop:.6f}"
        )

    if policy.require_absolute_hard_pass and not candidate.report.hard_pass:
        if not policy.allow_existing_hard_failures:
            blockers.append("candidate does not satisfy all hard clauses")
        else:
            baseline_failed = {
                index for index, row in old.items() if row.hard and not row.passed
            }
            candidate_failed = {
                index for index, row in new.items() if row.hard and not row.passed
            }
            if not candidate_failed.issubset(baseline_failed):
                blockers.append("candidate introduces a hard failure outside the grandfathered baseline set")

    return SemanticChangeReport(
        contract_digest=contract.digest,
        baseline_implementation=baseline.report.implementation,
        candidate_implementation=candidate.report.implementation,
        baseline_manifest_digest=baseline.snapshot.manifest.digest,
        candidate_manifest_digest=candidate.snapshot.manifest.digest,
        baseline_score=float(baseline.report.score),
        candidate_score=float(candidate.report.score),
        score_delta=score_delta,
        deltas=rows,
        deployment_eligible=not blockers,
        blockers=tuple(blockers),
        policy=policy,
    )
