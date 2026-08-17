from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from semantic_atlas import CalibrationEvent, NeighborClause, SemanticContract, TransitionAtlas, TripletClause, calibrate_semantic_risk
from semantic_atlas.release import EvidenceReference, ImplementationFingerprint, make_release_certificate
from semantic_atlas.support import contract_coverage, estimate_local_semantic_risk


def _normalize(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)


def _rank(query: np.ndarray, docs: np.ndarray, k: int) -> np.ndarray:
    return np.argsort(-(docs @ query))[:k]


def _metrics(query_vectors: np.ndarray, doc_vectors: np.ndarray, query_ids: list[str], doc_ids: list[str], qrels: dict[str, set[str]], k: int = 10) -> dict[str, float]:
    doc_lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    recalls: list[float] = []
    ndcgs: list[float] = []
    reciprocal: list[float] = []
    hit: list[float] = []
    for qi, qid in enumerate(query_ids):
        relevant = {doc_lookup[d] for d in qrels.get(qid, set()) if d in doc_lookup}
        if not relevant:
            continue
        order = _rank(query_vectors[qi], doc_vectors, k)
        found = [int(idx) in relevant for idx in order]
        recalls.append(sum(found) / len(relevant))
        hit.append(float(any(found)))
        dcg = sum((1.0 / math.log2(rank + 2)) for rank, ok in enumerate(found) if ok)
        ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(relevant), k)))
        ndcgs.append(dcg / ideal if ideal else 0.0)
        rr = 0.0
        for rank, ok in enumerate(found, start=1):
            if ok:
                rr = 1.0 / rank
                break
        reciprocal.append(rr)
    return {
        "queries": len(recalls),
        f"recall@{k}": float(np.mean(recalls)) if recalls else 0.0,
        f"ndcg@{k}": float(np.mean(ndcgs)) if ndcgs else 0.0,
        f"mrr@{k}": float(np.mean(reciprocal)) if reciprocal else 0.0,
        f"hit_rate@{k}": float(np.mean(hit)) if hit else 0.0,
    }


def _qrel_dict(rows: Iterable[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in rows:
        if float(row["score"]) <= 0:
            continue
        out.setdefault(str(row["query-id"]), set()).add(str(row["corpus-id"]))
    return out


def _select_query_ids(qrels: dict[str, set[str]], limit: int, seed: int) -> list[str]:
    ids = sorted(qrels)
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    return ids[: min(limit, len(ids))]


def _build_contract(query_ids: list[str], qrels: dict[str, set[str]], doc_ids: list[str], *, seed: int) -> SemanticContract:
    rng = np.random.default_rng(seed)
    docs = np.asarray(doc_ids, dtype=object)
    doc_universe = set(doc_ids)
    contract = SemanticContract(name="scifact-application-semantics", version="1", metadata={"dataset": "mteb/scifact", "semantics": "qrels relevance"})
    for qid in query_ids:
        relevant = sorted(qrels.get(qid, set()) & doc_universe)
        if not relevant:
            continue
        qkey = f"q:{qid}"
        expected = tuple(f"d:{doc_id}" for doc_id in relevant)
        contract.add(NeighborClause(qkey, expected, min_recall=1.0 / len(expected), candidate_k=10, weight=2.0, source="scifact_qrels"))
        nonrelevant = docs[~np.isin(docs, np.asarray(relevant, dtype=object))]
        if len(nonrelevant):
            negative = str(rng.choice(nonrelevant))
            positive = str(rng.choice(np.asarray(relevant, dtype=object)))
            contract.add(TripletClause(qkey, f"d:{positive}", f"d:{negative}", margin=0.0, weight=1.0, source="scifact_qrels"))
    return contract


def _combined_vectors(query_ids: list[str], query_vectors: np.ndarray, doc_ids: list[str], doc_vectors: np.ndarray) -> dict[str, np.ndarray]:
    out = {f"d:{doc_id}": doc_vectors[i] for i, doc_id in enumerate(doc_ids)}
    out.update({f"q:{qid}": query_vectors[i] for i, qid in enumerate(query_ids)})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Real neural-encoder Semantic ABI / migration benchmark on SciFact")
    parser.add_argument("--old-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--new-model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=500)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--anchor-fraction", type=float, default=0.20)
    parser.add_argument("--target-risk", type=float, default=0.20)
    parser.add_argument("--delta", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", default="artifacts/real_encoder_report.json")
    parser.add_argument("--npz", default="artifacts/scifact_pair.npz")
    args = parser.parse_args()

    from datasets import load_dataset
    from huggingface_hub import model_info
    from sentence_transformers import SentenceTransformer

    corpus_rows = load_dataset("mteb/scifact", "corpus", split="corpus")
    query_rows = load_dataset("mteb/scifact", "queries", split="queries")
    train_qrel_rows = load_dataset("mteb/scifact", "default", split="train")
    test_qrel_rows = load_dataset("mteb/scifact", "default", split="test")

    corpus = {str(row["_id"]): (str(row.get("title") or "") + "\n" + str(row["text"])).strip() for row in corpus_rows}
    queries = {str(row["_id"]): str(row["text"]) for row in query_rows}
    train_qrels = _qrel_dict(train_qrel_rows)
    test_qrels = _qrel_dict(test_qrel_rows)
    train_ids = [qid for qid in _select_query_ids(train_qrels, args.train_queries, args.seed) if qid in queries]
    test_ids = [qid for qid in _select_query_ids(test_qrels, args.test_queries, args.seed + 1) if qid in queries]

    required_docs: set[str] = set()
    for qid in train_ids:
        required_docs.update(train_qrels.get(qid, set()))
    for qid in test_ids:
        required_docs.update(test_qrels.get(qid, set()))
    required_docs &= set(corpus)

    rng = np.random.default_rng(args.seed)
    distractors = [doc_id for doc_id in sorted(corpus) if doc_id not in required_docs]
    rng.shuffle(distractors)
    doc_ids = (sorted(required_docs) + distractors[: max(0, args.max_docs - len(required_docs))])[: args.max_docs]
    doc_texts = [corpus[doc_id] for doc_id in doc_ids]
    train_texts = [queries[qid] for qid in train_ids]
    test_texts = [queries[qid] for qid in test_ids]

    old_revision = str(model_info(args.old_model).sha or "unknown")
    new_revision = str(model_info(args.new_model).sha or "unknown")
    old_model = SentenceTransformer(args.old_model)
    new_model = SentenceTransformer(args.new_model)

    old_docs = _normalize(old_model.encode(doc_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    old_test_q = _normalize(old_model.encode(test_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))

    new_prefix = "Represent this sentence for searching relevant passages: " if "bge" in args.new_model.lower() else ""
    new_docs = _normalize(new_model.encode(doc_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    new_train_q = _normalize(new_model.encode([new_prefix + text for text in train_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    new_test_q = _normalize(new_model.encode([new_prefix + text for text in test_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True))

    anchor_count = max(20, int(round(len(doc_ids) * args.anchor_fraction)))
    anchor_idx = np.sort(rng.choice(len(doc_ids), size=min(anchor_count, len(doc_ids)), replace=False))
    transition = TransitionAtlas.fit("new", "old", new_docs[anchor_idx], old_docs[anchor_idx], chart_size=48, chart_overlap=1.5, validation_fraction=0.20, validation_seed=args.seed)
    local_test_q = _normalize(np.vstack([transition.map(vector).vector for vector in new_test_q]))
    global_test_q = _normalize(np.vstack([transition.global_map.map(vector) for vector in new_test_q]))

    contract_n = max(40, int(round(len(train_ids) * 0.65)))
    contract_ids = train_ids[:contract_n]
    calibration_ids = train_ids[contract_n:]
    contract_query_vectors = new_train_q[:contract_n]
    calibration_query_vectors = new_train_q[contract_n:]
    contract = _build_contract(contract_ids, train_qrels, doc_ids, seed=args.seed)
    candidate_vectors = _combined_vectors(contract_ids, contract_query_vectors, doc_ids, new_docs)
    report = contract.audit(candidate_vectors, implementation=args.new_model)
    coverage = contract_coverage(contract, candidate_vectors)
    landmarks = {object_id: candidate_vectors[object_id] for object_id in report.object_risk if object_id in candidate_vectors}

    doc_lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    calibration_events: list[CalibrationEvent] = []
    calibration_support: list[float] = []
    for i, qid in enumerate(calibration_ids):
        relevant = {doc_lookup[d] for d in train_qrels.get(qid, set()) if d in doc_lookup}
        if not relevant:
            continue
        local = estimate_local_semantic_risk(report, calibration_query_vectors[i], landmarks)
        calibration_support.append(local.support)
        top = _rank(calibration_query_vectors[i], new_docs, 10)
        loss = 0.0 if any(int(idx) in relevant for idx in top) else 1.0
        calibration_events.append(CalibrationEvent(local.risk, loss, object_id=f"q:{qid}", group="scifact-train"))

    certificate = calibrate_semantic_risk(calibration_events, target_risk=args.target_risk, delta=args.delta, threshold_candidates=8, min_selection=max(10, len(calibration_events) // 6), min_certification=max(15, len(calibration_events) // 5), seed=args.seed)

    selective_losses: list[float] = []
    heldout_support: list[float] = []
    selective_total = accepted_total = 0
    for i, qid in enumerate(test_ids):
        relevant = {doc_lookup[d] for d in test_qrels.get(qid, set()) if d in doc_lookup}
        if not relevant:
            continue
        selective_total += 1
        local = estimate_local_semantic_risk(report, new_test_q[i], landmarks)
        heldout_support.append(local.support)
        if not certificate.accepts(local.risk):
            continue
        accepted_total += 1
        top = _rank(new_test_q[i], new_docs, 10)
        selective_losses.append(0.0 if any(int(idx) in relevant for idx in top) else 1.0)

    result = {
        "dataset": "mteb/scifact",
        "old_model": args.old_model,
        "old_revision": old_revision,
        "new_model": args.new_model,
        "new_revision": new_revision,
        "old_dimensions": int(old_docs.shape[1]),
        "new_dimensions": int(new_docs.shape[1]),
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "test_queries": len(test_ids),
        "anchor_count": int(len(anchor_idx)),
        "direct_old": _metrics(old_test_q, old_docs, test_ids, doc_ids, test_qrels),
        "direct_new": _metrics(new_test_q, new_docs, test_ids, doc_ids, test_qrels),
        "transport_local_new_to_old": _metrics(local_test_q, old_docs, test_ids, doc_ids, test_qrels),
        "transport_global_new_to_old": _metrics(global_test_q, old_docs, test_ids, doc_ids, test_qrels),
        "transition": {
            "held_out": bool(transition.fit_diagnostics.held_out),
            "mean_pair_cosine": float(transition.fit_diagnostics.mean_pair_cosine),
            "p10_pair_cosine": float(transition.fit_diagnostics.p10_pair_cosine),
            "neighborhood_jaccard": float(transition.fit_diagnostics.neighborhood_jaccard),
            "confidence": float(transition.confidence),
        },
        "semantic_abi": {
            "contract_digest": contract.digest,
            "contract_clauses": len(contract.clauses),
            "contract_object_coverage": coverage.object_coverage,
            "candidate_score": float(report.score),
            "hard_pass": bool(report.hard_pass),
            "calibration_events": len(calibration_events),
            "mean_calibration_support": float(np.mean(calibration_support)) if calibration_support else 0.0,
            "risk_certificate": asdict(certificate),
            "held_out_test_accepted": accepted_total,
            "held_out_test_total": selective_total,
            "held_out_test_coverage": accepted_total / max(1, selective_total),
            "held_out_test_realized_risk": float(np.mean(selective_losses)) if selective_losses else None,
            "mean_held_out_support": float(np.mean(heldout_support)) if heldout_support else 0.0,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    npz = Path(args.npz)
    npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(npz, old_docs=old_docs, new_docs=new_docs, new_queries=new_test_q)

    preprocessing_payload = f"query_prefix={new_prefix}|normalize_embeddings=true|sentence_transformers_default_pooling"
    fingerprint = ImplementationFingerprint(
        implementation_id=f"{args.new_model}@{new_revision[:12]}",
        model_id=args.new_model,
        revision=new_revision,
        dimensions=int(new_docs.shape[1]),
        preprocessing_digest=hashlib.sha256(preprocessing_payload.encode("utf-8")).hexdigest(),
        metadata={"dataset": "mteb/scifact", "legacy_model": args.old_model, "legacy_revision": old_revision},
    )
    evidence = EvidenceReference(name=output.name, sha256=hashlib.sha256(output.read_bytes()).hexdigest(), kind="real-neural-encoder-benchmark")
    release_certificate = make_release_certificate(
        fingerprint,
        report,
        coverage,
        certificate,
        evidence=[evidence],
        status="certified" if certificate.certified and report.hard_pass else "uncertified",
        metadata={"held_out_test_coverage": result["semantic_abi"]["held_out_test_coverage"], "held_out_test_realized_risk": result["semantic_abi"]["held_out_test_realized_risk"]},
    )
    release_certificate.save(output.parent / "semantic_release_certificate.json")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
