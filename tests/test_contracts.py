from dataclasses import replace

import numpy as np

from semantic_atlas.contracts import (
    ContractLedger,
    SemanticABIGate,
    SemanticContract,
    TripletClause,
    capture_behavior_contract,
    contract_from_labels,
)


def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def orthogonal(rng, d):
    q, _ = np.linalg.qr(rng.normal(size=(d, d)))
    return q.astype(np.float32)


def mapping(x):
    return {str(i): x[i] for i in range(len(x))}


def test_behavior_contract_is_coordinate_invariant_under_orthogonal_rotation():
    rng = np.random.default_rng(1)
    x = normalize(rng.normal(size=(80, 12)))
    contract = capture_behavior_contract(mapping(x), anchors=[str(i) for i in range(30)], k=6, triplets_per_anchor=2)
    base = contract.audit(mapping(x), implementation="base")
    rotated = contract.audit(mapping(normalize(x @ orthogonal(rng, 12))), implementation="rotated")
    assert base.score > 0.99
    assert rotated.score > 0.99
    assert rotated.hard_pass


def test_contract_detects_local_identity_corruption_and_hotspots():
    rng = np.random.default_rng(2)
    centers = normalize(rng.normal(size=(4, 10)))
    rows = [normalize(c + rng.normal(scale=0.08, size=(30, 10))) for c in centers]
    x = np.vstack(rows)
    labels = {str(i): i // 30 for i in range(len(x))}
    vectors = mapping(x)
    contract = contract_from_labels(vectors, labels, anchors=[str(i) for i in range(len(x))], triplets_per_anchor=4)
    good = contract.audit(vectors)
    corrupted = x.copy()
    bad_ids = list(range(0, 12))
    corrupted[bad_ids] = corrupted[np.arange(90, 102)]
    bad = contract.audit(mapping(corrupted))
    assert good.score > 0.92
    assert bad.score < good.score - 0.07
    risky = {int(i) for i, _ in bad.top_risks(25)}
    assert len(risky & set(bad_ids)) >= 6


def test_contract_digest_ignores_wall_clock_but_changes_with_semantics():
    a = SemanticContract("abi", "1").add(TripletClause("a", "b", "c"))
    b = SemanticContract("abi", "1").add(TripletClause("a", "b", "c"))
    assert a.digest == b.digest
    c = SemanticContract("abi", "1").add(TripletClause("a", "c", "b"))
    assert c.digest != a.digest


def test_ledger_detects_tampering(tmp_path):
    a = SemanticContract("abi", "1").add(TripletClause("a", "b", "c"))
    b = SemanticContract("abi", "2", parent_digest=a.digest).add(TripletClause("a", "b", "d"))
    ledger = ContractLedger()
    ledger.append(a, note="baseline")
    ledger.append(b, note="upgrade")
    assert ledger.verify()
    path = ledger.save(tmp_path / "ledger.jsonl")
    assert ContractLedger.load(path).verify()
    ledger.entries[1] = replace(ledger.entries[1], note="tampered")
    assert not ledger.verify()


def test_semantic_abi_gate_falls_back_from_locally_broken_implementation():
    rng = np.random.default_rng(4)
    centers = normalize(rng.normal(size=(3, 8)))
    x = np.vstack([normalize(c + rng.normal(scale=0.06, size=(30, 8))) for c in centers])
    labels = {str(i): i // 30 for i in range(90)}
    vectors = mapping(x)
    contract = contract_from_labels(vectors, labels, anchors=[str(i) for i in range(90)], triplets_per_anchor=5)
    legacy = contract.audit(vectors, implementation="legacy")
    new = x.copy()
    broken = list(range(30, 45))
    new[broken] = new[np.arange(60, 75)]
    new_vectors = mapping(new)
    candidate = contract.audit(new_vectors, implementation="new")
    gate = SemanticABIGate({"legacy": (legacy, vectors), "new": (candidate, new_vectors)}, max_local_risk=0.20, min_global_score=0.70)
    query_near_broken = normalize((centers[1] + rng.normal(scale=0.01, size=8)).reshape(1, -1))[0]
    decision = gate.choose({"legacy": query_near_broken, "new": query_near_broken}, prefer=("new", "legacy"))
    assert decision.accepted
    assert decision.implementation == "legacy"
