from semantic_atlas.contract_lint import lint_contract
from semantic_atlas.contracts import MutualNeighborClause, NeighborClause, SemanticContract, TripletClause


def test_lint_rejects_impossible_neighbor_recall_and_degenerate_relations():
    contract = SemanticContract("bad", "1")
    contract.add(NeighborClause("a", ("b", "c", "d", "e"), min_recall=0.75, candidate_k=2))
    contract.add(MutualNeighborClause("x", "x", k=0))
    report = lint_contract(contract)

    assert not report.valid
    assert report.by_code("impossible_neighbor_recall")
    assert report.by_code("degenerate_mutual_neighbor")
    assert report.by_code("invalid_mutual_k")


def test_lint_detects_reversed_triplets_and_positive_margin_cycle():
    contract = SemanticContract("cycle", "1")
    contract.add(TripletClause("q", "a", "b", margin=0.1, hard=True))
    contract.add(TripletClause("q", "b", "c", margin=0.1, hard=True))
    contract.add(TripletClause("q", "c", "a", margin=0.1, hard=True))
    contract.add(TripletClause("q", "b", "a", margin=0.1, hard=True))
    report = lint_contract(contract)

    assert not report.valid
    assert report.by_code("reversed_triplet")
    assert report.by_code("impossible_preference_cycle")


def test_zero_margin_cycle_is_warning_not_mathematical_impossibility():
    contract = SemanticContract("ties", "1")
    contract.add(TripletClause("q", "a", "b", margin=0.0))
    contract.add(TripletClause("q", "b", "c", margin=0.0))
    contract.add(TripletClause("q", "c", "a", margin=0.0))
    report = lint_contract(contract)

    assert report.valid
    assert report.by_code("degenerate_preference_cycle")


def test_clean_contract_has_no_lint_errors():
    contract = SemanticContract("good", "1")
    contract.add(TripletClause("q", "a", "b", margin=0.05))
    contract.add(NeighborClause("q", ("a", "c"), min_recall=0.5, candidate_k=2))
    contract.add(MutualNeighborClause("a", "c", k=3))
    report = lint_contract(contract)
    assert report.valid
    assert not report.errors
