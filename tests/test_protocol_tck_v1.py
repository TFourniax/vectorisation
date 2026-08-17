from __future__ import annotations

import json
from pathlib import Path

from semantic_atlas.contracts import SemanticContract
from semantic_atlas.protocol_v1 import NeighborRequest, OracleManifest, ScorePair, audit_contract_v1


class FixtureOracle:
    def __init__(self, fixture):
        self.fixture = fixture
        self.manifest = OracleManifest.from_dict(fixture["oracle_manifest"])
        wire = fixture["wire_responses"]
        self.contains = dict(wire["contains"])
        self.scores = {
            ScorePair(row["anchor"], row["candidate"]): float(row["score"])
            for row in wire["scores"]
        }
        self.neighborhoods = {
            NeighborRequest(row["anchor"], int(row["k"])): tuple(row["neighbors"])
            for row in wire["neighborhoods"]
        }

    def contains_many(self, object_ids):
        return {x: bool(self.contains.get(x, False)) for x in object_ids}

    def score_many(self, pairs):
        return {pair: self.scores[pair] for pair in pairs}

    def neighbors_many(self, requests):
        return {request: self.neighborhoods[request] for request in requests}


def test_language_neutral_tck_reproduces_all_canonical_digests():
    fixture = json.loads(Path("spec/semantic-abi-oracle-v1-tck.json").read_text())
    expected = fixture["expected"]
    contract = SemanticContract.from_dict(fixture["contract"])
    oracle = FixtureOracle(fixture)
    result = audit_contract_v1(contract, oracle)

    assert contract.digest == expected["contract_digest"]
    assert result.plan.digest == expected["plan_digest"]
    assert oracle.manifest.digest == expected["oracle_manifest_digest"]
    assert result.snapshot.digest == expected["snapshot_digest"]
    assert result.digest == expected["protocol_audit_digest"]
    assert result.report.score == expected["audit_score"]
    assert result.report.hard_pass is expected["hard_pass"]
    assert result.report.evaluated_clauses == expected["evaluated_clauses"]
    assert result.report.missing_clauses == expected["missing_clauses"]
    assert len(result.report.violated) == expected["violated_clauses"]
    assert result.snapshot.stats.transport_round_trips == expected["transport_round_trips"]
    assert len(result.plan.score_pairs) == expected["deduplicated_score_pairs"]
    assert len(result.plan.neighbor_requests) == expected["deduplicated_neighbor_requests"]
