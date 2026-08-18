import json

from semantic_atlas.cli import main
from semantic_atlas.contracts import SemanticContract


def test_forge_openinference_cli_requires_feedback_and_emits_contract(tmp_path, monkeypatch):
    spans = tmp_path / "spans.jsonl"
    feedback = tmp_path / "feedback.jsonl"
    contract_path = tmp_path / "contract.json"
    report_path = tmp_path / "report.json"
    review_path = tmp_path / "review.jsonl"

    span_rows = []
    feedback_rows = []
    for index in range(5):
        span_rows.append(
            {
                "trace_id": f"trace-{index}",
                "span_id": f"span-{index}",
                "attributes": {
                    "openinference.span.kind": "RETRIEVER",
                    "input.value": "delete my account",
                    "retrieval.documents": [
                        {"document.id": "doc:newsletter", "document.score": 0.9},
                        {"document.id": "doc:gdpr-delete", "document.score": 0.8},
                    ],
                },
            }
        )
        feedback_rows.append(
            {
                "span_id": f"span-{index}",
                "selected": ["doc:gdpr-delete"],
                "explicit_negative": ["doc:newsletter"],
                "event_id": f"review-{index}",
            }
        )

    spans.write_text("\n".join(json.dumps(row) for row in span_rows) + "\n", encoding="utf-8")
    feedback.write_text("\n".join(json.dumps(row) for row in feedback_rows) + "\n", encoding="utf-8")
    monkeypatch.setenv("SEMANTIC_ABI_QUERY_KEY", "test-tenant-secret")

    exit_code = main(
        [
            "forge-openinference",
            str(spans),
            "--feedback",
            str(feedback),
            "--query-secret-env",
            "SEMANTIC_ABI_QUERY_KEY",
            "--name",
            "support-search",
            "--output",
            str(contract_path),
            "--report",
            str(report_path),
            "--review",
            str(review_path),
            "--quiet",
        ]
    )

    assert exit_code == 0
    contract = SemanticContract.load(contract_path)
    assert contract.name == "support-search"
    assert len(contract.clauses) == 1
    clause = contract.clauses[0]
    assert clause.positive == "doc:gdpr-delete"
    assert clause.negative == "doc:newsletter"
    assert clause.hard is False

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["telemetry"]["observations_emitted"] == 5
    assert report["telemetry"]["feedback_matched"] == 5
    assert report["telemetry"]["evidence_emitted"] == 5
    assert report["acquisition"]["promoted_count"] == 1


def test_forge_openinference_cli_fails_if_secret_env_is_missing(tmp_path):
    spans = tmp_path / "spans.jsonl"
    feedback = tmp_path / "feedback.jsonl"
    spans.write_text("", encoding="utf-8")
    feedback.write_text("", encoding="utf-8")

    try:
        main(
            [
                "forge-openinference",
                str(spans),
                "--feedback",
                str(feedback),
                "--query-secret-env",
                "ABSENT_SEMANTIC_ABI_KEY",
                "--output",
                str(tmp_path / "contract.json"),
            ]
        )
    except SystemExit as exc:
        assert "ABSENT_SEMANTIC_ABI_KEY" in str(exc)
    else:
        raise AssertionError("missing query secret environment variable must fail closed")
