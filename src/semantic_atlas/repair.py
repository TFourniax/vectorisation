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
