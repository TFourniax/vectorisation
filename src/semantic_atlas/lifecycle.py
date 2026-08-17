from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence, Any

import numpy as np

from .contracts import ContractReport, SemanticContract
from .repair import CoverageRepairPlan, plan_repairs_by_coverage
from .risk_control import CalibrationEvent, RiskCertificate, calibrate_semantic_risk


@dataclass(slots=True)
class ChangeAssessment:
    """One evidence-gated assessment of a candidate semantic implementation."""

    implementation: str
    contract_digest: str
    report: ContractReport
    certificate: RiskCertificate
    repair_plan: CoverageRepairPlan | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "implementation": self.implementation,
            "contract_digest": self.contract_digest,
            "status": self.status,
            "reason": self.reason,
            "contract_score": self.report.score,
            "hard_pass": self.report.hard_pass,
            "evaluated_clauses": self.report.evaluated_clauses,
            "missing_clauses": self.report.missing_clauses,
            "certificate": asdict(self.certificate),
            "repair": None
            if self.repair_plan is None
            else {
                "spent": self.repair_plan.spent,
                "budget": self.repair_plan.budget,
                "violation_mass_coverage": self.repair_plan.violation_mass_coverage,
                "selected": [candidate.object_id for candidate in self.repair_plan.candidates],
            },
        }


@dataclass(slots=True, frozen=True)
class AssessmentDelta:
    score_delta: float
    hard_pass_improved: bool
    violated_clause_delta: int
    top_risk_delta: float
    status_changed: bool


def compare_assessments(before: ChangeAssessment, after: ChangeAssessment) -> AssessmentDelta:
    before_top = max(before.report.object_risk.values(), default=0.0)
    after_top = max(after.report.object_risk.values(), default=0.0)
    return AssessmentDelta(
        score_delta=float(after.report.score - before.report.score),
        hard_pass_improved=bool((not before.report.hard_pass) and after.report.hard_pass),
        violated_clause_delta=len(after.report.violated) - len(before.report.violated),
        top_risk_delta=float(after_top - before_top),
        status_changed=before.status != after.status,
    )


class SemanticChangeManager:
    """Reference closed loop: Contract -> Audit -> Certify -> Repair -> Re-certify.

    The manager deliberately does not mutate vectors or call embedding models.
    Repair actions are external operations (review, re-embedding, relabeling,
    data correction). After those operations, call ``assess`` again and compare
    the assessments. Keeping mutation outside the manager makes every semantic
    state transition explicit and auditable.
    """

    def __init__(
        self,
        contract: SemanticContract,
        *,
        min_global_score: float = 0.80,
        target_risk: float = 0.10,
        delta: float = 0.05,
    ) -> None:
        self.contract = contract
        self.min_global_score = float(np.clip(min_global_score, 0.0, 1.0))
        self.target_risk = float(target_risk)
        self.delta = float(delta)

    def assess(
        self,
        implementation: str,
        candidate_vectors: Mapping[str, np.ndarray],
        calibration_events: Sequence[CalibrationEvent],
        *,
        repair_budget: float = 0.0,
        repair_costs: Mapping[str, float] | None = None,
        threshold_candidates: int = 12,
        min_selection: int = 20,
        min_certification: int = 30,
        seed: int = 17,
    ) -> ChangeAssessment:
        report = self.contract.audit(candidate_vectors, implementation=implementation)
        certificate = calibrate_semantic_risk(
            calibration_events,
            target_risk=self.target_risk,
            delta=self.delta,
            threshold_candidates=threshold_candidates,
            min_selection=min_selection,
            min_certification=min_certification,
            seed=seed,
        )
        repair_plan = None
        if repair_budget > 0.0 and report.violated:
            repair_plan = plan_repairs_by_coverage(
                report,
                budget=repair_budget,
                costs=repair_costs,
            )

        if not report.hard_pass:
            status = "blocked"
            reason = "hard semantic contract failure"
        elif report.score < self.min_global_score:
            status = "repair" if repair_plan and repair_plan.candidates else "blocked"
            reason = f"global semantic score {report.score:.3f} below {self.min_global_score:.3f}"
        elif not certificate.certified:
            status = "repair" if repair_plan and repair_plan.candidates else "uncertified"
            reason = certificate.reason
        else:
            status = "certified"
            reason = (
                f"semantic risk <= {certificate.target_risk:.3f} with confidence "
                f">= {1.0 - certificate.delta:.3f} on the certified selective region"
            )

        return ChangeAssessment(
            implementation=implementation,
            contract_digest=self.contract.digest,
            report=report,
            certificate=certificate,
            repair_plan=repair_plan,
            status=status,
            reason=reason,
        )
