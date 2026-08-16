"""Synthetic falsification benchmark for hub-aware retrieval.

Run with: python benchmarks/hubness_benchmark.py
The benchmark does not claim production superiority; it tests whether the
prototype reacts in the intended direction when central hub vectors are injected.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from semantic_atlas import AtlasIndex, AtlasRecord, SearchPolicy


def norm(x):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-9)


def make_data(seed=4, dim=64, clusters=8, per_cluster=80):
    rng = np.random.default_rng(seed)
    common = norm(rng.normal(size=(1, dim)))[0]
    semantic_centers = norm(rng.normal(size=(clusters, dim)))
    centers = norm(common + semantic_centers)
    points, labels = [], []
    for label, center in enumerate(centers):
        batch = norm(center + rng.normal(scale=0.18, size=(per_cluster, dim)))
        points.append(batch)
        labels.extend([label] * per_cluster)
    return np.vstack(points).astype(np.float32), np.array(labels), centers.astype(np.float32)


def precision_at_k(results, labels, expected, k):
    return sum(labels[i] == expected for i in results[:k]) / k


def main():
    vectors, labels, centers = make_data()
    centroid = norm(vectors.mean(axis=0, keepdims=True))[0]
    rng_hub = np.random.default_rng(123)
    hubs = norm(centroid + rng_hub.normal(scale=0.002, size=(6, centroid.size)))
    hub_start = len(vectors)
    all_vectors = np.vstack([vectors, hubs]).astype(np.float32)

    index = AtlasIndex(chart_size=80, chart_overlap=1.4, graph_k=10)
    index.extend([AtlasRecord(str(i), v) for i, v in enumerate(all_vectors)])
    index.build()

    k = 10
    cosine_p, atlas_p, cosine_hubs, atlas_hubs = [], [], [], []
    rng = np.random.default_rng(99)
    for label, center in enumerate(centers):
        for _ in range(20):
            q = norm((center + rng.normal(scale=0.12, size=center.shape)).reshape(1, -1))[0]
            cosine_rank = np.argsort(-(all_vectors @ q))[:k]
            atlas_hits = index.search(q, policy=SearchPolicy(top_k=k, diversify=0.02))
            atlas_rank = np.array([int(h.id) for h in atlas_hits])
            cosine_p.append(sum((i < len(labels) and labels[i] == label) for i in cosine_rank) / k)
            atlas_p.append(sum((i < len(labels) and labels[i] == label) for i in atlas_rank) / k)
            cosine_hubs.append(sum(i >= hub_start for i in cosine_rank))
            atlas_hubs.append(sum(i >= hub_start for i in atlas_rank))

    print(f"cosine precision@{k}: {np.mean(cosine_p):.4f}")
    print(f"atlas  precision@{k}: {np.mean(atlas_p):.4f}")
    print(f"cosine injected-hubs/query: {np.mean(cosine_hubs):.4f}")
    print(f"atlas  injected-hubs/query: {np.mean(atlas_hubs):.4f}")


if __name__ == "__main__":
    main()
