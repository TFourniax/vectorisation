"""Semantic Manifold Atlas research prototype."""

from .alignment import RoutedTransport, TransitionAtlas, TransitionDiagnostics, TransitionGraph
from .contract_lint import ContractIssue, ContractLintReport, lint_contract
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
from .mutation import (
    MutationOutcome,
    SemanticMutation,
    SemanticMutationReport,
    add_vector_noise,
    collapse_region,
    default_semantic_mutations,
    mutation_test,
    permute_identities,
    pull_to_hub,
)
from .oracle import CallbackSemanticOracle, DenseVectorOracle, SemanticOracle, audit_contract, evaluate_contract_clause
from .progressive_audit import ProgressiveAuditResult, progressive_semantic_audit
from .release import EvidenceReference, ImplementationFingerprint, SemanticReleaseCertificate, make_release_certificate
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
from .risk_exact import calibrate_semantic_risk_preregistered, exact_binomial_upper_bound
from .risk_slices import SliceRiskPortfolio, calibrate_semantic_risk_by_slice
from .semantic_diff import ContractQuestion, ObjectSemanticDiff, RepresentationDiff, propose_contract_questions, semantic_diff
from .support import ContractCoverage, LocalSemanticRisk, contract_coverage, estimate_local_semantic_risk
from .transition_io import load_transition, save_transition
from .transition_policy import EvidenceGatedTransition, TransitionValidation
from .witness import (
    SemanticWitnessSet,
    WitnessEvaluation,
    WitnessScenario,
    WitnessScenarioEvaluation,
    build_semantic_witness_set,
    evaluate_clause_subset,
)

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
    "EvidenceGatedTransition",
    "TransitionValidation",
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
    "ContractIssue",
    "ContractLintReport",
    "lint_contract",
    "SemanticOracle",
    "DenseVectorOracle",
    "CallbackSemanticOracle",
    "audit_contract",
    "evaluate_contract_clause",
    "ProgressiveAuditResult",
    "progressive_semantic_audit",
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
    "exact_binomial_upper_bound",
    "calibrate_semantic_risk_preregistered",
    "SliceRiskPortfolio",
    "calibrate_semantic_risk_by_slice",
    "ContractCoverage",
    "LocalSemanticRisk",
    "contract_coverage",
    "estimate_local_semantic_risk",
    "ChangeAssessment",
    "AssessmentDelta",
    "SemanticChangeManager",
    "compare_assessments",
    "ImplementationFingerprint",
    "EvidenceReference",
    "SemanticReleaseCertificate",
    "make_release_certificate",
    "ObjectSemanticDiff",
    "RepresentationDiff",
    "ContractQuestion",
    "semantic_diff",
    "propose_contract_questions",
    "SemanticMutation",
    "MutationOutcome",
    "SemanticMutationReport",
    "permute_identities",
    "collapse_region",
    "pull_to_hub",
    "add_vector_noise",
    "default_semantic_mutations",
    "mutation_test",
    "WitnessScenario",
    "WitnessScenarioEvaluation",
    "WitnessEvaluation",
    "SemanticWitnessSet",
    "evaluate_clause_subset",
    "build_semantic_witness_set",
]
