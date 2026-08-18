from __future__ import annotations

"""Declarative product configuration for Semantic ABI provider oracles."""

import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib import parse as urllib_parse

from .providers import OpenSearchOracleV1, QdrantOracleV1, load_query_catalog
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


def _catalog(spec: Mapping[str, Any], base_dir: Path) -> dict[str, Any]:
    catalog_path = spec.get("query_catalog")
    if not catalog_path:
        return {}
    target = Path(str(catalog_path))
    if not target.is_absolute():
        target = base_dir / target
    return load_query_catalog(target)


def oracle_from_config(path: str | Path):
    """Instantiate a Protocol-v1 oracle from a JSON provider configuration.

    Supported kinds: ``remote``, ``qdrant`` and ``opensearch``. Secrets are referenced
    by environment-variable name rather than stored in the configuration file.
    """

    spec, base_dir = load_oracle_spec(path)
    kind = str(spec.get("kind", "")).lower()
    require_https = bool(spec.get("require_https", True))
    timeout = float(spec.get("timeout", 15.0))
    url = str(spec.get("url", ""))
    _validate_endpoint(url, require_https=require_https)

    if kind == "remote":
        return RemoteSemanticOracleV1.http(
            url,
            timeout=timeout,
            headers=_headers_from_spec(spec),
        )

    if kind == "qdrant":
        api_key = None
        if spec.get("api_key_env"):
            api_key = _required_env(str(spec["api_key_env"]))
        return QdrantOracleV1.http(
            url,
            collection=str(spec["collection"]),
            query_catalog=_catalog(spec, base_dir),
            api_key=api_key,
            vector_name=None if spec.get("vector_name") is None else str(spec["vector_name"]),
            timeout=timeout,
            require_https=require_https,
            implementation_id=None if spec.get("implementation_id") is None else str(spec["implementation_id"]),
            deterministic=bool(spec.get("deterministic", False)),
            state_digest=None if spec.get("state_digest") is None else str(spec["state_digest"]),
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
