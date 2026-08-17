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
from .lifecycle import AssessmentDelta, ChangeAssessment, SemanticChangeManager, compare_assessments
from .repair import (
    CoverageRepairCandidate,
    CoverageRepairPlan,
    RepairCandidate,
    RepairPlan,
    plan_repairs,
    plan_repairs_by_coverage,
)
from .risk_control import (
    CalibrationEvent,
    CertifiedGateDecision,
    CertifiedSemanticABIGate,
    RiskCertificate,
    bernoulli_kl_upper_bound,
    calibrate_semantic_risk,
)
from .support import ContractCoverage, LocalSemanticRisk, contract_coverage, estimate_local_semantic_risk
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
    "CoverageRepairCandidate",
    "CoverageRepairPlan",
    "plan_repairs_by_coverage",
    "CalibrationEvent",
    "RiskCertificate",
    "CertifiedGateDecision",
    "CertifiedSemanticABIGate",
    "bernoulli_kl_upper_bound",
    "calibrate_semantic_risk",
    "ContractCoverage",
    "LocalSemanticRisk",
    "contract_coverage",
    "estimate_local_semantic_risk",
    "ChangeAssessment",
    "AssessmentDelta",
    "SemanticChangeManager",
    "compare_assessments",
]