import json

from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.product_cli import main
from semantic_atlas.protocol_v1 import OracleManifest


class FakeOracle:
    def __init__(self, name, positive, negative):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test",
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


def test_product_check_returns_ci_block_code_and_writes_reports(tmp_path, monkeypatch):
    contract = SemanticContract(
        name="critical",
        version="1",
        clauses=[TripletClause("q", "good", "bad", hard=True)],
    )
    contract_path = tmp_path / "contract.json"
    contract.save(contract_path)
    baseline_cfg = tmp_path / "baseline.json"
    candidate_cfg = tmp_path / "candidate.json"
    baseline_cfg.write_text("{}", encoding="utf-8")
    candidate_cfg.write_text("{}", encoding="utf-8")
    output = tmp_path / "change.json"
    markdown = tmp_path / "summary.md"

    def load(path):
        if str(path).endswith("baseline.json"):
            return FakeOracle("prod", 2.0, 1.0)
        return FakeOracle("candidate", 0.5, 1.5)

    monkeypatch.setattr("semantic_atlas.product_cli.oracle_from_config", load)

    code = main(
        [
            "check",
            str(contract_path),
            "--baseline",
            str(baseline_cfg),
            "--candidate",
            str(candidate_cfg),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ]
    )

    assert code == 4
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["deployment_eligible"] is False
    assert payload["summary"]["hard_regressions"] == 1
    assert "BLOCK" in markdown.read_text(encoding="utf-8")


def test_product_check_returns_zero_for_semantically_safe_candidate(tmp_path, monkeypatch):
    contract = SemanticContract(
        name="critical",
        version="1",
        clauses=[TripletClause("q", "good", "bad", hard=True)],
    )
    contract_path = tmp_path / "contract.json"
    contract.save(contract_path)
    baseline_cfg = tmp_path / "baseline.json"
    candidate_cfg = tmp_path / "candidate.json"
    baseline_cfg.write_text("{}", encoding="utf-8")
    candidate_cfg.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "semantic_atlas.product_cli.oracle_from_config",
        lambda path: FakeOracle("prod" if str(path).endswith("baseline.json") else "candidate", 2.0, 1.0),
    )

    assert main(["check", str(contract_path), "--baseline", str(baseline_cfg), "--candidate", str(candidate_cfg)]) == 0


def test_forge_safe_gives_normative_policy_precedence(tmp_path):
    evidence = tmp_path / "evidence.jsonl"
    output = tmp_path / "contract.json"
    bundle = tmp_path / "review.json"
    rows = [
        {
            "type": "policy",
            "anchor": "q:delete",
            "preferred": "doc:gdpr",
            "rejected": "doc:newsletter",
            "criticality": 1.0,
            "hard_eligible": True,
        }
    ]
    rows.extend(
        {
            "type": "preference",
            "anchor": "q:delete",
            "preferred": "doc:newsletter",
            "rejected": "doc:gdpr",
            "source": "production_click",
            "confidence": 1.0,
            "event_id": f"click-{index}",
        }
        for index in range(20)
    )
    evidence.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    code = main(
        [
            "forge-safe",
            str(evidence),
            "--output",
            str(output),
            "--review-bundle",
            str(bundle),
            "--quiet",
        ]
    )

    assert code == 0
    contract = SemanticContract.load(output)
    assert len(contract.clauses) == 1
    clause = contract.clauses[0]
    assert clause.positive == "doc:gdpr"
    assert clause.negative == "doc:newsletter"
    assert clause.hard is True
    assert bundle.exists()


def test_product_cli_delegates_legacy_plan_command(tmp_path):
    contract = SemanticContract(name="x", version="1", clauses=[])
    path = tmp_path / "contract.json"
    out = tmp_path / "plan.json"
    contract.save(path)

    assert main(["plan", str(path), "--output", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["contract_digest"] == contract.digest
