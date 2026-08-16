import numpy as np

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.repair import plan_repairs


def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def mapping(x):
    return {str(i): x[i] for i in range(len(x))}


def test_repair_planner_enriches_for_corrupted_objects():
    rng = np.random.default_rng(5)
    centers = normalize(rng.normal(size=(4, 10)))
    x = np.vstack([normalize(c + rng.normal(scale=0.07, size=(35, 10))) for c in centers])
    labels = {str(i): i // 35 for i in range(len(x))}
    vectors = mapping(x)
    contract = contract_from_labels(vectors, labels, anchors=[str(i) for i in range(len(x))], triplets_per_anchor=5)

    broken = x.copy()
    corrupt = set(range(35, 50)) | set(range(105, 120))
    broken[list(corrupt)] = broken[list(range(70, 85)) + list(range(0, 15))]
    broken_vectors = mapping(broken)
    report = contract.audit(broken_vectors)
    plan = plan_repairs(report, broken_vectors, limit=30, diversity_weight=0.25)
    selected = {int(candidate.object_id) for candidate in plan.candidates}

    # Random expectation is ~6.4 corrupt objects in 30 draws from 140.
    assert len(selected & corrupt) >= 12
    assert plan.risk_mass_coverage > 0.20
