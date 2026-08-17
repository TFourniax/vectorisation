from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .contracts import ClauseResult, ContractReport, SemanticContract

_EPS = 1e-12


@dataclass(slots=True, frozen=True)
class WitnessScenario:
    """One implementation/fault scenario used to train or evaluate a witness set."""

    name: str
    report: ContractReport
    weight: float = 1.0


@dataclass(slots=True, frozen=True)
class WitnessScenarioEvaluation:
    name: str
    full_detected: bool
    witness_detected: bool
    full_score_drop: float
    witness_score_drop: float
    retained_loss_mass: float


@dataclass(slots=True, frozen=True)
class WitnessEvaluation:
    scenarios: tuple[WitnessScenarioEvaluation, ...]
    positive_recall: float
    false_positive_rate: float
    decision_accuracy: float
    mean_retained_loss_mass: float
    object_coverage: float


@dataclass(slots=True)
class SemanticWitnessSet:
    """Compact diagnostic subset of a larger Semantic Contract.

    A witness set is intentionally *not* claimed to be semantically equivalent
    to the full contract. It is a selected panel that attempts to preserve the
    full contract's observed regression/fault-detection behavior over a set of
    training scenarios while retaining broad logical-object coverage.
    """

    source_contract_digest: str
    selected_clause_indices: tuple[int, ...]
    contract: SemanticContract
    training_evaluation: WitnessEvaluation
    max_clauses: int
    target_detection_coverage: float
    target_loss_coverage: float

    @property
    def clause_fraction(self) -> float:
        source_count = int(self.contract.metadata.get("source_clause_count", 0))
        if source_count <= 0:
            return 0.0
        return len(self.selected_clause_indices) / source_count

    @property
    def compression_ratio(self) -> float:
        if not self.selected_clause_indices:
            return float("inf")
        source_count = int(self.contract.metadata.get("source_clause_count", 0))
        return source_count / len(self.selected_clause_indices) if source_count > 0 else 0.0


def _result_map(report: ContractReport) -> dict[int, ClauseResult]:
    return {result.clause_index: result for result in report.clause_results}


def _validate_reports(contract: SemanticContract, baseline: ContractReport, scenarios: Sequence[WitnessScenario]) -> None:
    if baseline.contract_digest != contract.digest:
        raise ValueError("baseline report was not produced by the supplied contract")
    for scenario in scenarios:
        if scenario.report.contract_digest != contract.digest:
            raise ValueError(f"scenario {scenario.name!r} was not produced by the supplied contract")
        if scenario.weight < 0:
            raise ValueError("scenario weights must be non-negative")


def _scenario_score(result_map: dict[int, ClauseResult], clause_index: int) -> tuple[float, bool]:
    result = result_map.get(clause_index)
    if result is None:
        return 0.0, False
    return float(result.score), bool(result.passed)


def _subset_detection(
    selected: Sequence[int],
    baseline_map: dict[int, ClauseResult],
    scenario_map: dict[int, ClauseResult],
    *,
    detection_drop: float,
) -> tuple[bool, float]:
    if not selected:
        return False, 0.0

    total_weight = 0.0
    baseline_earned = 0.0
    scenario_earned = 0.0
    hard_failed = False

    for clause_index in selected:
        baseline_result = baseline_map.get(clause_index)
        if baseline_result is None:
            continue
        weight = max(0.0, float(baseline_result.weight))
        total_weight += weight
        baseline_earned += weight * float(baseline_result.score)
        scenario_score, scenario_passed = _scenario_score(scenario_map, clause_index)
        scenario_earned += weight * scenario_score
        if bool(baseline_result.hard) and bool(baseline_result.passed) and not scenario_passed:
            hard_failed = True

    if total_weight <= _EPS:
        return hard_failed, 0.0
    baseline_score = baseline_earned / total_weight
    scenario_score = scenario_earned / total_weight
    score_drop = max(0.0, baseline_score - scenario_score)
    return bool(hard_failed or score_drop >= float(detection_drop)), float(score_drop)


def _clause_loss(
    clause_index: int,
    baseline_map: dict[int, ClauseResult],
    scenario_map: dict[int, ClauseResult],
) -> float:
    baseline_result = baseline_map.get(clause_index)
    if baseline_result is None:
        return 0.0
    scenario_score, scenario_passed = _scenario_score(scenario_map, clause_index)
    weight = max(0.0, float(baseline_result.weight))
    score_loss = max(0.0, float(baseline_result.score) - scenario_score)
    hard_loss = 0.0
    if bool(baseline_result.hard) and bool(baseline_result.passed) and not scenario_passed:
        hard_loss = 1.0
    return weight * max(score_loss, hard_loss)


def evaluate_clause_subset(
    contract: SemanticContract,
    baseline: ContractReport,
    scenarios: Sequence[WitnessScenario],
    clause_indices: Sequence[int],
    *,
    detection_drop: float = 0.05,
) -> WitnessEvaluation:
    """Evaluate how faithfully a clause subset preserves full-contract decisions.

    The calculation uses already-audited per-clause results, so evaluating many
    candidate subsets does not re-run vector/sparse/graph retrieval. It exactly
    re-aggregates the selected clause scores, but says nothing about unseen
    fault families unless those are evaluated as separate held-out scenarios.
    """
    _validate_reports(contract, baseline, scenarios)
    baseline_map = _result_map(baseline)
    selected = tuple(sorted({int(index) for index in clause_indices if int(index) in baseline_map}))
    all_indices = tuple(sorted(baseline_map))

    all_objects = {object_id for clause in contract.clauses for object_id in clause.objects}
    selected_objects = {
        object_id
        for index in selected
        if 0 <= index < len(contract.clauses)
        for object_id in contract.clauses[index].objects
    }
    object_coverage = len(selected_objects) / max(1, len(all_objects))

    positive_weight = negative_weight = 0.0
    true_positive_weight = false_positive_weight = 0.0
    correct_weight = total_weight = 0.0
    retained_loss_values: list[tuple[float, float]] = []
    evaluations: list[WitnessScenarioEvaluation] = []

    for scenario in scenarios:
        scenario_map = _result_map(scenario.report)
        full_detected, full_drop = _subset_detection(all_indices, baseline_map, scenario_map, detection_drop=detection_drop)
        witness_detected, witness_drop = _subset_detection(selected, baseline_map, scenario_map, detection_drop=detection_drop)
        full_loss = sum(_clause_loss(index, baseline_map, scenario_map) for index in all_indices)
        selected_loss = sum(_clause_loss(index, baseline_map, scenario_map) for index in selected)
        retained_loss = 1.0 if full_loss <= _EPS else min(1.0, selected_loss / full_loss)

        weight = max(0.0, float(scenario.weight))
        total_weight += weight
        if full_detected:
            positive_weight += weight
            if witness_detected:
                true_positive_weight += weight
        else:
            negative_weight += weight
            if witness_detected:
                false_positive_weight += weight
        if full_detected == witness_detected:
            correct_weight += weight
        if full_detected and full_loss > _EPS:
            retained_loss_values.append((retained_loss, weight))

        evaluations.append(
            WitnessScenarioEvaluation(
                name=scenario.name,
                full_detected=full_detected,
                witness_detected=witness_detected,
                full_score_drop=full_drop,
                witness_score_drop=witness_drop,
                retained_loss_mass=float(retained_loss),
            )
        )

    positive_recall = 1.0 if positive_weight <= _EPS else true_positive_weight / positive_weight
    false_positive_rate = 0.0 if negative_weight <= _EPS else false_positive_weight / negative_weight
    decision_accuracy = 1.0 if total_weight <= _EPS else correct_weight / total_weight
    loss_weight = sum(weight for _, weight in retained_loss_values)
    mean_retained_loss = 1.0 if not retained_loss_values else sum(value * weight for value, weight in retained_loss_values) / max(loss_weight, _EPS)

    return WitnessEvaluation(
        scenarios=tuple(evaluations),
        positive_recall=float(positive_recall),
        false_positive_rate=float(false_positive_rate),
        decision_accuracy=float(decision_accuracy),
        mean_retained_loss_mass=float(mean_retained_loss),
        object_coverage=float(object_coverage),
    )


def build_semantic_witness_set(
    contract: SemanticContract,
    baseline: ContractReport,
    scenarios: Sequence[WitnessScenario],
    *,
    max_clauses: int,
    detection_drop: float = 0.05,
    target_detection_coverage: float = 1.0,
    target_loss_coverage: float = 0.80,
    object_coverage_weight: float = 0.05,
    false_positive_penalty: float = 2.0,
) -> SemanticWitnessSet:
    """Greedily sparsify a Semantic Contract into a compact witness panel.

    Selection sees only per-clause behavior on the supplied training scenarios;
    it never uses the scenarios' true affected-object IDs. Hard clauses are
    always retained. Candidate additions are scored from incremental sufficient
    statistics, so each greedy comparison is O(number of scenarios) rather than
    rescanning the full contract.

    The returned witness must be evaluated on held-out scenarios before being
    trusted. It is a diagnostic/test-suite compression mechanism, not a proof
    that omitted clauses are universally semantically redundant.
    """
    _validate_reports(contract, baseline, scenarios)
    max_clauses = int(max_clauses)
    if max_clauses <= 0:
        raise ValueError("max_clauses must be positive")
    target_detection_coverage = min(1.0, max(0.0, float(target_detection_coverage)))
    target_loss_coverage = min(1.0, max(0.0, float(target_loss_coverage)))

    baseline_map = _result_map(baseline)
    available = sorted(baseline_map)
    hard_indices = [index for index in available if bool(baseline_map[index].hard)]
    if len(hard_indices) > max_clauses:
        raise ValueError("max_clauses is smaller than the number of hard clauses")

    all_indices = tuple(available)
    all_objects = {object_id for clause in contract.clauses for object_id in clause.objects}
    scenario_maps = [_result_map(scenario.report) for scenario in scenarios]
    scenario_weights = [max(0.0, float(scenario.weight)) for scenario in scenarios]
    full_detected: list[bool] = []
    full_losses: list[float] = []
    for scenario_map in scenario_maps:
        detected, _ = _subset_detection(all_indices, baseline_map, scenario_map, detection_drop=detection_drop)
        full_detected.append(detected)
        full_losses.append(sum(_clause_loss(index, baseline_map, scenario_map) for index in all_indices))

    selected = sorted(hard_indices)
    selected_set = set(selected)
    selected_objects = {
        object_id
        for index in selected
        if 0 <= index < len(contract.clauses)
        for object_id in contract.clauses[index].objects
    }
    selected_total_weight = sum(max(0.0, float(baseline_map[index].weight)) for index in selected)
    selected_baseline_earned = sum(
        max(0.0, float(baseline_map[index].weight)) * float(baseline_map[index].score)
        for index in selected
    )
    selected_scenario_earned: list[float] = []
    selected_hard_failed: list[bool] = []
    selected_losses: list[float] = []
    for scenario_map in scenario_maps:
        earned = 0.0
        hard_failed = False
        loss = 0.0
        for index in selected:
            baseline_result = baseline_map[index]
            weight = max(0.0, float(baseline_result.weight))
            scenario_score, scenario_passed = _scenario_score(scenario_map, index)
            earned += weight * scenario_score
            loss += _clause_loss(index, baseline_map, scenario_map)
            if bool(baseline_result.hard) and bool(baseline_result.passed) and not scenario_passed:
                hard_failed = True
        selected_scenario_earned.append(earned)
        selected_hard_failed.append(hard_failed)
        selected_losses.append(loss)

    positive_total = sum(weight for weight, target in zip(scenario_weights, full_detected) if target)
    negative_total = sum(weight for weight, target in zip(scenario_weights, full_detected) if not target)
    loss_weight_total = sum(
        weight
        for weight, loss, target in zip(scenario_weights, full_losses, full_detected)
        if target and loss > _EPS
    )

    def candidate_metrics(clause_index: int | None) -> tuple[float, float, float, float, float]:
        if clause_index is None:
            added_weight = 0.0
            added_baseline_earned = 0.0
            added_objects: set[str] = set()
        else:
            baseline_result = baseline_map[clause_index]
            added_weight = max(0.0, float(baseline_result.weight))
            added_baseline_earned = added_weight * float(baseline_result.score)
            added_objects = set(contract.clauses[clause_index].objects)

        denominator = selected_total_weight + added_weight
        baseline_earned = selected_baseline_earned + added_baseline_earned
        baseline_score = 0.0 if denominator <= _EPS else baseline_earned / denominator
        true_positive = false_positive = correct = 0.0
        retained_loss_sum = 0.0
        total_scenario_weight = sum(scenario_weights)

        for position, (scenario_map, weight, target, full_loss) in enumerate(
            zip(scenario_maps, scenario_weights, full_detected, full_losses)
        ):
            scenario_earned = selected_scenario_earned[position]
            hard_failed = selected_hard_failed[position]
            selected_loss = selected_losses[position]
            if clause_index is not None:
                scenario_score, scenario_passed = _scenario_score(scenario_map, clause_index)
                scenario_earned += added_weight * scenario_score
                selected_loss += _clause_loss(clause_index, baseline_map, scenario_map)
                baseline_result = baseline_map[clause_index]
                if bool(baseline_result.hard) and bool(baseline_result.passed) and not scenario_passed:
                    hard_failed = True

            scenario_score = 0.0 if denominator <= _EPS else scenario_earned / denominator
            score_drop = max(0.0, baseline_score - scenario_score)
            detected = bool(hard_failed or score_drop >= float(detection_drop))
            if target and detected:
                true_positive += weight
            if not target and detected:
                false_positive += weight
            if target == detected:
                correct += weight
            if target and full_loss > _EPS:
                retained_loss_sum += weight * min(1.0, selected_loss / full_loss)

        positive_recall = 1.0 if positive_total <= _EPS else true_positive / positive_total
        false_positive_rate = 0.0 if negative_total <= _EPS else false_positive / negative_total
        decision_accuracy = 1.0 if total_scenario_weight <= _EPS else correct / total_scenario_weight
        mean_loss = 1.0 if loss_weight_total <= _EPS else retained_loss_sum / loss_weight_total
        object_coverage = len(selected_objects | added_objects) / max(1, len(all_objects))
        utility = (
            positive_recall
            - float(false_positive_penalty) * false_positive_rate
            + 0.35 * mean_loss
            + float(object_coverage_weight) * object_coverage
            + 0.01 * decision_accuracy
        )
        return float(utility), float(positive_recall), float(false_positive_rate), float(mean_loss), float(object_coverage)

    _, current_positive_recall, _, current_loss, _ = candidate_metrics(None)

    while len(selected) < max_clauses:
        if current_positive_recall >= target_detection_coverage and current_loss >= target_loss_coverage:
            break

        best_index: int | None = None
        best_metrics: tuple[float, float, float, float, float] | None = None
        for clause_index in available:
            if clause_index in selected_set:
                continue
            metrics = candidate_metrics(clause_index)
            if best_metrics is None or metrics > best_metrics or (metrics == best_metrics and clause_index < int(best_index)):
                best_index = clause_index
                best_metrics = metrics

        if best_index is None or best_metrics is None:
            break

        baseline_result = baseline_map[best_index]
        added_weight = max(0.0, float(baseline_result.weight))
        selected_total_weight += added_weight
        selected_baseline_earned += added_weight * float(baseline_result.score)
        selected_objects.update(contract.clauses[best_index].objects)
        for position, scenario_map in enumerate(scenario_maps):
            scenario_score, scenario_passed = _scenario_score(scenario_map, best_index)
            selected_scenario_earned[position] += added_weight * scenario_score
            selected_losses[position] += _clause_loss(best_index, baseline_map, scenario_map)
            if bool(baseline_result.hard) and bool(baseline_result.passed) and not scenario_passed:
                selected_hard_failed[position] = True
        selected.append(best_index)
        selected_set.add(best_index)
        _, current_positive_recall, _, current_loss, _ = candidate_metrics(None)

    selected = sorted(selected)
    current_eval = evaluate_clause_subset(
        contract,
        baseline,
        scenarios,
        selected,
        detection_drop=detection_drop,
    )
    witness_contract = SemanticContract(
        name=f"{contract.name}-witness",
        version=f"{contract.version}-witness",
        clauses=[contract.clauses[index] for index in selected],
        metadata={
            **contract.metadata,
            "builder": "build_semantic_witness_set",
            "source_contract_digest": contract.digest,
            "source_clause_count": len(contract.clauses),
            "selected_clause_indices": selected,
            "detection_drop": float(detection_drop),
            "training_scenarios": [scenario.name for scenario in scenarios],
        },
        parent_digest=contract.digest,
    )

    return SemanticWitnessSet(
        source_contract_digest=contract.digest,
        selected_clause_indices=tuple(selected),
        contract=witness_contract,
        training_evaluation=current_eval,
        max_clauses=max_clauses,
        target_detection_coverage=target_detection_coverage,
        target_loss_coverage=target_loss_coverage,
    )
