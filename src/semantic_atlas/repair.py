from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np

from .contracts import ContractReport

_EPS = 1e-12


def _normalize(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    norm = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norm, _EPS)


@dataclass(slots=True, frozen=True)
class RepairCandidate:
    object_id: str
    risk: float
    violated_clauses: int
    novelty: float
    priority: float


@dataclass(slots=True)
class RepairPlan:
    candidates: list[RepairCandidate]
    selected_risk_mass: float
    total_risk_mass: float

    @property
    def risk_mass_coverage(self) -> float:
        if self.total_risk_mass <= 0.0:
            return 0.0
        return self.selected_risk_mass / self.total_risk_mass


def plan_repairs(
    report: ContractReport,
    vectors: Mapping[str, np.ndarray],
    *,
    limit: int = 50,
    diversity_weight: float = 0.35,
    min_risk: float = 1e-6,
) -> RepairPlan:
    """Select high-risk, diverse logical objects for review or re-embedding.

    This is deliberately a transparent greedy reference planner, not a claim of
    optimal active learning. Contract risk identifies semantic breakage;
    violation count approximates impact; diversity avoids spending the entire
    repair budget on one dense failure region.
    """

    available = [
        object_id
        for object_id, risk in report.object_risk.items()
        if risk >= min_risk and object_id in vectors
    ]
    total = float(sum(report.object_risk.get(object_id, 0.0) for object_id in available))
    if not available or limit <= 0:
        return RepairPlan([], 0.0, total)

    violation_count = {object_id: 0 for object_id in available}
    for result in report.violated:
        for object_id in result.objects:
            if object_id in violation_count:
                violation_count[object_id] += 1

    matrix = _normalize(np.vstack([vectors[object_id] for object_id in available]))
    id_to_idx = {object_id: i for i, object_id in enumerate(available)}
    selected: list[str] = []
    output: list[RepairCandidate] = []
    diversity = float(np.clip(diversity_weight, 0.0, 1.0))

    while len(selected) < min(int(limit), len(available)):
        best: tuple[float, str, float] | None = None
        for object_id in available:
            if object_id in selected:
                continue
            risk = report.object_risk[object_id]
            if not selected:
                novelty = 1.0
            else:
                i = id_to_idx[object_id]
                selected_idx = [id_to_idx[s] for s in selected]
                max_similarity = float(np.max(matrix[selected_idx] @ matrix[i]))
                novelty = float(np.clip((1.0 - max_similarity) / 2.0, 0.0, 1.0))
            centrality = 1.0 + np.log1p(violation_count.get(object_id, 0))
            priority = float(
                risk
                * centrality
                * ((1.0 - diversity) + diversity * novelty)
            )
            candidate = (priority, object_id, novelty)
            if best is None or candidate > best:
                best = candidate

        if best is None:
            break
        priority, object_id, novelty = best
        selected.append(object_id)
        output.append(
            RepairCandidate(
                object_id=object_id,
                risk=float(report.object_risk[object_id]),
                violated_clauses=int(violation_count.get(object_id, 0)),
                novelty=float(novelty),
                priority=float(priority),
            )
        )

    selected_risk = float(
        sum(report.object_risk.get(object_id, 0.0) for object_id in selected)
    )
    return RepairPlan(output, selected_risk, total)


@dataclass(slots=True, frozen=True)
class CoverageRepairCandidate:
    object_id: str
    cost: float
    marginal_violation_mass: float
    risk_bonus: float
    marginal_gain: float
    gain_per_cost: float
    newly_covered_clauses: tuple[int, ...]


@dataclass(slots=True)
class CoverageRepairPlan:
    candidates: list[CoverageRepairCandidate]
    spent: float
    budget: float
    covered_violation_mass: float
    total_violation_mass: float
    covered_clause_indices: tuple[int, ...]

    @property
    def violation_mass_coverage(self) -> float:
        if self.total_violation_mass <= 0.0:
            return 0.0
        return self.covered_violation_mass / self.total_violation_mass


def plan_repairs_by_coverage(
    report: ContractReport,
    *,
    budget: float,
    costs: Mapping[str, float] | None = None,
    risk_bonus_weight: float = 0.15,
    hard_multiplier: float = 2.0,
    min_gain: float = 1e-12,
) -> CoverageRepairPlan:
    """Allocate a repair/review budget to cover semantic violations efficiently.

    Each violated contract clause contributes a non-negative violation mass
    ``weight * (1-score)`` (optionally amplified for hard clauses). Reviewing or
    re-embedding any object that participates in a clause *touches* that clause.
    The planner greedily maximizes newly covered violation mass per unit cost,
    with a small modular bonus for high object risk.

    This is a diagnostic-budget objective, not a claim that touching one object
    will automatically repair every incident clause. Its value is explicit: it
    prioritizes the smallest set of logical objects that exposes the largest
    amount of known semantic breakage for investigation.
    """

    budget = float(budget)
    if budget <= 0.0:
        return CoverageRepairPlan([], 0.0, budget, 0.0, 0.0, ())
    costs = dict(costs or {})
    risk_bonus_weight = max(0.0, float(risk_bonus_weight))
    hard_multiplier = max(1.0, float(hard_multiplier))

    clause_mass: dict[int, float] = {}
    incidence: dict[str, set[int]] = {}
    for result in report.violated:
        loss = max(0.0, 1.0 - float(result.score))
        mass = max(0.0, float(result.weight)) * loss
        if result.hard:
            mass *= hard_multiplier
        if mass <= 0.0:
            continue
        clause_mass[result.clause_index] = mass
        for object_id in result.objects:
            incidence.setdefault(object_id, set()).add(result.clause_index)

    total_mass = float(sum(clause_mass.values()))
    if not incidence:
        return CoverageRepairPlan([], 0.0, budget, 0.0, total_mass, ())

    selected: list[CoverageRepairCandidate] = []
    covered: set[int] = set()
    spent = 0.0
    available = set(incidence)

    while available:
        best: tuple[float, float, str, float, float, tuple[int, ...]] | None = None
        for object_id in available:
            cost = float(costs.get(object_id, 1.0))
            if cost <= 0.0:
                raise ValueError(f"repair cost must be positive for {object_id!r}")
            if spent + cost > budget + _EPS:
                continue
            new_clauses = tuple(sorted(incidence[object_id] - covered))
            violation_gain = float(sum(clause_mass[idx] for idx in new_clauses))
            risk_bonus = risk_bonus_weight * float(report.object_risk.get(object_id, 0.0))
            marginal_gain = violation_gain + risk_bonus
            gain_per_cost = marginal_gain / cost
            candidate = (gain_per_cost, marginal_gain, object_id, cost, risk_bonus, new_clauses)
            if best is None or candidate > best:
                best = candidate

        if best is None or best[1] <= min_gain:
            break
        gain_per_cost, marginal_gain, object_id, cost, risk_bonus, new_clauses = best
        violation_gain = float(sum(clause_mass[idx] for idx in new_clauses))
        selected.append(
            CoverageRepairCandidate(
                object_id=object_id,
                cost=cost,
                marginal_violation_mass=violation_gain,
                risk_bonus=float(risk_bonus),
                marginal_gain=float(marginal_gain),
                gain_per_cost=float(gain_per_cost),
                newly_covered_clauses=new_clauses,
            )
        )
        spent += cost
        covered.update(new_clauses)
        available.remove(object_id)

    covered_mass = float(sum(clause_mass[idx] for idx in covered))
    return CoverageRepairPlan(
        selected,
        float(spent),
        budget,
        covered_mass,
        total_mass,
        tuple(sorted(covered)),
    )
