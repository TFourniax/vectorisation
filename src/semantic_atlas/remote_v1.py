from __future__ import annotations

"""Wire transport for Semantic ABI Oracle Protocol v1.

The protocol is framework-neutral. ``dispatch_protocol_request`` can sit behind
FastAPI, Flask, gRPC gateways, serverless functions, Unix-socket bridges, or an
in-process test transport. ``RemoteSemanticOracleV1`` uses a caller-supplied
transport; ``HttpJsonTransport`` is a zero-dependency reference client.
"""

import json
from typing import Any, Callable, Mapping, Sequence
from urllib import request as urllib_request

from .protocol_v1 import BatchSemanticOracleV1, NeighborRequest, OracleManifest, ScorePair

ProtocolTransport = Callable[[str, str, Mapping[str, Any] | None], Mapping[str, Any]]


def dispatch_protocol_request(
    oracle: BatchSemanticOracleV1,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Reference wire dispatcher; web frameworks only need to expose these routes."""
    method = method.upper()
    payload = dict(payload or {})
    if method == "GET" and path == "/v1/manifest":
        return oracle.manifest.to_dict()
    if method == "POST" and path == "/v1/contains":
        ids = [str(x) for x in payload.get("object_ids", ())]
        result = oracle.contains_many(ids)
        return {"contains": {object_id: bool(result.get(object_id, False)) for object_id in ids}}
    if method == "POST" and path == "/v1/score":
        pairs = [ScorePair(str(row["anchor"]), str(row["candidate"])) for row in payload.get("pairs", ())]
        result = oracle.score_many(pairs)
        return {"scores": [{**pair.to_dict(), "score": float(result[pair])} for pair in pairs]}
    if method == "POST" and path == "/v1/neighbors":
        requests = [NeighborRequest(str(row["anchor"]), int(row["k"])) for row in payload.get("requests", ())]
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
    """Minimal JSON-over-HTTP reference transport using the Python stdlib."""

    def __init__(self, base_url: str, *, timeout: float = 10.0, headers: Mapping[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.headers = {"Content-Type": "application/json", **dict(headers or {})}

    def __call__(self, method: str, path: str, payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
        data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        req = urllib_request.Request(f"{self.base_url}{path}", data=data, headers=self.headers, method=method.upper())
        with urllib_request.urlopen(req, timeout=self.timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Semantic ABI protocol response must be a JSON object")
        return value


class RemoteSemanticOracleV1:
    """Batch oracle client over any Semantic ABI protocol transport."""

    def __init__(self, transport: ProtocolTransport) -> None:
        self.transport = transport
        self.manifest = OracleManifest.from_dict(self.transport("GET", "/v1/manifest", None))

    @classmethod
    def http(cls, base_url: str, *, timeout: float = 10.0, headers: Mapping[str, str] | None = None) -> "RemoteSemanticOracleV1":
        return cls(HttpJsonTransport(base_url, timeout=timeout, headers=headers))

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        ids = [str(x) for x in object_ids]
        response = self.transport("POST", "/v1/contains", {"object_ids": ids})
        raw = response.get("contains", {})
        return {object_id: bool(raw.get(object_id, False)) for object_id in ids}

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        response = self.transport("POST", "/v1/score", {"pairs": [pair.to_dict() for pair in pairs]})
        out = {
            ScorePair(str(row["anchor"]), str(row["candidate"])): float(row["score"])
            for row in response.get("scores", ())
        }
        missing = [pair for pair in pairs if pair not in out]
        if missing:
            raise ValueError(f"remote score response omitted {len(missing)} requested pairs")
        return out

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        response = self.transport("POST", "/v1/neighbors", {"requests": [req.to_dict() for req in requests]})
        out = {
            NeighborRequest(str(row["anchor"]), int(row["k"])): tuple(str(x) for x in row.get("neighbors", ()))
            for row in response.get("results", ())
        }
        missing = [req for req in requests if req not in out]
        if missing:
            raise ValueError(f"remote neighbors response omitted {len(missing)} requested requests")
        return {req: tuple(out[req])[: req.k] for req in requests}
