from __future__ import annotations

import json
import time

import psycopg

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.pgvector_provider import PgVectorOracleV1
from semantic_atlas.protocol_v1 import audit_contract_v1

DSN = "postgresql://postgres:postgres@127.0.0.1:5432/postgres"


def connect_ready():
    error = None
    for _ in range(60):
        try:
            return psycopg.connect(DSN, autocommit=True)
        except Exception as exc:
            error = exc
            time.sleep(0.5)
    raise RuntimeError(f"PostgreSQL did not become ready: {error}")


def main() -> None:
    setup = connect_ready()
    try:
        setup.execute("CREATE EXTENSION IF NOT EXISTS vector")
        setup.execute("DROP TABLE IF EXISTS semantic_abi_documents")
        setup.execute("CREATE TABLE semantic_abi_documents (id text PRIMARY KEY, embedding vector(3) NOT NULL)")
        setup.execute(
            "INSERT INTO semantic_abi_documents (id, embedding) VALUES (%s, %s::vector), (%s, %s::vector), (%s, %s::vector)",
            (
                "doc:delete", "[1,0,0]",
                "doc:newsletter", "[0,1,0]",
                "doc:related", "[0.8,0.2,0]",
            ),
        )
        oracle = PgVectorOracleV1.psycopg(
            DSN,
            table="semantic_abi_documents",
            query_catalog={"q:delete": [1, 0, 0]},
            metric="cosine",
            deterministic=True,
            state_digest="integration-fixture-v1",
        )
        try:
            contract = SemanticContract(
                name="pgvector-live",
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
            oracle.close()
    finally:
        try:
            setup.execute("DROP TABLE IF EXISTS semantic_abi_documents")
        finally:
            setup.close()


if __name__ == "__main__":
    main()
