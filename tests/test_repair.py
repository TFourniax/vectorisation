import numpy as np

from semantic_atlas.contracts import ClauseResult, ContractReport, contract_from_labels
from semantic_atlas.repair import plan_repairs, plan_repairs_by_coverage


def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def mapping(x):
    return {str(i): x[i] for i in range(len(x))}


def test_repair_planner_enriches_for_corrupted_objects():
    rng = np.random.default_rng(5)
    centers = normalize(rng.normal(size=(4, 10)))
    x = np.vstack([normalize(c + rng.normal(scale=0.07, size=(35, 10))) for c in centers])
    labels = {str(i): i // 35 for i in range(len(x))}
    vectors = mapping(x)
    contract = contract_from_labels(vectors, labels, anchors=[str(i) for i in range(len(x))], triplets_per_anchor=5)

    broken = x.copy()
    corrupt = set(range(35, 50)) | set(range(105, 120))
    broken[list(corrupt)] = broken[list(range(70, 85)) + list(range(0, 15))]
    broken_vectors = mapping(broken)
    report = contract.audit(broken_vectors)
    plan = plan_repairs(report, broken_vectors, limit=30, diversity_weight=0.25)
    selected = {int(candidate.object_id) for candidate in plan.candidates}

    # Random expectation is ~6.4 corrupt objects in 30 draws from 140.
    assert len(selected & corrupt) >= 12
    assert plan.risk_mass_coverage > 0.20


def test_cost_aware_planner_maximizes_known_violation_coverage():
    violations = [
        ClauseResult(0, "triplet", 0.0, False, False, 3.0, ("a", "b", "c"), {}),
        ClauseResult(1, "neighbor", 0.2, False, False, 2.0, ("a", "d"), {}),
        ClauseResult(2, "triplet", 0.5, False, True, 2.0, ("e", "f", "g"), {}),
    ]
    report = ContractReport(
        contract_name="demo",
        contract_digest="digest",
        implementation="candidate",
        score=0.4,
        hard_pass=False,
        clause_results=violations,
        object_risk={"a": 0.9, "b": 0.5, "c": 0.4, "d": 0.6, "e": 0.8, "f": 0.4, "g": 0.4},
        evaluated_clauses=3,
        missing_clauses=0,
    )
    plan = plan_repairs_by_coverage(
        report,
        budget=2.0,
        costs={"a": 1.0, "b": 1.0, "c": 1.0, "d": 1.0, "e": 1.0, "f": 3.0, "g": 3.0},
        risk_bonus_weight=0.0,
    )
    selected = [candidate.object_id for candidate in plan.candidates]

    # a touches the two highest-mass soft violations; e then covers the hard one.
    assert selected == ["a", "e"]
    assert plan.spent == 2.0
    assert plan.violation_mass_coverage == 1.0
    assert set(plan.covered_clause_indices) == {0, 1, 2}
