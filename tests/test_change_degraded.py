from semantic_atlas.change_control import ReleasePolicy, compare_protocol_audits
from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import OracleManifest, audit_contract_v1


class Oracle:
    def __init__(self, name, scores):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test",
            score_directionality="asymmetric",
        )
        self.scores = dict(scores)

    def contains_many(self, ids):
        return {value: True for value in ids}

    def score_many(self, pairs):
        return {pair: self.scores[(pair.anchor, pair.candidate)] for pair in pairs}

    def neighbors_many(self, requests):
        return {request: () for request in requests}


def test_already_failing_clause_becoming_worse_counts_as_regression_even_if_other_clause_improves():
    contract = SemanticContract(
        name="debt",
        version="1",
        clauses=[
            TripletClause("q:debt", "good:debt", "bad:debt"),
            TripletClause("q:improve", "good:improve", "bad:improve"),
        ],
    )
    baseline = Oracle(
        "prod",
        {
            ("q:debt", "good:debt"): 0.9,
            ("q:debt", "bad:debt"): 1.0,
            ("q:improve", "good:improve"): 0.0,
            ("q:improve", "bad:improve"): 1.0,
        },
    )
    candidate = Oracle(
        "candidate",
        {
            ("q:debt", "good:debt"): 0.0,
            ("q:debt", "bad:debt"): 1.0,
            ("q:improve", "good:improve"): 2.0,
            ("q:improve", "bad:improve"): 1.0,
        },
    )

    report = compare_protocol_audits(
        contract,
        audit_contract_v1(contract, baseline),
        audit_contract_v1(contract, candidate),
        policy=ReleasePolicy(max_score_drop=1.0, allow_soft_regressions=0),
    )

    assert report.candidate_score > report.baseline_score
    assert report.deltas[0].status == "degraded"
    assert report.deltas[0].is_regression is True
    assert report.deltas[1].status == "fixed"
    assert report.deployment_eligible is False
    assert any("soft regression" in blocker for blocker in report.blockers)
