from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.oracle import CallbackSemanticOracle, audit_contract
from semantic_atlas.repair_incidence import plan_repairs_by_clause_incidence


def test_neighbor_incidence_prioritizes_missing_expected_document_over_query_anchor():
    contract = SemanticContract(
        "incidence-neighbor",
        "1",
        clauses=[
            NeighborClause(
                "q",
                ("expected",),
                min_recall=1.0,
                candidate_k=1,
                weight=2.0,
            )
        ],
    )
    oracle = CallbackSemanticOracle(
        frozenset({"q", "expected", "intruder"}),
        lambda left, right: 1.0 if {left, right} == {"q", "intruder"} else 0.0,
        lambda anchor, k: ("intruder",) if anchor == "q" else (),
        implementation="broken-neighbor",
    )
    report = audit_contract(contract, oracle)
    assert len(report.violated) == 1

    plan = plan_repairs_by_clause_incidence(
        contract,
        report,
        oracle,
        budget=1.0,
        repairable_ids={"expected", "intruder"},
    )
    assert plan.candidates[0].object_id == "expected"
    assert plan.candidates[0].role_mass["missing_expected_neighbor"] > 0.0
    assert "q" not in [candidate.object_id for candidate in plan.candidates]


def test_neighbor_incidence_keeps_intruder_as_secondary_causal_suspect():
    contract = SemanticContract(
        "incidence-intruder",
        "1",
        clauses=[NeighborClause("anchor", ("expected",), min_recall=1.0, candidate_k=1)],
    )
    oracle = CallbackSemanticOracle(
        frozenset({"anchor", "expected", "intruder"}),
        lambda left, right: 0.0,
        lambda anchor, k: ("intruder",) if anchor == "anchor" else (),
    )
    report = audit_contract(contract, oracle)
    plan = plan_repairs_by_clause_incidence(
        contract,
        report,
        oracle,
        budget=2.0,
        repairable_ids={"expected", "intruder"},
    )
    assert [candidate.object_id for candidate in plan.candidates] == ["expected", "intruder"]
    assert plan.candidates[0].blame_mass > plan.candidates[1].blame_mass


def test_triplet_incidence_prefers_repairable_members_when_anchor_is_not_repairable():
    contract = SemanticContract(
        "incidence-triplet",
        "1",
        clauses=[TripletClause("query", "positive", "negative", margin=0.0, weight=1.0)],
    )

    def similarity(left, right):
        pair = {left, right}
        if pair == {"query", "positive"}:
            return 0.1
        if pair == {"query", "negative"}:
            return 0.9
        return 0.0

    oracle = CallbackSemanticOracle(
        frozenset({"query", "positive", "negative"}),
        similarity,
        lambda anchor, k: (),
    )
    report = audit_contract(contract, oracle)
    plan = plan_repairs_by_clause_incidence(
        contract,
        report,
        oracle,
        budget=2.0,
        repairable_ids={"positive", "negative"},
    )
    assert {candidate.object_id for candidate in plan.candidates} == {"positive", "negative"}
    assert abs(plan.candidates[0].blame_mass - plan.candidates[1].blame_mass) < 1e-12


def test_incidence_plan_rejects_report_from_different_contract():
    left = SemanticContract("left", "1", clauses=[TripletClause("a", "b", "c")])
    right = SemanticContract("right", "1", clauses=[TripletClause("a", "b", "c")])
    oracle = CallbackSemanticOracle(
        frozenset({"a", "b", "c"}),
        lambda l, r: 0.0,
        lambda anchor, k: (),
    )
    report = audit_contract(left, oracle)
    try:
        plan_repairs_by_clause_incidence(right, report, oracle, budget=1.0)
    except ValueError as exc:
        assert "does not belong" in str(exc)
    else:
        raise AssertionError("expected contract/report identity check")
