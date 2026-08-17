from __future__ import annotations

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.incremental_v1 import execute_contract_plan_incremental
from semantic_atlas.protocol_v1 import NeighborRequest, OracleManifest, ScorePair, compile_contract, execute_contract_plan


class VersionedOracle:
    def __init__(self, state="state-A"):
        self.manifest = OracleManifest(
            "incremental-test",
            implementation_kind="test",
            score_semantics="directional",
            score_directionality="asymmetric",
            deterministic=True,
            metadata={"state_digest": state},
        )
        self.ids = {"q", "a", "b", "c", "d"}
        self.scores = {
            ScorePair("q", "a"): 4.0,
            ScorePair("q", "b"): 3.0,
            ScorePair("q", "c"): 2.0,
            ScorePair("q", "d"): 1.0,
        }
        self.calls = {"contains": [], "score": [], "neighbors": []}

    def contains_many(self, ids):
        ids = tuple(ids); self.calls["contains"].append(ids)
        return {x: x in self.ids for x in ids}

    def score_many(self, pairs):
        pairs = tuple(pairs); self.calls["score"].append(pairs)
        return {pair: self.scores[pair] for pair in pairs}

    def neighbors_many(self, requests):
        requests = tuple(requests); self.calls["neighbors"].append(requests)
        ranking = ("a", "b", "c", "d")
        return {req: ranking[: req.k] for req in requests}


def c1():
    return SemanticContract("v", "1", clauses=[NeighborClause("q", ("a",), candidate_k=3), TripletClause("q", "a", "c")])


def c2():
    return SemanticContract("v", "2", clauses=[
        NeighborClause("q", ("a",), candidate_k=2),  # can reuse old top-3 prefix
        TripletClause("q", "a", "c"),               # exact score pairs reusable
        TripletClause("q", "b", "d"),               # adds two score pairs + IDs
    ])


def test_incremental_execution_fetches_only_delta_operations():
    oracle = VersionedOracle()
    p1 = compile_contract(c1())
    s1 = execute_contract_plan(p1, oracle)
    oracle.calls = {"contains": [], "score": [], "neighbors": []}

    p2 = compile_contract(c2())
    result = execute_contract_plan_incremental(p2, oracle, previous_plan=p1, previous_snapshot=s1)

    assert result.stats.reused_object_checks == 3  # q, a, c
    assert result.stats.fetched_object_checks == 2  # b, d
    assert result.stats.reused_score_pairs == 2
    assert result.stats.fetched_score_pairs == 2
    assert result.stats.reused_neighbor_requests == 1
    assert result.stats.fetched_neighbor_requests == 0
    assert result.stats.transport_round_trips == 2
    assert result.stats.reuse_fraction > 0.5
    assert oracle.calls["contains"] == [("b", "d")]
    assert set(oracle.calls["score"][0]) == {ScorePair("q", "b"), ScorePair("q", "d")}
    assert oracle.calls["neighbors"] == []
    assert result.snapshot.neighbors("q", 2) == ("a", "b")


def test_incremental_execution_refuses_changed_state():
    first = VersionedOracle("state-A")
    p1 = compile_contract(c1())
    s1 = execute_contract_plan(p1, first)
    changed = VersionedOracle("state-B")
    try:
        execute_contract_plan_incremental(compile_contract(c2()), changed, previous_plan=p1, previous_snapshot=s1)
    except ValueError as exc:
        assert "manifest/state changed" in str(exc)
    else:
        raise AssertionError("state change must invalidate cached oracle evidence")


def test_incremental_execution_requires_state_digest():
    first = VersionedOracle()
    p1 = compile_contract(c1())
    s1 = execute_contract_plan(p1, first)
    unsafe = VersionedOracle()
    unsafe.manifest = OracleManifest("incremental-test", score_directionality="asymmetric")
    try:
        execute_contract_plan_incremental(compile_contract(c2()), unsafe, previous_plan=p1, previous_snapshot=s1)
    except ValueError as exc:
        assert "state_digest" in str(exc)
    else:
        raise AssertionError("incremental execution without a state identity must be rejected")


def test_incremental_execution_requires_determinism():
    first = VersionedOracle()
    p1 = compile_contract(c1())
    s1 = execute_contract_plan(p1, first)
    unsafe = VersionedOracle()
    unsafe.manifest = OracleManifest(
        "incremental-test",
        score_directionality="asymmetric",
        deterministic=False,
        metadata={"state_digest": "state-A"},
    )
    # Make manifest identity match impossible by design; determinism is checked first.
    try:
        execute_contract_plan_incremental(compile_contract(c2()), unsafe, previous_plan=p1, previous_snapshot=s1)
    except ValueError as exc:
        assert "deterministic" in str(exc)
    else:
        raise AssertionError("nondeterministic oracle reuse must be rejected")
