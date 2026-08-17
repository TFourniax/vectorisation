from semantic_atlas.contracts import ClauseResult, ContractReport, SemanticContract, TripletClause
from semantic_atlas.witness import WitnessScenario, build_semantic_witness_set, evaluate_clause_subset


def make_report(contract, name, scores, *, hard_fail_indices=()):
    results = []
    for index, (clause, score) in enumerate(zip(contract.clauses, scores)):
        passed = score >= 1.0 and index not in set(hard_fail_indices)
        results.append(
            ClauseResult(
                clause_index=index,
                kind=clause.kind,
                score=float(score),
                passed=passed,
                hard=clause.hard,
                weight=clause.weight,
                objects=clause.objects,
                detail={},
            )
        )
    total_weight = sum(result.weight for result in results)
    weighted = sum(result.weight * result.score for result in results)
    hard_pass = not any(result.hard and not result.passed for result in results)
    return ContractReport(
        contract_name=contract.name,
        contract_digest=contract.digest,
        implementation=name,
        score=weighted / total_weight,
        hard_pass=hard_pass,
        clause_results=results,
        object_risk={},
        evaluated_clauses=len(results),
        missing_clauses=0,
    )


def base_contract(*, hard=()):
    clauses = [
        TripletClause("a", "b", "c", hard=0 in hard),
        TripletClause("d", "e", "f", hard=1 in hard),
        TripletClause("g", "h", "i", hard=2 in hard),
        TripletClause("j", "k", "l", hard=3 in hard),
    ]
    return SemanticContract("demo", "1", clauses=clauses)


def test_witness_compresses_two_distinct_fault_signatures_without_false_positive():
    contract = base_contract()
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0, 1.0])
    fault_a = make_report(contract, "fault-a", [0.0, 1.0, 1.0, 1.0])
    fault_b = make_report(contract, "fault-b", [1.0, 1.0, 0.0, 1.0])
    benign = make_report(contract, "benign", [1.0, 1.0, 1.0, 0.8])
    scenarios = [
        WitnessScenario("fault-a", fault_a),
        WitnessScenario("fault-b", fault_b),
        WitnessScenario("benign", benign),
    ]

    witness = build_semantic_witness_set(
        contract,
        baseline,
        scenarios,
        max_clauses=2,
        detection_drop=0.20,
        target_loss_coverage=1.0,
    )

    assert set(witness.selected_clause_indices) == {0, 2}
    assert witness.training_evaluation.positive_recall == 1.0
    assert witness.training_evaluation.false_positive_rate == 0.0
    assert witness.training_evaluation.mean_retained_loss_mass == 1.0
    assert witness.compression_ratio == 2.0
    assert witness.contract.parent_digest == contract.digest


def test_witness_evaluation_exposes_heldout_fault_miss():
    contract = base_contract()
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0, 1.0])
    train_fault = make_report(contract, "train", [0.0, 1.0, 1.0, 1.0])
    heldout_fault = make_report(contract, "heldout", [1.0, 0.0, 1.0, 1.0])

    witness = build_semantic_witness_set(
        contract,
        baseline,
        [WitnessScenario("train", train_fault)],
        max_clauses=1,
        detection_drop=0.20,
        target_loss_coverage=1.0,
    )
    evaluation = evaluate_clause_subset(
        contract,
        baseline,
        [WitnessScenario("heldout", heldout_fault)],
        witness.selected_clause_indices,
        detection_drop=0.20,
    )

    assert evaluation.scenarios[0].full_detected
    assert not evaluation.scenarios[0].witness_detected
    assert evaluation.positive_recall == 0.0


def test_witness_always_keeps_passing_hard_clauses():
    contract = base_contract(hard={1})
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0, 1.0])
    fault = make_report(contract, "fault", [1.0, 0.9, 1.0, 1.0], hard_fail_indices={1})

    witness = build_semantic_witness_set(
        contract,
        baseline,
        [WitnessScenario("fault", fault)],
        max_clauses=1,
        detection_drop=0.50,
    )

    assert witness.selected_clause_indices == (1,)
    assert witness.training_evaluation.positive_recall == 1.0


def test_witness_refuses_budget_smaller_than_hard_contract_surface():
    contract = base_contract(hard={0, 1})
    baseline = make_report(contract, "baseline", [1.0, 1.0, 1.0, 1.0])
    scenario = make_report(contract, "candidate", [1.0, 1.0, 1.0, 1.0])

    try:
        build_semantic_witness_set(
            contract,
            baseline,
            [WitnessScenario("candidate", scenario)],
            max_clauses=1,
        )
    except ValueError as exc:
        assert "hard clauses" in str(exc)
    else:
        raise AssertionError("expected hard-clause budget validation")
