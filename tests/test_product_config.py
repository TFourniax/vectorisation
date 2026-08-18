import json

import pytest

from semantic_atlas.product_config import oracle_from_config
from semantic_atlas.providers import OpenSearchOracleV1, QdrantOracleV1


def test_qdrant_config_resolves_relative_catalog_and_secret_env(tmp_path, monkeypatch):
    catalog = tmp_path / "queries.json"
    catalog.write_text(json.dumps({"q:1": [0.1, 0.2]}), encoding="utf-8")
    config = tmp_path / "qdrant.json"
    config.write_text(
        json.dumps(
            {
                "kind": "qdrant",
                "url": "http://localhost:6333",
                "collection": "docs",
                "query_catalog": "queries.json",
                "api_key_env": "QDRANT_TEST_KEY",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("QDRANT_TEST_KEY", "secret")

    oracle = oracle_from_config(config)

    assert isinstance(oracle, QdrantOracleV1)
    assert oracle.collection == "docs"
    assert oracle.query_catalog["q:1"] == [0.1, 0.2]


def test_config_fails_closed_when_declared_secret_is_missing(tmp_path):
    config = tmp_path / "qdrant.json"
    config.write_text(
        json.dumps(
            {
                "kind": "qdrant",
                "url": "http://localhost:6333",
                "collection": "docs",
                "api_key_env": "ABSENT_PROVIDER_SECRET",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ABSENT_PROVIDER_SECRET"):
        oracle_from_config(config)


def test_non_local_plain_http_is_rejected_by_default(tmp_path):
    config = tmp_path / "remote.json"
    config.write_text(
        json.dumps({"kind": "remote", "url": "http://example.com/oracle"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="HTTPS"):
        oracle_from_config(config)


def test_opensearch_config_requires_query_catalog(tmp_path):
    config = tmp_path / "opensearch.json"
    config.write_text(
        json.dumps(
            {
                "kind": "opensearch",
                "url": "http://localhost:9200",
                "index": "kb",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="query_catalog"):
        oracle_from_config(config)
