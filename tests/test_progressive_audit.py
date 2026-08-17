from semantic_atlas.contracts import SemanticContract, TripletClause
from semantic_atlas.oracle import CallbackSemanticOracle
from semantic_atlas.progressive_audit import progressive_semantic_audit


def make_system(count=300, broken=()):
    broken = set(broken)
    clauses = []
    objects = set()
    for i in range(count):
        anchor, positive, negative = f"a{i}", f"p{i}", f"n{i}"
        clauses.append(TripletClause(anchor, positive, negative, weight=1.0))
        objects.update((anchor, positive, negative))
    contract = SemanticContract("progressive", "1", clauses=clauses)

    def similarity(left, right):
        if left == right:
            return 1.0
        if left.startswith("a"):
            index = int(left[1:])
            if right == f"p{index}":
                return 0.0 if index in broken else 1.0
            if right == f"n{index}":
                return 1.0 if index in broken else 0.0
        if right.startswith("a"):
            return similarity(right, left)
        return 0.0

    oracle = CallbackSemanticOracle(
        frozenset(objects),
        similarity,
        lambda _anchor, _k: (),
        implementation="synthetic-ranker",
    )
    return contract, oracle


def test_progressive_audit_passes_healthy_contract_without_full_audit():
    contract, oracle = make_system(300)
    result = progressive_semantic_audit(
        contract,
        oracle,
        max_soft_violation_rate=0.10,
        delta=0.05,
        batch_size=50,
        max_draws=500,
        seed=4,
    )
    assert result.decision == "pass"
    assert not result.used_full_audit
    assert result.upper_violation_bound <= 0.10
    assert result.unique_soft_clauses_evaluated < 300


def test_progressive_audit_fails_heavily_broken_contract_probabilistically():
    contract, oracle = make_system(300, broken=range(120))
    result = progressive_semantic_audit(
        contract,
        oracle,
        max_soft_violation_rate=0.10,
        delta=0.05,
        batch_size=50,
        max_draws=500,
        seed=9,
    )
    assert result.decision == "fail"
    assert not result.used_full_audit
    assert result.lower_violation_bound > 0.10
    assert result.unique_soft_clauses_evaluated < 300


def test_progressive_audit_falls_back_to_exact_full_decision_near_boundary():
    contract, oracle = make_system(120, broken=range(12))
    result = progressive_semantic_audit(
        contract,
        oracle,
        max_soft_violation_rate=0.10,
        delta=0.01,
        batch_size=10,
        max_draws=20,
        seed=3,
        fallback_to_full_audit=True,
    )
    assert result.used_full_audit
    assert result.exact_soft_violation_rate == 0.10
    assert result.decision == "pass"
    assert result.unique_soft_clauses_evaluated == 120


def test_progressive_audit_evaluates_hard_clauses_first():
    contract, oracle = make_system(50, broken={0})
    contract.clauses[0].hard = True
    result = progressive_semantic_audit(contract, oracle, max_soft_violation_rate=0.20)
    assert result.decision == "fail"
    assert not result.hard_pass
    assert result.draws == 0
    assert result.hard_clauses_evaluated == 1
