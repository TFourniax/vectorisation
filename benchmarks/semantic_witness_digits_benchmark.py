"""Held-out contract sparsification benchmark on real handwritten digits.

The selector sees only per-clause behavior on a training fault panel. It never
sees affected-object IDs. Evaluation uses different objects/seeds and weaker as
well as stronger severities. Random clause subsets of the same size are the
baseline.

This benchmark asks a narrow question: can a compact Semantic Witness Set retain
the full contract's observed fault-detection decisions on unseen fault
instances? It does not prove omitted clauses are universally redundant.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.geometry import normalize
from semantic_atlas.mutation import add_vector_noise, collapse_region, default_semantic_mutations, permute_identities, pull_to_hub
from semantic_atlas.witness import WitnessScenario, build_semantic_witness_set, evaluate_clause_subset


def fault_panel(mapping, *, seed: int, fraction: float, weak: bool) -> list:
    ids = sorted(mapping)
    rng = np.random.default_rng(seed)
    count = max(2, int(round(len(ids) * fraction)))
    chosen = [ids[int(i)] for i in rng.choice(len(ids), size=count, replace=False)]
    if weak:
        return [
            permute_identities(mapping, chosen, seed=seed, name=f"permute-{seed}"),
            collapse_region(mapping, chosen, strength=0.65, name=f"collapse-{seed}"),
            pull_to_hub(mapping, chosen, strength=0.55, name=f"hub-{seed}"),
            add_vector_noise(mapping, chosen, sigma=0.20, seed=seed + 1, name=f"noise-{seed}"),
        ]
    return [
        permute_identities(mapping, chosen, seed=seed, name=f"permute-{seed}"),
        collapse_region(mapping, chosen, strength=0.92, name=f"collapse-{seed}"),
        pull_to_hub(mapping, chosen, strength=0.82, name=f"hub-{seed}"),
        add_vector_noise(mapping, chosen, sigma=0.38, seed=seed + 1, name=f"noise-{seed}"),
    ]


def scenarios_from_mutations(contract, mutations, prefix: str) -> list[WitnessScenario]:
    scenarios = []
    for mutation in mutations:
        report = contract.audit(mutation.vectors, implementation=f"{prefix}:{mutation.name}")
        scenarios.append(WitnessScenario(mutation.name, report))
    return scenarios


def random_baseline(contract, baseline, scenarios, *, size: int, repeats: int = 20, seed: int = 991) -> dict:
    rng = np.random.default_rng(seed + size)
    available = np.asarray([index for index, clause in enumerate(contract.clauses) if not clause.hard], dtype=int)
    hard = [index for index, clause in enumerate(contract.clauses) if clause.hard]
    remaining = max(0, size - len(hard))
    rows = []
    for _ in range(repeats):
        if remaining >= len(available):
            sampled = available.tolist()
        else:
            sampled = rng.choice(available, size=remaining, replace=False).tolist()
        indices = sorted(set(hard + [int(index) for index in sampled]))
        evaluation = evaluate_clause_subset(contract, baseline, scenarios, indices, detection_drop=0.03)
        rows.append(evaluation)
    return {
        "positive_recall_mean": float(np.mean([row.positive_recall for row in rows])),
        "positive_recall_max": float(np.max([row.positive_recall for row in rows])),
        "false_positive_rate_mean": float(np.mean([row.false_positive_rate for row in rows])),
        "retained_loss_mean": float(np.mean([row.mean_retained_loss_mass for row in rows])),
        "object_coverage_mean": float(np.mean([row.object_coverage for row in rows])),
        "repeats": repeats,
    }


def main() -> None:
    digits = load_digits()
    vectors = normalize(digits.data.astype(np.float32))
    labels = np.asarray(digits.target)

    rng = np.random.default_rng(77)
    chosen = np.sort(rng.choice(len(vectors), size=1000, replace=False))
    ids = [str(int(idx)) for idx in chosen]
    mapping = {object_id: vectors[idx] for object_id, idx in zip(ids, chosen)}
    label_map = {object_id: int(labels[idx]) for object_id, idx in zip(ids, chosen)}

    contract = contract_from_labels(
        mapping,
        label_map,
        anchors=ids[:300],
        triplets_per_anchor=5,
        seed=19,
        name="digits-semantic-witness-source",
    )
    baseline = contract.audit(mapping, implementation="pixels64:baseline")

    # Selector training panel: one strong instance of each generic fault family.
    training_mutations = default_semantic_mutations(mapping, fraction=0.10, seed=23)
    training = scenarios_from_mutations(contract, training_mutations, "train")

    # Held-out panels use different affected IDs and both weaker and stronger
    # severities. The selector never observes these reports.
    heldout_mutations = fault_panel(mapping, seed=101, fraction=0.08, weak=True) + fault_panel(
        mapping, seed=211, fraction=0.15, weak=False
    )
    heldout = scenarios_from_mutations(contract, heldout_mutations, "heldout")

    full_heldout = evaluate_clause_subset(
        contract,
        baseline,
        heldout,
        range(len(contract.clauses)),
        detection_drop=0.03,
    )

    rows = []
    for budget in (10, 25, 50, 100, 200):
        witness = build_semantic_witness_set(
            contract,
            baseline,
            training,
            max_clauses=budget,
            detection_drop=0.03,
            target_detection_coverage=1.0,
            target_loss_coverage=0.95,
            object_coverage_weight=0.08,
        )
        heldout_eval = evaluate_clause_subset(
            contract,
            baseline,
            heldout,
            witness.selected_clause_indices,
            detection_drop=0.03,
        )
        random = random_baseline(
            contract,
            baseline,
            heldout,
            size=len(witness.selected_clause_indices),
        )
        rows.append(
            {
                "budget": budget,
                "selected_clauses": len(witness.selected_clause_indices),
                "clause_fraction": witness.clause_fraction,
                "compression_ratio": witness.compression_ratio,
                "training": {
                    "positive_recall": witness.training_evaluation.positive_recall,
                    "false_positive_rate": witness.training_evaluation.false_positive_rate,
                    "retained_loss": witness.training_evaluation.mean_retained_loss_mass,
                    "object_coverage": witness.training_evaluation.object_coverage,
                },
                "heldout": {
                    "positive_recall": heldout_eval.positive_recall,
                    "false_positive_rate": heldout_eval.false_positive_rate,
                    "decision_accuracy": heldout_eval.decision_accuracy,
                    "retained_loss": heldout_eval.mean_retained_loss_mass,
                    "object_coverage": heldout_eval.object_coverage,
                },
                "random_same_size": random,
            }
        )

    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(mapping),
                "source_contract_clauses": len(contract.clauses),
                "training_fault_instances": len(training),
                "heldout_fault_instances": len(heldout),
                "detection_score_drop": 0.03,
                "full_contract_heldout": {
                    "positive_recall": full_heldout.positive_recall,
                    "false_positive_rate": full_heldout.false_positive_rate,
                    "decision_accuracy": full_heldout.decision_accuracy,
                },
                "witness_curve": rows,
                "warning": (
                    "Witness selection is trained on controlled fault families. Held-out seeds/severities test instance "
                    "generalization, not unseen fault-family generalization or production semantic completeness."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
