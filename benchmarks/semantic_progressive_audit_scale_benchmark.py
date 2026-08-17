"""Scale test for Progressive Semantic Audit.

The benchmark constructs procedural semantic contracts up to hundreds of
thousands of clauses and asks whether the sequential audit reaches the same
weighted soft-violation SLA decision as the exact contract while evaluating a
shrinking *fraction* of clauses as contract size grows.

This is a scalability/mechanism benchmark. The semantic outcomes are procedural,
not a claim that synthetic clauses model production concept distributions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from semantic_atlas import SemanticContract, TripletClause, progressive_semantic_audit


class ProceduralOracle:
    implementation = "procedural-scale-oracle"

    def __init__(self, count: int, *, violation_rate: float, seed: int) -> None:
        self.count = int(count)
        self.violation_rate = float(violation_rate)
        self.seed = int(seed)
        self.cutoff = int(round(self.violation_rate * 1_000_003))

    def _index(self, object_id: str) -> int | None:
        if len(object_id) < 2 or object_id[0] not in {"a", "p", "n"}:
            return None
        try:
            value = int(object_id[1:])
        except ValueError:
            return None
        return value if 0 <= value < self.count else None

    def _broken(self, index: int) -> bool:
        value = (index * 2654435761 + self.seed * 2246822519) % 1_000_003
        return value < self.cutoff

    def contains(self, object_id: str) -> bool:
        return self._index(object_id) is not None

    def similarity(self, left: str, right: str) -> float:
        if left == right:
            return 1.0
        left_index = self._index(left)
        right_index = self._index(right)
        if left_index is None or right_index is None or left_index != right_index:
            return 0.0
        index = left_index
        if left.startswith("a"):
            if right.startswith("p"):
                return 0.0 if self._broken(index) else 1.0
            if right.startswith("n"):
                return 1.0 if self._broken(index) else 0.0
        if right.startswith("a"):
            return self.similarity(right, left)
        return 0.0

    def neighbors(self, anchor: str, k: int):
        return ()


def make_contract(count: int) -> SemanticContract:
    weights = (0.5, 1.0, 2.0, 5.0)
    clauses = [
        TripletClause(
            f"a{index}",
            f"p{index}",
            f"n{index}",
            weight=weights[index % len(weights)],
            source="procedural-scale",
        )
        for index in range(int(count))
    ]
    return SemanticContract(
        "progressive-audit-scale",
        "1",
        clauses=clauses,
        metadata={"synthetic": True, "purpose": "audit-cost scaling"},
    )


def exact_weighted_rate(contract: SemanticContract, oracle: ProceduralOracle) -> float:
    total = violated = 0.0
    for index, clause in enumerate(contract.clauses):
        weight = max(0.0, float(clause.weight))
        if weight <= 0.0 or clause.hard:
            continue
        total += weight
        if oracle._broken(index):
            violated += weight
    return 0.0 if total == 0.0 else violated / total


def run_case(
    contract: SemanticContract,
    *,
    violation_rate: float,
    sla: float,
    seed: int,
    batch_size: int,
    max_draws: int,
    fallback_to_full: bool,
) -> dict:
    oracle = ProceduralOracle(len(contract.clauses), violation_rate=violation_rate, seed=seed)
    exact = exact_weighted_rate(contract, oracle)
    exact_decision = "pass" if exact <= sla else "fail"
    started = time.perf_counter()
    result = progressive_semantic_audit(
        contract,
        oracle,
        max_soft_violation_rate=sla,
        delta=0.05,
        batch_size=batch_size,
        max_draws=max_draws,
        seed=seed + 101,
        fallback_to_full_audit=fallback_to_full,
    )
    elapsed = time.perf_counter() - started
    return {
        "declared_violation_rate": violation_rate,
        "exact_weighted_violation_rate": exact,
        "sla": sla,
        "exact_decision": exact_decision,
        "progressive_decision": result.decision,
        "decision_match": result.decision == exact_decision,
        "draws": result.draws,
        "unique_soft_clauses_evaluated": result.unique_soft_clauses_evaluated,
        "clause_evaluation_fraction": result.clause_evaluation_fraction,
        "used_full_audit": result.used_full_audit,
        "lower_bound": result.lower_violation_bound,
        "upper_bound": result.upper_violation_bound,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Progressive Semantic Audit scaling benchmark")
    parser.add_argument("--sizes", default="10000,100000,250000")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-draws", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=811)
    parser.add_argument("--output", default="artifacts/progressive_audit_scale.json")
    args = parser.parse_args()

    sizes = [int(value) for value in args.sizes.split(",") if value.strip()]
    rows = []
    for size_index, size in enumerate(sizes):
        build_started = time.perf_counter()
        contract = make_contract(size)
        build_seconds = time.perf_counter() - build_started
        cases = [
            (0.00, 0.05),
            (0.20, 0.05),
            (0.10, 0.05),
        ]
        if size == min(sizes):
            cases.append((0.05, 0.05))
        for case_index, (violation_rate, sla) in enumerate(cases):
            row = run_case(
                contract,
                violation_rate=violation_rate,
                sla=sla,
                seed=args.seed + size_index * 1009 + case_index * 37,
                batch_size=args.batch_size,
                max_draws=args.max_draws,
                fallback_to_full=True,
            )
            row["contract_clauses"] = size
            row["contract_build_seconds"] = build_seconds
            rows.append(row)

    matches = [row["decision_match"] for row in rows]
    early = [row for row in rows if not row["used_full_audit"] and row["progressive_decision"] != "inconclusive"]
    by_size = {}
    for size in sizes:
        subset = [row for row in early if row["contract_clauses"] == size]
        by_size[str(size)] = {
            "early_decisions": len(subset),
            "mean_clause_fraction": float(np.mean([row["clause_evaluation_fraction"] for row in subset])) if subset else None,
            "max_clause_fraction": float(np.max([row["clause_evaluation_fraction"] for row in subset])) if subset else None,
            "mean_unique_clauses": float(np.mean([row["unique_soft_clauses_evaluated"] for row in subset])) if subset else None,
        }

    result = {
        "benchmark": "progressive-semantic-audit-scale-v1",
        "sizes": sizes,
        "weighted_clause_cycle": [0.5, 1.0, 2.0, 5.0],
        "delta": 0.05,
        "batch_size": args.batch_size,
        "max_draws": args.max_draws,
        "decision_match_rate": float(np.mean(matches)) if matches else None,
        "early_decisions": len(early),
        "early_decision_fraction": len(early) / max(1, len(rows)),
        "by_contract_size": by_size,
        "rows": rows,
        "warning": (
            "This demonstrates the statistical sampling mechanics and asymptotic audit-cost behavior on procedural clauses. "
            "It is not evidence that production semantic violations are iid, stationary, or represented by the synthetic generator."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
