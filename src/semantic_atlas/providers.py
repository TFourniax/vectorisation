from __future__ import annotations

"""Production-provider adapters for Semantic ABI Oracle Protocol v1.

The Semantic Contract remains provider-independent.  A provider-local ``query_catalog``
materializes stable logical anchors into the native query representation required by a
backend (for example a dense vector for Qdrant or Query DSL for OpenSearch).  The
catalog is deliberately not embedded in the contract and may stay inside the customer's
security boundary.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .protocol_v1 import NeighborRequest, OracleManifest, ScorePair

JsonTransport = Callable[[str, str, Mapping[str, Any] | None], Mapping[str, Any]]
MSearchTransport = Callable[[str, Sequence[Mapping[str, Any]]], Sequence[Mapping[str, Any]]]


def load_query_catalog(path: str | Path) -> dict[str, Any]:
    """Load a provider-local JSON mapping from logical anchor ID to native query."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("query catalog must be a JSON object keyed by logical anchor ID")
    return {str(key): value for key, value in payload.items()}


def text_query_catalog(queries: Mapping[str, str], *, field: str) -> dict[str, Any]:
    """Build a basic OpenSearch ``match`` catalog from logical IDs and query text."""

    if not field or not isinstance(field, str):
        raise ValueError("field must be a non-empty string")
    return {str(key): {"match": {field: str(value)}} for key, value in queries.items()}


class ProviderHttpError(RuntimeError):
    pass


class ProviderHttpTransport:
    """Small bounded stdlib HTTP client used by provider adapters.

    It intentionally has no retry loop: Semantic ABI release checks should surface a
    provider failure rather than silently multiplying expensive retrieval requests.
    Retries, circuit breaking and service-level policy belong at the orchestration
    layer where idempotency and budgets are known.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        headers: Mapping[str, str] | None = None,
        max_response_bytes: int = 32 * 1024 * 1024,
        require_https: bool = False,
    ) -> None:
        parsed = urllib_parse.urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("provider base_url must be an absolute http(s) URL")
        if require_https and parsed.scheme != "https":
            host = (parsed.hostname or "").lower()
            if host not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("HTTPS is required for non-local provider endpoints")
        self.base_url = base_url.rstrip("/")
        self.timeout = max(0.1, float(timeout))
        self.headers = {"Accept": "application/json", **dict(headers or {})}
        self.max_response_bytes = max(1024, int(max_response_bytes))

    def _request(self, method: str, path: str, data: bytes | None, content_type: str) -> Mapping[str, Any]:
        headers = {"Content-Type": content_type, **self.headers}
        req = urllib_request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                length = response.headers.get("Content-Length")
                if length is not None and int(length) > self.max_response_bytes:
                    raise ProviderHttpError("provider response exceeds configured size limit")
                raw = response.read(self.max_response_bytes + 1)
        except Exception as exc:  # urllib exposes several transport-specific exception types
            if isinstance(exc, ProviderHttpError):
                raise
            raise ProviderHttpError(f"provider request failed: {method.upper()} {path}: {exc}") from exc
        if len(raw) > self.max_response_bytes:
            raise ProviderHttpError("provider response exceeds configured size limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ProviderHttpError("provider returned invalid JSON") from exc
        if not isinstance(value, Mapping):
            raise ProviderHttpError("provider response must be a JSON object")
        return value

    def json(self, method: str, path: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return self._request(method, path, data, "application/json")

    def msearch(self, path: str, bodies: Sequence[Mapping[str, Any]]) -> Sequence[Mapping[str, Any]]:
        chunks: list[str] = []
        for body in bodies:
            chunks.append("{}")
            chunks.append(json.dumps(body, separators=(",", ":")))
        data = (("\n".join(chunks) + "\n") if chunks else "").encode("utf-8")
        response = self._request("POST", path, data, "application/x-ndjson")
        rows = response.get("responses", ())
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            raise ProviderHttpError("OpenSearch _msearch response omitted responses array")
        return [row for row in rows if isinstance(row, Mapping)]


def _point_id(value: str) -> str | int:
    text = str(value)
    if text.isdigit() and (text == "0" or not text.startswith("0")):
        try:
            return int(text)
        except ValueError:
            pass
    return text


def _id_text(value: Any) -> str:
    return str(value)


class QdrantOracleV1:
    """Semantic ABI adapter for Qdrant Query API.

    External query anchors are resolved through ``query_catalog``.  Anchors not present
    in the catalog are treated as Qdrant point IDs, which also supports document-to-
    document semantic contracts.
    """

    def __init__(
        self,
        *,
        collection: str,
        query_catalog: Mapping[str, Any] | None = None,
        transport: JsonTransport,
        vector_name: str | None = None,
        implementation_id: str | None = None,
        deterministic: bool = False,
        state_digest: str | None = None,
    ) -> None:
        if not collection:
            raise ValueError("Qdrant collection is required")
        self.collection = str(collection)
        self.query_catalog = {str(key): value for key, value in dict(query_catalog or {}).items()}
        self.transport = transport
        self.vector_name = vector_name
        metadata: dict[str, Any] = {
            "provider": "qdrant",
            "collection": self.collection,
            "query_catalog_anchors": len(self.query_catalog),
        }
        if vector_name:
            metadata["vector_name"] = vector_name
        if state_digest:
            metadata["state_digest"] = str(state_digest)
        self.manifest = OracleManifest(
            implementation_id=implementation_id or f"qdrant:{self.collection}",
            implementation_kind="qdrant",
            score_semantics="qdrant-query-score",
            score_directionality="symmetric",
            deterministic=bool(deterministic),
            metadata=metadata,
        )

    @classmethod
    def http(
        cls,
        base_url: str,
        *,
        collection: str,
        query_catalog: Mapping[str, Any] | None = None,
        api_key: str | None = None,
        vector_name: str | None = None,
        timeout: float = 15.0,
        require_https: bool = False,
        implementation_id: str | None = None,
        deterministic: bool = False,
        state_digest: str | None = None,
    ) -> "QdrantOracleV1":
        headers = {} if api_key is None else {"api-key": str(api_key)}
        http = ProviderHttpTransport(
            base_url,
            timeout=timeout,
            headers=headers,
            require_https=require_https,
        )
        return cls(
            collection=collection,
            query_catalog=query_catalog,
            transport=http.json,
            vector_name=vector_name,
            implementation_id=implementation_id,
            deterministic=deterministic,
            state_digest=state_digest,
        )

    @property
    def _base(self) -> str:
        return f"/collections/{urllib_parse.quote(self.collection, safe='')}/points"

    def _query(self, anchor: str) -> Any:
        if anchor in self.query_catalog:
            return self.query_catalog[anchor]
        return _point_id(anchor)

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(value) for value in object_ids]
        result = {value: True for value in ids if value in self.query_catalog}
        backend_ids = [value for value in ids if value not in self.query_catalog]
        if backend_ids:
            response = self.transport(
                "POST",
                self._base,
                {"ids": [_point_id(value) for value in backend_ids], "with_payload": False, "with_vector": False},
            )
            rows = response.get("result", ())
            found = {
                _id_text(row.get("id"))
                for row in rows
                if isinstance(row, Mapping) and row.get("id") is not None
            }
            result.update({value: value in found for value in backend_ids})
        return {value: bool(result.get(value, False)) for value in ids}

    def _search_body(self, *, anchor: str, limit: int, candidate: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": self._query(anchor),
            "limit": max(1, int(limit)),
            "with_payload": False,
            "with_vector": False,
        }
        if self.vector_name:
            body["using"] = self.vector_name
        if candidate is not None:
            body["filter"] = {"must": [{"has_id": [_point_id(candidate)]}]}
        return body

    def _batch(self, searches: Sequence[Mapping[str, Any]]) -> Sequence[Mapping[str, Any]]:
        if not searches:
            return []
        response = self.transport("POST", f"{self._base}/query/batch", {"searches": list(searches)})
        rows = response.get("result", ())
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
            raise ValueError("Qdrant batch query response omitted result array")
        if len(rows) != len(searches):
            raise ValueError("Qdrant batch query response length does not match request")
        return [row if isinstance(row, Mapping) else {} for row in rows]

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        rows = self._batch(
            [self._search_body(anchor=pair.anchor, candidate=pair.candidate, limit=1) for pair in pairs]
        )
        output: dict[ScorePair, float] = {}
        for pair, row in zip(pairs, rows):
            points = row.get("points", ())
            if not points:
                raise ValueError(f"Qdrant returned no score for candidate {pair.candidate!r}")
            score = float(points[0]["score"])
            if not math.isfinite(score):
                raise ValueError("Qdrant returned a non-finite score")
            output[pair] = score
        return output

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        searches = []
        for req in requests:
            external = req.anchor in self.query_catalog
            searches.append(self._search_body(anchor=req.anchor, limit=req.k if external else req.k + 1))
        rows = self._batch(searches)
        output: dict[NeighborRequest, Sequence[str]] = {}
        for req, row in zip(requests, rows):
            values = []
            for point in row.get("points", ()):
                if not isinstance(point, Mapping) or point.get("id") is None:
                    continue
                value = _id_text(point["id"])
                if req.anchor not in self.query_catalog and value == req.anchor:
                    continue
                values.append(value)
                if len(values) >= req.k:
                    break
            output[req] = tuple(values)
        return output


class OpenSearchOracleV1:
    """Semantic ABI adapter for OpenSearch Query DSL and ``_msearch``.

    Every semantic anchor must have a provider-local Query DSL clause in
    ``query_catalog``.  This supports BM25, neural, hybrid and other OpenSearch query
    forms without changing the contract.
    """

    def __init__(
        self,
        *,
        index: str,
        query_catalog: Mapping[str, Mapping[str, Any]],
        json_transport: JsonTransport,
        msearch_transport: MSearchTransport,
        implementation_id: str | None = None,
        deterministic: bool = False,
        search_pipeline: str | None = None,
        state_digest: str | None = None,
    ) -> None:
        if not index:
            raise ValueError("OpenSearch index is required")
        if not query_catalog:
            raise ValueError("OpenSearch adapter requires a non-empty query_catalog")
        self.index = str(index)
        self.query_catalog = {str(key): dict(value) for key, value in query_catalog.items()}
        self.json_transport = json_transport
        self.msearch_transport = msearch_transport
        self.search_pipeline = search_pipeline
        metadata: dict[str, Any] = {
            "provider": "opensearch",
            "index": self.index,
            "query_catalog_anchors": len(self.query_catalog),
        }
        if search_pipeline:
            metadata["search_pipeline"] = search_pipeline
        if state_digest:
            metadata["state_digest"] = str(state_digest)
        self.manifest = OracleManifest(
            implementation_id=implementation_id or f"opensearch:{self.index}",
            implementation_kind="opensearch",
            score_semantics="opensearch-_score",
            score_directionality="asymmetric",
            deterministic=bool(deterministic),
            metadata=metadata,
        )

    @classmethod
    def http(
        cls,
        base_url: str,
        *,
        index: str,
        query_catalog: Mapping[str, Mapping[str, Any]],
        headers: Mapping[str, str] | None = None,
        timeout: float = 15.0,
        require_https: bool = False,
        implementation_id: str | None = None,
        deterministic: bool = False,
        search_pipeline: str | None = None,
        state_digest: str | None = None,
    ) -> "OpenSearchOracleV1":
        http = ProviderHttpTransport(
            base_url,
            timeout=timeout,
            headers=headers,
            require_https=require_https,
        )
        index_path = urllib_parse.quote(index, safe="")
        suffix = ""
        if search_pipeline:
            suffix = "?search_pipeline=" + urllib_parse.quote(str(search_pipeline), safe="")
        return cls(
            index=index,
            query_catalog=query_catalog,
            json_transport=http.json,
            msearch_transport=lambda _index, bodies: http.msearch(f"/{index_path}/_msearch{suffix}", bodies),
            implementation_id=implementation_id,
            deterministic=deterministic,
            search_pipeline=search_pipeline,
            state_digest=state_digest,
        )

    @property
    def _index_path(self) -> str:
        return urllib_parse.quote(self.index, safe="")

    def _query(self, anchor: str) -> Mapping[str, Any]:
        if anchor not in self.query_catalog:
            raise KeyError(
                f"OpenSearch logical anchor {anchor!r} is absent from the provider-local query catalog"
            )
        return self.query_catalog[anchor]

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(value) for value in object_ids]
        output = {value: True for value in ids if value in self.query_catalog}
        document_ids = [value for value in ids if value not in self.query_catalog]
        if document_ids:
            response = self.json_transport(
                "POST",
                f"/{self._index_path}/_mget",
                {"ids": document_ids, "_source": False},
            )
            found = {
                str(row.get("_id"))
                for row in response.get("docs", ())
                if isinstance(row, Mapping) and bool(row.get("found")) and row.get("_id") is not None
            }
            output.update({value: value in found for value in document_ids})
        return {value: bool(output.get(value, False)) for value in ids}

    def _filtered_query(self, anchor: str, candidate: str) -> Mapping[str, Any]:
        return {
            "bool": {
                "must": [self._query(anchor)],
                "filter": [{"ids": {"values": [candidate]}}],
            }
        }

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        bodies = [
            {"size": 1, "_source": False, "track_scores": True, "query": self._filtered_query(pair.anchor, pair.candidate)}
            for pair in pairs
        ]
        responses = list(self.msearch_transport(self.index, bodies)) if bodies else []
        if len(responses) != len(bodies):
            raise ValueError("OpenSearch _msearch response length does not match score request")
        output: dict[ScorePair, float] = {}
        for pair, response in zip(pairs, responses):
            hits = response.get("hits", {}).get("hits", ()) if isinstance(response.get("hits"), Mapping) else ()
            if not hits:
                raise ValueError(f"OpenSearch returned no score for candidate {pair.candidate!r}")
            score = float(hits[0]["_score"])
            if not math.isfinite(score):
                raise ValueError("OpenSearch returned a non-finite _score")
            output[pair] = score
        return output

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        bodies = [
            {"size": req.k, "_source": False, "track_scores": True, "query": self._query(req.anchor)}
            for req in requests
        ]
        responses = list(self.msearch_transport(self.index, bodies)) if bodies else []
        if len(responses) != len(bodies):
            raise ValueError("OpenSearch _msearch response length does not match neighbor request")
        output: dict[NeighborRequest, Sequence[str]] = {}
        for req, response in zip(requests, responses):
            hit_root = response.get("hits", {})
            hits = hit_root.get("hits", ()) if isinstance(hit_root, Mapping) else ()
            output[req] = tuple(
                str(hit.get("_id"))
                for hit in hits
                if isinstance(hit, Mapping) and hit.get("_id") is not None
            )[: req.k]
        return output
