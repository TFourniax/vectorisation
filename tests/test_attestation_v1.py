from __future__ import annotations

import json

import pytest

from semantic_atlas.adequacy import ContractAdequacyEvidence, ContractAdequacyRequirements, assess_contract_adequacy
from semantic_atlas.attestation_v1 import SemanticProtocolAttestation, make_protocol_attestation
from semantic_atlas.conformance import check_oracle_conformance
from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import OracleManifest, ScorePair, audit_contract_v1


class Oracle:
    manifest = OracleManifest(
        "attestation-oracle",
        implementation_kind="test",
        score_semantics="directional-test",
        score_directionality="asymmetric",
    )

    def contains_many(self, object_ids):
        ids = {"q", "a", "b"}
        return {x: x in ids for x in object_ids}

    def score_many(self, pairs):
        values = {ScorePair("q", "a"): 2.0, ScorePair("q", "b"): 0.0}
        return {pair: values[pair] for pair in pairs}

    def neighbors_many(self, requests):
        return {req: ("a", "b")[: req.k] for req in requests}


def inputs():
    contract = SemanticContract(
        "attestation",
        "1",
        clauses=[NeighborClause("q", ("a",), candidate_k=2, hard=True), TripletClause("q", "a", "b", hard=True)],
    )
    oracle = Oracle()
    audit = audit_contract_v1(contract, oracle)
    conformance = check_oracle_conformance(oracle, anchors=["q"], k_values=(1, 2))
    adequacy = assess_contract_adequacy(
        ContractAdequacyEvidence(contract.digest, object_coverage=1.0, heldout_cases=200, datasets=3),
        ContractAdequacyRequirements(min_object_coverage=0.9, min_heldout_cases=100, min_datasets=2),
    )
    return contract, oracle, audit, conformance, adequacy


def test_attestation_binds_contract_oracle_plan_snapshot_and_governance(tmp_path):
    _, _, audit, conformance, adequacy = inputs()
    attestation = make_protocol_attestation(
        audit,
        conformance,
        adequacy=adequacy,
        risk_certificate_digest="risk-sha",
        risk_certified=True,
        status="certified",
    )
    assert attestation.deployment_eligible
    assert attestation.contract_digest == audit.report.contract_digest
    assert attestation.oracle_manifest_digest == audit.snapshot.manifest.digest
    assert attestation.plan_digest == audit.plan.digest
    assert attestation.snapshot_digest == audit.snapshot.digest
    assert attestation.protocol_audit_digest == audit.digest
    path = attestation.save(tmp_path / "attestation.json")
    loaded = SemanticProtocolAttestation.load(path)
    assert loaded.digest == attestation.digest
    assert loaded.deployment_eligible


def test_candidate_never_becomes_deployment_eligible_from_good_metrics_alone():
    _, _, audit, conformance, adequacy = inputs()
    attestation = make_protocol_attestation(
        audit,
        conformance,
        adequacy=adequacy,
        risk_certificate_digest="risk-sha",
        risk_certified=True,
        status="observed",
    )
    assert not attestation.deployment_eligible


def test_attestation_requires_adequacy_and_risk_for_deployment_eligibility():
    _, _, audit, conformance, _ = inputs()
    attestation = make_protocol_attestation(audit, conformance, status="certified")
    assert not attestation.deployment_eligible


def test_attestation_detects_tampered_envelope(tmp_path):
    _, _, audit, conformance, adequacy = inputs()
    attestation = make_protocol_attestation(audit, conformance, adequacy=adequacy)
    path = attestation.save(tmp_path / "attestation.json")
    envelope = json.loads(path.read_text())
    envelope["attestation"]["audit_score"] = 0.123
    path.write_text(json.dumps(envelope))
    with pytest.raises(ValueError, match="digest mismatch"):
        SemanticProtocolAttestation.load(path)


def test_attestation_refuses_cross_oracle_conformance():
    _, _, audit, _, adequacy = inputs()
    other = Oracle()
    other.manifest = OracleManifest("other")
    conformance = check_oracle_conformance(other, anchors=["q"], k_values=(1, 2))
    with pytest.raises(ValueError, match="different oracle"):
        make_protocol_attestation(audit, conformance, adequacy=adequacy)
