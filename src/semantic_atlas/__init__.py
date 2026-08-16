"""Semantic Manifold Atlas research prototype."""

from .alignment import RoutedTransport, TransitionAtlas, TransitionDiagnostics, TransitionGraph
from .contracts import (
    ContractLedger,
    ContractReport,
    GateDecision,
    MutualNeighborClause,
    NeighborClause,
    SemanticABIGate,
    SemanticContract,
    TripletClause,
    capture_behavior_contract,
    contract_from_labels,
)
from .core import AtlasIndex, AtlasRecord, SearchHit, SearchPolicy
from .drift import DriftPoint, DriftReport, compare_indexes
from .embed import FeatureHashEmbedder
from .fabric import FabricRecord, SemanticCell, SemanticFabric, SpaceSpec
from .repair import RepairCandidate, RepairPlan, plan_repairs
from .transition_io import load_transition, save_transition

__all__ = [
    "AtlasIndex",
    "AtlasRecord",
    "SearchHit",
    "SearchPolicy",
    "FeatureHashEmbedder",
    "RoutedTransport",
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
    "SemanticContract",
    "TripletClause",
    "NeighborClause",
    "MutualNeighborClause",
    "ContractReport",
    "ContractLedger",
    "SemanticABIGate",
    "GateDecision",
    "capture_behavior_contract",
    "contract_from_labels",
    "RepairCandidate",
    "RepairPlan",
    "plan_repairs",
]
