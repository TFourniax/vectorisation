from __future__ import annotations

from semantic_atlas.compatibility_v1 import check_plan_compatibility
from semantic_atlas.contracts import MutualNeighborClause, NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import OracleManifest, compile_contract


def directional_manifest():
    return OracleManifest(
        "directional",
        implementation_kind="late_interaction",
        score_directionality="asymmetric",
        metadata={
            "score_anchor_prefixes": ["q:"],
            "score_candidate_prefixes": ["d:"],
            "neighbor_anchor_prefixes": ["q:"],
        },
    )


def test_query_document_contract_is_compatible_with_directional_provider():
    contract = SemanticContract("ok", "1", clauses=[
        NeighborClause("q:1", ("d:a",), candidate_k=5),
        TripletClause("q:1", "d:a", "d:b"),
    ])
    report = check_plan_compatibility(compile_contract(contract), directional_manifest())
    assert report.compatible
    assert not report.issues


def test_mutual_document_neighborhood_fails_fast_for_query_only_provider():
    contract = SemanticContract("bad", "1", clauses=[MutualNeighborClause("d:a", "d:b", k=5)])
    report = check_plan_compatibility(compile_contract(contract), directional_manifest())
    assert not report.compatible
    assert any(issue.code == "unsupported-neighbor-anchor" for issue in report.issues)


def test_missing_capability_is_reported_before_execution():
    contract = SemanticContract("triplet", "1", clauses=[TripletClause("q:1", "d:a", "d:b")])
    manifest = OracleManifest("ranking-only", capabilities=("contains_many", "neighbors_many"))
    report = check_plan_compatibility(compile_contract(contract), manifest)
    assert not report.compatible
    assert any(issue.context.get("capability") == "score_many" for issue in report.issues)
