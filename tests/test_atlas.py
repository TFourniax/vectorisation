import numpy as np
import pytest

from semantic_atlas import AtlasIndex, AtlasRecord, SearchPolicy
from semantic_atlas.persistence import AtlasStore


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def test_search_prefers_semantically_close_record_and_explains_score():
    index = AtlasIndex(chart_size=4, graph_k=2)
    index.extend(
        [
            AtlasRecord("a", unit([1, 0, 0, 0]), confidence=0.95),
            AtlasRecord("b", unit([0.9, 0.1, 0, 0])),
            AtlasRecord("c", unit([0, 1, 0, 0])),
            AtlasRecord("d", unit([0, 0, 1, 0])),
        ]
    )
    index.build()
    hits = index.search(unit([1, 0.02, 0, 0]), policy=SearchPolicy(top_k=2, diversify=0))
    assert hits[0].id in {"a", "b"}
    assert 0 <= hits[0].semantic_score <= 1
    assert len(hits[0].local_coordinates) == 3


def test_mutual_neighbor_graph_reduces_one_way_hub_edges():
    vectors = [
        unit([1, 0, 0]),
        unit([0.99, 0.05, 0]),
        unit([0, 1, 0]),
        unit([0, 0.99, 0.05]),
        unit([0.5, 0.5, 0.7]),
    ]
    index = AtlasIndex(chart_size=3, graph_k=2)
    index.extend([AtlasRecord(str(i), v) for i, v in enumerate(vectors)])
    index.build()
    assert all(i not in index.graph.adjacency[i] for i in range(len(vectors)))
    assert np.all(index.graph.hubness >= 0)


def test_overlapping_charts_create_a_nerve_graph():
    rng = np.random.default_rng(7)
    vectors = []
    for t in np.linspace(0, 1, 24):
        base = np.array([np.cos(t * np.pi), np.sin(t * np.pi), t, 0, 0, 0], dtype=np.float32)
        vectors.append(unit(base + rng.normal(0, 0.01, 6)))
    index = AtlasIndex(chart_size=6, chart_overlap=1.8, graph_k=3)
    index.extend([AtlasRecord(str(i), v) for i, v in enumerate(vectors)])
    index.build()
    assert len(index.charts) >= 2
    assert index.chart_edges
    assert any(len(m) > 1 for m in index.memberships)


def test_bridge_returns_topological_path_when_connected():
    vectors = [unit([1, 0, 0]), unit([0.95, 0.3, 0]), unit([0.7, 0.7, 0]), unit([0.3, 0.95, 0]), unit([0, 1, 0])]
    index = AtlasIndex(chart_size=3, graph_k=2)
    index.extend([AtlasRecord(chr(97 + i), v) for i, v in enumerate(vectors)])
    index.build()
    path = index.bridge("a", "e")
    assert path[0] == "a" and path[-1] == "e"
    assert len(path) >= 3


def test_duplicate_ids_are_rejected():
    index = AtlasIndex()
    index.add(AtlasRecord("x", unit([1, 0])))
    with pytest.raises(ValueError):
        index.add(AtlasRecord("x", unit([0, 1])))


def test_persistence_roundtrip(tmp_path):
    index = AtlasIndex(chart_size=4, graph_k=2)
    index.extend(
        [
            AtlasRecord("a", unit([1, 0, 0]), metadata={"kind": "alpha"}, provenance="test", confidence=0.8),
            AtlasRecord("b", unit([0, 1, 0]), facets=[unit([0.1, 0.9, 0])]),
            AtlasRecord("c", unit([0, 0, 1])),
        ]
    )
    index.build()
    store = AtlasStore(tmp_path)
    store.save(index)
    loaded = store.load(chart_size=4, graph_k=2)
    assert [r.id for r in loaded.records] == ["a", "b", "c"]
    assert loaded.records[0].metadata["kind"] == "alpha"
    assert len(loaded.records[1].facets) == 1


def test_boundary_finds_transition_record():
    vectors = [
        unit([1, 0, 0]),
        unit([0.8, 0.6, 0]),
        unit([0.7, 0.7, 0]),
        unit([0.6, 0.8, 0]),
        unit([0, 1, 0]),
    ]
    index = AtlasIndex(chart_size=3, graph_k=2).extend_and_build(
        [AtlasRecord(str(i), v) for i, v in enumerate(vectors)]
    )
    boundary = index.boundary("0", "4", limit=2)
    assert boundary[0]["id"] == "2"
    assert abs(boundary[0]["source_similarity"] - boundary[0]["target_similarity"]) < 0.05
