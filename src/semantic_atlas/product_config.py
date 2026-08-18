from __future__ import annotations

"""Declarative product configuration for Semantic ABI provider oracles."""

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib import parse as urllib_parse

from .pgvector_provider import PgVectorOracleV1
from .providers import OpenSearchOracleV1, load_query_catalog
from .qdrant_provider import PortableQdrantOracleV1
from .remote_v1 import RemoteSemanticOracleV1


def _required_env(name: str) -> str:
    if not name:
        raise ValueError("environment variable name must be non-empty")
    value = os.environ.get(name)
    if value is None or value == "":
        raise ValueError(f"required environment variable is missing: {name}")
    return value


def _headers_from_spec(spec: Mapping[str, Any]) -> dict[str, str]:
    headers = {str(k): str(v) for k, v in dict(spec.get("headers", {})).items()}
    authorization_env = spec.get("authorization_env")
    if authorization_env:
        headers["Authorization"] = _required_env(str(authorization_env))
    headers_json_env = spec.get("headers_json_env")
    if headers_json_env:
        raw = _required_env(str(headers_json_env))
        parsed = json.loads(raw)
        if not isinstance(parsed, Mapping):
            raise ValueError("headers_json_env must contain a JSON object")
        headers.update({str(k): str(v) for k, v in parsed.items()})
    return headers


def _validate_endpoint(url: str, *, require_https: bool) -> None:
    parsed = urllib_parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("oracle url must be an absolute http(s) URL")
    if require_https and parsed.scheme != "https":
        host = (parsed.hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("HTTPS is required for non-local oracle endpoints")


def load_oracle_spec(path: str | Path) -> tuple[dict[str, Any], Path]:
    target = Path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("oracle configuration must be a JSON object")
    return dict(payload), target.parent


def _mapping_file(spec: Mapping[str, Any], key: str, base_dir: Path) -> dict[str, Any]:
    value = spec.get(key)
    if not value:
        return {}
    target = Path(str(value))
    if not target.is_absolute():
        target = base_dir / target
    return load_query_catalog(target)


def _catalog(spec: Mapping[str, Any], base_dir: Path) -> dict[str, Any]:
    return _mapping_file(spec, "query_catalog", base_dir)


def oracle_from_config(path: str | Path):
    """Instantiate a Protocol-v1 oracle from a JSON provider configuration.

    Supported kinds: ``remote``, ``qdrant``, ``opensearch`` and ``pgvector``. Secrets
    are referenced by environment-variable name rather than stored in the config file.
    """

    spec, base_dir = load_oracle_spec(path)
    kind = str(spec.get("kind", "")).lower()
    timeout = float(spec.get("timeout", 15.0))

    if kind == "pgvector":
        dsn_env = spec.get("dsn_env")
        if not dsn_env:
            raise ValueError("pgvector configuration requires dsn_env")
        return PgVectorOracleV1.psycopg(
            _required_env(str(dsn_env)),
            table=str(spec["table"]),
            id_column=str(spec.get("id_column", "id")),
            vector_column=str(spec.get("vector_column", "embedding")),
            query_catalog=_catalog(spec, base_dir),
            metric=str(spec.get("metric", "cosine")),
            implementation_id=None if spec.get("implementation_id") is None else str(spec["implementation_id"]),
            deterministic=bool(spec.get("deterministic", True)),
            state_digest=None if spec.get("state_digest") is None else str(spec["state_digest"]),
            connect_timeout=max(1, int(timeout)),
        )

    require_https = bool(spec.get("require_https", True))
    url = str(spec.get("url", ""))
    _validate_endpoint(url, require_https=require_https)

    if kind == "remote":
        return RemoteSemanticOracleV1.http(
            url,
            timeout=timeout,
            headers=_headers_from_spec(spec),
            require_https=require_https,
        )

    if kind == "qdrant":
        api_key = None
        if spec.get("api_key_env"):
            api_key = _required_env(str(spec["api_key_env"]))
        return PortableQdrantOracleV1.http(
            url,
            collection=str(spec["collection"]),
            query_catalog=_catalog(spec, base_dir),
            object_id_map=_mapping_file(spec, "object_id_map", base_dir),
            api_key=api_key,
            vector_name=None if spec.get("vector_name") is None else str(spec["vector_name"]),
            timeout=timeout,
            require_https=require_https,
            implementation_id=None if spec.get("implementation_id") is None else str(spec["implementation_id"]),
            deterministic=bool(spec.get("deterministic", False)),
            state_digest=None if spec.get("state_digest") is None else str(spec["state_digest"]),
            score_directionality=str(spec.get("score_directionality", "unknown")),
        )

    if kind == "opensearch":
        catalog = _catalog(spec, base_dir)
        if not catalog:
            raise ValueError("OpenSearch configuration requires query_catalog")
        return OpenSearchOracleV1.http(
            url,
            index=str(spec["index"]),
            query_catalog=catalog,
            headers=_headers_from_spec(spec),
            timeout=timeout,
            require_https=require_https,
            implementation_id=None if spec.get("implementation_id") is None else str(spec["implementation_id"]),
            deterministic=bool(spec.get("deterministic", False)),
            search_pipeline=None if spec.get("search_pipeline") is None else str(spec["search_pipeline"]),
            state_digest=None if spec.get("state_digest") is None else str(spec["state_digest"]),
        )

    raise ValueError(f"unsupported oracle configuration kind: {kind!r}")
