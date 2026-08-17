from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .contracts import ContractReport, SemanticContract

_EPS = 1e-12


def _normalize(vector: np.ndarray) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), _EPS)


def _copy_vectors(vectors: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {object_id: _normalize(vector)[0].copy() for object_id, vector in vectors.items()}


@dataclass(slots=True)
class SemanticMutation:
    name: str
    vectors: dict[str, np.ndarray]
    affected_objects: tuple[str, ...]
    operator: str
    severity: float
    metadata: dict[str, object]


@dataclass(slots=True, frozen=True)
class MutationOutcome:
    name: str
    operator: str
    severity: float
    baseline_score: float
    mutated_score: float
    score_drop: float
    hard_failed: bool
    detected: bool
    affected_objects: tuple[str, ...]
    top_risk_precision: float
    top_risk_recall: float


@dataclass(slots=True)
class SemanticMutationReport:
    baseline: ContractReport
    outcomes: list[MutationOutcome]
    detection_drop: float

    @property
    def mutation_score(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(outcome.detected for outcome in self.outcomes) / len(self.outcomes)

    @property
    def mean_score_drop(self) -> float:
        if not self.outcomes:
            return 0.0
        return float(np.mean([outcome.score_drop for outcome in self.outcomes]))

    @property
    def mean_localization_precision(self) -> float:
        values = [outcome.top_risk_precision for outcome in self.outcomes if outcome.affected_objects]
        return float(np.mean(values)) if values else 0.0

    @property
    def mean_localization_recall(self) -> float:
        values = [outcome.top_risk_recall for outcome in self.outcomes if outcome.affected_objects]
        return float(np.mean(values)) if values else 0.0


def permute_identities(
    vectors: Mapping[str, np.ndarray],
    object_ids: Sequence[str],
    *,
    seed: int = 17,
    name: str = "identity-permutation",
) -> SemanticMutation:
    ids = [object_id for object_id in object_ids if object_id in vectors]
    if len(ids) < 2:
        raise ValueError("identity permutation requires at least two existing object IDs")
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(len(ids))
    if np.all(permutation == np.arange(len(ids))):
        permutation = np.roll(permutation, 1)
    mutated = _copy_vectors(vectors)
    originals = [mutated[object_id].copy() for object_id in ids]
    for destination, source_idx in zip(ids, permutation):
        mutated[destination] = originals[int(source_idx)].copy()
    return SemanticMutation(name, mutated, tuple(ids), "identity-permutation", 1.0, {"seed": seed})


def collapse_region(
    vectors: Mapping[str, np.ndarray],
    object_ids: Sequence[str],
    *,
    strength: float = 1.0,
    name: str = "local-collapse",
) -> SemanticMutation:
    ids = [object_id for object_id in object_ids if object_id in vectors]
    if len(ids) < 2:
        raise ValueError("local collapse requires at least two existing object IDs")
    mutated = _copy_vectors(vectors)
    matrix = np.vstack([mutated[object_id] for object_id in ids])
    centroid = _normalize(np.mean(matrix, axis=0))[0]
    alpha = float(np.clip(strength, 0.0, 1.0))
    for object_id in ids:
        mutated[object_id] = _normalize((1.0 - alpha) * mutated[object_id] + alpha * centroid)[0]
    return SemanticMutation(name, mutated, tuple(ids), "local-collapse", alpha, {})


def pull_to_hub(
    vectors: Mapping[str, np.ndarray],
    object_ids: Sequence[str],
    *,
    strength: float = 0.75,
    name: str = "hub-pull",
) -> SemanticMutation:
    ids = [object_id for object_id in object_ids if object_id in vectors]
    if not ids:
        raise ValueError("hub pull requires at least one existing object ID")
    mutated = _copy_vectors(vectors)
    global_centroid = _normalize(np.mean(np.vstack(list(mutated.values())), axis=0))[0]
    alpha = float(np.clip(strength, 0.0, 1.0))
    for object_id in ids:
        mutated[object_id] = _normalize((1.0 - alpha) * mutated[object_id] + alpha * global_centroid)[0]
    return SemanticMutation(name, mutated, tuple(ids), "hub-pull", alpha, {})


def add_vector_noise(
    vectors: Mapping[str, np.ndarray],
    object_ids: Sequence[str],
    *,
    sigma: float = 0.25,
    seed: int = 17,
    name: str = "coordinate-noise",
) -> SemanticMutation:
    ids = [object_id for object_id in object_ids if object_id in vectors]
    if not ids:
        raise ValueError("coordinate noise requires at least one existing object ID")
    mutated = _copy_vectors(vectors)
    rng = np.random.default_rng(seed)
    for object_id in ids:
        noise = rng.normal(0.0, float(sigma), size=mutated[object_id].shape).astype(np.float32)
        mutated[object_id] = _normalize(mutated[object_id] + noise)[0]
    return SemanticMutation(name, mutated, tuple(ids), "coordinate-noise", float(max(0.0, sigma)), {"seed": seed})


def mutation_test(
    contract: SemanticContract,
    baseline_vectors: Mapping[str, np.ndarray],
    mutations: Sequence[SemanticMutation],
    *,
    detection_drop: float = 0.05,
    localization_k: int | None = None,
    implementation: str = "mutation-test",
) -> SemanticMutationReport:
    """Measure whether a Semantic Contract detects controlled semantic faults.

    A mutant is killed when it introduces a hard-clause failure that did not
    exist at baseline or drops the weighted contract score by at least
    ``detection_drop``. Localization is evaluated independently by checking how
    many known affected objects appear among the highest-risk logical IDs.

    This is mutation-testing adequacy evidence, not a proof that unmodeled real
    failures will be detected.
    """
    baseline = contract.audit(baseline_vectors, implementation=f"{implementation}:baseline")
    outcomes: list[MutationOutcome] = []

    for mutation in mutations:
        report = contract.audit(mutation.vectors, implementation=f"{implementation}:{mutation.name}")
        score_drop = max(0.0, float(baseline.score - report.score))
        hard_failed = bool(baseline.hard_pass and not report.hard_pass)
        detected = bool(hard_failed or score_drop >= float(detection_drop))

        affected = set(mutation.affected_objects)
        if affected and report.object_risk:
            k = int(localization_k or len(affected))
            k = max(1, min(k, len(report.object_risk)))
            top = [
                object_id
                for object_id, _ in sorted(
                    report.object_risk.items(), key=lambda item: (-item[1], item[0])
                )[:k]
            ]
            intersection = len(set(top) & affected)
            precision = intersection / max(1, len(top))
            recall = intersection / max(1, len(affected))
        else:
            precision = recall = 0.0

        outcomes.append(
            MutationOutcome(
                name=mutation.name,
                operator=mutation.operator,
                severity=mutation.severity,
                baseline_score=float(baseline.score),
                mutated_score=float(report.score),
                score_drop=score_drop,
                hard_failed=hard_failed,
                detected=detected,
                affected_objects=mutation.affected_objects,
                top_risk_precision=float(precision),
                top_risk_recall=float(recall),
            )
        )

    return SemanticMutationReport(baseline, outcomes, float(detection_drop))


def default_semantic_mutations(
    vectors: Mapping[str, np.ndarray],
    *,
    fraction: float = 0.10,
    seed: int = 17,
) -> list[SemanticMutation]:
    """Generate deterministic generic stress mutants without semantic labels."""
    ids = sorted(vectors)
    if len(ids) < 4:
        raise ValueError("default semantic mutations require at least four vectors")
    rng = np.random.default_rng(seed)
    count = max(2, min(len(ids), int(round(len(ids) * float(np.clip(fraction, 0.0, 1.0))))))
    chosen = [ids[int(i)] for i in rng.choice(len(ids), size=count, replace=False)]
    return [
        permute_identities(vectors, chosen, seed=seed, name="identity-permutation"),
        collapse_region(vectors, chosen, strength=0.90, name="local-collapse"),
        pull_to_hub(vectors, chosen, strength=0.80, name="hub-pull"),
        add_vector_noise(vectors, chosen, sigma=0.35, seed=seed + 1, name="coordinate-noise"),
    ]
