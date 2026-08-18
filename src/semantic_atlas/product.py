"""Curated Semantic ABI product API.

The root package preserves the broader research surface for backward compatibility.
Production integrations should prefer this module: it intentionally exports the small
set of protocol, acquisition, provider and release-control primitives expected to remain
stable as the project approaches 1.0.
"""

from .acquisition import (
    AcquisitionPolicy,
    PreferenceEvidence,
    RelevantSetEvidence,
)
from .attestation_v1 import SemanticProtocolAttestation, make_protocol_attestation
from .certification_io import (
    BoundRiskCertificate,
    assess_adequacy_spec,
    calibrate_risk_from_jsonl,
    calibration_events_digest,
    load_adequacy_report,
    load_calibration_events_jsonl,
    load_risk_certificate,
    risk_certificate_digest,
    save_adequacy_report,
    save_risk_certificate,
)
from .change_control import (
    ClauseDelta,
    ReleasePolicy,
    SemanticChangeReport,
    compare_protocol_audits,
)
from .contracts import (
    MutualNeighborClause,
    NeighborClause,
    SemanticContract,
    TripletClause,
)
from .otlp import (
    OtlpObservationResult,
    decode_otlp_any_value,
    decode_otlp_attributes,
    load_otlp_jsonl,
    observations_from_otlp_payload,
)
from .pgvector_provider import PgVectorOracleV1
from .policy_forge import PolicyConflictError, forge_contract_with_policies
from .product_config import oracle_from_config
from .protocol_v1 import (
    BatchSemanticOracleV1,
    NeighborRequest,
    OracleManifest,
    ProtocolAuditResult,
    ScorePair,
    audit_contract_v1,
    compile_contract,
)
from .providers import OpenSearchOracleV1, ProviderHttpTransport, text_query_catalog
from .qdrant_provider import PortableQdrantOracleV1
from .release_control import (
    ProductionReleaseReport,
    attestation_matches_audit,
    attestation_matches_certification_evidence,
    evaluate_production_release,
)
from .review import (
    ReviewApplicationResult,
    ReviewBundle,
    ReviewDecision,
    ReviewProposal,
    apply_review_decisions,
    build_review_bundle,
    load_review_decisions_jsonl,
)
from .telemetry import (
    RetrievalFeedback,
    RetrievalObservation,
    TelemetryEvidenceResult,
    join_feedback,
    load_feedback_jsonl,
    stable_query_id,
)

__all__ = [
    "AcquisitionPolicy",
    "PreferenceEvidence",
    "RelevantSetEvidence",
    "PolicyConflictError",
    "forge_contract_with_policies",
    "SemanticContract",
    "TripletClause",
    "NeighborClause",
    "MutualNeighborClause",
    "ReviewProposal",
    "ReviewBundle",
    "ReviewDecision",
    "ReviewApplicationResult",
    "build_review_bundle",
    "apply_review_decisions",
    "load_review_decisions_jsonl",
    "RetrievalObservation",
    "RetrievalFeedback",
    "TelemetryEvidenceResult",
    "stable_query_id",
    "join_feedback",
    "load_feedback_jsonl",
    "OtlpObservationResult",
    "decode_otlp_any_value",
    "decode_otlp_attributes",
    "observations_from_otlp_payload",
    "load_otlp_jsonl",
    "OracleManifest",
    "ScorePair",
    "NeighborRequest",
    "BatchSemanticOracleV1",
    "ProtocolAuditResult",
    "compile_contract",
    "audit_contract_v1",
    "PortableQdrantOracleV1",
    "OpenSearchOracleV1",
    "PgVectorOracleV1",
    "ProviderHttpTransport",
    "text_query_catalog",
    "oracle_from_config",
    "ClauseDelta",
    "ReleasePolicy",
    "SemanticChangeReport",
    "compare_protocol_audits",
    "SemanticProtocolAttestation",
    "make_protocol_attestation",
    "assess_adequacy_spec",
    "save_adequacy_report",
    "load_adequacy_report",
    "calibrate_risk_from_jsonl",
    "load_calibration_events_jsonl",
    "calibration_events_digest",
    "save_risk_certificate",
    "load_risk_certificate",
    "risk_certificate_digest",
    "BoundRiskCertificate",
    "ProductionReleaseReport",
    "attestation_matches_audit",
    "attestation_matches_certification_evidence",
    "evaluate_production_release",
]
