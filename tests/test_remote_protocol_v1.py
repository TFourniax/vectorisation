from __future__ import annotations

from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import NeighborRequest, OracleManifest, ScorePair, audit_contract_v1
from semantic_atlas.remote_v1 import InProcessProtocolTransport, RemoteSemanticOracleV1


class ServiceOracle:
    manifest = OracleManifest(
        "service-test",
        implementation_kind="remote-test",
        score_semantics="directional",
        score_directionality="asymmetric",
    )

    def contains_many(self, object_ids):
        universe = {"q", "good", "bad"}
        return {x: x in universe for x in object_ids}

    def score_many(self, pairs):
        table = {ScorePair("q", "good"): 2.0, ScorePair("q", "bad"): -1.0}
        return {pair: table[pair] for pair in pairs}

    def neighbors_many(self, requests):
        return {req: ("good", "bad")[: req.k] for req in requests}


def test_remote_protocol_executes_contract_in_three_batched_data_roundtrips():
    contract = SemanticContract(
        "remote",
        "1",
        clauses=[
            NeighborClause("q", ("good",), min_recall=1.0, candidate_k=2),
            TripletClause("q", "good", "bad", margin=0.5),
            TripletClause("q", "good", "bad", margin=1.0),
        ],
    )
    transport = InProcessProtocolTransport(ServiceOracle())
    remote = RemoteSemanticOracleV1(transport)
    result = audit_contract_v1(contract, remote)

    assert result.report.score == 1.0
    assert result.report.hard_pass
    assert result.snapshot.stats.transport_round_trips == 3
    assert transport.calls == [
        ("GET", "/v1/manifest"),
        ("POST", "/v1/contains"),
        ("POST", "/v1/score"),
        ("POST", "/v1/neighbors"),
    ]
    assert result.plan.score_pairs == (ScorePair("q", "bad"), ScorePair("q", "good"))
    assert result.plan.neighbor_requests == (NeighborRequest("q", 2),)
