import json

from semantic_atlas.adequacy import ContractAdequacyEvidence, ContractAdequacyRequirements, assess_contract_adequacy
from semantic_atlas.certification_io import save_adequacy_report, save_risk_certificate
from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.product_cli import main
from semantic_atlas.protocol_v1 import OracleManifest
from semantic_atlas.risk_control import RiskCertificate


class FakeOracle:
    def __init__(self, name="candidate", positive=2.0, negative=1.0):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test-score",
            score_directionality="asymmetric",
            deterministic=True,
        )
        self.positive = positive
        self.negative = negative
        self.closed = False

    def contains_many(self, object_ids):
        return {value: True for value in object_ids}

    def score_many(self, pairs):
        return {
            pair: self.positive if pair.candidate == "good" else self.negative
            for pair in pairs
        }

    def neighbors_many(self, requests):
        return {request: () for request in requests}

    def close(self):
        self.closed = True


def _contract(tmp_path):
    contract = SemanticContract(
        name="critical",
        version="1",
        clauses=[TripletClause("q", "good", "bad", hard=True)],
    )
    path = tmp_path / "contract.json"
    contract.save(path)
    return contract, path


def _adequacy(contract, tmp_path):
    report = assess_contract_adequacy(
        ContractAdequacyEvidence(
            contract_digest=contract.digest,
            object_coverage=1.0,
            heldout_cases=500,
            fault_families=4,
        ),
        ContractAdequacyRequirements(
            min_object_coverage=0.9,
            min_heldout_cases=100,
            min_fault_families=2,
        ),
    )
    path = tmp_path / "adequacy.json"
    save_adequacy_report(report, path)
    return path


def _risk(tmp_path, certified=True):
    certificate = RiskCertificate(
        target_risk=0.10,
        delta=0.05,
        threshold=0.2 if certified else None,
        empirical_risk=0.02 if certified else 1.0,
        upper_risk_bound=0.08 if certified else 1.0,
        accepted_calibration=100 if certified else 0,
        certification_size=100,
        total_events=200,
        estimated_coverage=0.5 if certified else 0.0,
        candidate_count=4,
        certified=certified,
        method="test",
        reason="fixture",
    )
    path = tmp_path / "risk.json"
    save_risk_certificate(certificate, path)
    return path


def test_attest_then_release_forms_closed_certified_cli_chain(tmp_path, monkeypatch):
    contract, contract_path = _contract(tmp_path)
    adequacy = _adequacy(contract, tmp_path)
    risk = _risk(tmp_path)
    candidate_cfg = tmp_path / "candidate.json"
    baseline_cfg = tmp_path / "baseline.json"
    candidate_cfg.write_text("{}", encoding="utf-8")
    baseline_cfg.write_text("{}", encoding="utf-8")
    attestation = tmp_path / "attestation.json"
    release_report = tmp_path / "release.json"
    release_md = tmp_path / "release.md"

    def oracle_from_config(path):
        return FakeOracle("prod" if str(path).endswith("baseline.json") else "candidate")

    monkeypatch.setattr("semantic_atlas.product_cli.oracle_from_config", oracle_from_config)

    attest_code = main(
        [
            "attest",
            str(contract_path),
            "--oracle",
            str(candidate_cfg),
            "--adequacy",
            str(adequacy),
            "--risk-certificate",
            str(risk),
            "--output",
            str(attestation),
            "--quiet",
        ]
    )
    assert attest_code == 0
    envelope = json.loads(attestation.read_text(encoding="utf-8"))
    assert envelope["attestation"]["status"] == "certified"

    release_code = main(
        [
            "release",
            str(contract_path),
            "--baseline",
            str(baseline_cfg),
            "--candidate",
            str(candidate_cfg),
            "--attestation",
            str(attestation),
            "--output",
            str(release_report),
            "--markdown",
            str(release_md),
        ]
    )

    assert release_code == 0
    payload = json.loads(release_report.read_text(encoding="utf-8"))
    assert payload["deployment_eligible"] is True
    assert payload["attestation"]["bound_to_candidate"] is True
    assert "production release — PASS" in release_md.read_text(encoding="utf-8")


def test_attest_refuses_to_certify_when_risk_certificate_failed(tmp_path, monkeypatch):
    contract, contract_path = _contract(tmp_path)
    adequacy = _adequacy(contract, tmp_path)
    risk = _risk(tmp_path, certified=False)
    cfg = tmp_path / "candidate.json"
    cfg.write_text("{}", encoding="utf-8")
    attestation = tmp_path / "attestation.json"
    monkeypatch.setattr("semantic_atlas.product_cli.oracle_from_config", lambda path: FakeOracle())

    code = main(
        [
            "attest",
            str(contract_path),
            "--oracle",
            str(cfg),
            "--adequacy",
            str(adequacy),
            "--risk-certificate",
            str(risk),
            "--output",
            str(attestation),
            "--quiet",
        ]
    )

    assert code == 6
    envelope = json.loads(attestation.read_text(encoding="utf-8"))
    assert envelope["attestation"]["status"] == "blocked"
    assert envelope["attestation"]["risk_certified"] is False


def test_assess_adequacy_cli_returns_nonzero_for_missing_required_evidence(tmp_path):
    contract, contract_path = _contract(tmp_path)
    spec = tmp_path / "adequacy-spec.json"
    output = tmp_path / "adequacy.json"
    spec.write_text(
        json.dumps(
            {
                "evidence": {"contract_digest": contract.digest, "object_coverage": 1.0},
                "requirements": {"min_object_coverage": 0.9, "min_heldout_cases": 100},
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "assess-adequacy",
            str(contract_path),
            "--spec",
            str(spec),
            "--output",
            str(output),
            "--quiet",
        ]
    )

    assert code == 7
    envelope = json.loads(output.read_text(encoding="utf-8"))
    assert envelope["report"]["status"] == "insufficient_evidence"
