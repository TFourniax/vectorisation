from __future__ import annotations

"""Small zero-dependency CLI for Semantic ABI Protocol v1."""

import argparse
import json
from pathlib import Path
import sys

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
