"""Minimal Semantic ABI v0.6 change-control demo.

Run with:
    python examples/change_control_demo.py
"""

from semantic_atlas.change_control import (
    ChangeFacet,
    ChangeKind,
    ChangeSet,
    Comparator,
    CompatibilityContract,
    CompatibilityRule,
    MeaningFrame,
    ProbeObservation,
    RuleScope,
    SystemRun,
    evaluate_change,
    report_to_dict,
)
import json


def observation(probe_id: str, variant: str, claims: set[str], retrieved: set[str]) -> ProbeObservation:
    return ProbeObservation(
        probe_id=probe_id,
        family_id="refund-policy",
        variant_id=variant,
        frame=MeaningFrame(
            claims=frozenset(claims),
            retrieved=frozenset(retrieved),
            effects=frozenset({"read-only"}),
        ),
    )


contract = CompatibilityContract(
    name="customer-support-ai",
    version="1.0",
    minimum_probe_coverage=1.0,
    rules=(
        CompatibilityRule(
            rule_id="preserve-required-claims",
            target="claims",
            comparator=Comparator.BASELINE_RECALL,
            threshold=1.0,
            depends_on=(ChangeKind.MODEL, ChangeKind.RETRIEVER, ChangeKind.CORPUS),
        ),
        CompatibilityRule(
            rule_id="paraphrase-invariance",
            target="claims",
            comparator=Comparator.EXACT,
            scope=RuleScope.METAMORPHIC,
            depends_on=(ChangeKind.MODEL, ChangeKind.PROMPT),
        ),
        CompatibilityRule(
            rule_id="retrieval-overlap",
            target="retrieved",
            comparator=Comparator.JACCARD,
            threshold=0.5,
            hard=False,
            weight=0.5,
        ),
    ),
    max_soft_regression_weight=0.5,
)

baseline = SystemRun(
    system_id="prod@2026-08-17",
    manifest_digest="baseline-manifest",
    observations=(
        observation("refund-1", "canonical", {"refund:30-days", "refund:original-method"}, {"doc:refund-v3"}),
        observation("refund-2", "paraphrase", {"refund:30-days", "refund:original-method"}, {"doc:refund-v3"}),
    ),
)

candidate = SystemRun(
    system_id="candidate@2026-08-18",
    manifest_digest="candidate-manifest",
    observations=(
        observation("refund-1", "canonical", {"refund:30-days", "refund:original-method"}, {"doc:refund-v4"}),
        observation("refund-2", "paraphrase", {"refund:30-days", "refund:original-method"}, {"doc:refund-v4"}),
    ),
)

changes = ChangeSet(
    baseline_system=baseline.system_id,
    candidate_system=candidate.system_id,
    facets=(
        ChangeFacet(ChangeKind.MODEL, "provider-model"),
        ChangeFacet(ChangeKind.CORPUS, "support-kb"),
    ),
)

report = evaluate_change(contract, changes, baseline, candidate)
print(json.dumps(report_to_dict(report), indent=2, ensure_ascii=False))
