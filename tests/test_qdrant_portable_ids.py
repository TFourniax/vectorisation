import pytest

from semantic_atlas.protocol_v1 import NeighborRequest, ScorePair
from semantic_atlas.qdrant_provider import PortableQdrantOracleV1


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, method, path, payload):
        self.calls.append((method, path, payload))
        if path.endswith("/points"):
            return {"result": [{"id": value} for value in payload["ids"] if value != 999]}
        if path.endswith("/query/batch"):
            rows = []
            for search in payload["searches"]:
                if search.get("filter"):
                    native = search["filter"]["must"][0]["has_id"][0]
                    rows.append({"points": [{"id": native, "score": 0.91}]})
                else:
                    rows.append({"points": [
                        {"id": 101, "score": 1.0},
                        {"id": 102, "score": 0.8},
                        {"id": 103, "score": 0.7},
                    ]})
            return {"result": rows}
        raise AssertionError((method, path, payload))


def test_qdrant_mapping_translates_contains_scores_and_neighbors_both_directions():
    transport = FakeTransport()
    oracle = PortableQdrantOracleV1(
        collection="docs",
        query_catalog={"q:delete": [1, 0, 0]},
        object_id_map={
            "doc:gdpr": 101,
            "doc:newsletter": 102,
            "doc:other": 103,
            "doc:missing": 999,
        },
        transport=transport,
    )

    assert oracle.contains_many(["q:delete", "doc:gdpr", "doc:missing"]) == {
        "q:delete": True,
        "doc:gdpr": True,
        "doc:missing": False,
    }
    pair = ScorePair("q:delete", "doc:gdpr")
    assert oracle.score_many([pair])[pair] == pytest.approx(0.91)
    score_payload = [call[2] for call in transport.calls if call[1].endswith("/query/batch")][-1]
    assert score_payload["searches"][0]["filter"]["must"][0]["has_id"] == [101]

    request = NeighborRequest("q:delete", 2)
    assert oracle.neighbors_many([request])[request] == ("doc:gdpr", "doc:newsletter")


def test_qdrant_mapped_document_anchor_excludes_logical_self():
    transport = FakeTransport()
    oracle = PortableQdrantOracleV1(
        collection="docs",
        object_id_map={"doc:self": 101, "doc:b": 102, "doc:c": 103},
        transport=transport,
    )
    request = NeighborRequest("doc:self", 2)

    assert oracle.neighbors_many([request])[request] == ("doc:b", "doc:c")
    payload = [call[2] for call in transport.calls if call[1].endswith("/query/batch")][-1]
    assert payload["searches"][0]["query"] == 101


def test_qdrant_mapping_must_be_reversible():
    with pytest.raises(ValueError, match="not one-to-one"):
        PortableQdrantOracleV1(
            collection="docs",
            object_id_map={"doc:a": 1, "doc:b": 1},
            transport=FakeTransport(),
        )
