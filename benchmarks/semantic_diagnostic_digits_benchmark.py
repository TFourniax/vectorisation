"""Held-out benchmark for learned Semantic Diagnostic Panels on Digits.

The full Semantic Contract remains normative. A diagnostic panel is a cheap
canary learned from full-contract decisions over change scenarios. Clause losses
are treated as item responses; selection favors clauses that discriminate known
regressions from accepted micro-drift and penalizes redundant signals.

Evaluation uses different affected IDs, footprints/severities and an unseen
coherent-drift fault family. Random same-size panels receive the same threshold-
calibration privilege, so the comparison measures clause selection rather than
threshold tuning.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.datasets import load_digits

from semantic_atlas.contracts import contract_from_labels
from semantic_atlas.diagnostic import build_semantic_diagnostic_panel, evaluate_diagnostic_panel
from semantic_atlas.geometry import normalize
from semantic_atlas.mutation import default_semantic_mutations
from semantic_atlas.witness import WitnessScenario
from semantic_witness_digits_benchmark import (
    DETECTION_DROP,
    fault_panel,
    negative_controls,
    scenarios_from_mutations,
)


def full_label(baseline, candidate) -> bool:
    return bool((baseline.hard_pass and not candidate.hard_pass) or max(0.0, baseline.score - candidate.score) >= DETECTION_DROP)


def clause_loss(baseline_result, candidate_result) -> float:
    after_score = 0.0 if candidate_result is None else float(candidate_result.score)
    loss = max(0.0, float(baseline_result.score) - after_score)
    if baseline_result.hard and baseline_result.passed and (candidate_result is None or not candidate_result.passed):
        loss = max(loss, 1.0)
    return loss


def calibrate_threshold(scores, labels, *, max_fpr: float = 0.0):
    scores = np.asarray(scores, dtype=np.float64)
    labels = np.asarray(labels, dtype=bool)
    unique = np.unique(scores)
    candidates = [0.0]
    candidates.extend(float((a + b) / 2.0) for a, b in zip(unique[:-1], unique[1:]))
    candidates.append(float(unique[-1] + 1e-12))
    best = None
    for threshold in candidates:
        pred = scores >= threshold
        pos = max(1, int(np.sum(labels)))
        neg = max(1, int(np.sum(~labels)))
        tpr = float(np.sum(pred & labels) / pos)
        fpr = float(np.sum(pred & ~labels) / neg)
        if fpr > max_fpr + 1e-12:
            continue
        key = (tpr, -fpr, -threshold)
        if best is None or key > best[0]:
            best = (key, float(threshold))
    return float(unique[-1] + 1e-12) if best is None else best[1]


def random_panel_eval(contract, baseline, train, heldout, *, size: int, repeats: int = 30, seed: int = 901):
    baseline_map = {item.clause_index: item for item in baseline.clause_results}
    train_maps = [{item.clause_index: item for item in scenario.report.clause_results} for scenario in train]
    heldout_maps = [{item.clause_index: item for item in scenario.report.clause_results} for scenario in heldout]
    train_labels = np.asarray([full_label(baseline, scenario.report) for scenario in train], dtype=bool)
    heldout_labels = np.asarray([full_label(baseline, scenario.report) for scenario in heldout], dtype=bool)
    rng = np.random.default_rng(seed + size)
    available = np.asarray(sorted(baseline_map), dtype=int)
    rows = []
    for _ in range(repeats):
        indices = rng.choice(available, size=min(size, len(available)), replace=False).tolist()
        train_scores = [
            float(np.mean([clause_loss(baseline_map[index], candidate_map.get(index)) for index in indices]))
            for candidate_map in train_maps
        ]
        threshold = calibrate_threshold(train_scores, train_labels)
        held_scores = np.asarray([
            float(np.mean([clause_loss(baseline_map[index], candidate_map.get(index)) for index in indices]))
            for candidate_map in heldout_maps
        ])
        predictions = held_scores >= threshold
        positives = max(1, int(np.sum(heldout_labels)))
        negatives = max(1, int(np.sum(~heldout_labels)))
        tpr = float(np.sum(predictions & heldout_labels) / positives)
        fpr = float(np.sum(predictions & ~heldout_labels) / negatives)
        rows.append((tpr, fpr))
    return {
        "repeats": repeats,
        "heldout_tpr_mean": float(np.mean([row[0] for row in rows])),
        "heldout_tpr_max": float(np.max([row[0] for row in rows])),
        "heldout_fpr_mean": float(np.mean([row[1] for row in rows])),
        "heldout_fpr_min": float(np.min([row[1] for row in rows])),
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
        name="digits-semantic-diagnostic-source",
    )
    baseline = contract.audit(mapping, implementation="pixels64:baseline")
    training_faults = scenarios_from_mutations(
        contract,
        default_semantic_mutations(mapping, fraction=0.10, seed=23),
        "train-fault",
    )
    training_negatives = negative_controls(contract, baseline, mapping, seed=47)
    training = training_faults + training_negatives
    heldout = scenarios_from_mutations(
        contract,
        fault_panel(mapping, seed=101, fraction=0.03, weak=True)
        + fault_panel(mapping, seed=211, fraction=0.05, weak=False)
        + fault_panel(mapping, seed=307, fraction=0.10, weak=False),
        "heldout",
    )

    rows = []
    for budget in (5, 10, 25, 50, 100):
        panel = build_semantic_diagnostic_panel(
            contract,
            baseline,
            training,
            max_clauses=budget,
            detection_drop=DETECTION_DROP,
            max_training_fpr=0.0,
            redundancy_penalty=0.35,
        )
        heldout_eval = evaluate_diagnostic_panel(panel, baseline, heldout)
        rows.append(
            {
                "budget": budget,
                "selected_clauses": len(panel.clauses),
                "threshold": panel.threshold,
                "training": {
                    "tpr": panel.training_evaluation.true_positive_rate,
                    "fpr": panel.training_evaluation.false_positive_rate,
                    "balanced_accuracy": panel.training_evaluation.balanced_accuracy,
                },
                "heldout": {
                    "tpr": heldout_eval.true_positive_rate,
                    "fpr": heldout_eval.false_positive_rate,
                    "balanced_accuracy": heldout_eval.balanced_accuracy,
                    "accuracy": heldout_eval.accuracy,
                },
                "mean_selected_discrimination": float(np.mean([item.discrimination for item in panel.clauses])),
                "random_same_size": random_panel_eval(
                    contract,
                    baseline,
                    training,
                    heldout,
                    size=len(panel.clauses),
                ),
            }
        )

    print(
        json.dumps(
            {
                "dataset": "sklearn.datasets.load_digits",
                "objects": len(mapping),
                "contract_clauses": len(contract.clauses),
                "training_regressions": sum(full_label(baseline, scenario.report) for scenario in training),
                "training_non_regressions": sum(not full_label(baseline, scenario.report) for scenario in training),
                "heldout_regressions": sum(full_label(baseline, scenario.report) for scenario in heldout),
                "heldout_non_regressions": sum(not full_label(baseline, scenario.report) for scenario in heldout),
                "heldout_unseen_fault_family": "coherent-directional-drift",
                "panel_curve": rows,
                "interpretation": (
                    "Diagnostic panels are learned canaries for full-contract decisions, not normative contract replacements."
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
