import numpy as np

from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.lifecycle import SemanticChangeManager, compare_assessments
from semantic_atlas.oracle import CallbackSemanticOracle
from semantic_atlas.risk_control import CalibrationEvent


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def calibration_events(n=400, high_loss=False):
    events = []
    for i in range(n):
        proxy = (i % 100) / 100
        if proxy < 0.35:
            loss = 1.0 if i % 47 == 0 else 0.0
        else:
            loss = 1.0 if (high_loss or i % 3 == 0) else 0.0
        events.append(CalibrationEvent(proxy, loss))
    return events


def test_change_manager_certifies_good_candidate_and_blocks_hard_failure():
    contract = SemanticContract("demo", "1").add(TripletClause("a", "b", "c", hard=True))
    good = {"a": unit([1.0, 0.0]), "b": unit([0.9, 0.1]), "c": unit([-1.0, 0.0])}
    bad = {"a": unit([1.0, 0.0]), "b": unit([-1.0, 0.0]), "c": unit([0.9, 0.1])}
    manager = SemanticChangeManager(contract, min_global_score=0.5, target_risk=0.25, delta=0.10)
    good_assessment = manager.assess("good", good, calibration_events(), min_selection=40, min_certification=50, threshold_candidates=8)
    bad_assessment = manager.assess("bad", bad, calibration_events(), repair_budget=2.0, min_selection=40, min_certification=50, threshold_candidates=8)

    assert good_assessment.status == "certified"
    assert good_assessment.certificate.certified
    assert bad_assessment.status == "blocked"
    assert not bad_assessment.report.hard_pass
    assert bad_assessment.repair_plan is not None


def test_change_manager_runs_same_lifecycle_over_non_vector_oracle():
    contract = SemanticContract("demo", "1").add(TripletClause("a", "b", "c", hard=True))
    values = {("a", "b"): 0.9, ("a", "c"): 0.1, ("b", "c"): 0.2}

    def similarity(left, right):
        if left == right:
            return 1.0
        if (left, right) in values:
            return values[(left, right)]
        return values[(right, left)]

    neighbors = {"a": ("b", "c"), "b": ("a", "c"), "c": ("b", "a")}
    oracle = CallbackSemanticOracle(
        object_ids=frozenset(neighbors),
        similarity_fn=similarity,
        neighbors_fn=lambda anchor, k: neighbors[anchor][:k],
        implementation="graph-ranker",
    )
    manager = SemanticChangeManager(contract, min_global_score=0.5, target_risk=0.25, delta=0.10)
    assessment = manager.assess_oracle(
        oracle,
        calibration_events(),
        min_selection=40,
        min_certification=50,
        threshold_candidates=8,
    )
    assert assessment.implementation == "graph-ranker"
    assert assessment.report.score == 1.0
    assert assessment.status == "certified"


def test_assessment_delta_reports_semantic_improvement():
    contract = SemanticContract("demo", "1").add(TripletClause("a", "b", "c", hard=False))
    broken = {"a": unit([1, 0]), "b": unit([-1, 0]), "c": unit([0.9, 0.1])}
    repaired = {"a": unit([1, 0]), "b": unit([0.9, 0.1]), "c": unit([-1, 0])}
    manager = SemanticChangeManager(contract, min_global_score=0.0, target_risk=0.25, delta=0.10)
    before = manager.assess("candidate", broken, calibration_events(), min_selection=40, min_certification=50)
    after = manager.assess("candidate", repaired, calibration_events(), min_selection=40, min_certification=50)
    delta = compare_assessments(before, after)

    assert delta.score_delta > 0
    assert delta.violated_clause_delta < 0
    assert delta.top_risk_delta < 0
