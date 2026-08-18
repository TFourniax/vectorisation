import json

import pytest

from semantic_atlas.product_config import oracle_from_config


def test_pgvector_config_reads_dsn_from_environment_and_relative_catalog(tmp_path, monkeypatch):
    catalog = tmp_path / "queries.json"
    catalog.write_text(json.dumps({"q:1": [1, 0, 0]}), encoding="utf-8")
    config = tmp_path / "pgvector.json"
    config.write_text(
        json.dumps(
            {
                "kind": "pgvector",
                "dsn_env": "SEMANTIC_ABI_PG_DSN",
                "table": "documents",
                "query_catalog": "queries.json",
                "metric": "cosine",
                "timeout": 7,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SEMANTIC_ABI_PG_DSN", "postgresql://example.invalid/db")
    captured = {}

    def fake_psycopg(dsn, **kwargs):
        captured["dsn"] = dsn
        captured.update(kwargs)
        return "oracle"

    monkeypatch.setattr("semantic_atlas.product_config.PgVectorOracleV1.psycopg", fake_psycopg)

    assert oracle_from_config(config) == "oracle"
    assert captured["dsn"] == "postgresql://example.invalid/db"
    assert captured["table"] == "documents"
    assert captured["query_catalog"] == {"q:1": [1, 0, 0]}
    assert captured["connect_timeout"] == 7


def test_pgvector_config_requires_dsn_environment_variable(tmp_path):
    config = tmp_path / "pgvector.json"
    config.write_text(
        json.dumps({"kind": "pgvector", "dsn_env": "ABSENT_PG_DSN", "table": "documents"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ABSENT_PG_DSN"):
        oracle_from_config(config)
