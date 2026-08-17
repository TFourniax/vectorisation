import numpy as np

from semantic_atlas.geometry import normalize
from semantic_atlas.transition_policy import EvidenceGatedTransition


def orthogonal(rng, d):
    q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return q.astype(np.float32)


def test_selector_chooses_local_only_when_piecewise_warp_earns_it():
    rng = np.random.default_rng(122)
    d = 16
    centers = normalize(rng.normal(size=(4, d)))
    rotations = [orthogonal(rng, d) for _ in range(4)]
    x, y = [], []
    for center, rotation in zip(centers, rotations):
        block = normalize(center + rng.normal(scale=0.15, size=(70, d)))
        x.append(block)
        y.append(normalize(block @ rotation + rng.normal(scale=0.004, size=(70, d))))
    x, y = np.vstack(x), np.vstack(y)

    transition = EvidenceGatedTransition.fit(
        "a",
        "b",
        x,
        y,
        chart_size=70,
        chart_overlap=1.1,
        min_chart_anchors=35,
        min_local_gain=0.05,
        selection_seed=9,
    )
    assert transition.validation.mode == "local"
    assert transition.validation.local_gain > 0.05


def test_selector_prefers_simple_global_map_for_one_global_rotation():
    rng = np.random.default_rng(44)
    d = 24
    x = normalize(rng.normal(size=(300, d)))
    rotation = orthogonal(rng, d)
    y = normalize(x @ rotation + rng.normal(scale=0.002, size=(300, d)))

    transition = EvidenceGatedTransition.fit(
        "a",
        "b",
        x,
        y,
        chart_size=40,
        min_chart_anchors=24,
        min_local_gain=0.02,
        selection_seed=11,
    )
    assert transition.validation.mode == "global"
    assert transition.validation.global_score > 0.95

    heldout = normalize(rng.normal(size=(10, d)))
    expected = normalize(heldout @ rotation)
    mapped = np.vstack([transition.map(row).vector for row in heldout])
    assert float(np.mean(np.sum(mapped * expected, axis=1))) > 0.95
