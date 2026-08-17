from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from semantic_atlas.geometry import normalize
from semantic_atlas.transition_policy import EvidenceGatedTransition


def topk(queries: np.ndarray, docs: np.ndarray, k: int) -> np.ndarray:
    return np.argsort(-(normalize(queries) @ normalize(docs).T), axis=1)[:, :k]


def overlap(reference: np.ndarray, candidate: np.ndarray, k: int) -> float:
    return float(
        np.mean([
            len(set(map(int, a[:k])) & set(map(int, b[:k]))) / k
            for a, b in zip(reference, candidate)
        ])
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-gated global/local transition ablation on paired embedding NPZ")
    parser.add_argument("npz")
    parser.add_argument("--anchor-fraction", type=float, default=0.20)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", default="artifacts/evidence_gated_transition.json")
    args = parser.parse_args()

    payload = np.load(args.npz, allow_pickle=False)
    old_docs = normalize(payload["old_docs"])
    new_docs = normalize(payload["new_docs"])
    new_queries = normalize(payload["new_queries"])
    if len(old_docs) != len(new_docs):
        raise ValueError("old_docs/new_docs must represent the same logical objects")

    rng = np.random.default_rng(args.seed)
    anchor_count = max(20, int(round(len(old_docs) * args.anchor_fraction)))
    anchors = np.sort(rng.choice(len(old_docs), size=min(anchor_count, len(old_docs)), replace=False))
    transition = EvidenceGatedTransition.fit(
        "new",
        "old",
        new_docs[anchors],
        old_docs[anchors],
        chart_size=48,
        chart_overlap=1.5,
        min_chart_anchors=16,
        selection_fraction=0.20,
        selection_seed=args.seed + 5,
        min_local_gain=0.02,
    )

    oracle = topk(new_queries, new_docs, args.k)
    local_queries = np.vstack([transition.map_local(query).vector for query in new_queries])
    global_queries = np.vstack([transition.map_global(query).vector for query in new_queries])
    adaptive_queries = np.vstack([transition.map(query).vector for query in new_queries])

    local_rank = topk(local_queries, old_docs, args.k)
    global_rank = topk(global_queries, old_docs, args.k)
    adaptive_rank = topk(adaptive_queries, old_docs, args.k)

    result = {
        "documents": len(old_docs),
        "queries": len(new_queries),
        "anchor_count": len(anchors),
        "dimensions": {"old": int(old_docs.shape[1]), "new": int(new_docs.shape[1])},
        "selected_mode": transition.validation.mode,
        "validation": {
            "local_score": transition.validation.local_score,
            "global_score": transition.validation.global_score,
            "local_gain": transition.validation.local_gain,
            "local_pair_cosine": transition.validation.local_pair_cosine,
            "global_pair_cosine": transition.validation.global_pair_cosine,
            "local_neighborhood_jaccard": transition.validation.local_neighborhood_jaccard,
            "global_neighborhood_jaccard": transition.validation.global_neighborhood_jaccard,
            "validation_size": transition.validation.validation_size,
            "min_local_gain": transition.validation.min_local_gain,
        },
        f"local_target_neighbor_overlap@{args.k}": overlap(oracle, local_rank, args.k),
        f"global_target_neighbor_overlap@{args.k}": overlap(oracle, global_rank, args.k),
        f"adaptive_target_neighbor_overlap@{args.k}": overlap(oracle, adaptive_rank, args.k),
        "interpretation": "Adaptive must equal the held-out-selected expert; complexity is not used unless it beats the global baseline before serving.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
