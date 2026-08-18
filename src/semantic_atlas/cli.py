from __future__ import annotations

"""Small zero-dependency CLI for Semantic ABI Protocol v1."""

import argparse
import json
from pathlib import Path
import sys

from .acquisition import AcquisitionPolicy, forge_contract, load_evidence_jsonl, save_review_queue
from .conformance import check_oracle_conformance
from .contracts import SemanticContract
from .protocol_v1 import audit_contract_v1, compile_contract
from .remote_v1 import RemoteSemanticOracleV1


def _write(value: dict, output: str | None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def _plan(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    plan = compile_contract(contract)
    _write({**plan.to_dict(), "plan_digest": plan.digest}, args.output)
    return 0


def _forge(args: argparse.Namespace) -> int:
    evidence = load_evidence_jsonl(args.evidence)
    parent_digest = SemanticContract.load(args.parent).digest if args.parent else None
    policy = AcquisitionPolicy(
        auto_promote_confidence=args.auto_promote_confidence,
        review_confidence=args.review_confidence,
        min_effective_support=args.min_effective_support,
        hard_confidence=args.hard_confidence,
        hard_min_criticality=args.hard_min_criticality,
        opposition_ratio_review=args.opposition_ratio_review,
        max_review_items=args.max_review_items,
    )
    result = forge_contract(
        evidence,
        name=args.name,
        version=args.version,
        parent_digest=parent_digest,
        policy=policy,
        estimated_seconds_per_review=args.seconds_per_review,
    )
    result.contract.save(args.output)
    if args.report:
        _write(result.report.to_dict(), args.report)
    if args.review:
        save_review_queue(result.review_queue, args.review)
    if not args.quiet:
        _write(result.report.to_dict(), None)
    return 0


def _remote_audit(args: argparse.Namespace) -> int:
    contract = SemanticContract.load(args.contract)
    oracle = RemoteSemanticOracleV1.http(args.url, timeout=args.timeout)
    result = audit_contract_v1(contract, oracle)
    payload = result.to_dict()
    if args.include_snapshot:
        payload["snapshot"] = result.snapshot.to_dict()
    _write(payload, args.output)
    return 0 if result.report.hard_pass and result.report.missing_clauses == 0 else 2


def _remote_conformance(args: argparse.Namespace) -> int:
    oracle = RemoteSemanticOracleV1.http(args.url, timeout=args.timeout)
    anchors = tuple(x.strip() for x in args.anchors.split(",") if x.strip())
    if not anchors:
        raise SystemExit("--anchors must contain at least one logical object ID")
    ks = tuple(int(x.strip()) for x in args.k.split(",") if x.strip())
    report = check_oracle_conformance(oracle, anchors=anchors, k_values=ks)
    _write(report.to_dict(), args.output)
    return 0 if report.passed else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="semantic-abi", description="Semantic ABI Protocol v1 tooling")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="compile a Semantic Contract into a canonical batch execution plan")
    plan.add_argument("contract")
    plan.add_argument("--output")
    plan.set_defaults(func=_plan)

    forge = sub.add_parser("forge", help="infer a reviewable Semantic Contract from JSONL evidence")
    forge.add_argument("evidence", help="JSONL preferences, relevant sets, policies and/or production traces")
    forge.add_argument("--name", default="application-semantics")
    forge.add_argument("--version", default="1")
    forge.add_argument("--parent", help="optional parent contract whose digest is linked as lineage")
    forge.add_argument("--output", required=True, help="path for the auto-promoted Semantic Contract")
    forge.add_argument("--report", help="optional acquisition report JSON")
    forge.add_argument("--review", help="optional JSONL review queue")
    forge.add_argument("--auto-promote-confidence", type=float, default=0.85)
    forge.add_argument("--review-confidence", type=float, default=0.60)
    forge.add_argument("--min-effective-support", type=float, default=0.80)
    forge.add_argument("--hard-confidence", type=float, default=0.98)
    forge.add_argument("--hard-min-criticality", type=float, default=0.80)
    forge.add_argument("--opposition-ratio-review", type=float, default=0.20)
    forge.add_argument("--max-review-items", type=int, default=200)
    forge.add_argument("--seconds-per-review", type=float, default=20.0)
    forge.add_argument("--quiet", action="store_true")
    forge.set_defaults(func=_forge)

    audit = sub.add_parser("remote-audit", help="audit a contract against a protocol-v1 HTTP oracle")
    audit.add_argument("url")
    audit.add_argument("contract")
    audit.add_argument("--timeout", type=float, default=10.0)
    audit.add_argument("--include-snapshot", action="store_true")
    audit.add_argument("--output")
    audit.set_defaults(func=_remote_audit)

    conformance = sub.add_parser("remote-conformance", help="run protocol conformance checks against remote anchors")
    conformance.add_argument("url")
    conformance.add_argument("--anchors", required=True, help="comma-separated stable logical IDs")
    conformance.add_argument("--k", default="1,5,10", help="comma-separated top-k values")
    conformance.add_argument("--timeout", type=float, default=10.0)
    conformance.add_argument("--output")
    conformance.set_defaults(func=_remote_conformance)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
