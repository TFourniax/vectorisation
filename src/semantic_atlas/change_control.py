"""Semantic ABI change-control plane.

This module provides a representation-agnostic compatibility layer for AI-system
changes. It deliberately does not decide what "meaning" is. Adapters emit
normalized :class:`MeaningFrame` observations, and declarative rules state which
relations must survive a release.

The same contract can therefore gate a model swap, prompt rewrite, retrieval
migration, corpus refresh, tool/schema change, or a combination of them without
requiring the old and new systems to share coordinates, providers, or internal
implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from typing import Any, Mapping, Sequence


JSONScalar = str | int | float | bool | None


class ChangeKind(str, Enum):
    MODEL = "model"
    PROMPT = "prompt"
    CORPUS = "corpus"
    EMBEDDING = "embedding"
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    TOOL = "tool"
    POLICY = "policy"
    SCHEMA = "schema"
    CODE = "code"
    CONFIG = "config"
    OTHER = "other"


class RuleScope(str, Enum):
    CROSS_VERSION = "cross_version"
    METAMORPHIC = "metamorphic"


class Comparator(str, Enum):
    EXACT = "exact"
    BASELINE_RECALL = "baseline_recall"
    JACCARD = "jaccard"
    CANDIDATE_SUBSET = "candidate_subset"
    CANDIDATE_SUPERSET = "candidate_superset"
    NUMERIC_ABS_DELTA = "numeric_abs_delta"
    NUMERIC_FLOOR = "numeric_floor"
    NUMERIC_CEILING = "numeric_ceiling"


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditionally_compatible"
    BREAKING = "breaking"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RolloutDecision(str, Enum):
    ALLOW = "allow"
    CANARY = "canary"
    BLOCK = "block"


def _stable_value(value: Any) -> Any:
    """Convert values to a deterministic JSON-compatible representation."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _stable_value(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (set, frozenset)):
        return sorted(_stable_value(v) for v in value)
    if isinstance(value, tuple):
        return [_stable_value(v) for v in value]
    if isinstance(value, list):
        return [_stable_value(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _stable_value(asdict(value))
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _stable_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest_of(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ChangeFacet:
    """A declared component-level change between baseline and candidate."""

    kind: ChangeKind
    name: str
    before_digest: str | None = None
    after_digest: str | None = None
    metadata: Mapping[str, JSONScalar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("change facet name must be non-empty")


@dataclass(frozen=True)
class ChangeSet:
    baseline_system: str
    candidate_system: str
    facets: tuple[ChangeFacet, ...]

    def __post_init__(self) -> None:
        if not self.baseline_system or not self.candidate_system:
            raise ValueError("baseline_system and candidate_system are required")
        if not self.facets:
            raise ValueError("at least one change facet is required")

    @property
    def digest(self) -> str:
        return digest_of(self)


@dataclass(frozen=True)
class MeaningFrame:
    """Normalized semantic/effect observation emitted by a system adapter.

    Sets contain application-defined stable IDs rather than embeddings or raw
    natural-language strings whenever possible. ``scores`` and ``labels`` are
    escape hatches for domain-specific measurements that remain serializable.
    """

    claims: frozenset[str] = frozenset()
    entities: frozenset[str] = frozenset()
    retrieved: frozenset[str] = frozenset()
    citations: frozenset[str] = frozenset()
    tools: frozenset[str] = frozenset()
    effects: frozenset[str] = frozenset()
    scores: Mapping[str, float] = field(default_factory=dict)
    labels: Mapping[str, str] = field(default_factory=dict)
    output_schema_digest: str | None = None

    def __post_init__(self) -> None:
        for key, value in self.scores.items():
            if not isinstance(value, (int, float)) or not isfinite(float(value)):
                raise ValueError(f"score {key!r} must be a finite number")

    @property
    def digest(self) -> str:
        return digest_of(self)

    def surface(self, target: str) -> Any:
        if target in {"claims", "entities", "retrieved", "citations", "tools", "effects"}:
            return getattr(self, target)
        if target == "output_schema_digest":
            return self.output_schema_digest
        if target.startswith("score:"):
            return self.scores.get(target.split(":", 1)[1])
        if target.startswith("label:"):
            return self.labels.get(target.split(":", 1)[1])
        raise KeyError(f"unknown meaning surface: {target}")


@dataclass(frozen=True)
class ProbeObservation:
    probe_id: str
    family_id: str
    variant_id: str
    frame: MeaningFrame
    execution_ok: bool = True
    raw_evidence_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.probe_id or not self.family_id or not self.variant_id:
            raise ValueError("probe_id, family_id and variant_id are required")


@dataclass(frozen=True)
class SystemRun:
    system_id: str
    manifest_digest: str
    observations: tuple[ProbeObservation, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for observation in self.observations:
            if observation.probe_id in seen:
                raise ValueError(f"duplicate probe_id {observation.probe_id!r}")
            seen.add(observation.probe_id)

    @property
    def digest(self) -> str:
        return digest_of(self)

    def by_probe(self) -> dict[str, ProbeObservation]:
        return {obs.probe_id: obs for obs in self.observations}

    def by_family(self) -> dict[str, list[ProbeObservation]]:
        result: dict[str, list[ProbeObservation]] = {}
        for obs in self.observations:
            result.setdefault(obs.family_id, []).append(obs)
        return result


@dataclass(frozen=True)
class CompatibilityRule:
    """Declarative compatibility invariant.

    ``threshold`` semantics depend on the comparator. Set comparators use a
    [0, 1] minimum similarity/recall. ``NUMERIC_ABS_DELTA`` uses a maximum
    absolute difference. FLOOR/CEILING compare the candidate value directly.
    """

    rule_id: str
    target: str
    comparator: Comparator
    scope: RuleScope = RuleScope.CROSS_VERSION
    threshold: float | None = None
    hard: bool = True
    weight: float = 1.0
    canonical_variant_id: str = "canonical"
    applies_to_families: tuple[str, ...] = ()
    depends_on: tuple[ChangeKind, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id is required")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")
        needs_threshold = self.comparator in {
            Comparator.BASELINE_RECALL,
            Comparator.JACCARD,
            Comparator.NUMERIC_ABS_DELTA,
            Comparator.NUMERIC_FLOOR,
            Comparator.NUMERIC_CEILING,
        }
        if needs_threshold and self.threshold is None:
            raise ValueError(f"{self.comparator.value} requires threshold")
        if self.comparator in {Comparator.BASELINE_RECALL, Comparator.JACCARD}:
            if self.threshold is None or not 0 <= self.threshold <= 1:
                raise ValueError("set similarity threshold must be in [0, 1]")


@dataclass(frozen=True)
class CompatibilityContract:
    name: str
    version: str
    rules: tuple[CompatibilityRule, ...]
    minimum_probe_coverage: float = 1.0
    max_soft_regression_weight: float = 0.0

    def __post_init__(self) -> None:
        if not self.name or not self.version:
            raise ValueError("contract name and version are required")
        if not self.rules:
            raise ValueError("contract must contain at least one rule")
        if not 0 <= self.minimum_probe_coverage <= 1:
            raise ValueError("minimum_probe_coverage must be in [0, 1]")
        if self.max_soft_regression_weight < 0:
            raise ValueError("max_soft_regression_weight must be >= 0")
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("rule_id values must be unique")

    @property
    def digest(self) -> str:
        return digest_of(self)


@dataclass(frozen=True)
class RuleWitness:
    rule_id: str
    scope: RuleScope
    probe_id: str
    compared_to: str
    target: str
    comparator: Comparator
    observed: float | bool | str | None
    threshold: float | None
    hard: bool
    passed: bool
    message: str


@dataclass(frozen=True)
class CompatibilityReport:
    contract_digest: str
    change_digest: str
    baseline_run_digest: str
    candidate_run_digest: str
    status: CompatibilityStatus
    rollout: RolloutDecision
    semantic_version_bump: str
    probe_coverage: float
    evaluated_checks: int
    passed_checks: int
    hard_violations: tuple[RuleWitness, ...]
    soft_violations: tuple[RuleWitness, ...]
    missing_evidence: tuple[str, ...]
    suspicious_facets: Mapping[str, tuple[str, ...]]

    @property
    def evidence_digest(self) -> str:
        return digest_of(self)

    @property
    def passing_fraction(self) -> float:
        if self.evaluated_checks == 0:
            return 0.0
        return self.passed_checks / self.evaluated_checks


def _as_set(value: Any, target: str) -> frozenset[Any]:
    if isinstance(value, (set, frozenset)):
        return frozenset(value)
    raise TypeError(f"target {target!r} is not a set-valued surface")


def _as_number(value: Any, target: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"target {target!r} is missing or non-numeric")
    value = float(value)
    if not isfinite(value):
        raise TypeError(f"target {target!r} is non-finite")
    return value


def _compare(rule: CompatibilityRule, reference: Any, candidate: Any) -> tuple[bool, float | bool | str | None, str]:
    comparator = rule.comparator

    if comparator == Comparator.EXACT:
        passed = reference == candidate
        return passed, passed, "exact match" if passed else "values differ"

    if comparator in {Comparator.BASELINE_RECALL, Comparator.JACCARD, Comparator.CANDIDATE_SUBSET, Comparator.CANDIDATE_SUPERSET}:
        left = _as_set(reference, rule.target)
        right = _as_set(candidate, rule.target)
        if comparator == Comparator.BASELINE_RECALL:
            score = 1.0 if not left else len(left & right) / len(left)
            passed = score >= float(rule.threshold)
            return passed, score, f"baseline recall={score:.6f}"
        if comparator == Comparator.JACCARD:
            union = left | right
            score = 1.0 if not union else len(left & right) / len(union)
            passed = score >= float(rule.threshold)
            return passed, score, f"jaccard={score:.6f}"
        if comparator == Comparator.CANDIDATE_SUBSET:
            passed = right <= left
            return passed, passed, "candidate subset preserved" if passed else "candidate introduced new values"
        passed = right >= left
        return passed, passed, "candidate superset preserved" if passed else "candidate lost required values"

    if comparator == Comparator.NUMERIC_ABS_DELTA:
        ref = _as_number(reference, rule.target)
        cand = _as_number(candidate, rule.target)
        delta = abs(cand - ref)
        passed = delta <= float(rule.threshold)
        return passed, delta, f"absolute delta={delta:.6f}"

    if comparator == Comparator.NUMERIC_FLOOR:
        cand = _as_number(candidate, rule.target)
        passed = cand >= float(rule.threshold)
        return passed, cand, f"candidate value={cand:.6f}"

    if comparator == Comparator.NUMERIC_CEILING:
        cand = _as_number(candidate, rule.target)
        passed = cand <= float(rule.threshold)
        return passed, cand, f"candidate value={cand:.6f}"

    raise AssertionError(f"unhandled comparator: {comparator}")


def _family_allowed(rule: CompatibilityRule, family_id: str) -> bool:
    return not rule.applies_to_families or family_id in rule.applies_to_families


def _witness(
    rule: CompatibilityRule,
    probe: ProbeObservation,
    compared_to: ProbeObservation,
    *,
    reference_value: Any,
    candidate_value: Any,
) -> RuleWitness:
    try:
        passed, observed, message = _compare(rule, reference_value, candidate_value)
    except (TypeError, KeyError, ValueError) as exc:
        passed, observed, message = False, None, f"missing/incompatible evidence: {exc}"
    return RuleWitness(
        rule_id=rule.rule_id,
        scope=rule.scope,
        probe_id=probe.probe_id,
        compared_to=compared_to.probe_id,
        target=rule.target,
        comparator=rule.comparator,
        observed=observed,
        threshold=rule.threshold,
        hard=rule.hard,
        passed=passed,
        message=message,
    )


def _cross_version_witnesses(
    rule: CompatibilityRule,
    baseline: SystemRun,
    candidate: SystemRun,
) -> tuple[list[RuleWitness], list[str]]:
    baseline_map = baseline.by_probe()
    candidate_map = candidate.by_probe()
    witnesses: list[RuleWitness] = []
    missing: list[str] = []

    for probe_id, old in baseline_map.items():
        if not _family_allowed(rule, old.family_id):
            continue
        new = candidate_map.get(probe_id)
        if new is None:
            missing.append(f"{rule.rule_id}:candidate_missing:{probe_id}")
            continue
        if not old.execution_ok or not new.execution_ok:
            missing.append(f"{rule.rule_id}:execution_failed:{probe_id}")
            continue
        try:
            ref_value = old.frame.surface(rule.target)
            cand_value = new.frame.surface(rule.target)
        except KeyError as exc:
            missing.append(f"{rule.rule_id}:surface_error:{probe_id}:{exc}")
            continue
        witnesses.append(
            _witness(
                rule,
                new,
                old,
                reference_value=ref_value,
                candidate_value=cand_value,
            )
        )
    return witnesses, missing


def _metamorphic_witnesses(
    rule: CompatibilityRule,
    candidate: SystemRun,
) -> tuple[list[RuleWitness], list[str]]:
    witnesses: list[RuleWitness] = []
    missing: list[str] = []

    for family_id, family in candidate.by_family().items():
        if not _family_allowed(rule, family_id):
            continue
        canonical = next((obs for obs in family if obs.variant_id == rule.canonical_variant_id), None)
        if canonical is None:
            missing.append(f"{rule.rule_id}:canonical_missing:{family_id}")
            continue
        if not canonical.execution_ok:
            missing.append(f"{rule.rule_id}:canonical_failed:{family_id}")
            continue
        variants = [obs for obs in family if obs.probe_id != canonical.probe_id]
        if not variants:
            missing.append(f"{rule.rule_id}:variant_missing:{family_id}")
            continue
        for variant in variants:
            if not variant.execution_ok:
                missing.append(f"{rule.rule_id}:variant_failed:{variant.probe_id}")
                continue
            try:
                ref_value = canonical.frame.surface(rule.target)
                cand_value = variant.frame.surface(rule.target)
            except KeyError as exc:
                missing.append(f"{rule.rule_id}:surface_error:{variant.probe_id}:{exc}")
                continue
            witnesses.append(
                _witness(
                    rule,
                    variant,
                    canonical,
                    reference_value=ref_value,
                    candidate_value=cand_value,
                )
            )
    return witnesses, missing


def _probe_coverage(baseline: SystemRun, candidate: SystemRun) -> float:
    baseline_ids = {obs.probe_id for obs in baseline.observations if obs.execution_ok}
    if not baseline_ids:
        return 0.0
    candidate_ids = {obs.probe_id for obs in candidate.observations if obs.execution_ok}
    return len(baseline_ids & candidate_ids) / len(baseline_ids)


def _localize(
    violations: Sequence[RuleWitness],
    contract: CompatibilityContract,
    changes: ChangeSet,
) -> dict[str, tuple[str, ...]]:
    rules = {rule.rule_id: rule for rule in contract.rules}
    result: dict[str, set[str]] = {}
    for violation in violations:
        rule = rules[violation.rule_id]
        candidates = [
            facet for facet in changes.facets if not rule.depends_on or facet.kind in rule.depends_on
        ]
        for facet in candidates:
            key = f"{facet.kind.value}:{facet.name}"
            result.setdefault(key, set()).add(violation.rule_id)
    return {key: tuple(sorted(rule_ids)) for key, rule_ids in sorted(result.items())}


def evaluate_change(
    contract: CompatibilityContract,
    changes: ChangeSet,
    baseline: SystemRun,
    candidate: SystemRun,
) -> CompatibilityReport:
    """Evaluate semantic backwards compatibility for a release.

    Hard rule failures or inadequate evidence fail closed. Soft regressions can
    result in a canary recommendation when they stay inside the contract's
    declared error budget.
    """

    if baseline.system_id != changes.baseline_system:
        raise ValueError("baseline run does not match ChangeSet.baseline_system")
    if candidate.system_id != changes.candidate_system:
        raise ValueError("candidate run does not match ChangeSet.candidate_system")

    coverage = _probe_coverage(baseline, candidate)
    witnesses: list[RuleWitness] = []
    missing: list[str] = []

    for rule in contract.rules:
        if rule.scope == RuleScope.CROSS_VERSION:
            rule_witnesses, rule_missing = _cross_version_witnesses(rule, baseline, candidate)
        else:
            rule_witnesses, rule_missing = _metamorphic_witnesses(rule, candidate)
        witnesses.extend(rule_witnesses)
        missing.extend(rule_missing)

    hard_violations = tuple(w for w in witnesses if w.hard and not w.passed)
    soft_violations = tuple(w for w in witnesses if not w.hard and not w.passed)
    soft_weight_by_rule = {rule.rule_id: rule.weight for rule in contract.rules if not rule.hard}
    violated_soft_rule_ids = {w.rule_id for w in soft_violations}
    soft_regression_weight = sum(soft_weight_by_rule[rule_id] for rule_id in violated_soft_rule_ids)

    insufficient = coverage < contract.minimum_probe_coverage or bool(missing) or not witnesses
    if insufficient:
        status = CompatibilityStatus.INSUFFICIENT_EVIDENCE
        rollout = RolloutDecision.BLOCK
        bump = "major"
    elif hard_violations:
        status = CompatibilityStatus.BREAKING
        rollout = RolloutDecision.BLOCK
        bump = "major"
    elif soft_regression_weight > contract.max_soft_regression_weight:
        status = CompatibilityStatus.BREAKING
        rollout = RolloutDecision.BLOCK
        bump = "major"
    elif soft_violations:
        status = CompatibilityStatus.CONDITIONAL
        rollout = RolloutDecision.CANARY
        bump = "minor"
    else:
        status = CompatibilityStatus.COMPATIBLE
        rollout = RolloutDecision.ALLOW
        bump = "patch"

    all_violations = (*hard_violations, *soft_violations)
    return CompatibilityReport(
        contract_digest=contract.digest,
        change_digest=changes.digest,
        baseline_run_digest=baseline.digest,
        candidate_run_digest=candidate.digest,
        status=status,
        rollout=rollout,
        semantic_version_bump=bump,
        probe_coverage=coverage,
        evaluated_checks=len(witnesses),
        passed_checks=sum(1 for w in witnesses if w.passed),
        hard_violations=hard_violations,
        soft_violations=soft_violations,
        missing_evidence=tuple(sorted(set(missing))),
        suspicious_facets=_localize(all_violations, contract, changes),
    )


def contract_from_dict(payload: Mapping[str, Any]) -> CompatibilityContract:
    """Load a compatibility contract from a plain JSON/YAML-compatible mapping."""

    rules: list[CompatibilityRule] = []
    for raw in payload.get("rules", []):
        rules.append(
            CompatibilityRule(
                rule_id=str(raw["rule_id"]),
                target=str(raw["target"]),
                comparator=Comparator(raw["comparator"]),
                scope=RuleScope(raw.get("scope", RuleScope.CROSS_VERSION.value)),
                threshold=raw.get("threshold"),
                hard=bool(raw.get("hard", True)),
                weight=float(raw.get("weight", 1.0)),
                canonical_variant_id=str(raw.get("canonical_variant_id", "canonical")),
                applies_to_families=tuple(raw.get("applies_to_families", ())),
                depends_on=tuple(ChangeKind(item) for item in raw.get("depends_on", ())),
                description=str(raw.get("description", "")),
            )
        )
    return CompatibilityContract(
        name=str(payload["name"]),
        version=str(payload["version"]),
        rules=tuple(rules),
        minimum_probe_coverage=float(payload.get("minimum_probe_coverage", 1.0)),
        max_soft_regression_weight=float(payload.get("max_soft_regression_weight", 0.0)),
    )


def report_to_dict(report: CompatibilityReport) -> dict[str, Any]:
    """Return a stable JSON-compatible report including its evidence digest."""

    result = _stable_value(report)
    assert isinstance(result, dict)
    result["evidence_digest"] = report.evidence_digest
    return result
