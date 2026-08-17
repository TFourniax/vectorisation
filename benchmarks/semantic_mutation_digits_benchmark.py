"""Real-data mutation adequacy benchmark for Semantic ABI contracts.

A contract should not be trusted simply because one candidate implementation
scores well. This benchmark asks whether the contract can detect controlled
representation faults whose affected logical IDs are known.

Labels are used only to create the application contract. Mutations themselves
are representation-level and label-agnostic.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.geometry import normalize
from semantic_atlas.mutation import default_semantic_mutations, mutation_test


def main() -> None:
    digits = load_digits()
    vectors = normalize(digits.data.astype(np.float32))
    labels = np.asarray(digits.target)

    rng = np.random.default_rng(77)
    chosen = np.sort(rng.choice(len(vectors), size=1400, replace=False))
    ids = [str(int(idx)) for idx in chosen]
    mapping = {object_id: vectors[idx] for object_id, idx in zip(ids, chosen)}
    label_map = {object_id: int(labels[idx]) for object_id, idx in zip(ids, chosen)}

    # Compare contract densities rather than presenting one favorable contract.
    rows = []
    for triplets_per_anchor in (1, 2, 5, 10):
        anchor_count = 500
        anchors = ids[:anchor_count]
        contract = contract_from_labels(
            mapping,
            label_map,
            anchors=anchors,
            triplets_per_anchor=triplets_per_anchor,
            seed=19,
            name=f"digits-app-{triplets_per_anchor}",
        )
        mutations = default_semantic_mutations(mapping, fraction=0.10, seed=23)
        report = mutation_test(
            contract,
            mapping,
            mutations,
            detection_drop=0.03,
            localization_k=140,
            implementation="pixels64",
        )
        rows.append(
            {
                "triplets_per_anchor": triplets_per_anchor,
                "clauses": len(contract.clauses),
                "baseline_score": report.baseline.score,
                "mutation_score": report.mutation_score,
                "mean_score_drop": report.mean_score_drop,
                "mean_localization_precision": report.mean_localization_precision,
                "mean_localization_recall": report.mean_localization_recall,
                "mutants": [
                    {
                        "name": outcome.name,
                        "operator": outcome.operator,
                        "detected": outcome.detected,
                        "score_drop": outcome.score_drop,
                        "hard_failed": outcome.hard_failed,
                        "top_risk_precision": outcome.top_risk_precision,
                        "top_risk_recall": outcome.top_risk_recall,
                    }
                    for outcome in report.outcomes
                ],
            }
        )

    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(mapping),
                "representation": "normalized raw pixels 64-D",
                "mutated_fraction": 0.10,
                "detection_score_drop": 0.03,
                "contract_density_curve": rows,
                "warning": (
                    "Mutation score measures sensitivity to the included fault operators only; "
                    "it is contract-adequacy evidence, not universal failure coverage."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
