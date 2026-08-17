from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .contracts import ContractReport, SemanticContract
from .witness import WitnessScenario

_EPS = 1e-12


@dataclass(slots=True, frozen=True)
class DiagnosticClause:
    clause_index: int
    weight: float
    discrimination: float
    positive_mean_loss: float
    negative_mean_loss: float


@dataclass(slots=True, frozen=True)
class DiagnosticEvaluation:
    true_positive_rate: float
    false_positive_rate: float
    balanced_accuracy: float
    accuracy: float
    positives: int
    negatives: int
    scores: tuple[float, ...]
    labels: tuple[bool, ...]
    predictions: tuple[bool, ...]


@dataclass(slots=True)
class SemanticDiagnosticPanel:
    """A cheap learned canary for a full Semantic Contract.

    A panel is explicitly *not* a smaller normative contract. The full contract
    remains the source of truth. The panel learns which clauses are informative
    about full-contract regression decisions over observed change scenarios and
    can be used as a fast preflight/canary before a full audit.
    """

    source_contract_digest: str
    clauses: tuple[DiagnosticClause, ...]
    threshold: float
    detection_drop: float
    training_evaluation: DiagnosticEvaluation

    @property
    def selected_clause_indices(self) -> tuple[int, ...]:
        return tuple(item.clause_index for item in self.clauses)

    def score_report(self, baseline: ContractReport, candidate: ContractReport) -> float:
        if baseline.contract_digest != self.source_contract_digest or candidate.contract_digest != self.source_contract_digest:
            raise ValueError("panel reports must belong to the source contract")
        baseline_map = {item.clause_index: item for item in baseline.clause_results}
        candidate_map = {item.clause_index: item for item in candidate.clause_results}
        total = 0.0
        for item in self.clauses:
            before = baseline_map.get(item.clause_index)
            after = candidate_map.get(item.clause_index)
            before_score = 0.0 if before is None else float(before.score)
            after_score = 0.0 if after is None else float(after.score)
            loss = max(0.0, before_score - after_score)
            if before is not None and before.hard and before.passed and (after is None or not after.passed):
                loss = max(loss, 1.0)
            total += item.weight * loss
        return float(total)

    def predicts_regression(self, baseline: ContractReport, candidate: ContractReport) -> bool:
        return self.score_report(baseline, candidate) >= self.threshold


def _full_contract_label(baseline: ContractReport, candidate: ContractReport, *, detection_drop: float) -> bool:
    hard_regression = bool(baseline.hard_pass and not candidate.hard_pass)
    score_drop = max(0.0, float(baseline.score) - float(candidate.score))
    return bool(hard_regression or score_drop >= float(detection_drop))


def _clause_loss_matrix(baseline: ContractReport, scenarios: Sequence[WitnessScenario]) -> tuple[np.ndarray, list[int]]:
    baseline_map = {item.clause_index: item for item in baseline.clause_results}
    clause_indices = sorted(baseline_map)
    matrix = np.zeros((len(scenarios), len(clause_indices)), dtype=np.float64)
    for row, scenario in enumerate(scenarios):
        candidate_map = {item.clause_index: item for item in scenario.report.clause_results}
        for column, clause_index in enumerate(clause_indices):
            before = baseline_map[clause_index]
            after = candidate_map.get(clause_index)
            after_score = 0.0 if after is None else float(after.score)
            loss = max(0.0, float(before.score) - after_score)
            if before.hard and before.passed and (after is None or not after.passed):
                loss = max(loss, 1.0)
            matrix[row, column] = loss
    return matrix, clause_indices


def _evaluate_scores(scores: np.ndarray, labels: np.ndarray, threshold: float) -> DiagnosticEvaluation:
    predictions = scores >= float(threshold)
    positives = int(np.sum(labels))
    negatives = int(np.sum(~labels))
    tp = int(np.sum(predictions & labels))
    fp = int(np.sum(predictions & ~labels))
    tn = int(np.sum(~predictions & ~labels))
    tpr = 1.0 if positives == 0 else tp / positives
    fpr = 0.0 if negatives == 0 else fp / negatives
    tnr = 1.0 if negatives == 0 else tn / negatives
    balanced = 0.5 * (tpr + tnr)
    accuracy = float(np.mean(predictions == labels)) if len(labels) else 1.0
    return DiagnosticEvaluation(
        true_positive_rate=float(tpr),
        false_positive_rate=float(fpr),
        balanced_accuracy=float(balanced),
        accuracy=accuracy,
        positives=positives,
        negatives=negatives,
        scores=tuple(float(value) for value in scores),
        labels=tuple(bool(value) for value in labels),
        predictions=tuple(bool(value) for value in predictions),
    )


def evaluate_diagnostic_panel(
    panel: SemanticDiagnosticPanel,
    baseline: ContractReport,
    scenarios: Sequence[WitnessScenario],
) -> DiagnosticEvaluation:
    labels = np.asarray(
        [_full_contract_label(baseline, scenario.report, detection_drop=panel.detection_drop) for scenario in scenarios],
        dtype=bool,
    )
    scores = np.asarray([panel.score_report(baseline, scenario.report) for scenario in scenarios], dtype=np.float64)
    return _evaluate_scores(scores, labels, panel.threshold)


def build_semantic_diagnostic_panel(
    contract: SemanticContract,
    baseline: ContractReport,
    scenarios: Sequence[WitnessScenario],
    *,
    max_clauses: int = 25,
    detection_drop: float = 0.03,
    max_training_fpr: float = 0.0,
    redundancy_penalty: float = 0.35,
) -> SemanticDiagnosticPanel:
    """Build a psychometrics-inspired discriminative canary panel.

    Full-contract decisions provide scenario labels. Clause-level score losses are
    treated as item responses. Clauses are ranked by separation between positive
    and negative scenarios and greedily de-correlated so the panel does not
    spend its budget on near-duplicate signals. The final threshold is calibrated
    on training scenarios subject to a maximum training false-positive rate.

    This is a transparent baseline inspired by test-item discrimination, not a
    full Item Response Theory model and not new psychometric theory. Held-out
    evaluation is mandatory before the panel is trusted.
    """
    if baseline.contract_digest != contract.digest:
        raise ValueError("baseline report must belong to the supplied contract")
    if max_clauses <= 0:
        raise ValueError("max_clauses must be positive")
    if not 0.0 <= max_training_fpr <= 1.0:
        raise ValueError("max_training_fpr must be in [0, 1]")

    rows = list(scenarios)
    if not rows:
        raise ValueError("at least one scenario is required")
    for scenario in rows:
        if scenario.report.contract_digest != contract.digest:
            raise ValueError(f"scenario {scenario.name!r} belongs to another contract")

    matrix, clause_indices = _clause_loss_matrix(baseline, rows)
    labels = np.asarray(
        [_full_contract_label(baseline, scenario.report, detection_drop=detection_drop) for scenario in rows],
        dtype=bool,
    )
    if not np.any(labels) or not np.any(~labels):
        raise ValueError("diagnostic panel training requires both regression and non-regression scenarios")

    pos = matrix[labels]
    neg = matrix[~labels]
    pos_mean = np.mean(pos, axis=0)
    neg_mean = np.mean(neg, axis=0)
    pooled_scale = np.std(matrix, axis=0) + 0.02
    raw_discrimination = (pos_mean - neg_mean) / pooled_scale
    raw_discrimination = np.maximum(raw_discrimination, 0.0)

    baseline_map = {item.clause_index: item for item in baseline.clause_results}
    hard_columns = [
        column
        for column, clause_index in enumerate(clause_indices)
        if baseline_map[clause_index].hard
    ]
    if len(hard_columns) > max_clauses:
        raise ValueError("max_clauses is smaller than the hard-clause diagnostic surface")

    selected_columns: list[int] = list(hard_columns)
    selected_set = set(selected_columns)
    normalized = matrix.copy()
    column_norm = np.linalg.norm(normalized, axis=0)
    valid = column_norm > _EPS
    normalized[:, valid] /= column_norm[valid]

    while len(selected_columns) < min(max_clauses, len(clause_indices)):
        best_column = None
        best_score = float("-inf")
        for column in range(len(clause_indices)):
            if column in selected_set:
                continue
            discrimination = float(raw_discrimination[column])
            if discrimination <= 0.0:
                continue
            redundancy = 0.0
            if selected_columns and valid[column]:
                redundancy = max(
                    abs(float(np.dot(normalized[:, column], normalized[:, chosen])))
                    for chosen in selected_columns
                    if valid[chosen]
                ) if any(valid[chosen] for chosen in selected_columns) else 0.0
            score = discrimination * max(0.0, 1.0 - float(redundancy_penalty) * redundancy)
            if score > best_score + 1e-12:
                best_score = score
                best_column = column
        if best_column is None:
            break
        selected_columns.append(best_column)
        selected_set.add(best_column)

    if not selected_columns:
        raise ValueError("no discriminative clauses found")

    selected_discrimination = np.asarray(
        [max(float(raw_discrimination[column]), 1e-6) for column in selected_columns],
        dtype=np.float64,
    )
    weights = selected_discrimination / max(float(np.sum(selected_discrimination)), _EPS)
    panel_scores = matrix[:, selected_columns] @ weights

    unique = np.unique(panel_scores)
    candidates = [0.0]
    candidates.extend(float((left + right) / 2.0) for left, right in zip(unique[:-1], unique[1:]))
    candidates.append(float(unique[-1] + 1e-12))

    best_threshold = candidates[-1]
    best_eval = _evaluate_scores(panel_scores, labels, best_threshold)
    for threshold in candidates:
        evaluation = _evaluate_scores(panel_scores, labels, threshold)
        if evaluation.false_positive_rate > max_training_fpr + 1e-12:
            continue
        key = (evaluation.true_positive_rate, evaluation.balanced_accuracy, -threshold)
        best_key = (best_eval.true_positive_rate, best_eval.balanced_accuracy, -best_threshold)
        if best_eval.false_positive_rate > max_training_fpr + 1e-12 or key > best_key:
            best_threshold = float(threshold)
            best_eval = evaluation

    clauses = tuple(
        DiagnosticClause(
            clause_index=clause_indices[column],
            weight=float(weight),
            discrimination=float(raw_discrimination[column]),
            positive_mean_loss=float(pos_mean[column]),
            negative_mean_loss=float(neg_mean[column]),
        )
        for column, weight in zip(selected_columns, weights)
    )
    return SemanticDiagnosticPanel(
        source_contract_digest=contract.digest,
        clauses=clauses,
        threshold=float(best_threshold),
        detection_drop=float(detection_drop),
        training_evaluation=best_eval,
    )
