import numpy as np

from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.mutation import collapse_region, mutation_test, permute_identities


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def test_contract_kills_and_localizes_identity_mutation():
    vectors = {
        "a": unit([1.0, 0.0, 0.0]),
        "b": unit([0.98, 0.20, 0.0]),
        "c": unit([-1.0, 0.0, 0.0]),
        "d": unit([0.0, 1.0, 0.0]),
    }
    contract = SemanticContract("demo", "1").add(
        TripletClause("a", "b", "c", hard=True, weight=3.0)
    )
    mutant = permute_identities(vectors, ["b", "c"], seed=1)
    report = mutation_test(contract, vectors, [mutant], detection_drop=0.01, localization_k=2)

    assert report.mutation_score == 1.0
    outcome = report.outcomes[0]
    assert outcome.detected
    assert outcome.hard_failed
    assert outcome.top_risk_precision >= 0.5
    assert outcome.top_risk_recall >= 0.5


def test_weak_contract_fails_to_kill_unrelated_mutation():
    vectors = {
        "a": unit([1.0, 0.0, 0.0]),
        "b": unit([0.98, 0.20, 0.0]),
        "c": unit([-1.0, 0.0, 0.0]),
        "d": unit([0.0, 1.0, 0.0]),
        "e": unit([0.0, 0.9, 0.4]),
    }
    contract = SemanticContract("weak", "1").add(TripletClause("a", "b", "c"))
    mutant = collapse_region(vectors, ["d", "e"], strength=1.0)
    report = mutation_test(contract, vectors, [mutant], detection_drop=0.01)

    assert report.mutation_score == 0.0
    assert not report.outcomes[0].detected
