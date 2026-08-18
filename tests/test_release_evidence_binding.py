from semantic_atlas.attestation_v1 import SemanticProtocolAttestation
from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import OracleManifest, audit_contract_v1
from semantic_atlas.release_control import (
    attestation_matches_certification_evidence,
    evaluate_production_release,
)


class Oracle:
    def __init__(self, name):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test",
            score_directionality="asymmetric",
        )

    def contains_many(self, ids):
        return {value: True for value in ids}

    def score_many(self, pairs):
        return {pair: 2.0 if pair.candidate == "good" else 1.0 for pair in pairs}

    def neighbors_many(self, requests):
        return {request: () for request in requests}


def _attestation(audit):
    return SemanticProtocolAttestation(
        contract_digest=audit.report.contract_digest,
        oracle_manifest_digest=audit.snapshot.manifest.digest,
        plan_digest=audit.plan.digest,
        snapshot_digest=audit.snapshot.digest,
        protocol_audit_digest=audit.digest,
        audit_score=audit.report.score,
        hard_pass=True,
        evaluated_clauses=audit.report.evaluated_clauses,
        missing_clauses=0,
        conformance_digest="conf-v1",
        conformance_passed=True,
        adequacy_digest="adequacy-v1",
        adequacy_status="adequate",
        risk_certificate_digest="risk-v1",
        risk_certified=True,
        status="certified",
    )


def test_recomputed_evidence_mismatch_blocks_otherwise_safe_release():
    contract = SemanticContract(
        name="x",
        version="1",
        clauses=[TripletClause("q", "good", "bad", hard=True)],
    )
    baseline = audit_contract_v1(contract, Oracle("prod"))
    candidate = audit_contract_v1(contract, Oracle("candidate"))
    attestation = _attestation(candidate)

    bound, mismatches = attestation_matches_certification_evidence(
        attestation,
        conformance_digest="conf-v2",
        conformance_passed=True,
        adequacy_digest="adequacy-v1",
        adequacy_status="adequate",
        risk_certificate_digest="risk-v1",
        risk_certified=True,
    )
    assert bound is False
    assert any("conformance_digest" in value for value in mismatches)

    report = evaluate_production_release(
        contract,
        baseline,
        candidate,
        attestation=attestation,
        certification_evidence_mismatches=mismatches,
    )

    assert report.change.deployment_eligible is True
    assert report.attestation_bound is True
    assert report.certification_evidence_bound is False
    assert report.deployment_eligible is False
