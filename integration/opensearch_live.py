from __future__ import annotations

import json
import time

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import audit_contract_v1
from semantic_atlas.providers import OpenSearchOracleV1, ProviderHttpTransport, text_query_catalog

BASE = "http://127.0.0.1:9200"
INDEX = "semantic-abi-integration"


def wait_ready(http: ProviderHttpTransport) -> None:
    error = None
    for _ in range(120):
        try:
            health = http.json("GET", "/_cluster/health", None)
            if health.get("status") in {"green", "yellow"}:
                return
        except Exception as exc:
            error = exc
        time.sleep(0.5)
    raise RuntimeError(f"OpenSearch did not become ready: {error}")


def main() -> None:
    http = ProviderHttpTransport(BASE, timeout=10.0)
    wait_ready(http)
    try:
        try:
            http.json("DELETE", f"/{INDEX}", None)
        except Exception:
            pass
        http.json(
            "PUT",
            f"/{INDEX}",
            {
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
            http.json("PUT", f"/{INDEX}/_doc/{object_id}", {"content": content})
        http.json("POST", f"/{INDEX}/_refresh", None)

        catalog = text_query_catalog(
            {"q:delete": "delete account GDPR data"},
            field="content",
        )
        oracle = OpenSearchOracleV1.http(
            BASE,
            index=INDEX,
            query_catalog=catalog,
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
            http.json("DELETE", f"/{INDEX}", None)
        except Exception:
            pass


if __name__ == "__main__":
    main()
