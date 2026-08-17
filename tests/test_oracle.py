import numpy as np

from semantic_atlas.contracts import MutualNeighborClause, NeighborClause, SemanticContract, TripletClause
from semantic_atlas.oracle import CallbackSemanticOracle, DenseVectorOracle, audit_contract


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def build_contract():
    contract = SemanticContract("oracle-demo", "1")
    contract.add(TripletClause("a", "b", "d", hard=True))
    contract.add(NeighborClause("a", ("b", "c"), min_recall=1.0, candidate_k=2))
    contract.add(MutualNeighborClause("a", "b", k=2))
    return contract


def test_dense_oracle_matches_legacy_dense_contract_audit():
    vectors = {
        "a": unit([1.0, 0.0, 0.0]),
        "b": unit([0.95, 0.25, 0.0]),
        "c": unit([0.82, 0.56, 0.0]),
        "d": unit([-1.0, 0.0, 0.0]),
    }
    contract = build_contract()
    legacy = contract.audit(vectors, implementation="legacy")
    via_oracle = audit_contract(contract, DenseVectorOracle(vectors, implementation="oracle"))

    assert via_oracle.score == legacy.score
    assert via_oracle.hard_pass == legacy.hard_pass
    assert via_oracle.missing_clauses == legacy.missing_clauses
    assert [row.passed for row in via_oracle.clause_results] == [row.passed for row in legacy.clause_results]
    assert via_oracle.object_risk == legacy.object_risk


def test_callback_oracle_audits_non_vector_semantic_system():
    # This semantic implementation has no coordinates. It could represent a
    # graph, sparse ranker or remote search service. Only behavior is exposed.
    affinities = {
        frozenset(("a", "b")): 0.95,
        frozenset(("a", "c")): 0.80,
        frozenset(("a", "d")): 0.05,
        frozenset(("b", "c")): 0.72,
        frozenset(("b", "d")): 0.10,
        frozenset(("c", "d")): 0.20,
    }
    neighbors = {
        "a": ("b", "c", "d"),
        "b": ("a", "c", "d"),
        "c": ("a", "b", "d"),
        "d": ("c", "b", "a"),
    }
    oracle = CallbackSemanticOracle(
        object_ids=frozenset(neighbors),
        similarity_fn=lambda left, right: 1.0 if left == right else affinities[frozenset((left, right))],
        neighbors_fn=lambda anchor, k: neighbors[anchor][:k],
        implementation="symbolic-graph-ranker",
    )
    report = audit_contract(build_contract(), oracle)

    assert report.implementation == "symbolic-graph-ranker"
    assert report.hard_pass
    assert report.score == 1.0
    assert report.missing_clauses == 0
    assert all(result.passed for result in report.clause_results)


def test_oracle_missing_hard_object_blocks_contract():
    oracle = CallbackSemanticOracle(
        object_ids=frozenset({"a", "b", "c"}),
        similarity_fn=lambda left, right: 0.5,
        neighbors_fn=lambda anchor, k: tuple(x for x in ("a", "b", "c") if x != anchor)[:k],
        implementation="incomplete",
    )
    report = audit_contract(build_contract(), oracle)
    assert not report.hard_pass
    assert report.missing_clauses >= 1
