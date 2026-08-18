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
from .attestation_v1 import SemanticProtocolAttestation, make_protocol_attestation
from .certification_io import (
    assess_adequacy_spec,
    calibrate_risk_from_jsonl,
    load_adequacy_report,
    load_risk_certificate,
    risk_certificate_digest,
    save_adequacy_report,
    save_risk_certificate,
)
from .change_control import ReleasePolicy, compare_protocol_audits
from .conformance import check_oracle_conformance
from .contracts import MutualNeighborClause, SemanticContract
from .otlp import load_otlp_jsonl
from .policy_forge import forge_contract_with_policies
from .product_config import oracle_from_config
from .protocol_v1 import ScorePair, audit_contract_v1
from .release_control import evaluate_production_release
from .review import ReviewBundle, apply_review_decisions, build_review_bundle, load_review_decisions_jsonl
from .telemetry import join_feedback, load_feedback_jsonl

_PRODUCT_COMMANDS = {
    "check",
    "release",
    "assess-adequacy",
    "calibrate-risk",
    "attest",
    "forge-safe",
    "forge-otlp",
    "apply-review",
}


def _write_json(value, path: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _close_oracle(oracle) -> None:
    close = getattr(oracle, "close", None)
    if callable(close):
        close()


def _release_policy(args: argparse.Namespace) -> ReleasePolicy:
    return ReleasePolicy(
        min_candidate_score=args.min_candidate_score,
        max_score_drop=args.max_score_drop,
        allow_soft_regressions=args.allow_soft_regressions,
        require_no_new_missing=not args.allow_new_missing,
        require_absolute_hard_pass=not args.no_absolute_hard_pass,
        allow_existing_hard_failures=args.allow_existing_hard_failures,
    )


def _add_release_policy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--min-candidate-score", type=float, default=0.0)
    parser.add_argument("--max-score-drop", type=float, default=0.0)
    parser.add_argument("--allow-soft-regressions", type=int, default=0)
    parser.add_argument("--allow-new-missing", action="store_true")
    parser.add_argument("--no-absolute-hard-pass", action="store_true")
    parser.add_argument("--allow-existing-hard-failures", action="store_true")


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
    try:
        baseline = audit_contract_v1(contract, baseline_oracle)
        candidate = audit_contract_v1(contract, candidate_oracle)
        report = compare_protocol_audits(contract, baseline, candidate, policy=_release_policy(args))
    finally:
        _close_oracle(baseline_oracle)
        if candidate_oracle is not baseline_oracle:
            _close_oracle(candidate_oracle)
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


def _release(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    attestation = SemanticProtocolAttestation.load(args.attestation)
    baseline_oracle = oracle_from_config(args.baseline)
    candidate_oracle = oracle_from_config(args.candidate)
    try:
        baseline = audit_contract_v1(contract, baseline_oracle)
        candidate = audit_contract_v1(contract, candidate_oracle)
        report = evaluate_production_release(
            contract,
            baseline,
            candidate,
            attestation=attestation,
            change_policy=_release_policy(args),
            require_certified_attestation=True,
        )
    finally:
        _close_oracle(baseline_oracle)
        if candidate_oracle is not baseline_oracle:
            _close_oracle(candidate_oracle)
    payload = report.to_dict(include_clauses=not args.summary_only)
    if args.output:
        _write_json(payload, args.output)
    elif not args.markdown:
        _write_json(payload, None)
    if args.markdown:
        target = Path(args.markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report.to_markdown(max_rows=args.max_rows), encoding="utf-8")
    return 0 if report.deployment_eligible else 5


def _assess_adequacy(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    report = assess_adequacy_spec(args.spec, contract_digest=contract.digest)
    save_adequacy_report(report, args.output)
    if not args.quiet:
        _write_json({"report": report.to_dict(), "report_digest": report.digest}, None)
    return 0 if report.adequate else 7


def _calibrate_risk(args: argparse.Namespace) -> int:
    certificate = calibrate_risk_from_jsonl(
        args.events,
        target_risk=args.target_risk,
        delta=args.delta,
        selection_fraction=args.selection_fraction,
        threshold_candidates=args.threshold_candidates,
        min_selection=args.min_selection,
        min_certification=args.min_certification,
        seed=args.seed,
    )
    save_risk_certificate(certificate, args.output)
    if not args.quiet:
        _write_json(
            {"certificate": {**certificate.__dict__} if hasattr(certificate, "__dict__") else {
                "target_risk": certificate.target_risk,
                "delta": certificate.delta,
                "threshold": certificate.threshold,
                "empirical_risk": certificate.empirical_risk,
                "upper_risk_bound": certificate.upper_risk_bound,
                "accepted_calibration": certificate.accepted_calibration,
                "certification_size": certificate.certification_size,
                "total_events": certificate.total_events,
                "estimated_coverage": certificate.estimated_coverage,
                "candidate_count": certificate.candidate_count,
                "certified": certificate.certified,
                "method": certificate.method,
                "reason": certificate.reason,
            }, "certificate_digest": risk_certificate_digest(certificate)},
            None,
        )
    return 0 if certificate.certified else 8


def _contract_anchors(contract: SemanticContract) -> tuple[str, ...]:
    values: list[str] = []
    for clause in contract.clauses:
        objects = tuple(clause.objects)
        if objects:
            values.append(str(objects[0]))
        if isinstance(clause, MutualNeighborClause) and len(objects) > 1:
            values.append(str(objects[1]))
    return tuple(dict.fromkeys(values))


def _contract_score_pairs(contract: SemanticContract) -> tuple[ScorePair, ...]:
    pairs: list[ScorePair] = []
    for clause in contract.clauses:
        if clause.kind == "triplet":
            pairs.append(ScorePair(str(clause.anchor), str(clause.positive)))
            pairs.append(ScorePair(str(clause.anchor), str(clause.negative)))
    return tuple(dict.fromkeys(pairs))


def _attest(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    adequacy = load_adequacy_report(args.adequacy, contract_digest=contract.digest)
    risk = load_risk_certificate(args.risk_certificate)
    oracle = oracle_from_config(args.oracle)
    try:
        audit = audit_contract_v1(contract, oracle)
        anchors = _contract_anchors(contract)
        if not anchors:
            raise ValueError("cannot attest an empty contract without conformance anchors")
        conformance = check_oracle_conformance(
            oracle,
            anchors=anchors,
            k_values=tuple(int(x) for x in args.k.split(",") if x.strip()),
            score_pairs=_contract_score_pairs(contract) if args.check_score_pairs else (),
        )
        certifiable = bool(
            conformance.passed
            and audit.report.hard_pass
            and audit.report.missing_clauses == 0
            and adequacy.adequate
            and risk.certified
        )
        attestation = make_protocol_attestation(
            audit,
            conformance,
            adequacy=adequacy,
            risk_certificate_digest=risk_certificate_digest(risk),
            risk_certified=risk.certified,
            status="certified" if certifiable else "blocked",
            metadata={"created_by": "semantic-abi attest"},
        )
        attestation.save(args.output)
    finally:
        _close_oracle(oracle)
    summary = {
        "attestation_digest": attestation.digest,
        "status": attestation.status,
        "deployment_eligible": attestation.deployment_eligible,
        "conformance_passed": attestation.conformance_passed,
        "adequacy_status": attestation.adequacy_status,
        "risk_certified": attestation.risk_certified,
        "hard_pass": attestation.hard_pass,
        "missing_clauses": attestation.missing_clauses,
    }
    if args.report:
        _write_json(summary, args.report)
    if not args.quiet:
        _write_json(summary, None)
    return 0 if attestation.deployment_eligible else 6


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

    check = sub.add_parser("check", help="preflight diff: compare baseline and candidate against one Semantic Contract")
    check.add_argument("contract")
    check.add_argument("--baseline", required=True, help="baseline oracle JSON config")
    check.add_argument("--candidate", required=True, help="candidate oracle JSON config")
    check.add_argument("--output", help="JSON change report")
    check.add_argument("--markdown", help="Markdown CI summary")
    check.add_argument("--summary-only", action="store_true")
    check.add_argument("--max-rows", type=int, default=20)
    _add_release_policy_args(check)
    check.set_defaults(func=_check)

    release = sub.add_parser("release", help="strict production gate: semantic diff plus certified attestation")
    release.add_argument("contract")
    release.add_argument("--baseline", required=True)
    release.add_argument("--candidate", required=True)
    release.add_argument("--attestation", required=True)
    release.add_argument("--output")
    release.add_argument("--markdown")
    release.add_argument("--summary-only", action="store_true")
    release.add_argument("--max-rows", type=int, default=20)
    _add_release_policy_args(release)
    release.set_defaults(func=_release)

    adequacy = sub.add_parser("assess-adequacy", help="recompute contract adequacy from declared evidence requirements")
    adequacy.add_argument("contract")
    adequacy.add_argument("--spec", required=True)
    adequacy.add_argument("--output", required=True)
    adequacy.add_argument("--quiet", action="store_true")
    adequacy.set_defaults(func=_assess_adequacy)

    risk = sub.add_parser("calibrate-risk", help="calibrate a held-out semantic rollout risk certificate")
    risk.add_argument("events")
    risk.add_argument("--output", required=True)
    risk.add_argument("--target-risk", type=float, default=0.10)
    risk.add_argument("--delta", type=float, default=0.05)
    risk.add_argument("--selection-fraction", type=float, default=0.5)
    risk.add_argument("--threshold-candidates", type=int, default=12)
    risk.add_argument("--min-selection", type=int, default=20)
    risk.add_argument("--min-certification", type=int, default=30)
    risk.add_argument("--seed", type=int, default=17)
    risk.add_argument("--quiet", action="store_true")
    risk.set_defaults(func=_calibrate_risk)

    attest = sub.add_parser("attest", help="create a candidate attestation from audit, conformance, adequacy and risk evidence")
    attest.add_argument("contract")
    attest.add_argument("--oracle", required=True)
    attest.add_argument("--adequacy", required=True)
    attest.add_argument("--risk-certificate", required=True)
    attest.add_argument("--output", required=True)
    attest.add_argument("--report")
    attest.add_argument("--k", default="1,3,5")
    attest.add_argument("--check-score-pairs", action="store_true")
    attest.add_argument("--quiet", action="store_true")
    attest.set_defaults(func=_attest)

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
