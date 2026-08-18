from __future__ import annotations

"""Wire transport for Semantic ABI Oracle Protocol v1.

The protocol is framework-neutral. ``dispatch_protocol_request`` can sit behind
FastAPI, Flask, gRPC gateways, serverless functions, Unix-socket bridges, or an
in-process test transport. ``RemoteSemanticOracleV1`` uses a caller-supplied
transport; ``HttpJsonTransport`` is a bounded zero-dependency reference client.
"""

import json
import math
from typing import Any, Callable, Mapping, Sequence
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from .protocol_v1 import BatchSemanticOracleV1, NeighborRequest, OracleManifest, ScorePair

ProtocolTransport = Callable[[str, str, Mapping[str, Any] | None], Mapping[str, Any]]


class ProtocolTransportError(RuntimeError):
    pass


def _rows(payload: Mapping[str, Any], key: str, *, max_items: int) -> Sequence[Any]:
    value = payload.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"protocol field {key!r} must be an array")
    if len(value) > max_items:
        raise ValueError(f"protocol field {key!r} exceeds batch limit {max_items}")
    return value


def dispatch_protocol_request(
    oracle: BatchSemanticOracleV1,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None,
    *,
    max_batch_items: int = 100_000,
    max_neighbor_k: int = 10_000,
    max_logical_id_length: int = 4096,
) -> dict[str, Any]:
    """Reference wire dispatcher with explicit resource limits.

    Web frameworks should still apply their own request-body, authentication and rate
    limits. These checks protect the protocol adapter from accidental or hostile fanout
    after a JSON body has already been accepted by the HTTP layer.
    """

    method = method.upper()
    payload = dict(payload or {})
    batch_limit = max(1, int(max_batch_items))
    k_limit = max(1, int(max_neighbor_k))
    id_limit = max(1, int(max_logical_id_length))

    def logical_id(value: Any) -> str:
        text = str(value)
        if not text or len(text) > id_limit:
            raise ValueError("logical object ID is empty or exceeds configured length limit")
        return text

    if method == "GET" and path == "/v1/manifest":
        return oracle.manifest.to_dict()
    if method == "POST" and path == "/v1/contains":
        ids = [logical_id(x) for x in _rows(payload, "object_ids", max_items=batch_limit)]
        result = oracle.contains_many(ids)
        return {"contains": {object_id: bool(result.get(object_id, False)) for object_id in ids}}
    if method == "POST" and path == "/v1/score":
        pairs = [
            ScorePair(logical_id(row["anchor"]), logical_id(row["candidate"]))
            for row in _rows(payload, "pairs", max_items=batch_limit)
            if isinstance(row, Mapping)
        ]
        if len(pairs) != len(_rows(payload, "pairs", max_items=batch_limit)):
            raise ValueError("every score pair must be a JSON object")
        result = oracle.score_many(pairs)
        return {"scores": [{**pair.to_dict(), "score": float(result[pair])} for pair in pairs]}
    if method == "POST" and path == "/v1/neighbors":
        raw_requests = _rows(payload, "requests", max_items=batch_limit)
        requests: list[NeighborRequest] = []
        for row in raw_requests:
            if not isinstance(row, Mapping):
                raise ValueError("every neighbor request must be a JSON object")
            k = int(row["k"])
            if k <= 0 or k > k_limit:
                raise ValueError(f"neighbor k must be within [1, {k_limit}]")
            requests.append(NeighborRequest(logical_id(row["anchor"]), k))
        result = oracle.neighbors_many(requests)
        return {"results": [{**req.to_dict(), "neighbors": list(result[req])[: req.k]} for req in requests]}
    raise KeyError(f"unsupported protocol route: {method} {path}")


class InProcessProtocolTransport:
    def __init__(self, oracle: BatchSemanticOracleV1) -> None:
        self.oracle = oracle
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, path: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
        self.calls.append((method.upper(), path))
        return dispatch_protocol_request(self.oracle, method, path, payload)


class HttpJsonTransport:
    """Bounded JSON-over-HTTP reference transport using the Python stdlib."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        max_response_bytes: int = 32 * 1024 * 1024,
        require_https: bool = False,
    ) -> None:
        parsed = urllib_parse.urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Semantic ABI base_url must be an absolute http(s) URL")
        if require_https and parsed.scheme != "https":
            host = (parsed.hostname or "").lower()
            if host not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("HTTPS is required for non-local Semantic ABI endpoints")
        self.base_url = base_url.rstrip("/")
        self.timeout = max(0.1, float(timeout))
        self.max_response_bytes = max(1024, int(max_response_bytes))
        self.headers = {"Content-Type": "application/json", "Accept": "application/json", **dict(headers or {})}

    def __call__(self, method: str, path: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urllib_request.Request(f"{self.base_url}{path}", data=data, headers=self.headers, method=method.upper())
        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) > self.max_response_bytes:
                    raise ProtocolTransportError("Semantic ABI response exceeds configured size limit")
                raw = response.read(self.max_response_bytes + 1)
        except Exception as exc:
            if isinstance(exc, ProtocolTransportError):
                raise
            raise ProtocolTransportError(f"Semantic ABI request failed: {method.upper()} {path}: {exc}") from exc
        if len(raw) > self.max_response_bytes:
            raise ProtocolTransportError("Semantic ABI response exceeds configured size limit")
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ProtocolTransportError("Semantic ABI endpoint returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ProtocolTransportError("Semantic ABI protocol response must be a JSON object")
        return value


class RemoteSemanticOracleV1:
    """Batch oracle client over any Semantic ABI protocol transport."""

    def __init__(self, transport: ProtocolTransport) -> None:
        self.transport = transport
        self.manifest = OracleManifest.from_dict(self.transport("GET", "/v1/manifest", None))

    @classmethod
    def http(
        cls,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        max_response_bytes: int = 32 * 1024 * 1024,
        require_https: bool = False,
    ) -> "RemoteSemanticOracleV1":
        return cls(
            HttpJsonTransport(
                base_url,
                timeout=timeout,
                headers=headers,
                max_response_bytes=max_response_bytes,
                require_https=require_https,
            )
        )

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(x) for x in object_ids]
        response = self.transport("POST", "/v1/contains", {"object_ids": ids})
        raw = response.get("contains", {})
        if not isinstance(raw, Mapping):
            raise ValueError("remote contains response must contain an object")
        return {object_id: bool(raw.get(object_id, False)) for object_id in ids}

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        response = self.transport("POST", "/v1/score", {"pairs": [pair.to_dict() for pair in pairs]})
        out: dict[ScorePair, float] = {}
        for row in response.get("scores", ()):
            pair = ScorePair(str(row["anchor"]), str(row["candidate"]))
            if pair in out:
                raise ValueError("remote score response contains duplicate pair")
            score = float(row["score"])
            if not math.isfinite(score):
                raise ValueError("remote score response contains non-finite score")
            out[pair] = score
        missing = [pair for pair in pairs if pair not in out]
        if missing:
            raise ValueError(f"remote score response omitted {len(missing)} requested pairs")
        return out

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        response = self.transport("POST", "/v1/neighbors", {"requests": [req.to_dict() for req in requests]})
        out: dict[NeighborRequest, tuple[str, ...]] = {}
        for row in response.get("results", ()):
            req = NeighborRequest(str(row["anchor"]), int(row["k"]))
            if req in out:
                raise ValueError("remote neighbors response contains duplicate request")
            out[req] = tuple(str(x) for x in row.get("neighbors", ()))
        missing = [req for req in requests if req not in out]
        if missing:
            raise ValueError(f"remote neighbors response omitted {len(missing)} requested requests")
        return {req: tuple(out[req])[: req.k] for req in requests}
