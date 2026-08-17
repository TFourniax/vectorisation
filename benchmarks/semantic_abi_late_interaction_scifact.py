from __future__ import annotations

"""Real late-interaction portability gate for Semantic ABI Protocol v1.

The application contract is authored exclusively from SciFact train qrels. The
same contract is audited against lexical BM25 and a real ColBERTv2 MaxSim
retriever. Official test qrels are used only for held-out retrieval metrics.

Primary gate: the protocol/compiler and conformance suite must execute the
unchanged contract against an explicitly asymmetric multi-vector retriever.
Retrieval quality is reported as evidence, not used to tune the contract.
"""

import argparse
import json
import math
from pathlib import Path
import tempfile

import numpy as np

from semantic_atlas.conformance import check_oracle_conformance
from semantic_atlas.late_interaction import LateInteractionOracleV1
from semantic_atlas.protocol_v1 import ScorePair, audit_contract_v1
from semantic_abi_multidataset_benchmark import (
    BM25Index,
    build_contract,
    choose_corpus,
    make_oracle,
    qrel_dict,
    score_metrics,
    select_ids,
)


def as_numpy(value) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value, dtype=np.float32)


def ranking_metrics(rankings, query_ids, qrels, doc_ids, *, k=10):
    universe = set(doc_ids)
    recalls, hits, mrrs, ndcgs = [], [], [], []
    for qid, rows in zip(query_ids, rankings):
        relevant = set(qrels.get(qid, set())) & universe
        if not relevant:
            continue
        ranked = [str(row["id"]) for row in rows[:k]]
        found = [doc_id in relevant for doc_id in ranked]
        recalls.append(sum(found) / len(relevant))
        hits.append(float(any(found)))
        mrrs.append(next((1.0 / rank for rank, ok in enumerate(found, 1) if ok), 0.0))
        dcg = sum(1.0 / math.log2(rank + 2) for rank, ok in enumerate(found) if ok)
        ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(relevant), k)))
        ndcgs.append(dcg / ideal if ideal else 0.0)
    return {
        "queries": len(recalls),
        f"recall@{k}": float(np.mean(recalls)) if recalls else 0.0,
        f"hit_rate@{k}": float(np.mean(hits)) if hits else 0.0,
        f"mrr@{k}": float(np.mean(mrrs)) if mrrs else 0.0,
        f"ndcg@{k}": float(np.mean(ndcgs)) if ndcgs else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="lightonai/colbertv2.0")
    parser.add_argument("--train-queries", type=int, default=300)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=827)
    parser.add_argument("--output", default="artifacts/scifact_late_interaction_protocol_v1.json")
    args = parser.parse_args()

    from datasets import load_dataset
    from pylate import indexes, models, retrieve

    corpus_rows = load_dataset("mteb/scifact", "corpus", split="corpus")
    query_rows = load_dataset("mteb/scifact", "queries", split="queries")
    train_rows = load_dataset("mteb/scifact", "default", split="train")
    test_rows = load_dataset("mteb/scifact", "default", split="test")

    corpus = {
        str(row["_id"]): (str(row.get("title") or "") + "\n" + str(row["text"])).strip()
        for row in corpus_rows
    }
    queries = {str(row["_id"]): str(row["text"]) for row in query_rows}
    train_qrels, test_qrels = qrel_dict(train_rows), qrel_dict(test_rows)
    train_ids = [qid for qid in select_ids(train_qrels, args.train_queries, args.seed) if qid in queries]
    test_ids = [qid for qid in select_ids(test_qrels, args.test_queries, args.seed + 1) if qid in queries]
    doc_ids = choose_corpus(corpus, train_ids, test_ids, train_qrels, test_qrels, max_docs=args.max_docs, seed=args.seed)
    doc_set = set(doc_ids)
    train_ids = [qid for qid in train_ids if train_qrels.get(qid, set()) & doc_set]
    test_ids = [qid for qid in test_ids if test_qrels.get(qid, set()) & doc_set]
    doc_texts = [corpus[doc_id] for doc_id in doc_ids]

    contract = build_contract("scifact", train_ids, train_qrels, doc_ids, seed=args.seed)

    # Cheap independent sparse baseline under the exact same contract.
    bm25 = BM25Index(doc_ids, doc_texts)
    bm25_train = np.vstack([bm25.scores(queries[qid]) for qid in train_ids])
    bm25_test = np.vstack([bm25.scores(queries[qid]) for qid in test_ids])
    bm25_audit = audit_contract_v1(contract, make_oracle("bm25-sparse", train_ids, doc_ids, bm25_train))
    bm25_metrics = score_metrics(bm25_test, test_ids, doc_ids, test_qrels, k=10)

    model = models.ColBERT(model_name_or_path=args.model, device="cpu")
    doc_embeddings = model.encode(doc_texts, batch_size=args.batch_size, is_query=False, show_progress_bar=True)
    train_embeddings = model.encode([queries[qid] for qid in train_ids], batch_size=args.batch_size, is_query=True, show_progress_bar=True)
    test_embeddings = model.encode([queries[qid] for qid in test_ids], batch_size=args.batch_size, is_query=True, show_progress_bar=True)

    with tempfile.TemporaryDirectory(prefix="semantic-abi-colbert-") as index_dir:
        index = indexes.Voyager(index_folder=index_dir, index_name="scifact", override=True)
        index.add_documents(documents_ids=doc_ids, documents_embeddings=doc_embeddings)
        retriever = retrieve.ColBERT(index=index)
        train_rankings = retriever.retrieve(queries_embeddings=train_embeddings, k=10)
        test_rankings = retriever.retrieve(queries_embeddings=test_embeddings, k=10)

    query_map = {f"q:{qid}": as_numpy(embedding) for qid, embedding in zip(train_ids, train_embeddings)}
    doc_map = {f"d:{doc_id}": as_numpy(embedding) for doc_id, embedding in zip(doc_ids, doc_embeddings)}
    ranking_map = {
        f"q:{qid}": tuple(f"d:{row['id']}" for row in rows)
        for qid, rows in zip(train_ids, train_rankings)
    }
    colbert = LateInteractionOracleV1(
        query_map,
        doc_map,
        rankings=ranking_map,
        implementation_id=f"colbert-maxsim:{args.model}",
        model_id=args.model,
    )
    colbert_audit = audit_contract_v1(contract, colbert)
    colbert_metrics = ranking_metrics(test_rankings, test_ids, test_qrels, doc_ids, k=10)

    conformance_anchors = [f"q:{qid}" for qid in train_ids[: min(20, len(train_ids))]]
    sample_pairs = []
    for clause in contract.clauses:
        if getattr(clause, "kind", None) == "triplet" and clause.anchor in set(conformance_anchors):
            sample_pairs.extend([ScorePair(clause.anchor, clause.positive), ScorePair(clause.anchor, clause.negative)])
            if len(sample_pairs) >= 20:
                break
    conformance = check_oracle_conformance(
        colbert,
        anchors=conformance_anchors,
        k_values=(1, 5, 10),
        score_pairs=tuple(sample_pairs[:20]),
    )

    result = {
        "benchmark": "semantic-abi-late-interaction-scifact-v1",
        "dataset": "mteb/scifact",
        "model": args.model,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "contract_digest": contract.digest,
        "contract_clauses": len(contract.clauses),
        "test_qrels_used_for_contract": False,
        "implementations": {
            "bm25": {
                "abi": bm25_audit.report.score,
                "hard_pass": bm25_audit.report.hard_pass,
                "retrieval": bm25_metrics,
                "protocol_execution": bm25_audit.snapshot.stats.to_dict(),
            },
            "colbert_late_interaction": {
                "abi": colbert_audit.report.score,
                "hard_pass": colbert_audit.report.hard_pass,
                "retrieval": colbert_metrics,
                "manifest": colbert.manifest.to_dict(),
                "manifest_digest": colbert.manifest.digest,
                "protocol_execution": colbert_audit.snapshot.stats.to_dict(),
                "conformance": conformance.to_dict(),
            },
        },
        "promotion_gate": {
            "unchanged_contract_digest_across_bm25_and_colbert": bm25_audit.report.contract_digest == colbert_audit.report.contract_digest == contract.digest,
            "colbert_protocol_conformance": conformance.passed,
            "colbert_missing_clauses": colbert_audit.report.missing_clauses,
            "protocol_compilation_round_trips": colbert_audit.snapshot.stats.transport_round_trips,
            "passed": bool(conformance.passed and colbert_audit.report.missing_clauses == 0 and colbert_audit.snapshot.stats.transport_round_trips <= 3),
        },
        "guardrail": "This gate tests protocol/contract portability to a real asymmetric multi-vector retriever. It does not claim ColBERT, MaxSim, Voyager, OpenAPI, or batch RPC as novel, and it does not infer broad quality superiority from one dataset.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
