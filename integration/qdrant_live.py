from __future__ import annotations

import json
import time

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import audit_contract_v1
from semantic_atlas.providers import ProviderHttpTransport
from semantic_atlas.qdrant_provider import PortableQdrantOracleV1

BASE = "http://127.0.0.1:6333"
COLLECTION = "semantic_abi_integration"


def wait_ready(http: ProviderHttpTransport) -> None:
    error = None
    for _ in range(60):
        try:
            http.json("GET", "/", None)
            return
        except Exception as exc:
            error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Qdrant did not become ready: {error}")


def main() -> None:
    http = ProviderHttpTransport(BASE, timeout=5.0)
    wait_ready(http)
    try:
        try:
            http.json("DELETE", f"/collections/{COLLECTION}", None)
        except Exception:
            pass
        http.json(
            "PUT",
            f"/collections/{COLLECTION}",
            {"vectors": {"size": 3, "distance": "Cosine"}},
        )
        http.json(
            "PUT",
            f"/collections/{COLLECTION}/points?wait=true",
            {
                "points": [
                    {"id": 101, "vector": [1.0, 0.0, 0.0]},
                    {"id": 102, "vector": [0.0, 1.0, 0.0]},
                    {"id": 103, "vector": [0.8, 0.2, 0.0]},
                ]
            },
        )
        oracle = PortableQdrantOracleV1.http(
            BASE,
            collection=COLLECTION,
            query_catalog={"q:delete": [1.0, 0.0, 0.0]},
            object_id_map={"doc:delete": 101, "doc:newsletter": 102, "doc:related": 103},
            deterministic=True,
            state_digest="integration-fixture-v1",
        )
        contract = SemanticContract(
            name="qdrant-live",
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
                TripletClause("doc:delete", "doc:related", "doc:newsletter", hard=True),
            ],
        )
        result = audit_contract_v1(contract, oracle)
        assert result.report.hard_pass, result.to_dict()
        assert result.report.missing_clauses == 0, result.to_dict()
        assert len(result.report.clause_results) == 3
        assert all(row.passed for row in result.report.clause_results)
        print(json.dumps({"score": result.report.score, "hard_pass": result.report.hard_pass, "manifest": result.snapshot.manifest.to_dict()}, sort_keys=True))
    finally:
        try:
            http.json("DELETE", f"/collections/{COLLECTION}", None)
        except Exception:
            pass


if __name__ == "__main__":
    main()
