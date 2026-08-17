import numpy as np

from semantic_atlas.alignment import TransitionAtlas, TransitionGraph
from semantic_atlas.fabric import FabricRecord, SemanticFabric, SpaceSpec
from semantic_atlas.geometry import cosine_matrix, normalize


def orthogonal(rng, d):
    q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return q.astype(np.float32)


def test_piecewise_local_transition_beats_one_global_map_on_local_warp():
    rng = np.random.default_rng(12)
    d = 24
    centers = normalize(rng.normal(size=(4, d)))
    rotations = [orthogonal(rng, d) for _ in range(4)]

    anchor_x, anchor_y, test_x, test_y = [], [], [], []
    for c, rot in zip(centers, rotations):
        xa = normalize(c + rng.normal(scale=0.18, size=(55, d)))
        xt = normalize(c + rng.normal(scale=0.18, size=(25, d)))
        ya = normalize(xa @ rot + rng.normal(scale=0.005, size=(55, d)))
        yt = normalize(xt @ rot + rng.normal(scale=0.005, size=(25, d)))
        anchor_x.append(xa); anchor_y.append(ya); test_x.append(xt); test_y.append(yt)
    ax, ay = np.vstack(anchor_x), np.vstack(anchor_y)
    tx, ty = np.vstack(test_x), np.vstack(test_y)

    atlas = TransitionAtlas.fit("old", "new", ax, ay, chart_size=55, chart_overlap=1.15, min_chart_anchors=28)
    local = np.vstack([atlas.map(x, probes=1).vector for x in tx])
    global_only = np.vstack([atlas.global_map.map(x) for x in tx])
    local_cos = float(np.mean(np.sum(local * ty, axis=1)))
    global_cos = float(np.mean(np.sum(global_only * ty, axis=1)))
    assert local_cos > 0.92
    assert local_cos > global_cos + 0.15


def test_transition_graph_cycle_consistency_detects_bad_coordinate_map():
    rng = np.random.default_rng(3)
    d = 18
    a = normalize(rng.normal(size=(120, d)))
    rab, rbc = orthogonal(rng, d), orthogonal(rng, d)
    b = normalize(a @ rab)
    c = normalize(b @ rbc)

    graph = TransitionGraph()
    graph.add(TransitionAtlas.fit("a", "b", a, b, chart_size=200))
    graph.add(TransitionAtlas.fit("b", "c", b, c, chart_size=200))
    graph.add(TransitionAtlas.fit("c", "a", c, a, chart_size=200))
    good = graph.cycle_consistency(("a", "b", "c", "a"), a[:30])
    assert good["mean_cosine"] > 0.98

    shuffled = a.copy()
    rng.shuffle(shuffled)
    graph.transitions[("c", "a")] = TransitionAtlas.fit("c", "a", c, shuffled, chart_size=200)
    bad = graph.cycle_consistency(("a", "b", "c", "a"), a[:30])
    assert bad["mean_cosine"] < good["mean_cosine"] - 0.25


def test_partial_migration_keeps_legacy_corpus_searchable_from_new_model():
    rng = np.random.default_rng(77)
    n, d = 360, 20
    latent = normalize(rng.normal(size=(n, d)))
    legacy_rot = orthogonal(rng, d)
    new_rot = orthogonal(rng, d)
    legacy = normalize(latent @ legacy_rot)
    new = normalize(latent @ new_rot)

    fabric = SemanticFabric(chart_size=48, graph_k=8)
    fabric.add_space(SpaceSpec("legacy", d, version="v1"))
    fabric.add_space(SpaceSpec("new", d, version="v2"))
    migrated = set(range(0, n, 4))
    for i in range(n):
        vectors = {"legacy": legacy[i]}
        if i in migrated:
            vectors["new"] = new[i]
        fabric.add(FabricRecord(str(i), vectors=vectors))
    fabric.build()
    fabric.fit_bidirectional("new", "legacy", chart_size=128)

    recalls_fabric, recalls_new_only = [], []
    for _ in range(20):
        q_latent = normalize(rng.normal(size=(1, d)))[0]
        q_new = normalize(q_latent.reshape(1, -1) @ new_rot)[0]
        q_legacy = normalize(q_latent.reshape(1, -1) @ legacy_rot)[0]
        oracle = {h.id for h in fabric.indexes["legacy"].search(q_legacy)[:10]}
        got = {h.id for h in fabric.search(q_new, "new", top_k=10, min_route_confidence=0.5)}
        new_idx = fabric.indexes["new"]
        direct = {h.id for h in new_idx.search(q_new)[:10]}
        recalls_fabric.append(len(oracle & got) / 10)
        recalls_new_only.append(len(oracle & direct) / 10)
    assert np.mean(recalls_fabric) > np.mean(recalls_new_only) + 0.45
    assert np.mean(recalls_fabric) > 0.78

    status = fabric.migration_status("legacy", "new")
    assert status["legacy_only"] == 270
    assert status["new_coverage"] == 0.25
    assert status["legacy_searchable_from_new"] is True


def test_fault_lines_surface_cross_model_semantic_disagreement():
    rng = np.random.default_rng(91)
    d = 16
    c1 = normalize(rng.normal(size=(1, d)))[0]
    c2 = normalize(-c1.reshape(1, -1) + rng.normal(scale=0.05, size=(1, d)))[0]
    a = normalize(c1 + rng.normal(scale=0.05, size=(25, d)))
    b = normalize(c2 + rng.normal(scale=0.05, size=(25, d)))
    x = np.vstack([a, b])
    rot = orthogonal(rng, d)
    y = normalize(x @ rot)
    y[0] = y[-1]

    fabric = SemanticFabric(chart_size=16, graph_k=5)
    fabric.add_space("m1", d)
    fabric.add_space("m2", d)
    for i in range(len(x)):
        fabric.add(FabricRecord(str(i), vectors={"m1": x[i], "m2": y[i]}))
    fabric.build()

    bad = fabric.neighborhood_disagreement("0", k=8)
    stable = fabric.neighborhood_disagreement("10", k=8)
    assert bad["representation_sensitivity"] > 0.75
    assert bad["representation_sensitivity"] > stable["representation_sensitivity"] + 0.40
    assert fabric.fault_lines(limit=3, k=8)[0]["id"] == "0"


def test_virtual_space_materializes_full_new_coordinate_before_reembedding_finishes():
    rng = np.random.default_rng(101)
    n, d = 240, 18
    latent = normalize(rng.normal(size=(n, d)))
    old_rot, new_rot = orthogonal(rng, d), orthogonal(rng, d)
    old, new = normalize(latent @ old_rot), normalize(latent @ new_rot)
    fabric = SemanticFabric(chart_size=40, graph_k=7)
    fabric.add_space("old", d)
    fabric.add_space("new", d)
    for i in range(n):
        vectors = {"old": old[i]}
        if i % 5 == 0:
            vectors["new"] = new[i]
        fabric.add(FabricRecord(str(i), vectors=vectors))
    fabric.build()
    fabric.fit_bidirectional("old", "new", chart_size=96)

    coverage = fabric.virtual_coverage("new", min_cell_confidence=0.8)
    assert coverage["direct_coverage"] == 0.2
    assert coverage["virtual_coverage"] == 1.0
    assert coverage["mean_cell_dispersion"] < 1e-5

    virtual = fabric.materialize_virtual_space("new", min_cell_confidence=0.8)
    overlaps = []
    for _ in range(12):
        q_latent = normalize(rng.normal(size=(1, d)))[0]
        q_old = normalize(q_latent.reshape(1, -1) @ old_rot)[0]
        q_new = normalize(q_latent.reshape(1, -1) @ new_rot)[0]
        legacy_oracle = {h.id for h in fabric.indexes["old"].search(q_old)[:10]}
        virtual_hits = {h.id for h in virtual.search(q_new)[:10]}
        overlaps.append(len(legacy_oracle & virtual_hits) / 10)
    assert np.mean(overlaps) > 0.90
