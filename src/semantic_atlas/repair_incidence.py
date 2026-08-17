from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .contracts import ContractReport, MutualNeighborClause, NeighborClause, SemanticContract, TripletClause
from .oracle import SemanticOracle

_EPS = 1e-12


@dataclass(slots=True, frozen=True)
class IncidenceRepairCandidate:
    """One repairable object with blame mass derived from violated clause roles."""

    object_id: str
    cost: float
    blame_mass: float
    blame_per_cost: float
    implicated_clauses: tuple[int, ...]
    role_mass: Mapping[str, float]


@dataclass(slots=True, frozen=True)
class IncidenceRepairPlan:
    candidates: tuple[IncidenceRepairCandidate, ...]
    spent: float
    budget: float
    selected_blame_mass: float
    total_repairable_blame_mass: float
    unattributed_violation_mass: float

    @property
    def blame_mass_coverage(self) -> float:
        if self.total_repairable_blame_mass <= 0.0:
            return 0.0
        return self.selected_blame_mass / self.total_repairable_blame_mass


def _distribute(
    clause_index: int,
    mass: float,
    roles: Sequence[tuple[str, str, float]],
    *,
    repairable: set[str] | None,
    object_clause_mass: dict[str, dict[int, float]],
    object_role_mass: dict[str, dict[str, float]],
) -> float:
    """Partition one clause's violation mass across plausible causal roles.

    The role weights are diagnostic priors, not causal guarantees. They are
    normalized *after* filtering to repairable objects, so the clause's mass is
    not diluted by objects an external repair action cannot change (for example
    a query ID when only document re-embedding is available).
    """

    eligible = [
        (object_id, role, max(0.0, float(weight)))
        for object_id, role, weight in roles
        if weight > 0.0 and (repairable is None or object_id in repairable)
    ]
    total_weight = sum(weight for _, _, weight in eligible)
    if total_weight <= _EPS:
        return mass

    for object_id, role, weight in eligible:
        share = mass * weight / total_weight
        object_clause_mass.setdefault(object_id, {})[clause_index] = (
            object_clause_mass.setdefault(object_id, {}).get(clause_index, 0.0) + share
        )
        role_bucket = object_role_mass.setdefault(object_id, {})
        role_bucket[role] = role_bucket.get(role, 0.0) + share
    return 0.0


def plan_repairs_by_clause_incidence(
    contract: SemanticContract,
    report: ContractReport,
    oracle: SemanticOracle,
    *,
    budget: float,
    costs: Mapping[str, float] | None = None,
    repairable_ids: Sequence[str] | set[str] | frozenset[str] | None = None,
    hard_multiplier: float = 2.0,
    neighbor_anchor_weight: float = 0.20,
    neighbor_missing_weight: float = 1.00,
    neighbor_intruder_weight: float = 0.60,
    triplet_anchor_weight: float = 0.30,
    triplet_member_weight: float = 1.00,
    reciprocal_anchor_weight: float = 0.30,
    reciprocal_missing_weight: float = 1.00,
) -> IncidenceRepairPlan:
    """Prioritize repairable objects using the *roles* inside violated clauses.

    ``ContractReport.object_risk`` intentionally spreads loss over every object
    participating in a clause. That is useful for local semantic risk, but it is
    not a causal repair model. For example, a healthy neighborhood anchor can
    receive high risk because one expected neighbor was silently corrupted.

    This planner re-inspects each violated clause through the current oracle and
    partitions its violation mass across role-specific suspects:

    - NeighborClause: missing expected neighbors > intruding returned neighbors
      > anchor.
    - TripletClause: positive/negative members > anchor (causality is ambiguous).
    - MutualNeighborClause: the missing endpoint > the endpoint whose neighborhood
      was queried.

    The weights are explicit diagnostic priors, not claims of causal certainty.
    External systems should restrict ``repairable_ids`` to objects the available
    action can actually change (for example only documents, not queries).
    """

    budget = float(budget)
    if budget <= 0.0:
        return IncidenceRepairPlan((), 0.0, budget, 0.0, 0.0, 0.0)
    if report.contract_digest != contract.digest:
        raise ValueError("report does not belong to the supplied contract")

    costs = dict(costs or {})
    repairable = None if repairable_ids is None else set(repairable_ids)
    hard_multiplier = max(1.0, float(hard_multiplier))
    object_clause_mass: dict[str, dict[int, float]] = {}
    object_role_mass: dict[str, dict[str, float]] = {}
    unattributed = 0.0

    for result in report.violated:
        if not (0 <= result.clause_index < len(contract.clauses)):
            continue
        clause = contract.clauses[result.clause_index]
        loss = max(0.0, 1.0 - float(result.score))
        mass = max(0.0, float(result.weight)) * loss
        if result.hard:
            mass *= hard_multiplier
        if mass <= _EPS:
            continue

        roles: list[tuple[str, str, float]] = []
        if isinstance(clause, NeighborClause):
            candidate_k = max(1, int(clause.candidate_k or len(clause.expected) or 1))
            returned = tuple(oracle.neighbors(clause.anchor, candidate_k))
            returned_set = set(returned)
            expected_set = set(clause.expected)
            missing = sorted(expected_set - returned_set)
            intruders = [object_id for object_id in returned if object_id not in expected_set]

            roles.append((clause.anchor, "neighbor_anchor", neighbor_anchor_weight))
            roles.extend((object_id, "missing_expected_neighbor", neighbor_missing_weight) for object_id in missing)
            # Only the leading intruders needed to displace the missing expected
            # members receive blame. This prevents a large candidate_k from
            # swamping the signal with every non-expected result.
            intruder_limit = max(1, len(missing)) if intruders else 0
            roles.extend(
                (object_id, "intruding_neighbor", neighbor_intruder_weight)
                for object_id in intruders[:intruder_limit]
            )

        elif isinstance(clause, TripletClause):
            roles.extend(
                [
                    (clause.anchor, "triplet_anchor", triplet_anchor_weight),
                    (clause.positive, "triplet_positive", triplet_member_weight),
                    (clause.negative, "triplet_negative", triplet_member_weight),
                ]
            )

        elif isinstance(clause, MutualNeighborClause):
            left_neighbors = set(oracle.neighbors(clause.left, clause.k))
            right_neighbors = set(oracle.neighbors(clause.right, clause.k))
            if clause.right not in left_neighbors:
                roles.extend(
                    [
                        (clause.left, "reciprocal_anchor", reciprocal_anchor_weight),
                        (clause.right, "missing_reciprocal_endpoint", reciprocal_missing_weight),
                    ]
                )
            if clause.left not in right_neighbors:
                roles.extend(
                    [
                        (clause.right, "reciprocal_anchor", reciprocal_anchor_weight),
                        (clause.left, "missing_reciprocal_endpoint", reciprocal_missing_weight),
                    ]
                )
        else:
            roles.extend((object_id, "generic_clause_member", 1.0) for object_id in result.objects)

        unattributed += _distribute(
            result.clause_index,
            mass,
            roles,
            repairable=repairable,
            object_clause_mass=object_clause_mass,
            object_role_mass=object_role_mass,
        )

    candidates: list[IncidenceRepairCandidate] = []
    for object_id, clause_mass in object_clause_mass.items():
        cost = float(costs.get(object_id, 1.0))
        if cost <= 0.0:
            raise ValueError(f"repair cost must be positive for {object_id!r}")
        blame = float(sum(clause_mass.values()))
        candidates.append(
            IncidenceRepairCandidate(
                object_id=object_id,
                cost=cost,
                blame_mass=blame,
                blame_per_cost=blame / cost,
                implicated_clauses=tuple(sorted(clause_mass)),
                role_mass=dict(sorted(object_role_mass.get(object_id, {}).items())),
            )
        )

    candidates.sort(key=lambda item: (-item.blame_per_cost, -item.blame_mass, item.object_id))
    total_blame = float(sum(candidate.blame_mass for candidate in candidates))
    selected: list[IncidenceRepairCandidate] = []
    spent = 0.0
    for candidate in candidates:
        if spent + candidate.cost > budget + _EPS:
            continue
        selected.append(candidate)
        spent += candidate.cost

    return IncidenceRepairPlan(
        candidates=tuple(selected),
        spent=float(spent),
        budget=budget,
        selected_blame_mass=float(sum(candidate.blame_mass for candidate in selected)),
        total_repairable_blame_mass=total_blame,
        unattributed_violation_mass=float(unattributed),
    )
