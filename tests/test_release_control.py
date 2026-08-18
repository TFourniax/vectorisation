from dataclasses import replace

from semantic_atlas.attestation_v1 import SemanticProtocolAttestation
from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import OracleManifest, audit_contract_v1
from semantic_atlas.release_control import evaluate_production_release


class FakeOracle:
    def __init__(self, name, positive=2.0, negative=1.0):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test-score",
            score_directionality="asymmetric",
        )
        self.positive = positive
        self.negative = negative

    def contains_many(self, object_ids):
        return {value: True for value in object_ids}

    def score_many(self, pairs):
        return {
            pair: self.positive if pair.candidate == "good" else self.negative
            for pair in pairs
        }

    def neighbors_many(self, requests):
        return {request: () for request in requests}


def _contract():
    return SemanticContract(
        name="critical",
        version="1",
        clauses=[TripletClause("q", "good", "bad", hard=True)],
    )


def _certified_attestation(audit):
    return SemanticProtocolAttestation(
        contract_digest=audit.report.contract_digest,
        oracle_manifest_digest=audit.snapshot.manifest.digest,
        plan_digest=audit.plan.digest,
        snapshot_digest=audit.snapshot.digest,
        protocol_audit_digest=audit.digest,
        audit_score=audit.report.score,
        hard_pass=audit.report.hard_pass,
        evaluated_clauses=audit.report.evaluated_clauses,
        missing_clauses=audit.report.missing_clauses,
        conformance_digest="conformance-digest",
        conformance_passed=True,
        adequacy_digest="adequacy-digest",
        adequacy_status="adequate",
        risk_certificate_digest="risk-digest",
        risk_certified=True,
        status="certified",
    )


def test_safe_change_with_bound_certified_attestation_can_release():
    contract = _contract()
    baseline = audit_contract_v1(contract, FakeOracle("prod"))
    candidate = audit_contract_v1(contract, FakeOracle("candidate"))
    attestation = _certified_attestation(candidate)

    report = evaluate_production_release(
        contract,
        baseline,
        candidate,
        attestation=attestation,
    )

    assert report.deployment_eligible is True
    assert report.attestation_bound is True
    assert report.attestation_deployment_eligible is True
    assert report.blockers == ()
    assert "production release — PASS" in report.to_markdown()


def test_release_without_attestation_fails_closed_by_default():
    contract = _contract()
    baseline = audit_contract_v1(contract, FakeOracle("prod"))
    candidate = audit_contract_v1(contract, FakeOracle("candidate"))

    report = evaluate_production_release(contract, baseline, candidate, attestation=None)

    assert report.deployment_eligible is False
    assert any("no certified" in blocker for blocker in report.blockers)


def test_stale_attestation_for_different_candidate_is_blocked():
    contract = _contract()
    baseline = audit_contract_v1(contract, FakeOracle("prod"))
    candidate = audit_contract_v1(contract, FakeOracle("candidate"))
    other = audit_contract_v1(contract, FakeOracle("other-candidate"))
    stale = _certified_attestation(other)

    report = evaluate_production_release(contract, baseline, candidate, attestation=stale)

    assert report.deployment_eligible is False
    assert report.attestation_bound is False
    assert any("manifest_digest" in blocker for blocker in report.blockers)


def test_certified_label_cannot_hide_inadequate_or_uncertified_risk_evidence():
    contract = _contract()
    baseline = audit_contract_v1(contract, FakeOracle("prod"))
    candidate = audit_contract_v1(contract, FakeOracle("candidate"))
    attestation = replace(
        _certified_attestation(candidate),
        adequacy_status="insufficient_evidence",
        risk_certified=False,
    )

    report = evaluate_production_release(
        contract,
        baseline,
        candidate,
        attestation=attestation,
    )

    assert report.attestation_bound is True
    assert report.attestation_deployment_eligible is False
    assert report.deployment_eligible is False
    assert any("not deployment-eligible" in blocker for blocker in report.blockers)


def test_semantic_regression_blocks_even_with_valid_candidate_attestation():
    contract = _contract()
    baseline = audit_contract_v1(contract, FakeOracle("prod"))
    candidate = audit_contract_v1(contract, FakeOracle("candidate", positive=0.5, negative=1.5))
    # Build an envelope that is bound to the candidate, but it cannot itself be
    # deployment-eligible because the hard clause failed.
    attestation = _certified_attestation(candidate)

    report = evaluate_production_release(
        contract,
        baseline,
        candidate,
        attestation=attestation,
    )

    assert report.change.deployment_eligible is False
    assert report.deployment_eligible is False
    assert len(report.change.hard_regressions) == 1
