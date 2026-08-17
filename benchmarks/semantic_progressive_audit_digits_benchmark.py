"""Progressive Semantic Audit benchmark on real handwritten digits.

The full 1,500-clause contract is the reference. Hard clauses (none in this
label-derived benchmark) would always be evaluated. Soft clauses are sampled
proportional to weight, and exact-binomial bounds with alpha spending decide
whether weighted violation mass is below an SLA. Inconclusive cases fall back
to the exact full audit.

The metric is not retrieval quality; it is **unique contract clauses actually
evaluated before reaching the same SLA decision as the exhaustive audit**.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.geometry import normalize
from semantic_atlas.mutation import default_semantic_mutations
from semantic_atlas.oracle import DenseVectorOracle, audit_contract
from semantic_atlas.progressive_audit import progressive_semantic_audit


def exact_weighted_soft_violation_rate(contract, report) -> float:
    result_map = {result.clause_index: result for result in report.clause_results}
    total = 0.0
    violated = 0.0
    for index, clause in enumerate(contract.clauses):
        if clause.hard:
            continue
        weight = max(0.0, float(clause.weight))
        if weight <= 0.0:
            continue
        total += weight
        result = result_map.get(index)
        if result is None or not result.passed:
            violated += weight
    return 0.0 if total == 0.0 else violated / total


def main() -> None:
    digits = load_digits()
    vectors = normalize(digits.data.astype(np.float32))
    labels = np.asarray(digits.target)
    rng = np.random.default_rng(77)
    chosen = np.sort(rng.choice(len(vectors), size=1000, replace=False))
    ids = [str(int(idx)) for idx in chosen]
    mapping = {object_id: vectors[idx] for object_id, idx in zip(ids, chosen)}
    label_map = {object_id: int(labels[idx]) for object_id, idx in zip(ids, chosen)}

    contract = contract_from_labels(
        mapping,
        label_map,
        anchors=ids[:300],
        triplets_per_anchor=5,
        seed=19,
        name="digits-progressive-audit-source",
    )
    scenarios = [("baseline", mapping)] + [
        (mutation.name, mutation.vectors)
        for mutation in default_semantic_mutations(mapping, fraction=0.10, seed=23)
    ]

    rows = []
    for name, scenario_vectors in scenarios:
        oracle = DenseVectorOracle(scenario_vectors, implementation=name)
        full_report = audit_contract(contract, oracle)
        exact_rate = exact_weighted_soft_violation_rate(contract, full_report)
        for sla in (0.02, 0.05, 0.10):
            progressive = progressive_semantic_audit(
                contract,
                oracle,
                max_soft_violation_rate=sla,
                delta=0.05,
                batch_size=50,
                max_draws=750,
                seed=31,
                fallback_to_full_audit=True,
            )
            exact_decision = "pass" if full_report.hard_pass and exact_rate <= sla else "fail"
            rows.append(
                {
                    "scenario": name,
                    "sla": sla,
                    "exact_soft_violation_rate": exact_rate,
                    "exact_decision": exact_decision,
                    "progressive_decision": progressive.decision,
                    "decision_match": progressive.decision == exact_decision,
                    "draws": progressive.draws,
                    "unique_soft_clauses_evaluated": progressive.unique_soft_clauses_evaluated,
                    "clause_evaluation_fraction": progressive.clause_evaluation_fraction,
                    "used_full_audit": progressive.used_full_audit,
                    "lower_bound": progressive.lower_violation_bound,
                    "upper_bound": progressive.upper_violation_bound,
                }
            )

    matches = [row["decision_match"] for row in rows]
    non_full = [row for row in rows if not row["used_full_audit"]]
    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(mapping),
                "contract_clauses": len(contract.clauses),
                "scenarios": len(scenarios),
                "sla_values": [0.02, 0.05, 0.10],
                "delta": 0.05,
                "decision_match_rate": float(np.mean(matches)),
                "non_full_decisions": len(non_full),
                "mean_clause_evaluation_fraction_non_full": (
                    float(np.mean([row["clause_evaluation_fraction"] for row in non_full])) if non_full else None
                ),
                "rows": rows,
                "warning": (
                    "The probabilistic guarantee concerns the weighted soft-clause violation-rate policy under the declared randomized "
                    "sampling procedure; it is distinct from aggregate SemanticContract score semantics and does not remove the need "
                    "to evaluate every hard clause."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
