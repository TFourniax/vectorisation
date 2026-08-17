from semantic_atlas.contracts import ClauseResult, ContractReport, SemanticContract, TripletClause
from semantic_atlas.diagnostic import build_semantic_diagnostic_panel, evaluate_diagnostic_panel
from semantic_atlas.witness import WitnessScenario


def make_contract():
    return SemanticContract(
        "diagnostic-demo",
        "1",
        clauses=[
            TripletClause("a", "b", "c"),
            TripletClause("d", "e", "f"),
            TripletClause("g", "h", "i"),
        ],
    )


def make_report(contract, name, scores):
    results = []
    for index, (clause, score) in enumerate(zip(contract.clauses, scores)):
        results.append(
            ClauseResult(
                clause_index=index,
                kind=clause.kind,
                score=float(score),
                passed=score >= 1.0,
                hard=clause.hard,
                weight=clause.weight,
                objects=clause.objects,
                detail={},
            )
        )
    return ContractReport(
        contract.name,
        contract.digest,
        name,
        sum(scores) / len(scores),
        True,
        results,
        {},
        len(results),
        0,
    )


def test_diagnostic_panel_selects_discriminative_clause_and_generalizes():
    contract = make_contract()
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0])
    train = [
        WitnessScenario("fault-1", make_report(contract, "fault-1", [0.2, 1.0, 0.95])),
        WitnessScenario("fault-2", make_report(contract, "fault-2", [0.3, 1.0, 1.0])),
        WitnessScenario("benign-1", make_report(contract, "benign-1", [0.99, 0.8, 1.0])),
        WitnessScenario("benign-2", make_report(contract, "benign-2", [1.0, 0.85, 0.98])),
    ]
    panel = build_semantic_diagnostic_panel(contract, baseline, train, max_clauses=1, detection_drop=0.10)
    assert panel.selected_clause_indices == (0,)
    assert panel.training_evaluation.true_positive_rate == 1.0
    assert panel.training_evaluation.false_positive_rate == 0.0

    heldout = [
        WitnessScenario("fault-heldout", make_report(contract, "fault-heldout", [0.4, 1.0, 1.0])),
        WitnessScenario("benign-heldout", make_report(contract, "benign-heldout", [0.98, 0.7, 1.0])),
    ]
    evaluation = evaluate_diagnostic_panel(panel, baseline, heldout)
    assert evaluation.true_positive_rate == 1.0
    assert evaluation.false_positive_rate == 0.0


def test_diagnostic_panel_requires_positive_and_negative_training_examples():
    contract = make_contract()
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0])
    only_faults = [WitnessScenario("fault", make_report(contract, "fault", [0.0, 1.0, 1.0]))]
    try:
        build_semantic_diagnostic_panel(contract, baseline, only_faults, max_clauses=1, detection_drop=0.10)
    except ValueError as exc:
        assert "both regression and non-regression" in str(exc)
    else:
        raise AssertionError("expected mixed-label validation")
