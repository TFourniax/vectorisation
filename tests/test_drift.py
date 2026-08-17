import numpy as np
from semantic_atlas import AtlasIndex, AtlasRecord
from semantic_atlas.alignment import TransitionAtlas
from semantic_atlas.drift import compare_indexes
from semantic_atlas.geometry import normalize


def orthogonal(rng, d):
    q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return q.astype(np.float32)


def make_index(vectors):
    return AtlasIndex(chart_size=24, graph_k=6).extend_and_build(
        AtlasRecord(str(i), v) for i, v in enumerate(vectors)
    )


def test_coordinate_aware_drift_separates_model_rotation_from_content_change():
    rng = np.random.default_rng(808)
    n, d = 120, 18
    before_vectors = normalize(rng.normal(size=(n, d)))
    rot = orthogonal(rng, d)
    after_vectors = normalize(before_vectors @ rot)
    changed = {0, 1, 2, 3, 4}
    for i in changed:
        after_vectors[i] = normalize(rng.normal(size=(1, d)) @ rot)[0]

    before = make_index(before_vectors)
    after = make_index(after_vectors)
    stable = np.array([i for i in range(n) if i not in changed])
    transition = TransitionAtlas.fit(
        "before", "after", before_vectors[stable], after_vectors[stable], chart_size=200
    )
    report = compare_indexes(before, after, transition=transition, k=8)
    top_ids = {p.id for p in report.top(8)}
    assert {str(i) for i in changed}.issubset(top_ids)

    stable_scores = [p.drift_score for p in report.points if int(p.id) not in changed]
    changed_scores = [p.drift_score for p in report.points if int(p.id) in changed]
    assert np.mean(changed_scores) > np.mean(stable_scores) + 0.50
    assert transition.fit_diagnostics.held_out is True


def test_pure_coordinate_change_has_small_residual_drift():
    rng = np.random.default_rng(809)
    n, d = 100, 16
    x = normalize(rng.normal(size=(n, d)))
    y = normalize(x @ orthogonal(rng, d))
    before, after = make_index(x), make_index(y)
    transition = TransitionAtlas.fit("a", "b", x[:70], y[:70], chart_size=100)
    report = compare_indexes(before, after, transition=transition, k=8)
    assert report.mean_aligned_cosine > 0.99
    assert report.median_drift < 0.08
