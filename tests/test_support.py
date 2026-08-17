import numpy as np

from semantic_atlas.contracts import ContractReport, SemanticContract, TripletClause
from semantic_atlas.support import contract_coverage, estimate_local_semantic_risk


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def test_contract_coverage_exposes_sparse_semantic_schema():
    contract = SemanticContract("demo", "1")
    contract.add(TripletClause("a", "b", "c"))
    vectors = {
        "a": unit([1, 0, 0]),
        "b": unit([0.9, 0.1, 0]),
        "c": unit([-1, 0, 0]),
        "d": unit([0, 1, 0]),
        "e": unit([0, 0, 1]),
    }
    coverage = contract_coverage(contract, vectors)
    assert coverage.referenced_objects == 3
    assert coverage.present_referenced_objects == 3
    assert coverage.object_coverage == 3 / 5
    assert coverage.triplet_clauses == 1


def test_support_aware_risk_abstains_far_from_contract_landmarks():
    landmarks = {
        "a": unit([1.0, 0.0, 0.0]),
        "b": unit([0.98, 0.2, 0.0]),
        "c": unit([0.96, -0.25, 0.0]),
        "d": unit([0.92, 0.35, 0.0]),
    }
    report = ContractReport(
        contract_name="demo",
        contract_digest="x",
        implementation="candidate",
        score=0.98,
        hard_pass=True,
        clause_results=[],
        object_risk={key: 0.02 for key in landmarks},
        evaluated_clauses=0,
        missing_clauses=0,
    )

    inside = estimate_local_semantic_risk(report, unit([1.0, 0.05, 0.0]), landmarks, k=3)
    outside = estimate_local_semantic_risk(report, unit([0.0, 0.0, 1.0]), landmarks, k=3)

    assert inside.support > 0.90
    assert inside.risk < 0.10
    assert outside.support < 0.20
    assert outside.risk > 0.75
    assert outside.interpolated_risk < 0.10  # proves support, not neighbor risk, caused abstention
