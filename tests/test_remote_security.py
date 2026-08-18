import pytest

from semantic_atlas.protocol_v1 import OracleManifest, ScorePair
from semantic_atlas.remote_v1 import HttpJsonTransport, RemoteSemanticOracleV1, dispatch_protocol_request


class Oracle:
    manifest = OracleManifest("test")

    def contains_many(self, object_ids):
        return {value: True for value in object_ids}

    def score_many(self, pairs):
        return {pair: 1.0 for pair in pairs}

    def neighbors_many(self, requests):
        return {request: tuple(f"d:{i}" for i in range(request.k)) for request in requests}


def test_dispatch_rejects_excessive_batch_and_neighbor_k():
    oracle = Oracle()
    with pytest.raises(ValueError, match="batch limit"):
        dispatch_protocol_request(
            oracle,
            "POST",
            "/v1/contains",
            {"object_ids": ["a", "b"]},
            max_batch_items=1,
        )
    with pytest.raises(ValueError, match="neighbor k"):
        dispatch_protocol_request(
            oracle,
            "POST",
            "/v1/neighbors",
            {"requests": [{"anchor": "q", "k": 11}]},
            max_neighbor_k=10,
        )


def test_dispatch_rejects_oversized_logical_id():
    with pytest.raises(ValueError, match="length limit"):
        dispatch_protocol_request(
            Oracle(),
            "POST",
            "/v1/contains",
            {"object_ids": ["abcdef"]},
            max_logical_id_length=5,
        )


def test_http_transport_requires_absolute_url_and_can_require_https():
    with pytest.raises(ValueError, match="absolute"):
        HttpJsonTransport("localhost:8000")
    with pytest.raises(ValueError, match="HTTPS"):
        HttpJsonTransport("http://example.com", require_https=True)
    # Local development remains possible when HTTPS enforcement is requested.
    HttpJsonTransport("http://localhost:8000", require_https=True)


def test_remote_client_rejects_duplicate_or_nonfinite_scores():
    manifest = OracleManifest("remote").to_dict()

    def duplicate_transport(method, path, payload):
        if path == "/v1/manifest":
            return manifest
        if path == "/v1/score":
            pair = payload["pairs"][0]
            return {"scores": [{**pair, "score": 1.0}, {**pair, "score": 1.0}]}
        raise AssertionError(path)

    client = RemoteSemanticOracleV1(duplicate_transport)
    with pytest.raises(ValueError, match="duplicate"):
        client.score_many([ScorePair("q", "d")])

    def nan_transport(method, path, payload):
        if path == "/v1/manifest":
            return manifest
        if path == "/v1/score":
            pair = payload["pairs"][0]
            return {"scores": [{**pair, "score": float("nan")}]}
        raise AssertionError(path)

    client = RemoteSemanticOracleV1(nan_transport)
    with pytest.raises(ValueError, match="non-finite"):
        client.score_many([ScorePair("q", "d")])
