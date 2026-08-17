from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from .contracts import ClauseResult, SemanticContract
from .oracle import SemanticOracle, evaluate_contract_clause
from .risk_exact import exact_binomial_upper_bound

_EPS = 1e-12


@dataclass(slots=True, frozen=True)
class ProgressiveAuditResult:
    decision: Literal["pass", "fail", "inconclusive"]
    reason: str
    hard_pass: bool
    max_soft_violation_rate: float
    estimated_soft_violation_rate: float
    lower_violation_bound: float
    upper_violation_bound: float
    delta: float
    draws: int
    unique_soft_clauses_evaluated: int
    hard_clauses_evaluated: int
    total_soft_clauses: int
    total_contract_clauses: int
    used_full_audit: bool
    exact_soft_violation_rate: float | None = None

    @property
    def clause_evaluation_fraction(self) -> float:
        unique = self.unique_soft_clauses_evaluated + self.hard_clauses_evaluated
        return unique / max(1, self.total_contract_clauses)


def _lower_binomial_bound(losses: np.ndarray, *, delta: float) -> float:
    if len(losses) == 0:
        return 0.0
    successes = 1.0 - losses
    return float(max(0.0, 1.0 - exact_binomial_upper_bound(successes, delta=delta)))


def progressive_semantic_audit(
    contract: SemanticContract,
    oracle: SemanticOracle,
    *,
    max_soft_violation_rate: float = 0.05,
    delta: float = 0.05,
    batch_size: int = 50,
    max_draws: int = 1000,
    seed: int = 17,
    fallback_to_full_audit: bool = True,
) -> ProgressiveAuditResult:
    """Sequentially audit a weighted Semantic Contract with explicit error budget.

    Policy:
    - every hard clause is always evaluated;
    - soft clauses are sampled *with replacement* with probability proportional
      to clause weight, so each Bernoulli draw estimates the weighted soft-clause
      violation rate;
    - repeated indices reuse cached oracle evaluation but remain valid random
      draws from the finite weighted clause population;
    - at each pre-declared batch look, exact one-sided binomial bounds are used;
    - the global ``delta`` is union-split over both tails and all possible looks;
    - PASS occurs when the simultaneous upper bound is at/below the configured
      soft-violation SLA; FAIL occurs when the lower bound is above it;
    - if sampling remains inconclusive, the procedure optionally evaluates the
      remaining clauses and returns the exact weighted decision.

    Missing hard clauses fail immediately. Missing sampled soft clauses are
    conservatively counted as violations. This policy is distinct from the
    historical aggregate contract score and is intended for scalable audit
    SLAs, not as a silent replacement for existing gate semantics.
    """
    if not 0.0 <= max_soft_violation_rate < 1.0:
        raise ValueError("max_soft_violation_rate must be in [0, 1)")
    if not 0.0 < delta < 1.0:
        raise ValueError("delta must be in (0, 1)")
    if batch_size <= 0 or max_draws <= 0:
        raise ValueError("batch_size and max_draws must be positive")

    hard_indices = [index for index, clause in enumerate(contract.clauses) if clause.hard]
    soft_indices = [
        index
        for index, clause in enumerate(contract.clauses)
        if not clause.hard and max(0.0, float(clause.weight)) > 0.0
    ]
    hard_cache: dict[int, ClauseResult | None] = {}
    for index in hard_indices:
        result = evaluate_contract_clause(contract, oracle, index)
        hard_cache[index] = result
        if result is None or not result.passed:
            return ProgressiveAuditResult(
                "fail",
                f"hard clause {index} failed or is missing",
                False,
                float(max_soft_violation_rate),
                1.0,
                1.0,
                1.0,
                float(delta),
                0,
                0,
                len(hard_indices),
                len(soft_indices),
                len(contract.clauses),
                False,
                None,
            )

    if not soft_indices:
        return ProgressiveAuditResult(
            "pass",
            "all hard clauses passed and there are no positive-weight soft clauses",
            True,
            float(max_soft_violation_rate),
            0.0,
            0.0,
            0.0,
            float(delta),
            0,
            0,
            len(hard_indices),
            0,
            len(contract.clauses),
            False,
            0.0,
        )

    weights = np.asarray([max(0.0, float(contract.clauses[index].weight)) for index in soft_indices], dtype=np.float64)
    weights /= max(float(np.sum(weights)), _EPS)
    rng = np.random.default_rng(int(seed))
    cache: dict[int, ClauseResult | None] = {}
    observations: list[float] = []
    max_looks = max(1, int(math.ceil(max_draws / batch_size)))
    per_tail_per_look_delta = float(delta) / (2.0 * max_looks)

    draws = 0
    lower = 0.0
    upper = 1.0
    empirical = 0.0
    for _look in range(max_looks):
        take = min(batch_size, max_draws - draws)
        if take <= 0:
            break
        sampled_positions = rng.choice(len(soft_indices), size=take, replace=True, p=weights)
        for position in sampled_positions:
            index = soft_indices[int(position)]
            if index not in cache:
                cache[index] = evaluate_contract_clause(contract, oracle, index)
            result = cache[index]
            observations.append(1.0 if result is None or not result.passed else 0.0)
        draws += take

        losses = np.asarray(observations, dtype=np.float64)
        empirical = float(np.mean(losses))
        upper = exact_binomial_upper_bound(losses, delta=per_tail_per_look_delta)
        lower = _lower_binomial_bound(losses, delta=per_tail_per_look_delta)
        if upper <= max_soft_violation_rate:
            return ProgressiveAuditResult(
                "pass",
                "simultaneous upper violation bound satisfies the soft-clause SLA",
                True,
                float(max_soft_violation_rate),
                empirical,
                lower,
                upper,
                float(delta),
                draws,
                len(cache),
                len(hard_indices),
                len(soft_indices),
                len(contract.clauses),
                False,
                None,
            )
        if lower > max_soft_violation_rate:
            return ProgressiveAuditResult(
                "fail",
                "simultaneous lower violation bound exceeds the soft-clause SLA",
                True,
                float(max_soft_violation_rate),
                empirical,
                lower,
                upper,
                float(delta),
                draws,
                len(cache),
                len(hard_indices),
                len(soft_indices),
                len(contract.clauses),
                False,
                None,
            )

    if not fallback_to_full_audit:
        return ProgressiveAuditResult(
            "inconclusive",
            "sampling budget exhausted without a certified decision",
            True,
            float(max_soft_violation_rate),
            empirical,
            lower,
            upper,
            float(delta),
            draws,
            len(cache),
            len(hard_indices),
            len(soft_indices),
            len(contract.clauses),
            False,
            None,
        )

    violation_weight = 0.0
    total_weight = 0.0
    for index in soft_indices:
        if index not in cache:
            cache[index] = evaluate_contract_clause(contract, oracle, index)
        result = cache[index]
        weight = max(0.0, float(contract.clauses[index].weight))
        total_weight += weight
        if result is None or not result.passed:
            violation_weight += weight
    exact_rate = 0.0 if total_weight <= _EPS else violation_weight / total_weight
    decision: Literal["pass", "fail"] = "pass" if exact_rate <= max_soft_violation_rate else "fail"
    return ProgressiveAuditResult(
        decision,
        "sampling was inconclusive; completed exact weighted soft-clause audit",
        True,
        float(max_soft_violation_rate),
        float(exact_rate),
        float(exact_rate),
        float(exact_rate),
        float(delta),
        draws,
        len(cache),
        len(hard_indices),
        len(soft_indices),
        len(contract.clauses),
        True,
        float(exact_rate),
    )
