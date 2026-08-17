"""Held-out contract sparsification benchmark on real handwritten digits.

Witness selection is contrastive: it sees strong regression examples plus
micro-drift candidates that are retained as negative controls only when the
*full* contract classifies them as non-regressions. It never sees affected-object
IDs. Evaluation varies affected IDs, footprint and severity, and adds coherent
directional drift, a fault family absent from training. Random clause subsets
of identical size are the baseline.

This asks whether a compact Semantic Witness Set can retain the full contract's
observed regression decisions without becoming hypersensitive to acceptable
drift. It does not prove omitted clauses are universally redundant.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.geometry import normalize
from semantic_atlas.mutation import (
    SemanticMutation,
    add_vector_noise,
    collapse_region,
    default_semantic_mutations,
    permute_identities,
    pull_to_hub,
)
from semantic_atlas.witness import WitnessScenario, build_semantic_witness_set, evaluate_clause_subset

DETECTION_DROP = 0.03


def coherent_drift(mapping, object_ids, *, strength: float, seed: int, name: str) -> SemanticMutation:
    ids = [object_id for object_id in object_ids if object_id in mapping]
    rng = np.random.default_rng(seed)
    dimension = len(next(iter(mapping.values())))
    direction = normalize(rng.normal(size=(1, dimension)).astype(np.float32))[0]
    mutated = {object_id: np.asarray(vector, dtype=np.float32).copy() for object_id, vector in mapping.items()}
    alpha = float(np.clip(strength, 0.0, 1.0))
    for object_id in ids:
        mutated[object_id] = normalize(((1.0 - alpha) * mutated[object_id] + alpha * direction).reshape(1, -1))[0]
    return SemanticMutation(name, mutated, tuple(ids), "coherent-directional-drift", alpha, {"seed": seed})


def choose_ids(mapping, *, seed: int, fraction: float) -> list[str]:
    ids = sorted(mapping)
    rng = np.random.default_rng(seed)
    count = max(2, int(round(len(ids) * fraction)))
    return [ids[int(i)] for i in rng.choice(len(ids), size=count, replace=False)]


def fault_panel(mapping, *, seed: int, fraction: float, weak: bool) -> list[SemanticMutation]:
    chosen = choose_ids(mapping, seed=seed, fraction=fraction)
    if weak:
        strength, hub_strength, sigma, drift_strength = 0.65, 0.55, 0.20, 0.30
    else:
        strength, hub_strength, sigma, drift_strength = 0.92, 0.82, 0.38, 0.60
    suffix = f"{seed}-f{fraction:.3f}"
    return [
        permute_identities(mapping, chosen, seed=seed, name=f"permute-{suffix}"),
        collapse_region(mapping, chosen, strength=strength, name=f"collapse-{suffix}"),
        pull_to_hub(mapping, chosen, strength=hub_strength, name=f"hub-{suffix}"),
        add_vector_noise(mapping, chosen, sigma=sigma, seed=seed + 1, name=f"noise-{suffix}"),
        coherent_drift(mapping, chosen, strength=drift_strength, seed=seed + 2, name=f"coherent-drift-{suffix}"),
    ]


def micro_drift_candidates(mapping, *, seed: int, fraction: float = 0.10) -> list[SemanticMutation]:
    chosen = choose_ids(mapping, seed=seed, fraction=fraction)
    suffix = f"{seed}-f{fraction:.3f}"
    out: list[SemanticMutation] = []
    for strength in (0.01, 0.02, 0.04, 0.08):
        out.append(collapse_region(mapping, chosen, strength=strength, name=f"micro-collapse-{strength:.3f}-{suffix}"))
    for strength in (0.01, 0.02, 0.04, 0.08):
        out.append(pull_to_hub(mapping, chosen, strength=strength, name=f"micro-hub-{strength:.3f}-{suffix}"))
    for offset, sigma in enumerate((0.003, 0.006, 0.012, 0.024)):
        out.append(add_vector_noise(mapping, chosen, sigma=sigma, seed=seed + 10 + offset, name=f"micro-noise-{sigma:.3f}-{suffix}"))
    return out


def scenario(contract, mutation, prefix: str) -> WitnessScenario:
    return WitnessScenario(mutation.name, contract.audit(mutation.vectors, implementation=f"{prefix}:{mutation.name}"))


def scenarios_from_mutations(contract, mutations, prefix: str) -> list[WitnessScenario]:
    return [scenario(contract, mutation, prefix) for mutation in mutations]


def full_contract_detects(contract, baseline, candidate: WitnessScenario) -> bool:
    evaluation = evaluate_clause_subset(
        contract,
        baseline,
        [candidate],
        range(len(contract.clauses)),
        detection_drop=DETECTION_DROP,
    )
    return evaluation.scenarios[0].full_detected


def negative_controls(contract, baseline, mapping, *, seed: int) -> list[WitnessScenario]:
    controls = []
    for mutation in micro_drift_candidates(mapping, seed=seed):
        candidate = scenario(contract, mutation, "train-negative")
        if not full_contract_detects(contract, baseline, candidate):
            controls.append(candidate)
    if len(controls) < 3:
        raise RuntimeError(f"expected at least three full-contract negative controls, found {len(controls)}")
    return controls


def random_baseline(contract, baseline, scenarios, *, size: int, repeats: int = 20, seed: int = 991) -> dict:
    rng = np.random.default_rng(seed + size)
    available = np.asarray([index for index, clause in enumerate(contract.clauses) if not clause.hard], dtype=int)
    hard = [index for index, clause in enumerate(contract.clauses) if clause.hard]
    remaining = max(0, size - len(hard))
    rows = []
    for _ in range(repeats):
        sampled = available.tolist() if remaining >= len(available) else rng.choice(available, size=remaining, replace=False).tolist()
        indices = sorted(set(hard + [int(index) for index in sampled]))
        rows.append(evaluate_clause_subset(contract, baseline, scenarios, indices, detection_drop=DETECTION_DROP))
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

    training_faults = scenarios_from_mutations(
        contract,
        default_semantic_mutations(mapping, fraction=0.10, seed=23),
        "train-fault",
    )
    training_negatives = negative_controls(contract, baseline, mapping, seed=47)
    training = training_faults + training_negatives

    heldout_mutations = (
        fault_panel(mapping, seed=101, fraction=0.03, weak=True)
        + fault_panel(mapping, seed=211, fraction=0.05, weak=False)
        + fault_panel(mapping, seed=307, fraction=0.10, weak=False)
    )
    heldout = scenarios_from_mutations(contract, heldout_mutations, "heldout")
    full_heldout = evaluate_clause_subset(
        contract,
        baseline,
        heldout,
        range(len(contract.clauses)),
        detection_drop=DETECTION_DROP,
    )

    rows = []
    for budget in (10, 25, 50, 100, 200):
        witness = build_semantic_witness_set(
            contract,
            baseline,
            training,
            max_clauses=budget,
            detection_drop=DETECTION_DROP,
            target_detection_coverage=1.0,
            target_loss_coverage=0.95,
            object_coverage_weight=0.08,
            false_positive_penalty=3.0,
        )
        heldout_eval = evaluate_clause_subset(
            contract,
            baseline,
            heldout,
            witness.selected_clause_indices,
            detection_drop=DETECTION_DROP,
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
                "random_same_size": random_baseline(contract, baseline, heldout, size=len(witness.selected_clause_indices)),
            }
        )

    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(mapping),
                "source_contract_clauses": len(contract.clauses),
                "training_fault_instances": len(training_faults),
                "training_negative_controls": len(training_negatives),
                "negative_controls_definition": "micro-drifts retained only if full contract does not detect them",
                "heldout_fault_instances": len(heldout),
                "heldout_fault_fractions": [0.03, 0.05, 0.10],
                "heldout_unseen_fault_family": "coherent-directional-drift",
                "detection_score_drop": DETECTION_DROP,
                "full_contract_heldout": {
                    "positive_recall": full_heldout.positive_recall,
                    "false_positive_rate": full_heldout.false_positive_rate,
                    "decision_accuracy": full_heldout.decision_accuracy,
                },
                "witness_curve": rows,
                "warning": (
                    "Witness selection learns full-contract decisions from broad faults and explicit negative controls. Held-out evaluation "
                    "changes IDs, footprint and severity and adds one unseen fault family, but this remains a small real-data mechanism "
                    "benchmark rather than a guarantee of production semantic completeness."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
