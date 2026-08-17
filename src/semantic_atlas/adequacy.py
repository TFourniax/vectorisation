from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Mapping


@dataclass(slots=True, frozen=True)
class ContractAdequacyEvidence:
    """Evidence about whether a Semantic Contract is observant enough for a use.

    Conformity and adequacy are deliberately different questions:

    - conformity: does one implementation satisfy the clauses that exist?
    - adequacy: are those clauses/evaluations sufficient evidence for the
      deployment claim we want to make?

    No metric below has a universal passing threshold. A domain/release policy
    must declare requirements explicitly through ``ContractAdequacyRequirements``.
    Missing evidence therefore remains missing rather than being silently treated
    as zero or as a pass.
    """

    contract_digest: str
    object_coverage: float | None = None
    mutation_kill_rate: float | None = None
    mutation_localization: float | None = None
    predictive_correlation: float | None = None
    baseline_predictive_correlation: float | None = None
    heldout_cases: int | None = None
    datasets: int | None = None
    fault_families: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def predictive_lift_over_baseline(self) -> float | None:
        if self.predictive_correlation is None or self.baseline_predictive_correlation is None:
            return None
        return float(self.predictive_correlation - self.baseline_predictive_correlation)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["predictive_lift_over_baseline"] = self.predictive_lift_over_baseline
        payload["metadata"] = dict(self.metadata)
        return payload


@dataclass(slots=True, frozen=True)
class ContractAdequacyRequirements:
    """Application-declared evidence floor; there are intentionally no defaults."""

    min_object_coverage: float | None = None
    min_mutation_kill_rate: float | None = None
    min_mutation_localization: float | None = None
    min_predictive_correlation: float | None = None
    min_predictive_lift_over_baseline: float | None = None
    min_heldout_cases: int | None = None
    min_datasets: int | None = None
    min_fault_families: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class AdequacyCheck:
    name: str
    required: float | int
    observed: float | int | None
    passed: bool | None

    @property
    def state(self) -> str:
        if self.passed is None:
            return "missing"
        return "pass" if self.passed else "fail"


@dataclass(slots=True, frozen=True)
class ContractAdequacyReport:
    contract_digest: str
    checks: tuple[AdequacyCheck, ...]
    evidence: ContractAdequacyEvidence
    requirements: ContractAdequacyRequirements

    @property
    def status(self) -> str:
        if any(check.passed is False for check in self.checks):
            return "failed"
        if any(check.passed is None for check in self.checks):
            return "insufficient_evidence"
        return "adequate"

    @property
    def adequate(self) -> bool:
        return self.status == "adequate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-contract-adequacy",
            "format_version": 1,
            "contract_digest": self.contract_digest,
            "status": self.status,
            "checks": [
                {
                    "name": check.name,
                    "required": check.required,
                    "observed": check.observed,
                    "state": check.state,
                }
                for check in self.checks
            ],
            "evidence": self.evidence.to_dict(),
            "requirements": self.requirements.to_dict(),
        }

    @property
    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assess_contract_adequacy(
    evidence: ContractAdequacyEvidence,
    requirements: ContractAdequacyRequirements,
) -> ContractAdequacyReport:
    """Evaluate only explicitly declared adequacy requirements.

    This function intentionally refuses to invent a universal adequacy score.
    ``None`` observations remain ``missing``. This prevents a strong conformity
    score or one favorable benchmark from being promoted into a broader
    deployment claim without the evidence that the application policy requires.
    """

    checks: list[AdequacyCheck] = []

    def minimum(name: str, required: float | int | None, observed: float | int | None) -> None:
        if required is None:
            return
        checks.append(
            AdequacyCheck(
                name=name,
                required=required,
                observed=observed,
                passed=None if observed is None else bool(observed >= required),
            )
        )

    minimum("object_coverage", requirements.min_object_coverage, evidence.object_coverage)
    minimum("mutation_kill_rate", requirements.min_mutation_kill_rate, evidence.mutation_kill_rate)
    minimum("mutation_localization", requirements.min_mutation_localization, evidence.mutation_localization)
    minimum("predictive_correlation", requirements.min_predictive_correlation, evidence.predictive_correlation)
    minimum(
        "predictive_lift_over_baseline",
        requirements.min_predictive_lift_over_baseline,
        evidence.predictive_lift_over_baseline,
    )
    minimum("heldout_cases", requirements.min_heldout_cases, evidence.heldout_cases)
    minimum("datasets", requirements.min_datasets, evidence.datasets)
    minimum("fault_families", requirements.min_fault_families, evidence.fault_families)

    if not checks:
        raise ValueError("adequacy policy must declare at least one explicit requirement")
    if not evidence.contract_digest:
        raise ValueError("contract_digest is required")

    return ContractAdequacyReport(
        contract_digest=evidence.contract_digest,
        checks=tuple(checks),
        evidence=evidence,
        requirements=requirements,
    )
