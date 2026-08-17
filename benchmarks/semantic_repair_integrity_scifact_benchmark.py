"""Can an implementation-integrity contract close the repair blind spot?

The application contract is compiled only from SciFact training qrels. The first
real neural repair benchmark showed that this sparse application contract can be
fully restored while held-out nDCG remains damaged: the contract simply does not
observe every document whose embedding was corrupted.

This experiment adds a *separate* implementation-integrity contract. It is not
application truth and is never used to judge a model migration. Instead, it
freezes a small number of BGE document-neighborhood canaries from the clean index
and asks whether those canaries improve diagnosis/repair of silent corruption of
that same implementation.

No held-out test qrel is used for canary selection, contract construction or
repair planning. Test qrels are used only after repair to measure downstream
recovery.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from semantic_atlas import NeighborClause, SemanticContract, TripletClause, audit_contract
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
    score_metrics,
    select_ids,
)


def farthest_first(vectors: np.ndarray, count: int, *, seed: int) -> list[int]:
    """Deterministic coverage-oriented anchors; never sees corruption labels."""
    x = normalize(vectors)
    count = min(max(1, int(count)), len(x))
    rng = np.random.default_rng(int(seed))
    first = int(rng.integers(0, len(x)))
    chosen = [first]
    best_similarity = x @ x[first]
    for _ in range(1, count):
        index = int(np.argmin(best_similarity))
        chosen.append(index)
        best_similarity = np.maximum(best_similarity, x @ x[index])
        best_similarity[chosen] = 1.0
    return chosen


def build_integrity_contract(
    doc_ids: list[str],
    clean_docs: np.ndarray,
    *,
    anchors: int,
    anchor_policy: str,
    seed: int,
) -> SemanticContract:
    x = normalize(clean_docs)
    if anchor_policy == "coverage":
        selected = farthest_first(x, anchors, seed=seed)
    elif anchor_policy == "random":
        rng = np.random.default_rng(int(seed))
        selected = sorted(int(i) for i in rng.choice(len(x), size=min(anchors, len(x)), replace=False))
    else:
        raise ValueError(anchor_policy)

    similarities = x @ x.T
    np.fill_diagonal(similarities, -np.inf)
    contract = SemanticContract(
        name=f"bge-index-integrity-{anchor_policy}",
        version="1",
        metadata={
            "role": "implementation-integrity-only",
            "anchor_policy": anchor_policy,
            "anchors": len(selected),
            "heldout_qrels_used": False,
        },
    )
    for index in selected:
        order = np.argsort(-similarities[index])
        expected_idx = order[:5]
        expected = tuple(f"d:{doc_ids[int(j)]}" for j in expected_idx)
        contract.add(
            NeighborClause(
                f"d:{doc_ids[index]}",
                expected,
                min_recall=0.6,
                candidate_k=10,
                weight=1.0,
                source=f"clean-bge-integrity:{anchor_policy}",
            )
        )
        positive = int(order[0])
        # Self has similarity -inf and is therefore the final rank. Use the
        # final *non-self* document as the negative control.
        negative = int(order[-2])
        contract.add(
            TripletClause(
                f"d:{doc_ids[index]}",
                f"d:{doc_ids[positive]}",
                f"d:{doc_ids[negative]}",
                weight=0.5,
                source=f"clean-bge-integrity:{anchor_policy}",
            )
        )
    return contract


def merge_contracts(application: SemanticContract, integrity: SemanticContract) -> SemanticContract:
    return SemanticContract(
        name=f"{application.name}+{integrity.name}",
        version="1",
        clauses=[*application.clauses, *integrity.clauses],
        metadata={
            "application_digest": application.digest,
            "integrity_digest": integrity.digest,
            "roles_kept_separate": True,
        },
    )


class QueryDocumentOracle:
    """Query->document plus document->document behavior without query-query leakage."""

    def __init__(
        self,
        train_ids: list[str],
        doc_ids: list[str],
        train_query_vectors: np.ndarray,
        document_vectors: np.ndarray,
        *,
        implementation: str,
    ) -> None:
        self.implementation = implementation
        self.train_ids = list(train_ids)
        self.doc_ids = list(doc_ids)
        self.q_lookup = {qid: i for i, qid in enumerate(self.train_ids)}
        self.d_lookup = {doc_id: i for i, doc_id in enumerate(self.doc_ids)}
        self.qd = np.asarray(normalize(train_query_vectors) @ normalize(document_vectors).T, dtype=np.float64)
        self.dd = np.asarray(normalize(document_vectors) @ normalize(document_vectors).T, dtype=np.float64)
        np.fill_diagonal(self.dd, -np.inf)
        self.object_ids = frozenset([
            *(f"q:{qid}" for qid in self.train_ids),
            *(f"d:{doc_id}" for doc_id in self.doc_ids),
        ])

    def contains(self, object_id: str) -> bool:
        return object_id in self.object_ids

    def similarity(self, left: str, right: str) -> float:
        if left == right:
            return 1.0
        if left.startswith("q:") and right.startswith("d:"):
            return float(self.qd[self.q_lookup[left[2:]], self.d_lookup[right[2:]]])
        if right.startswith("q:") and left.startswith("d:"):
            return float(self.qd[self.q_lookup[right[2:]], self.d_lookup[left[2:]]])
        if left.startswith("d:") and right.startswith("d:"):
            return float(self.dd[self.d_lookup[left[2:]], self.d_lookup[right[2:]]])
        return 0.0

    def neighbors(self, anchor: str, k: int):
        take = min(max(0, int(k)), len(self.doc_ids))
        if anchor.startswith("q:"):
            row = self.qd[self.q_lookup[anchor[2:]]]
        elif anchor.startswith("d:"):
            row = self.dd[self.d_lookup[anchor[2:]]]
            take = min(take, max(0, len(self.doc_ids) - 1))
        else:
            return ()
        order = np.argsort(-row)[:take]
        return tuple(f"d:{self.doc_ids[int(index)]}" for index in order)


def contract_doc_coverage(contract: SemanticContract, doc_ids: list[str]) -> float:
    universe = {f"d:{doc_id}" for doc_id in doc_ids}
    touched = {
        object_id
        for clause in contract.clauses
        for object_id in clause.objects
        if object_id in universe
    }
    return len(touched) / max(1, len(universe))


def evaluate(
    contract: SemanticContract,
    train_ids: list[str],
    test_ids: list[str],
    doc_ids: list[str],
    train_qrels: dict[str, set[str]],
    test_qrels: dict[str, set[str]],
    train_q: np.ndarray,
    test_q: np.ndarray,
    docs: np.ndarray,
    *,
    label: str,
) -> dict:
    oracle = QueryDocumentOracle(train_ids, doc_ids, train_q, docs, implementation=label)
    report = audit_contract(contract, oracle)
    test_scores = np.asarray(normalize(test_q) @ normalize(docs).T, dtype=np.float64)
    return {
        "report": report,
        "contract_score": float(report.score),
        "test": score_metrics(test_scores, test_ids, doc_ids, test_qrels),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SciFact BGE repair with separate integrity canaries")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=350)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--integrity-anchors", type=int, default=250)
    parser.add_argument("--corruption-fraction", type=float, default=0.10)
    parser.add_argument("--budgets", default="10,25,50,100,180")
    parser.add_argument("--seed", type=int, default=619)
    parser.add_argument("--output", default="artifacts/scifact_repair_integrity.json")
    args = parser.parse_args()

    from datasets import load_dataset
    from sentence_transformers import SentenceTransformer

    corpus_rows = load_dataset("mteb/scifact", "corpus", split="corpus")
    query_rows = load_dataset("mteb/scifact", "queries", split="queries")
    train_rows = load_dataset("mteb/scifact", "default", split="train")
    test_rows = load_dataset("mteb/scifact", "default", split="test")
    corpus = {str(row["_id"]): (str(row.get("title") or "") + "\n" + str(row["text"])).strip() for row in corpus_rows}
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
    integrity_random = build_integrity_contract(doc_ids, clean_docs, anchors=args.integrity_anchors, anchor_policy="random", seed=args.seed + 11)
    integrity_coverage = build_integrity_contract(doc_ids, clean_docs, anchors=args.integrity_anchors, anchor_policy="coverage", seed=args.seed + 11)
    contracts = {
        "application-only": application,
        "application+random-integrity": merge_contracts(application, integrity_random),
        "application+coverage-integrity": merge_contracts(application, integrity_coverage),
    }

    clean_eval = evaluate(application, train_ids, test_ids, doc_ids, train_qrels, test_qrels, train_q, test_q, clean_docs, label="clean")
    clean_ndcg = float(clean_eval["test"]["ndcg@10"])
    corrupted_docs, corrupted_tuple = corrupt_by_permutation(clean_docs, fraction=args.corruption_fraction, seed=args.seed)
    corrupted_indices = set(corrupted_tuple)
    budgets = [int(v) for v in args.budgets.split(",") if v.strip()]
    report_rows = []

    for contract_name, contract in contracts.items():
        corrupted_eval = evaluate(contract, train_ids, test_ids, doc_ids, train_qrels, test_qrels, train_q, test_q, corrupted_docs, label=f"corrupted:{contract_name}")
        corrupted_ndcg = float(corrupted_eval["test"]["ndcg@10"])
        report = corrupted_eval["report"]
        curves = []
        for budget in budgets:
            methods = {}
            for planner in ("highest-risk", "risk-diversity", "coverage"):
                selected = planner_selection(report, corrupted_docs, doc_ids, planner=planner, budget=budget, seed=args.seed + budget)
                repaired = apply_repairs(corrupted_docs, clean_docs, doc_ids, selected)
                state = evaluate(contract, train_ids, test_ids, doc_ids, train_qrels, test_qrels, train_q, test_q, repaired, label=f"{contract_name}:{planner}:{budget}")
                ndcg = float(state["test"]["ndcg@10"])
                methods[planner] = {
                    "corruption_precision": selected_corruption_precision(selected, corrupted_indices, doc_ids),
                    "contract_score": float(state["contract_score"]),
                    "heldout_ndcg": ndcg,
                    "heldout_recall": float(state["test"]["recall@10"]),
                    "ndcg_recovery_fraction": recovery_fraction(ndcg, corrupted_ndcg, clean_ndcg),
                }
            curves.append({"budget": budget, "methods": methods})
        report_rows.append({
            "contract": contract_name,
            "clauses": len(contract.clauses),
            "document_coverage": contract_doc_coverage(contract, doc_ids),
            "corrupted_contract_score": float(corrupted_eval["contract_score"]),
            "corrupted_heldout_ndcg": corrupted_ndcg,
            "curves": curves,
        })

    result = {
        "benchmark": "semantic-repair-integrity-canaries-v1",
        "dataset": "mteb/scifact",
        "model": args.model,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "corruption_fraction": args.corruption_fraction,
        "corrupted_documents": len(corrupted_indices),
        "integrity_anchors": args.integrity_anchors,
        "clean_application_contract_score": float(clean_eval["contract_score"]),
        "clean_heldout_ndcg": clean_ndcg,
        "contracts": report_rows,
        "interpretation_guardrail": (
            "Integrity canaries are implementation-specific diagnostics and must not be confused with application-semantic truth. "
            "They may legitimately freeze local behavior for corruption detection while remaining excluded from cross-model compatibility decisions."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
