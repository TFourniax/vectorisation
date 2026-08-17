"""Held-out test of clause-incidence-aware repair on SciFact/BGE corruption.

This benchmark uses the same application + coverage-oriented integrity contract
and 10% document-embedding permutation regime as the prior integrity-canary
experiment. It compares the new role-aware incidence planner with the existing
highest-risk, risk/diversity and violation-coverage baselines.

No test qrels participate in contract construction, corruption diagnosis or
planner selection. Test qrels are read only after a repair set has been chosen.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from semantic_atlas import audit_contract
from semantic_atlas.repair_incidence import plan_repairs_by_clause_incidence
from semantic_repair_integrity_scifact_benchmark import (
    QueryDocumentOracle,
    build_integrity_contract,
    merge_contracts,
    test_retrieval,
)
from semantic_repair_scifact_benchmark import (
    apply_repairs,
    corrupt_by_permutation,
    planner_selection,
    recovery_fraction,
    selected_corruption_precision,
)
from semantic_abi_multidataset_benchmark import (
    build_contract,
    choose_corpus,
    normalize,
    qrel_dict,
    select_ids,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Clause-incidence-aware neural repair benchmark")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=350)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--integrity-anchors", type=int, default=250)
    parser.add_argument("--corruption-fraction", type=float, default=0.10)
    parser.add_argument("--budgets", default="10,25,50,100,180")
    parser.add_argument("--seed", type=int, default=619)
    parser.add_argument("--output", default="artifacts/scifact_repair_incidence.json")
    args = parser.parse_args()

    from datasets import load_dataset
    from sentence_transformers import SentenceTransformer

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

    model = SentenceTransformer(args.model)
    prefix = "Represent this sentence for searching relevant passages: " if "bge" in args.model.lower() else ""
    clean_docs = normalize(model.encode([corpus[doc_id] for doc_id in doc_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    train_q = normalize(model.encode([prefix + queries[qid] for qid in train_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    test_q = normalize(model.encode([prefix + queries[qid] for qid in test_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))

    application = build_contract("scifact-repair", train_ids, train_qrels, doc_ids, seed=args.seed)
    integrity = build_integrity_contract(
        doc_ids,
        clean_docs,
        anchors=args.integrity_anchors,
        anchor_policy="coverage",
        seed=args.seed + 11,
    )
    contract = merge_contracts(application, integrity)

    clean_metrics = test_retrieval(test_q, clean_docs, test_ids, doc_ids, test_qrels)
    clean_ndcg = float(clean_metrics["ndcg@10"])
    corrupted_docs, corrupted_tuple = corrupt_by_permutation(
        clean_docs,
        fraction=args.corruption_fraction,
        seed=args.seed,
    )
    corrupted_indices = set(corrupted_tuple)
    corrupted_metrics = test_retrieval(test_q, corrupted_docs, test_ids, doc_ids, test_qrels)
    corrupted_ndcg = float(corrupted_metrics["ndcg@10"])

    oracle = QueryDocumentOracle(train_ids, doc_ids, train_q, corrupted_docs, implementation="corrupted-bge")
    report = audit_contract(contract, oracle)
    document_object_ids = [f"d:{doc_id}" for doc_id in doc_ids]
    budgets = [int(value) for value in args.budgets.split(",") if value.strip()]
    rows = []

    for budget in budgets:
        selections: dict[str, list[str]] = {}
        for planner in ("highest-risk", "risk-diversity", "coverage"):
            selections[planner] = planner_selection(
                report,
                corrupted_docs,
                doc_ids,
                planner=planner,
                budget=budget,
                seed=args.seed + budget,
            )

        incidence = plan_repairs_by_clause_incidence(
            contract,
            report,
            oracle,
            budget=float(budget),
            repairable_ids=set(document_object_ids),
        )
        selections["clause-incidence"] = [candidate.object_id for candidate in incidence.candidates]

        methods = {}
        for planner, selected in selections.items():
            repaired = apply_repairs(corrupted_docs, clean_docs, doc_ids, selected)
            metrics = test_retrieval(test_q, repaired, test_ids, doc_ids, test_qrels)
            ndcg = float(metrics["ndcg@10"])
            methods[planner] = {
                "selected_documents": len(selected),
                "corruption_precision": selected_corruption_precision(selected, corrupted_indices, doc_ids),
                "heldout_ndcg": ndcg,
                "heldout_recall": float(metrics["recall@10"]),
                "ndcg_recovery_fraction": recovery_fraction(ndcg, corrupted_ndcg, clean_ndcg),
            }
            if planner == "clause-incidence":
                methods[planner]["blame_mass_coverage"] = incidence.blame_mass_coverage
                methods[planner]["unattributed_violation_mass"] = incidence.unattributed_violation_mass

        rows.append({"budget": budget, "methods": methods})

    result = {
        "benchmark": "semantic-repair-clause-incidence-scifact-v1",
        "dataset": "mteb/scifact",
        "model": args.model,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "corruption_fraction": args.corruption_fraction,
        "corrupted_documents": len(corrupted_indices),
        "application_contract_digest": application.digest,
        "integrity_contract_digest": integrity.digest,
        "combined_contract_digest": contract.digest,
        "clean_retrieval": clean_metrics,
        "corrupted_retrieval": corrupted_metrics,
        "rows": rows,
        "guardrail": (
            "Clause-incidence weights are explicit diagnostic priors, not causal truth. Promotion requires held-out economic improvement over simple highest-risk and existing coverage planners."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
