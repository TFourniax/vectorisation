import hashlib

from semantic_atlas.contracts import ContractReport
from semantic_atlas.release import EvidenceReference, ImplementationFingerprint, SemanticReleaseCertificate, make_release_certificate
from semantic_atlas.risk_control import RiskCertificate
from semantic_atlas.support import ContractCoverage


def certificate_inputs():
    implementation = ImplementationFingerprint(
        implementation_id="bge-v1",
        model_id="BAAI/bge-small-en-v1.5",
        revision="abc123",
        dimensions=384,
        preprocessing_digest="query-prefix:v1",
    )
    report = ContractReport("demo", "contract-digest", "bge-v1", 0.93, True, [], {"a": 0.02}, 10, 0)
    coverage = ContractCoverage(100, 70, 70, 0.70, 10, 5, 4, 1, 1.2, 3)
    risk = RiskCertificate(0.10, 0.05, 0.12, 0.03, 0.08, 120, 200, 400, 0.60, 6, True, "test", "certified")
    return implementation, report, coverage, risk


def test_release_certificate_roundtrip_and_digest(tmp_path):
    implementation, report, coverage, risk = certificate_inputs()
    evidence_bytes = b"benchmark-json"
    evidence = EvidenceReference("benchmark.json", hashlib.sha256(evidence_bytes).hexdigest())
    certificate = make_release_certificate(implementation, report, coverage, risk, evidence=[evidence], status="certified")
    path = certificate.save(tmp_path / "release.json")
    loaded = SemanticReleaseCertificate.load(path)

    assert loaded.digest == certificate.digest
    assert loaded.implementation.digest == implementation.digest
    assert loaded.rollout_eligible
    assert loaded.verify_evidence({"benchmark.json": evidence_bytes})["benchmark.json"]
    assert not loaded.verify_evidence({"benchmark.json": b"tampered"})["benchmark.json"]


def test_candidate_status_is_never_rollout_eligible_even_with_strong_metrics():
    implementation, report, coverage, risk = certificate_inputs()
    candidate = make_release_certificate(implementation, report, coverage, risk, status="candidate")
    assert not candidate.rollout_eligible


def test_release_certificate_detects_manifest_tampering(tmp_path):
    implementation, report, coverage, risk = certificate_inputs()
    certificate = make_release_certificate(implementation, report, coverage, risk)
    path = certificate.save(tmp_path / "release.json")
    text = path.read_text()
    path.write_text(text.replace('"audit_score": 0.93', '"audit_score": 0.99'))

    try:
        SemanticReleaseCertificate.load(path)
        assert False, "tampered certificate should fail"
    except ValueError as exc:
        assert "digest mismatch" in str(exc)
