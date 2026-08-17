"""Compare semantic rollout risk-certification policies on real SciFact/BGE.

This benchmark intentionally leaves the original real_encoder_scifact_benchmark
unchanged. It recreates the same BGE contract/risk field and compares:

1. split + simultaneous Chernoff/KL certification over several candidate rules;
2. one threshold chosen only on the selection split, then frozen and certified
   with an exact one-sided binomial bound on the independent holdout.

The second policy is not allowed to inspect holdout labels and then switch to a
narrower threshold. If its pre-registered threshold fails, it abstains.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from semantic_atlas import CalibrationEvent, calibrate_semantic_risk, calibrate_semantic_risk_preregistered
from semantic_atlas.support import estimate_local_semantic_risk
from real_encoder_scifact_benchmark import (
    _build_contract,
    _combined_vectors,
    _normalize,
    _qrel_dict,
    _rank,
    _risk_auc,
    _select_query_ids,
)


def evaluate_certificate(certificate, proxy, losses):
    accepted = [loss for risk, loss in zip(proxy, losses) if certificate.accepts(risk)]
    return {
        "certificate": asdict(certificate),
        "held_out_accepted": len(accepted),
        "held_out_total": len(losses),
        "held_out_coverage": len(accepted) / max(1, len(losses)),
        "held_out_realized_risk": float(np.mean(accepted)) if accepted else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Semantic ABI risk certification methods on SciFact")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=500)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--delta", type=float, default=0.10)
    parser.add_argument("--selection-risk-fraction", type=float, default=0.75)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", default="artifacts/risk_calibration_comparison.json")
    args = parser.parse_args()

    from datasets import load_dataset
    from huggingface_hub import model_info
    from sentence_transformers import SentenceTransformer

    corpus_rows = load_dataset("mteb/scifact", "corpus", split="corpus")
    query_rows = load_dataset("mteb/scifact", "queries", split="queries")
    train_qrel_rows = load_dataset("mteb/scifact", "default", split="train")
    test_qrel_rows = load_dataset("mteb/scifact", "default", split="test")

    corpus = {
        str(row["_id"]): (str(row.get("title") or "") + "\n" + str(row["text"])).strip()
        for row in corpus_rows
    }
    queries = {str(row["_id"]): str(row["text"]) for row in query_rows}
    train_qrels, test_qrels = _qrel_dict(train_qrel_rows), _qrel_dict(test_qrel_rows)
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

    revision = str(model_info(args.model).sha or "unknown")
    model = SentenceTransformer(args.model)
    prefix = "Represent this sentence for searching relevant passages: " if "bge" in args.model.lower() else ""
    docs = _normalize(model.encode(doc_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    train_q = _normalize(
        model.encode([prefix + text for text in train_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    )
    test_q = _normalize(
        model.encode([prefix + text for text in test_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    )

    contract_n = max(40, int(round(len(train_ids) * 0.65)))
    contract_ids, calibration_ids = train_ids[:contract_n], train_ids[contract_n:]
    contract = _build_contract(contract_ids, train_qrels, doc_ids, seed=args.seed)
    candidate = _combined_vectors(contract_ids, train_q[:contract_n], doc_ids, docs)
    report = contract.audit(candidate, implementation=args.model)
    landmarks = {object_id: candidate[object_id] for object_id in report.object_risk if object_id in candidate}
    doc_lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}

    calibration_events: list[CalibrationEvent] = []
    calibration_proxy: list[float] = []
    calibration_losses: list[float] = []
    for offset, qid in enumerate(calibration_ids, start=contract_n):
        relevant = {doc_lookup[d] for d in train_qrels.get(qid, set()) if d in doc_lookup}
        if not relevant:
            continue
        local = estimate_local_semantic_risk(report, train_q[offset], landmarks)
        top = _rank(train_q[offset], docs, 10)
        loss = 0.0 if any(int(index) in relevant for index in top) else 1.0
        calibration_proxy.append(local.risk)
        calibration_losses.append(loss)
        calibration_events.append(CalibrationEvent(local.risk, loss, object_id=f"q:{qid}", group="scifact-train"))

    test_proxy: list[float] = []
    test_losses: list[float] = []
    for i, qid in enumerate(test_ids):
        relevant = {doc_lookup[d] for d in test_qrels.get(qid, set()) if d in doc_lookup}
        if not relevant:
            continue
        local = estimate_local_semantic_risk(report, test_q[i], landmarks)
        top = _rank(test_q[i], docs, 10)
        loss = 0.0 if any(int(index) in relevant for index in top) else 1.0
        test_proxy.append(local.risk)
        test_losses.append(loss)

    targets = (0.05, 0.10, 0.15, 0.20)
    rows = []
    for target in targets:
        common = {
            "target_risk": target,
            "delta": args.delta,
            "threshold_candidates": 8,
            "min_selection": max(10, len(calibration_events) // 6),
            "min_certification": max(15, len(calibration_events) // 5),
            "seed": args.seed,
        }
        simultaneous = calibrate_semantic_risk(calibration_events, **common)
        preregistered = calibrate_semantic_risk_preregistered(
            calibration_events,
            selection_risk_fraction=args.selection_risk_fraction,
            **common,
        )
        rows.append(
            {
                "target_risk": target,
                "simultaneous_kl": evaluate_certificate(simultaneous, test_proxy, test_losses),
                "preregistered_exact": evaluate_certificate(preregistered, test_proxy, test_losses),
            }
        )

    result = {
        "dataset": "mteb/scifact",
        "model": args.model,
        "revision": revision,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "test_queries": len(test_ids),
        "contract_clauses": len(contract.clauses),
        "contract_score": float(report.score),
        "calibration_events": len(calibration_events),
        "calibration_failure_rate": float(np.mean(calibration_losses)) if calibration_losses else None,
        "held_out_failure_rate": float(np.mean(test_losses)) if test_losses else None,
        "calibration_risk_auc": _risk_auc(calibration_proxy, calibration_losses),
        "held_out_risk_auc": _risk_auc(test_proxy, test_losses),
        "selection_risk_fraction": args.selection_risk_fraction,
        "methods": {
            "simultaneous_kl": "selection proposes multiple rules; independent certification tests the family with union-corrected Chernoff/KL bounds",
            "preregistered_exact": "selection freezes exactly one rule under an internal slack budget; independent certification uses a one-sided exact binomial bound and cannot switch rules after holdout labels are seen",
        },
        "risk_coverage_curve": rows,
        "warning": (
            "Both guarantees assume certification and deployment are exchangeable enough for the Bernoulli risk statement. "
            "Neither method provides arbitrary covariate-shift guarantees."
        ),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
