"""Deterministic stress benchmark for the cross-model Semantic Fabric.

This benchmark is synthetic by design. It tests mechanisms, not production
superiority: piecewise model drift, partial migration, cycle corruption and
cross-model neighborhood disagreement.
"""
from __future__ import annotations

import json
import numpy as np

from semantic_atlas.alignment import TransitionAtlas, TransitionGraph
from semantic_atlas.fabric import FabricRecord, SemanticFabric, SpaceSpec
from semantic_atlas.geometry import normalize


def orthogonal(rng: np.random.Generator, d: int) -> np.ndarray:
    q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return q.astype(np.float32)


def piecewise_alignment() -> dict[str, float]:
    rng = np.random.default_rng(12)
    d = 24
    centers = normalize(rng.normal(size=(4, d)))
    rotations = [orthogonal(rng, d) for _ in range(4)]
    ax, ay, tx, ty = [], [], [], []
    for center, rot in zip(centers, rotations):
        train = normalize(center + rng.normal(scale=0.18, size=(55, d)))
        test = normalize(center + rng.normal(scale=0.18, size=(25, d)))
        ax.append(train)
        ay.append(normalize(train @ rot + rng.normal(scale=0.005, size=(55, d))))
        tx.append(test)
        ty.append(normalize(test @ rot + rng.normal(scale=0.005, size=(25, d))))
    ax, ay, tx, ty = map(np.vstack, (ax, ay, tx, ty))
    atlas = TransitionAtlas.fit("old", "new", ax, ay, chart_size=55, chart_overlap=1.15, min_chart_anchors=28)
    local = np.vstack([atlas.map(x, probes=1).vector for x in tx])
    global_only = np.vstack([atlas.global_map.map(x) for x in tx])
    return {
        "local_heldout_pair_cosine": float(np.mean(np.sum(local * ty, axis=1))),
        "global_heldout_pair_cosine": float(np.mean(np.sum(global_only * ty, axis=1))),
        "local_minus_global": float(np.mean(np.sum(local * ty, axis=1)) - np.mean(np.sum(global_only * ty, axis=1))),
    }


def partial_migration() -> dict[str, float]:
    rng = np.random.default_rng(77)
    n, d = 360, 20
    latent = normalize(rng.normal(size=(n, d)))
    legacy_rot, new_rot = orthogonal(rng, d), orthogonal(rng, d)
    legacy, new = normalize(latent @ legacy_rot), normalize(latent @ new_rot)
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

    fabric_overlap, new_only_overlap = [], []
    for _ in range(50):
        q_latent = normalize(rng.normal(size=(1, d)))[0]
        q_new = normalize(q_latent.reshape(1, -1) @ new_rot)[0]
        q_legacy = normalize(q_latent.reshape(1, -1) @ legacy_rot)[0]
        oracle = {h.id for h in fabric.indexes["legacy"].search(q_legacy)[:10]}
        fused = {h.id for h in fabric.search(q_new, "new", top_k=10, min_route_confidence=0.5)}
        direct = {h.id for h in fabric.indexes["new"].search(q_new)[:10]}
        fabric_overlap.append(len(oracle & fused) / 10)
        new_only_overlap.append(len(oracle & direct) / 10)
    return {
        "new_model_coverage": len(migrated) / n,
        "fabric_overlap_at_10_vs_legacy_oracle": float(np.mean(fabric_overlap)),
        "new_only_overlap_at_10_vs_legacy_oracle": float(np.mean(new_only_overlap)),
        "fabric_gain": float(np.mean(fabric_overlap) - np.mean(new_only_overlap)),
    }


def cycle_corruption() -> dict[str, float]:
    rng = np.random.default_rng(3)
    d = 18
    a = normalize(rng.normal(size=(120, d)))
    b = normalize(a @ orthogonal(rng, d))
    c = normalize(b @ orthogonal(rng, d))
    graph = TransitionGraph()
    graph.add(TransitionAtlas.fit("a", "b", a, b, chart_size=200))
    graph.add(TransitionAtlas.fit("b", "c", b, c, chart_size=200))
    graph.add(TransitionAtlas.fit("c", "a", c, a, chart_size=200))
    good = graph.cycle_consistency(("a", "b", "c", "a"), a[:30])
    shuffled = a.copy(); rng.shuffle(shuffled)
    graph.transitions[("c", "a")] = TransitionAtlas.fit("c", "a", c, shuffled, chart_size=200)
    bad = graph.cycle_consistency(("a", "b", "c", "a"), a[:30])
    return {
        "good_cycle_mean_cosine": good["mean_cosine"],
        "corrupted_cycle_mean_cosine": bad["mean_cosine"],
        "cycle_detection_gap": good["mean_cosine"] - bad["mean_cosine"],
    }


def virtual_materialization() -> dict[str, float]:
    rng = np.random.default_rng(101)
    n, d = 240, 18
    latent = normalize(rng.normal(size=(n, d)))
    old_rot, new_rot = orthogonal(rng, d), orthogonal(rng, d)
    old, new = normalize(latent @ old_rot), normalize(latent @ new_rot)
    fabric = SemanticFabric(chart_size=40, graph_k=7)
    fabric.add_space("old", d); fabric.add_space("new", d)
    for i in range(n):
        vectors = {"old": old[i]}
        if i % 5 == 0:
            vectors["new"] = new[i]
        fabric.add(FabricRecord(str(i), vectors=vectors))
    fabric.build(); fabric.fit_bidirectional("old", "new", chart_size=96)
    virtual = fabric.materialize_virtual_space("new", min_cell_confidence=0.8)
    overlaps = []
    for _ in range(30):
        q_latent = normalize(rng.normal(size=(1, d)))[0]
        q_old = normalize(q_latent.reshape(1, -1) @ old_rot)[0]
        q_new = normalize(q_latent.reshape(1, -1) @ new_rot)[0]
        oracle = {h.id for h in fabric.indexes["old"].search(q_old)[:10]}
        got = {h.id for h in virtual.search(q_new)[:10]}
        overlaps.append(len(oracle & got) / 10)
    coverage = fabric.virtual_coverage("new", min_cell_confidence=0.8)
    return {
        "true_new_embedding_coverage": float(coverage["direct_coverage"]),
        "virtual_index_coverage": float(coverage["virtual_coverage"]),
        "virtual_overlap_at_10_vs_legacy_oracle": float(np.mean(overlaps)),
        "mean_cell_confidence": float(coverage["mean_cell_confidence"]),
    }


def main() -> None:
    print(json.dumps({
        "piecewise_alignment": piecewise_alignment(),
        "partial_migration": partial_migration(),
        "virtual_materialization": virtual_materialization(),
        "cycle_corruption": cycle_corruption(),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
