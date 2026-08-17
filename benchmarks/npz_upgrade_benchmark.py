"""Benchmark two real embedding models from precomputed NPZ arrays.

Required arrays:
  old_docs:    [N, D_old]
  new_docs:    [N, D_new]
  new_queries: [Q, D_new]

The full-new exact cosine ranking is treated as the migration oracle. A subset
of paired documents is used as transition anchors. We compare global
Procrustes and local Semantic Atlas transport of *new-model queries* into the
legacy document space. This isolates coordinate interoperability from ANN
implementation details.
"""
from __future__ import annotations

import argparse
import json
from time import perf_counter

import numpy as np

from semantic_atlas.alignment import TransitionAtlas
from semantic_atlas.geometry import cosine_matrix, normalize


def recall_at_k(reference: np.ndarray, candidate: np.ndarray, k: int) -> float:
    vals = []
    for a, b in zip(reference[:, :k], candidate[:, :k]):
        vals.append(len(set(map(int, a)) & set(map(int, b))) / k)
    return float(np.mean(vals))


def topk(queries: np.ndarray, docs: np.ndarray, k: int) -> np.ndarray:
    sims = cosine_matrix(queries, docs)
    return np.argsort(-sims, axis=1)[:, :k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("npz")
    ap.add_argument("--anchor-fraction", type=float, default=0.10)
    ap.add_argument("--chart-size", type=int, default=64)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--seed", type=int, default=17)
    args = ap.parse_args()

    with np.load(args.npz, allow_pickle=False) as data:
        old_docs = normalize(data["old_docs"])
        new_docs = normalize(data["new_docs"])
        new_queries = normalize(data["new_queries"])
    if len(old_docs) != len(new_docs):
        raise SystemExit("old_docs and new_docs must contain the same logical document IDs")

    rng = np.random.default_rng(args.seed)
    n_anchor = max(10, min(len(old_docs) - 2, int(round(len(old_docs) * args.anchor_fraction))))
    anchor_idx = rng.choice(len(old_docs), size=n_anchor, replace=False)

    # Query transport direction: new -> old, so the legacy corpus can stay live.
    started = perf_counter()
    transition = TransitionAtlas.fit(
        "new", "old", new_docs[anchor_idx], old_docs[anchor_idx], chart_size=args.chart_size
    )
    fit_ms = (perf_counter() - started) * 1000

    oracle = topk(new_queries, new_docs, args.k)
    started = perf_counter()
    local_queries = np.vstack([transition.map(q).vector for q in new_queries])
    local_ms = (perf_counter() - started) * 1000 / max(1, len(new_queries))
    global_queries = np.vstack([transition.global_map.map(q) for q in new_queries])
    local_rank = topk(local_queries, old_docs, args.k)
    global_rank = topk(global_queries, old_docs, args.k)

    out = {
        "documents": len(old_docs),
        "queries": len(new_queries),
        "anchor_count": n_anchor,
        "anchor_fraction": n_anchor / len(old_docs),
        "fit_ms": fit_ms,
        "local_transport_ms_per_query_python_reference": local_ms,
        "heldout_transition_confidence": transition.confidence,
        "heldout_diagnostics": {
            "mean_pair_cosine": transition.fit_diagnostics.mean_pair_cosine,
            "p10_pair_cosine": transition.fit_diagnostics.p10_pair_cosine,
            "pair_recall_at_1": transition.fit_diagnostics.pair_recall_at_1,
            "neighborhood_jaccard": transition.fit_diagnostics.neighborhood_jaccard,
            "held_out": transition.fit_diagnostics.held_out,
        },
        f"global_procrustes_recall@{args.k}": recall_at_k(oracle, global_rank, args.k),
        f"local_atlas_recall@{args.k}": recall_at_k(oracle, local_rank, args.k),
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
