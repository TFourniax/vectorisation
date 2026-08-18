from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import audit_contract_v1
from semantic_atlas.providers import OpenSearchOracleV1, text_query_catalog

BASE = "https://127.0.0.1:9200"
INDEX = "semantic-abi-integration"
USER = "admin"
PASSWORD = os.environ.get("OPENSEARCH_INITIAL_ADMIN_PASSWORD", "")


def _curl(
    method: str,
    path: str,
    *,
    payload: Mapping[str, Any] | None = None,
    raw_body: bytes | None = None,
    content_type: str = "application/json",
) -> Mapping[str, Any]:
    if not PASSWORD:
        raise RuntimeError("OPENSEARCH_INITIAL_ADMIN_PASSWORD is required for live integration")
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--insecure",  # CI fixture uses the container's generated self-signed certificate.
        "--user",
        f"{USER}:{PASSWORD}",
        "--request",
        method.upper(),
        "--header",
        f"Content-Type: {content_type}",
        f"{BASE}{path}",
    ]
    data = raw_body
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if data is not None:
        command.extend(["--data-binary", "@-"])
    try:
        completed = subprocess.run(
            command,
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        body = exc.stdout.decode("utf-8", errors="replace")
        error = exc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenSearch request failed {method} {path}: {error} {body}") from exc
    value = json.loads(completed.stdout.decode("utf-8")) if completed.stdout else {}
    if not isinstance(value, Mapping):
        raise RuntimeError("OpenSearch returned a non-object JSON response")
    return value


def _json_transport(method: str, path: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return _curl(method, path, payload=payload)


def _msearch_transport(index: str, bodies: Sequence[Mapping[str, Any]]) -> Sequence[Mapping[str, Any]]:
    lines: list[str] = []
    for body in bodies:
        lines.append("{}")
        lines.append(json.dumps(body, separators=(",", ":")))
    raw = (("\n".join(lines) + "\n") if lines else "").encode("utf-8")
    response = _curl(
        "POST",
        f"/{quote(index, safe='')}/_msearch",
        raw_body=raw,
        content_type="application/x-ndjson",
    )
    rows = response.get("responses", ())
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise RuntimeError("OpenSearch _msearch omitted responses")
    return [row for row in rows if isinstance(row, Mapping)]


def wait_ready() -> None:
    error: Exception | None = None
    for _ in range(180):
        try:
            health = _curl("GET", "/_cluster/health")
            if health.get("status") in {"green", "yellow"}:
                return
        except Exception as exc:
            error = exc
        time.sleep(0.5)
    raise RuntimeError(f"OpenSearch did not become ready: {error}")


def main() -> None:
    wait_ready()
    try:
        try:
            _curl("DELETE", f"/{INDEX}")
        except Exception:
            pass
        _curl(
            "PUT",
            f"/{INDEX}",
            payload={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {"properties": {"content": {"type": "text"}}},
            },
        )
        documents = {
            "doc:delete": "Delete your account permanently. GDPR erasure procedure account deletion.",
            "doc:newsletter": "Unsubscribe from marketing newsletter emails and promotional messages.",
            "doc:related": "Account closure and personal data deletion help procedure.",
        }
        for object_id, content in documents.items():
            encoded_id = quote(object_id, safe="")
            _curl("PUT", f"/{INDEX}/_doc/{encoded_id}", payload={"content": content})
        _curl("POST", f"/{INDEX}/_refresh")

        catalog = text_query_catalog(
            {"q:delete": "delete account GDPR data"},
            field="content",
        )
        oracle = OpenSearchOracleV1(
            index=INDEX,
            query_catalog=catalog,
            json_transport=_json_transport,
            msearch_transport=_msearch_transport,
            deterministic=True,
            implementation_id="opensearch-live-bm25",
            state_digest="integration-fixture-v1",
        )
        contract = SemanticContract(
            name="opensearch-live",
            version="1",
            clauses=[
                TripletClause("q:delete", "doc:delete", "doc:newsletter", hard=True),
                NeighborClause(
                    "q:delete",
                    ("doc:delete", "doc:related"),
                    min_recall=1.0,
                    candidate_k=2,
                    hard=True,
                ),
            ],
        )
        result = audit_contract_v1(contract, oracle)
        assert result.report.hard_pass, result.to_dict()
        assert result.report.missing_clauses == 0, result.to_dict()
        assert len(result.report.clause_results) == 2
        assert all(row.passed for row in result.report.clause_results)
        print(
            json.dumps(
                {
                    "score": result.report.score,
                    "hard_pass": result.report.hard_pass,
                    "manifest": result.snapshot.manifest.to_dict(),
                },
                sort_keys=True,
            )
        )
    finally:
        try:
            _curl("DELETE", f"/{INDEX}")
        except Exception:
            pass


if __name__ == "__main__":
    main()
