from __future__ import annotations

import json

from semantic_atlas.cli import main
from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause


def test_cli_plan_emits_canonical_execution_plan(tmp_path):
    contract = SemanticContract(
        "cli",
        "1",
        clauses=[
            NeighborClause("q:1", ("d:a",), candidate_k=5),
            TripletClause("q:1", "d:a", "d:b"),
        ],
    )
    contract_path = contract.save(tmp_path / "contract.json")
    output = tmp_path / "plan.json"
    assert main(["plan", str(contract_path), "--output", str(output)]) == 0
    payload = json.loads(output.read_text())
    assert payload["format"] == "semantic-abi-execution-plan"
    assert payload["contract_digest"] == contract.digest
    assert len(payload["plan_digest"]) == 64
    assert payload["neighbor_requests"] == [{"anchor": "q:1", "k": 5}]
    assert payload["score_pairs"] == [
        {"anchor": "q:1", "candidate": "d:a"},
        {"anchor": "q:1", "candidate": "d:b"},
    ]
