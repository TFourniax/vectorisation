import numpy as np

from semantic_atlas.alignment import TransitionAtlas, TransitionGraph, TransportedVector
from semantic_atlas.geometry import normalize


def test_local_transition_confidence_drops_outside_anchor_support():
    rng = np.random.default_rng(202)
    d = 12
    center = np.zeros(d, dtype=np.float32)
    center[0] = 1.0
    x = normalize(center + rng.normal(scale=0.05, size=(160, d)))
    y = x.copy()
    transition = TransitionAtlas.fit("a", "b", x, y, chart_size=48, min_chart_anchors=20)

    inside = normalize((center + rng.normal(scale=0.02, size=d)).reshape(1, -1))[0]
    outside = -center
    inside_moved = transition.map(inside)
    outside_moved = transition.map(outside)

    assert inside_moved.confidence > 0.65
    assert outside_moved.confidence < inside_moved.confidence * 0.25
    assert float(inside_moved.vector @ inside) > 0.99


class _ConditionalTransition:
    def __init__(self, source, target, confidence_fn):
        self.source_space = source
        self.target_space = target
        self._confidence_fn = confidence_fn
        self.confidence = 0.9

    def map(self, vector):
        v = normalize(np.asarray(vector, dtype=np.float32).reshape(1, -1))[0]
        return TransportedVector(v, float(self._confidence_fn(v)), ())


def test_query_aware_routing_can_choose_different_paths_by_region():
    graph = TransitionGraph()
    graph.add(_ConditionalTransition("a", "c", lambda v: 0.92 if v[0] > 0 else 0.20))
    graph.add(_ConditionalTransition("a", "b", lambda v: 0.82))
    graph.add(_ConditionalTransition("b", "c", lambda v: 0.82))

    positive = normalize(np.array([[1.0, 0.1, 0.0]], dtype=np.float32))[0]
    negative = normalize(np.array([[-1.0, 0.1, 0.0]], dtype=np.float32))[0]

    direct = graph.transport_best(positive, "a", "c")
    detour = graph.transport_best(negative, "a", "c")

    assert direct is not None and direct.path == ("a", "c")
    assert detour is not None and detour.path == ("a", "b", "c")
    assert detour.confidence > 0.60
