"""Semantic Manifold Atlas research prototype."""

from .alignment import TransitionAtlas, TransitionDiagnostics, TransitionGraph
from .core import AtlasIndex, AtlasRecord, SearchHit, SearchPolicy
from .drift import DriftPoint, DriftReport, compare_indexes
from .embed import FeatureHashEmbedder
from .fabric import FabricRecord, SemanticCell, SemanticFabric, SpaceSpec
from .transition_io import load_transition, save_transition

__all__ = [
    "AtlasIndex",
    "AtlasRecord",
    "SearchHit",
    "SearchPolicy",
    "FeatureHashEmbedder",
    "TransitionAtlas",
    "TransitionDiagnostics",
    "TransitionGraph",
    "FabricRecord",
    "SemanticCell",
    "SemanticFabric",
    "SpaceSpec",
    "DriftPoint",
    "DriftReport",
    "compare_indexes",
    "save_transition",
    "load_transition",
]
