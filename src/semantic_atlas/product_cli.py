from __future__ import annotations

"""Product-facing CLI layered over the research Protocol-v1 CLI.

Unknown commands are delegated to the original CLI so existing research and protocol
workflows remain backward compatible while product commands can evolve independently.
"""

import argparse
import json
import os
from pathlib import Path
import sys

from . import cli as legacy_cli
from .acquisition import AcquisitionPolicy, load_evidence_jsonl
from .change_control import ReleasePolicy, compare_protocol_audits
from .contracts import SemanticContract
from .otlp import load_otlp_jsonl
from .policy_forge import forge_contract_with_policies
from .product_config import oracle_from_config
from .protocol_v1 import audit_contract_v1
from .review import ReviewBundle, apply_review_decisions, build_review_bundle, load_review_decisions_jsonl
from .telemetry import join_feedback, load_feedback_jsonl

_PRODUCT_COMMANDS = {"check", "forge-safe", "forge-otlp", "apply-review"}


def _write_json(value, path: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _acquisition_policy(args: argparse.Namespace) -> AcquisitionPolicy:
    return AcquisitionPolicy(
        auto_promote_confidence=args.auto_promote_confidence,
        review_confidence=args.review_confidence,
        min_effective_support=args.min_effective_support,
        hard_confidence=args.hard_confidence,
        hard_min_criticality=args.hard_min_criticality,
        opposition_ratio_review=args.opposition_ratio_review,
        max_review_items=args.max_review_items,
    )


def _add_acquisition_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--name", default="application-semantics")
    parser.add_argument("--version", default="1")
    parser.add_argument("--parent", help="optional parent Semantic Contract")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument("--review-bundle")
    parser.add_argument("--auto-promote-confidence", type=float, default=0.85)
    parser.add_argument("--review-confidence", type=float, default=0.60)
    parser.add_argument("--min-effective-support", type=float, default=0.80)
    parser.add_argument("--hard-confidence", type=float, default=0.98)
    parser.add_argument("--hard-min-criticality", type=float, default=0.80)
    parser.add_argument("--opposition-ratio-review", type=float, default=0.20)
    parser.add_argument("--max-review-items", type=int, default=200)
    parser.add_argument("--seconds-per-review", type=float, default=20.0)
    parser.add_argument("--quiet", action="store_true")


def _forge_common(args: argparse.Namespace, evidence, extra_report=None) -> int:
    parent_digest = SemanticContract.load(args.parent).digest if args.parent else None
    result = forge_contract_with_policies(
        evidence,
        name=args.name,
        version=args.version,
        parent_digest=parent_digest,
        policy=_acquisition_policy(args),
        estimated_seconds_per_review=args.seconds_per_review,
    )
    result.contract.save(args.output)
    bundle = build_review_bundle(result, evidence)
    if args.review_bundle:
        bundle.save(args.review_bundle)
    report = {"acquisition": result.report.to_dict(), "review_bundle_digest": bundle.digest}
    if extra_report:
        report.update(extra_report)
    if args.report:
        _write_json(report, args.report)
    if not args.quiet:
        _write_json(report, None)
    return 0


def _forge_safe(args: argparse.Namespace) -> int:
    return _forge_common(args, load_evidence_jsonl(args.evidence))


def _query_secret(args: argparse.Namespace) -> str | None:
    if not args.query_secret_env:
        return None
    value = os.environ.get(args.query_secret_env)
    if value is None or value == "":
        raise SystemExit(f"required query-secret environment variable is missing: {args.query_secret_env}")
    return value


def _forge_otlp(args: argparse.Namespace) -> int:
    telemetry = load_otlp_jsonl(
        args.traces,
        query_secret=_query_secret(args),
        retain_query_text=bool(args.retain_query_text),
        allow_reranker=not args.no_reranker,
    )
    feedback = load_feedback_jsonl(args.feedback)
    joined = join_feedback(telemetry.observations, feedback)
    evidence = list(joined.evidence)
    if args.evidence:
        evidence.extend(load_evidence_jsonl(args.evidence))
    telemetry_report = telemetry.report.to_dict()
    telemetry_report.update(
        {
            "feedback_records": len(feedback),
            "feedback_matched": joined.report.feedback_matched,
            "evidence_emitted": joined.report.evidence_emitted,
        }
    )
    return _forge_common(args, evidence, extra_report={"telemetry": telemetry_report})


def _check(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    baseline_oracle = oracle_from_config(args.baseline)
    candidate_oracle = oracle_from_config(args.candidate)
    baseline = audit_contract_v1(contract, baseline_oracle)
    candidate = audit_contract_v1(contract, candidate_oracle)
    policy = ReleasePolicy(
        min_candidate_score=args.min_candidate_score,
        max_score_drop=args.max_score_drop,
        allow_soft_regressions=args.allow_soft_regressions,
        require_no_new_missing=not args.allow_new_missing,
        require_absolute_hard_pass=not args.no_absolute_hard_pass,
        allow_existing_hard_failures=args.allow_existing_hard_failures,
    )
    report = compare_protocol_audits(contract, baseline, candidate, policy=policy)
    payload = report.to_dict(include_clauses=not args.summary_only)
    if args.output:
        _write_json(payload, args.output)
    elif not args.markdown:
        _write_json(payload, None)
    if args.markdown:
        target = Path(args.markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report.to_markdown(max_rows=args.max_rows), encoding="utf-8")
    return 0 if report.deployment_eligible else 4


def _apply_review(args: argparse.Namespace) -> int:
    parent = SemanticContract.load(args.parent)
    bundle = ReviewBundle.load(args.bundle)
    decisions = load_review_decisions_jsonl(args.decisions)
    result = apply_review_decisions(
        parent,
        bundle,
        decisions,
        version=args.version,
        allow_hard=args.allow_hard,
    )
    result.contract.save(args.output)
    if args.report:
        _write_json(result.to_dict(), args.report)
    elif not args.quiet:
        _write_json(result.to_dict(), None)
    return 0


def build_product_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic-abi", description="Semantic ABI semantic change-control tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="compare baseline and candidate providers against one Semantic Contract")
    check.add_argument("contract")
    check.add_argument("--baseline", required=True, help="baseline oracle JSON config")
    check.add_argument("--candidate", required=True, help="candidate oracle JSON config")
    check.add_argument("--output", help="JSON change report")
    check.add_argument("--markdown", help="Markdown CI summary")
    check.add_argument("--summary-only", action="store_true")
    check.add_argument("--max-rows", type=int, default=20)
    check.add_argument("--min-candidate-score", type=float, default=0.0)
    check.add_argument("--max-score-drop", type=float, default=0.0)
    check.add_argument("--allow-soft-regressions", type=int, default=0)
    check.add_argument("--allow-new-missing", action="store_true")
    check.add_argument("--no-absolute-hard-pass", action="store_true")
    check.add_argument("--allow-existing-hard-failures", action="store_true")
    check.set_defaults(func=_check)

    forge = sub.add_parser("forge-safe", help="forge a contract with normative policy precedence")
    forge.add_argument("evidence")
    _add_acquisition_args(forge)
    forge.set_defaults(func=_forge_safe)

    otlp = sub.add_parser("forge-otlp", help="forge from raw OTLP/OpenInference traces plus explicit feedback")
    otlp.add_argument("traces")
    otlp.add_argument("--feedback", required=True)
    otlp.add_argument("--evidence", help="optional extra JSONL policies/judgments")
    otlp.add_argument("--query-secret-env")
    otlp.add_argument("--retain-query-text", action="store_true")
    otlp.add_argument("--no-reranker", action="store_true")
    _add_acquisition_args(otlp)
    otlp.set_defaults(func=_forge_otlp)

    review = sub.add_parser("apply-review", help="apply auditable review decisions to a parent contract")
    review.add_argument("--parent", required=True)
    review.add_argument("--bundle", required=True)
    review.add_argument("--decisions", required=True)
    review.add_argument("--version", required=True)
    review.add_argument("--output", required=True)
    review.add_argument("--report")
    review.add_argument("--allow-hard", action="store_true")
    review.add_argument("--quiet", action="store_true")
    review.set_defaults(func=_apply_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if values and values[0] not in _PRODUCT_COMMANDS:
        return int(legacy_cli.main(values))
    args = build_product_parser().parse_args(values)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
