from semantic_atlas.change_control import ReleasePolicy, compare_protocol_audits
from semantic_atlas.contracts import NeighborClause, SemanticContract, TripletClause
from semantic_atlas.protocol_v1 import NeighborRequest, OracleManifest, ScorePair, audit_contract_v1


class FakeOracle:
    def __init__(self, name, *, scores, neighborhoods, missing=()):
        self.manifest = OracleManifest(
            implementation_id=name,
            implementation_kind="test",
            score_semantics="test-score",
            score_directionality="asymmetric",
        )
        self._scores = dict(scores)
        self._neighborhoods = dict(neighborhoods)
        self._missing = set(missing)

    def contains_many(self, object_ids):
        return {value: value not in self._missing for value in object_ids}

    def score_many(self, pairs):
        return {pair: self._scores[(pair.anchor, pair.candidate)] for pair in pairs}

    def neighbors_many(self, requests):
        return {req: tuple(self._neighborhoods.get(req.anchor, ()))[: req.k] for req in requests}


def _contract(hard=True):
    return SemanticContract(
        name="support",
        version="1",
        clauses=[
            TripletClause("q:delete", "doc:delete", "doc:newsletter", hard=hard),
            NeighborClause("q:billing", ("doc:invoice",), min_recall=1.0, candidate_k=1),
        ],
    )


def test_change_control_blocks_hard_regression_even_when_other_clause_improves():
    contract = _contract()
    baseline = FakeOracle(
        "prod",
        scores={("q:delete", "doc:delete"): 2.0, ("q:delete", "doc:newsletter"): 1.0},
        neighborhoods={"q:billing": ("doc:other",)},
    )
    candidate = FakeOracle(
        "candidate",
        scores={("q:delete", "doc:delete"): 0.5, ("q:delete", "doc:newsletter"): 1.5},
        neighborhoods={"q:billing": ("doc:invoice",)},
    )

    report = compare_protocol_audits(
        contract,
        audit_contract_v1(contract, baseline),
        audit_contract_v1(contract, candidate),
        policy=ReleasePolicy(max_score_drop=1.0, allow_soft_regressions=10),
    )

    assert report.deployment_eligible is False
    assert len(report.hard_regressions) == 1
    assert report.hard_regressions[0].clause_index == 0
    assert len(report.improvements) == 1
    assert "new hard-clause regression" in " ".join(report.blockers)
    assert "Semantic ABI change control — BLOCK" in report.to_markdown()


def test_change_control_blocks_new_missing_clause():
    contract = _contract(hard=False)
    baseline = FakeOracle(
        "prod",
        scores={("q:delete", "doc:delete"): 2.0, ("q:delete", "doc:newsletter"): 1.0},
        neighborhoods={"q:billing": ("doc:invoice",)},
    )
    candidate = FakeOracle(
        "candidate",
        scores={("q:delete", "doc:delete"): 2.0, ("q:delete", "doc:newsletter"): 1.0},
        neighborhoods={"q:billing": ("doc:invoice",)},
        missing={"doc:invoice"},
    )

    report = compare_protocol_audits(
        contract,
        audit_contract_v1(contract, baseline),
        audit_contract_v1(contract, candidate),
        policy=ReleasePolicy(max_score_drop=1.0, allow_soft_regressions=10),
    )

    assert report.deployment_eligible is False
    assert len(report.new_missing) == 1
    assert report.new_missing[0].status == "new_missing"


def test_change_control_can_grandfather_preexisting_hard_debt_without_allowing_new_debt():
    contract = _contract()
    baseline = FakeOracle(
        "prod",
        scores={("q:delete", "doc:delete"): 0.5, ("q:delete", "doc:newsletter"): 1.5},
        neighborhoods={"q:billing": ("doc:invoice",)},
    )
    candidate = FakeOracle(
        "candidate",
        scores={("q:delete", "doc:delete"): 0.5, ("q:delete", "doc:newsletter"): 1.5},
        neighborhoods={"q:billing": ("doc:invoice",)},
    )

    report = compare_protocol_audits(
        contract,
        audit_contract_v1(contract, baseline),
        audit_contract_v1(contract, candidate),
        policy=ReleasePolicy(
            max_score_drop=0.0,
            allow_soft_regressions=0,
            require_absolute_hard_pass=True,
            allow_existing_hard_failures=True,
        ),
    )

    assert report.deployment_eligible is True
    assert report.hard_regressions == []
    assert report.blockers == ()
