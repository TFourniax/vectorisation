"""Real-data stress test for the Semantic ABI abstraction.

Two contracts are intentionally separated:

1. an *application semantic* contract saying a handwritten digit should prefer
   same-class examples over hard different-class negatives;
2. a *behavior regression* contract freezing selected neighborhoods/triplets
   from the legacy raw-pixel retriever.

This lets us distinguish semantic compatibility from implementation identity.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits
from skimage.feature import hog

from semantic_atlas.contracts import capture_behavior_contract, contract_from_labels


def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def mapping(x):
    return {str(i): x[i] for i in range(len(x))}


def main() -> None:
    digits = load_digits()
    images = digits.images.astype(np.float32)
    labels = np.asarray(digits.target)
    pixels = normalize(images.reshape(len(images), -1))
    hogs = normalize(
        np.vstack(
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
    )

    rng = np.random.default_rng(42)
    permutation = rng.permutation(len(images))
    doc_idx = permutation[:1400]
    pixel_docs = pixels[doc_idx]
    hog_docs = hogs[doc_idx]
    doc_labels = labels[doc_idx]

    pixel_vectors = mapping(pixel_docs)
    hog_vectors = mapping(hog_docs)
    label_map = {str(i): int(doc_labels[i]) for i in range(len(doc_labels))}
    anchors = [str(i) for i in rng.choice(len(pixel_docs), size=350, replace=False)]

    application = contract_from_labels(
        pixel_vectors,
        label_map,
        name="digit-identity-abi",
        anchors=anchors,
        triplets_per_anchor=4,
        seed=9,
    )
    behavior = capture_behavior_contract(
        pixel_vectors,
        name="pixel-retrieval-regression",
        anchors=anchors,
        k=8,
        min_neighbor_recall=0.5,
        triplets_per_anchor=1,
        include_mutual=False,
        seed=9,
    )

    app_pixel = application.audit(pixel_vectors, implementation="pixels-64d")
    app_hog = application.audit(hog_vectors, implementation="hog-324d")
    behavior_pixel = behavior.audit(pixel_vectors, implementation="pixels-64d")
    behavior_hog = behavior.audit(hog_vectors, implementation="hog-324d")

    corrupted = hog_docs.copy()
    corrupt_idx = rng.choice(len(hog_docs), size=140, replace=False)
    replacement = rng.permutation(corrupt_idx)
    corrupted[corrupt_idx] = corrupted[replacement]
    corrupted_vectors = mapping(corrupted)
    app_bad = application.audit(corrupted_vectors, implementation="hog-corrupted-10pct")
    behavior_bad = behavior.audit(corrupted_vectors, implementation="hog-corrupted-10pct")

    risky = {int(i) for i, _ in app_bad.top_risks(200)}
    corrupt = set(map(int, corrupt_idx))

    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(pixel_docs),
                "spaces": {"pixels": 64, "hog": int(hog_docs.shape[1])},
                "application_contract": {
                    "clauses": len(application.clauses),
                    "pixel_score": app_pixel.score,
                    "hog_score": app_hog.score,
                    "corrupted_hog_score": app_bad.score,
                    "hog_certified_coverage_risk_0.15": app_hog.certified_coverage(max_risk=0.15),
                    "corrupted_certified_coverage_risk_0.15": app_bad.certified_coverage(max_risk=0.15),
                    "corruption_hotspot_precision_top200": len(risky & corrupt) / max(1, len(risky)),
                    "corruption_hotspot_recall_top200": len(risky & corrupt) / len(corrupt),
                },
                "behavior_contract": {
                    "clauses": len(behavior.clauses),
                    "pixel_score": behavior_pixel.score,
                    "hog_score": behavior_hog.score,
                    "corrupted_hog_score": behavior_bad.score,
                },
                "interpretation": "Application semantics and legacy retrieval behavior are independent compatibility dimensions.",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
