"""Real-data mechanism test for active Semantic ABI contract discovery.

The benchmark treats digit labels as a hidden domain-expert oracle. The contract
miner only sees two incompatible representations (pixels and HOG), never the
labels. It proposes pairwise questions where the representations reverse their
nearest-neighbor preference. Labels are revealed afterwards to measure whether
those questions concentrate semantically meaningful disagreements.

This is a contract-acquisition mechanism test, not evidence about text models.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits
from skimage.feature import hog

from semantic_atlas.geometry import normalize
from semantic_atlas.semantic_diff import propose_contract_questions, semantic_diff


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


def evaluate_questions(questions, labels: dict[str, int]) -> dict[str, float | int]:
    resolvable = 0
    old_correct = 0
    new_correct = 0
    both_options_same_class = 0
    neither_option_same_class = 0
    generated_clauses = 0

    for question in questions:
        anchor_label = labels[question.anchor_id]
        a_match = labels[question.option_a] == anchor_label
        b_match = labels[question.option_b] == anchor_label
        if a_match and b_match:
            both_options_same_class += 1
            continue
        if not a_match and not b_match:
            neither_option_same_class += 1
            continue
        resolvable += 1
        oracle_preference = question.option_a if a_match else question.option_b
        if question.old_preference == oracle_preference:
            old_correct += 1
        if question.new_preference == oracle_preference:
            new_correct += 1
        # Proves the reviewed disagreement can be promoted into the ABI schema.
        clause = question.resolve(oracle_preference, source="digits-label-oracle")
        if clause.positive == oracle_preference:
            generated_clauses += 1

    total = len(questions)
    return {
        "questions": total,
        "oracle_resolvable": resolvable,
        "oracle_resolvable_rate": resolvable / max(1, total),
        "both_options_same_class": both_options_same_class,
        "neither_option_same_class": neither_option_same_class,
        "old_preference_accuracy_on_resolvable": old_correct / max(1, resolvable),
        "new_preference_accuracy_on_resolvable": new_correct / max(1, resolvable),
        "reviewed_clauses_generated": generated_clauses,
    }


def main() -> None:
    digits = load_digits()
    pixels, hog_vectors = make_spaces(digits.images.astype(np.float32))
    labels_array = np.asarray(digits.target)

    rng = np.random.default_rng(123)
    chosen = np.sort(rng.choice(len(pixels), size=1400, replace=False))
    ids = [str(int(i)) for i in chosen]
    old_vectors = {object_id: pixels[idx] for object_id, idx in zip(ids, chosen)}
    new_vectors = {object_id: hog_vectors[idx] for object_id, idx in zip(ids, chosen)}
    labels = {object_id: int(labels_array[idx]) for object_id, idx in zip(ids, chosen)}

    topology = semantic_diff(old_vectors, new_vectors, k=10)
    # A very low minimum exposes the full candidate pool; priorities are then
    # evaluated at fixed review budgets.
    all_questions = propose_contract_questions(
        old_vectors,
        new_vectors,
        limit=len(ids),
        k=10,
        min_disagreement=1e-6,
    )
    all_eval = evaluate_questions(all_questions, labels)

    budgets = []
    for budget in (25, 50, 100, 200):
        selected = all_questions[: min(budget, len(all_questions))]
        stats = evaluate_questions(selected, labels)
        stats["budget"] = budget
        stats["resolvable_enrichment_vs_all_questions"] = (
            float(stats["oracle_resolvable_rate"]) / max(1e-12, float(all_eval["oracle_resolvable_rate"]))
        )
        budgets.append(stats)

    # Random-question baseline estimated without selecting from labels.
    random_rates = []
    if all_questions:
        sample_size = min(50, len(all_questions))
        for _ in range(200):
            sample = [all_questions[int(i)] for i in rng.choice(len(all_questions), size=sample_size, replace=False)]
            random_rates.append(float(evaluate_questions(sample, labels)["oracle_resolvable_rate"]))

    output = {
        "dataset": "sklearn.datasets.load_digits",
        "objects": len(ids),
        "representations": {"old": "raw-pixels-64d", "new": "hog-324d"},
        "topology": {
            "mean_neighbor_jaccard": topology.mean_neighbor_jaccard,
            "mean_neighbor_churn": topology.mean_neighbor_churn,
            "top1_change_rate": topology.top1_change_rate,
            "mean_reciprocal_retention": topology.mean_reciprocal_retention,
        },
        "candidate_questions": all_eval,
        "priority_budgets": budgets,
        "random_50_resolvable_rate_mean": float(np.mean(random_rates)) if random_rates else 0.0,
        "random_50_resolvable_rate_std": float(np.std(random_rates)) if random_rates else 0.0,
        "interpretation": (
            "A question is oracle-resolvable only when exactly one of the two disputed neighbors shares "
            "the anchor digit label. Labels are never used to generate or rank questions."
        ),
        "warning": "Real observations and an oracle mechanism test, not a neural text-embedding benchmark.",
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
