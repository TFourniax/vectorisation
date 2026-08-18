import pytest

from semantic_atlas.protocol_v1 import NeighborRequest, ScorePair
from semantic_atlas.providers import OpenSearchOracleV1, QdrantOracleV1, text_query_catalog


class FakeQdrantTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, method, path, payload):
        self.calls.append((method, path, payload))
        if path.endswith("/points"):
            ids = payload["ids"]
            return {"result": [{"id": value} for value in ids if str(value) != "missing"]}
        if path.endswith("/query/batch"):
            rows = []
            for search in payload["searches"]:
                filt = search.get("filter")
                if filt:
                    candidate = filt["must"][0]["has_id"][0]
                    score = {"doc:a": 0.9, "doc:b": 0.2}.get(str(candidate), 0.1)
                    rows.append({"points": [{"id": candidate, "score": score}]})
                else:
                    query = search["query"]
                    if query == "doc:a":
                        rows.append({"points": [
                            {"id": "doc:a", "score": 1.0},
                            {"id": "doc:b", "score": 0.8},
                            {"id": "doc:c", "score": 0.7},
                        ]})
                    else:
                        rows.append({"points": [
                            {"id": "doc:a", "score": 0.9},
                            {"id": "doc:b", "score": 0.8},
                        ]})
            return {"result": rows}
        raise AssertionError((method, path, payload))


def test_qdrant_adapter_materializes_external_anchor_and_scores_candidate_by_id():
    transport = FakeQdrantTransport()
    oracle = QdrantOracleV1(
        collection="docs",
        query_catalog={"q:delete": [0.1, 0.2, 0.3]},
        transport=transport,
        vector_name="dense",
    )

    contains = oracle.contains_many(["q:delete", "doc:a", "missing"])
    assert contains == {"q:delete": True, "doc:a": True, "missing": False}

    pair = ScorePair("q:delete", "doc:a")
    scores = oracle.score_many([pair])
    assert scores[pair] == pytest.approx(0.9)

    batch_payload = [call[2] for call in transport.calls if call[1].endswith("/query/batch")][-1]
    search = batch_payload["searches"][0]
    assert search["query"] == [0.1, 0.2, 0.3]
    assert search["using"] == "dense"
    assert search["filter"] == {"must": [{"has_id": ["doc:a"]}]}


def test_qdrant_document_anchor_excludes_self_from_neighbors():
    transport = FakeQdrantTransport()
    oracle = QdrantOracleV1(collection="docs", transport=transport)
    request = NeighborRequest("doc:a", 2)

    result = oracle.neighbors_many([request])

    assert result[request] == ("doc:b", "doc:c")
    batch_payload = [call[2] for call in transport.calls if call[1].endswith("/query/batch")][-1]
    assert batch_payload["searches"][0]["limit"] == 3


class FakeOpenSearch:
    def __init__(self):
        self.json_calls = []
        self.msearch_calls = []

    def json(self, method, path, payload):
        self.json_calls.append((method, path, payload))
        if path.endswith("/_mget"):
            return {
                "docs": [
                    {"_id": value, "found": str(value) != "missing"}
                    for value in payload["ids"]
                ]
            }
        raise AssertionError((method, path, payload))

    def msearch(self, index, bodies):
        self.msearch_calls.append((index, list(bodies)))
        rows = []
        for body in bodies:
            query = body["query"]
            if "bool" in query:
                candidate = query["bool"]["filter"][0]["ids"]["values"][0]
                score = {"doc:gdpr": 4.2, "doc:newsletter": 1.1}.get(candidate, 0.1)
                rows.append({"hits": {"hits": [{"_id": candidate, "_score": score}]}})
            else:
                rows.append({"hits": {"hits": [
                    {"_id": "doc:gdpr", "_score": 4.2},
                    {"_id": "doc:account", "_score": 3.5},
                ]}})
        return rows


def test_opensearch_adapter_uses_query_catalog_for_pair_score_and_neighbors():
    fake = FakeOpenSearch()
    catalog = text_query_catalog({"q:delete": "delete my account"}, field="content")
    oracle = OpenSearchOracleV1(
        index="kb",
        query_catalog=catalog,
        json_transport=fake.json,
        msearch_transport=fake.msearch,
    )

    contains = oracle.contains_many(["q:delete", "doc:gdpr", "missing"])
    assert contains == {"q:delete": True, "doc:gdpr": True, "missing": False}

    pair = ScorePair("q:delete", "doc:gdpr")
    assert oracle.score_many([pair])[pair] == pytest.approx(4.2)
    score_body = fake.msearch_calls[-1][1][0]
    assert score_body["query"] == {
        "bool": {
            "must": [{"match": {"content": "delete my account"}}],
            "filter": [{"ids": {"values": ["doc:gdpr"]}}],
        }
    }

    request = NeighborRequest("q:delete", 2)
    assert oracle.neighbors_many([request])[request] == ("doc:gdpr", "doc:account")


def test_opensearch_missing_anchor_fails_closed():
    fake = FakeOpenSearch()
    oracle = OpenSearchOracleV1(
        index="kb",
        query_catalog={"q:known": {"match_all": {}}},
        json_transport=fake.json,
        msearch_transport=fake.msearch,
    )

    with pytest.raises(KeyError):
        oracle.neighbors_many([NeighborRequest("q:unknown", 1)])
