from __future__ import annotations

import numpy as np

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.conformance import check_oracle_conformance
from semantic_atlas.late_interaction import LateInteractionOracleV1, maxsim_score
from semantic_atlas.protocol_v1 import (
    NeighborRequest,
    OracleManifest,
    ScorePair,
    audit_contract_v1,
    compile_contract,
)


class TableOracle:
    def __init__(self, *, rankings=None, deterministic=True, directionality="asymmetric"):
        self.rankings = rankings or {"q": ("a", "b", "c")}
        self.ids = {"q", "a", "b", "c"}
        self.scores = {
            ScorePair("q", "a"): 3.0,
            ScorePair("q", "b"): 2.0,
            ScorePair("q", "c"): 1.0,
        }
        self.manifest = OracleManifest(
            "table",
            implementation_kind="test",
            score_semantics="directional-table",
            score_directionality=directionality,
            deterministic=deterministic,
        )
        self.calls = {"contains": 0, "score": 0, "neighbors": 0}

    def contains_many(self, object_ids):
        self.calls["contains"] += 1
        return {x: x in self.ids for x in object_ids}

    def score_many(self, pairs):
        self.calls["score"] += 1
        return {pair: self.scores[pair] for pair in pairs}

    def neighbors_many(self, requests):
        self.calls["neighbors"] += 1
        return {req: tuple(self.rankings.get(req.anchor, ()))[: req.k] for req in requests}


def contract() -> SemanticContract:
    return SemanticContract(
        "protocol-test",
        "1",
        clauses=[
            NeighborClause("q", ("a",), min_recall=1.0, candidate_k=2, hard=True),
            TripletClause("q", "a", "c", margin=0.5, hard=True),
            TripletClause("q", "a", "c", margin=0.25),  # deliberate duplicate operations
        ],
    )


def test_compile_contract_deduplicates_oracle_operations():
    plan = compile_contract(contract())
    assert plan.clause_count == 3
    assert plan.object_ids == ("a", "c", "q")
    assert plan.score_pairs == (ScorePair("q", "a"), ScorePair("q", "c"))
    assert plan.neighbor_requests == (NeighborRequest("q", 2),)
    assert len(plan.digest) == 64


def test_protocol_audit_executes_one_batch_per_operation_family():
    oracle = TableOracle()
    result = audit_contract_v1(contract(), oracle)
    assert result.report.hard_pass
    assert result.report.score == 1.0
    assert result.snapshot.stats.transport_round_trips == 3
    assert oracle.calls == {"contains": 1, "score": 1, "neighbors": 1}
    assert result.report.clause_results[1].detail["protocol_version"] == 1


def test_directional_score_does_not_require_reverse_pair():
    oracle = TableOracle(directionality="asymmetric")
    result = audit_contract_v1(contract(), oracle)
    assert result.report.hard_pass
    assert all(pair.anchor == "q" for pair in result.plan.score_pairs)


def test_maxsim_is_directional_and_explainable():
    # q has two opposing tokens while d has one. Query->document MaxSim sums
    # +1 and -1 (=0); reversing the operands has a single query token whose
    # best match is +1. The asymmetry is therefore structural, not numerical.
    q = np.asarray([[1.0, 0.0], [-1.0, 0.0]], dtype=np.float32)
    d = np.asarray([[1.0, 0.0]], dtype=np.float32)
    forward = maxsim_score(q, d)
    reverse = maxsim_score(d, q)
    assert np.isclose(forward, 0.0, atol=1e-6)
    assert np.isclose(reverse, 1.0, atol=1e-6)

    oracle = LateInteractionOracleV1(
        {"q": q},
        {"a": d, "b": np.asarray([[0.0, 1.0]], dtype=np.float32)},
        rankings={"q": ("a", "b")},
        implementation_id="maxsim-test",
    )
    explanation = oracle.explain("q", "a")
    assert explanation.query_token_best_document_token == (0, 0)
    assert np.allclose(explanation.query_token_scores, (1.0, -1.0), atol=1e-6)
    assert np.isclose(explanation.total_score, forward)
    assert oracle.manifest.score_directionality == "asymmetric"


def test_late_interaction_oracle_executes_semantic_contract():
    q = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    good = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    bad = np.asarray([[-1.0, 0.0], [0.0, -1.0]], dtype=np.float32)
    oracle = LateInteractionOracleV1({"q": q}, {"a": good, "c": bad}, rankings={"q": ("a", "c")})
    result = audit_contract_v1(
        SemanticContract("late", "1", clauses=[NeighborClause("q", ("a",), candidate_k=1), TripletClause("q", "a", "c")]),
        oracle,
    )
    assert result.report.score == 1.0
    assert result.report.missing_clauses == 0


def test_conformance_accepts_stable_directional_oracle():
    report = check_oracle_conformance(
        TableOracle(),
        anchors=["q"],
        k_values=(1, 2, 3),
        score_pairs=(ScorePair("q", "a"), ScorePair("q", "c")),
    )
    assert report.passed
    assert not report.issues


def test_conformance_rejects_topk_prefix_instability():
    class Broken(TableOracle):
        def neighbors_many(self, requests):
            self.calls["neighbors"] += 1
            out = {}
            for req in requests:
                out[req] = ("a",) if req.k == 1 else ("b", "a")[: req.k]
            return out

    report = check_oracle_conformance(Broken(), anchors=["q"], k_values=(1, 2))
    assert not report.passed
    assert any(issue.code == "topk-prefix-violation" for issue in report.issues)
