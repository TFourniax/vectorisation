"""Real-data coordinate benchmark using scikit-learn handwritten digits.

This is deliberately *not* presented as a neural-embedding benchmark. It uses
real observations and two genuinely different vector representations of the
same logical objects:

- legacy space: normalized 8x8 raw pixels (64-D)
- target space: HOG descriptors (324-D)

Held-out digit images are queries and are never used as transition anchors.
We report both exact target-neighborhood imitation and task-level class
relevance. The distinction matters: two representations can disagree on the
identity/order of nearest neighbors while still preserving the useful class
semantics of retrieval.

Requires the optional ``bench`` dependencies.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits
from skimage.feature import hog

from semantic_atlas.alignment import TransitionAtlas
from semantic_atlas.geometry import cosine_matrix, normalize


def topk(queries: np.ndarray, docs: np.ndarray, k: int) -> np.ndarray:
    return np.argsort(-cosine_matrix(queries, docs), axis=1)[:, :k]


def overlap_at_k(reference: np.ndarray, candidate: np.ndarray, k: int) -> float:
    values = []
    for left, right in zip(reference[:, :k], candidate[:, :k]):
        values.append(len(set(map(int, left)) & set(map(int, right))) / k)
    return float(np.mean(values))


def label_precision_at_k(ranks: np.ndarray, query_labels: np.ndarray, doc_labels: np.ndarray, k: int) -> float:
    values = []
    for row, label in zip(ranks[:, :k], query_labels):
        values.append(float(np.mean(doc_labels[row] == label)))
    return float(np.mean(values))


def make_spaces(images: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pixels = normalize(images.reshape(len(images), -1).astype(np.float32))
    descriptors = np.vstack(
        [
            hog(
                image,
                orientations=9,
                pixels_per_cell=(2, 2),
                cells_per_block=(2, 2),
                block_norm="L2-Hys",
                feature_vector=True,
            )
            for image in images
        ]
    ).astype(np.float32)
    return pixels, normalize(descriptors)


def main() -> None:
    digits = load_digits()
    pixels, hog_vectors = make_spaces(digits.images.astype(np.float32))
    labels = np.asarray(digits.target)

    rng = np.random.default_rng(42)
    permutation = rng.permutation(len(pixels))
    doc_idx = permutation[:1400]
    query_idx = permutation[1400:]

    old_docs = pixels[doc_idx]
    new_docs = hog_vectors[doc_idx]
    old_queries = pixels[query_idx]
    new_queries = hog_vectors[query_idx]
    doc_labels = labels[doc_idx]
    query_labels = labels[query_idx]
    k = 10

    target_oracle = topk(new_queries, new_docs, k)
    pixel_native = topk(old_queries, old_docs, k)

    curves = []
    for fraction in (0.05, 0.10, 0.20, 0.40, 0.70):
        anchor_count = max(20, int(round(len(old_docs) * fraction)))
        anchor_idx = rng.choice(len(old_docs), anchor_count, replace=False)
        transition = TransitionAtlas.fit(
            "hog",
            "pixels",
            new_docs[anchor_idx],
            old_docs[anchor_idx],
            chart_size=32,
            chart_overlap=1.25,
            min_chart_anchors=12,
        )
        local_queries = np.vstack([transition.map(query, probes=2).vector for query in new_queries])
        global_queries = np.vstack([transition.global_map.map(query) for query in new_queries])
        local_rank = topk(local_queries, old_docs, k)
        global_rank = topk(global_queries, old_docs, k)
        curves.append(
            {
                "anchor_fraction": fraction,
                "anchor_count": anchor_count,
                "heldout_transition_confidence": transition.confidence,
                "local_target_neighbor_overlap@10": overlap_at_k(target_oracle, local_rank, k),
                "global_target_neighbor_overlap@10": overlap_at_k(target_oracle, global_rank, k),
                "local_same_digit_precision@10": label_precision_at_k(local_rank, query_labels, doc_labels, k),
                "global_same_digit_precision@10": label_precision_at_k(global_rank, query_labels, doc_labels, k),
            }
        )

    output = {
        "dataset": "sklearn.datasets.load_digits",
        "objects": len(pixels),
        "documents": len(doc_idx),
        "heldout_queries": len(query_idx),
        "legacy_dimensions": int(old_docs.shape[1]),
        "target_dimensions": int(new_docs.shape[1]),
        "target_hog_same_digit_precision@10": label_precision_at_k(target_oracle, query_labels, doc_labels, k),
        "native_pixel_same_digit_precision@10": label_precision_at_k(pixel_native, query_labels, doc_labels, k),
        "curves": curves,
        "warning": "Real data and real feature representations, but not a neural embedding-model benchmark.",
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
