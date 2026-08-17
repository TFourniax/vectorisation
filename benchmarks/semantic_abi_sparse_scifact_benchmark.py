"""Representation-independence benchmark: the same Semantic ABI over BGE and BM25.

The dense BGE audit is produced by ``real_encoder_scifact_benchmark.py`` in the
same workflow. This script reconstructs the *same* SciFact semantic contract,
verifies its digest against that dense evidence, then audits a lexical BM25
retriever through ``CallbackSemanticOracle``. BM25 exposes no dense vectors.

This is a first real inter-paradigm portability test for the contract/oracle
abstraction. It does not claim BGE and BM25 should have equal quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re

import numpy as np

from semantic_atlas import CallbackSemanticOracle, audit_contract
from real_encoder_scifact_benchmark import _build_contract, _qrel_dict, _select_query_ids

_TOKEN = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


class BM25Index:
    def __init__(self, doc_ids: list[str], doc_texts: list[str], *, k1: float = 1.2, b: float = 0.75) -> None:
        self.doc_ids = list(doc_ids)
        self.k1 = float(k1)
        self.b = float(b)
        tokens = [tokenize(text) for text in doc_texts]
        self.lengths = np.asarray([len(row) for row in tokens], dtype=np.float64)
        self.avgdl = float(np.mean(self.lengths)) if len(self.lengths) else 1.0
        self.term_freqs = [Counter(row) for row in tokens]
        df: Counter[str] = Counter()
        for row in self.term_freqs:
            df.update(row.keys())
        n = max(1, len(self.doc_ids))
        self.idf = {
            term: math.log(1.0 + (n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }

    def scores(self, query: str) -> np.ndarray:
        terms = Counter(tokenize(query))
        out = np.zeros(len(self.doc_ids), dtype=np.float64)
        norm = self.k1 * (1.0 - self.b + self.b * self.lengths / max(self.avgdl, 1e-12))
        for term, qtf in terms.items():
            idf = self.idf.get(term)
            if idf is None:
                continue
            tf = np.asarray([row.get(term, 0) for row in self.term_freqs], dtype=np.float64)
            contribution = idf * (tf * (self.k1 + 1.0)) / np.maximum(tf + norm, 1e-12)
            out += float(qtf) * contribution
        return out


def retrieval_metrics(score_rows: dict[str, np.ndarray], query_ids: list[str], doc_ids: list[str], qrels: dict[str, set[str]], *, k: int = 10) -> dict[str, float]:
    lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    recalls: list[float] = []
    hits: list[float] = []
    reciprocal: list[float] = []
    ndcgs: list[float] = []
    for qid in query_ids:
        relevant = {lookup[doc_id] for doc_id in qrels.get(qid, set()) if doc_id in lookup}
        if not relevant or qid not in score_rows:
            continue
        order = np.argsort(-score_rows[qid])[:k]
        found = [int(index) in relevant for index in order]
        recalls.append(sum(found) / len(relevant))
        hits.append(float(any(found)))
        reciprocal.append(next((1.0 / rank for rank, ok in enumerate(found, start=1) if ok), 0.0))
        dcg = sum(1.0 / math.log2(rank + 2) for rank, ok in enumerate(found) if ok)
        ideal = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(relevant), k)))
        ndcgs.append(dcg / ideal if ideal else 0.0)
    return {
        "queries": len(recalls),
        f"recall@{k}": float(np.mean(recalls)) if recalls else 0.0,
        f"hit_rate@{k}": float(np.mean(hits)) if hits else 0.0,
        f"mrr@{k}": float(np.mean(reciprocal)) if reciprocal else 0.0,
        f"ndcg@{k}": float(np.mean(ndcgs)) if ndcgs else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the same SciFact Semantic ABI over dense BGE and sparse BM25")
    parser.add_argument("--dense-report", default="artifacts/real_encoder_report.json")
    parser.add_argument("--train-queries", type=int, default=500)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", default="artifacts/sparse_portability_report.json")
    args = parser.parse_args()

    from datasets import load_dataset

    dense = json.loads(Path(args.dense_report).read_text(encoding="utf-8"))
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

    contract_n = max(40, int(round(len(train_ids) * 0.65)))
    contract_ids = train_ids[:contract_n]
    contract = _build_contract(contract_ids, train_qrels, doc_ids, seed=args.seed)
    dense_digest = str(dense["semantic_abi"]["contract_digest"])
    if contract.digest != dense_digest:
        raise RuntimeError(f"contract digest mismatch: sparse={contract.digest} dense={dense_digest}")

    bm25 = BM25Index(doc_ids, doc_texts)
    score_rows = {qid: bm25.scores(queries[qid]) for qid in sorted(set(contract_ids) | set(test_ids))}
    doc_lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    object_ids = frozenset([*(f"d:{doc_id}" for doc_id in doc_ids), *(f"q:{qid}" for qid in contract_ids)])

    def similarity(left: str, right: str) -> float:
        if left == right:
            return 1.0
        if left.startswith("q:") and right.startswith("d:"):
            qid, did = left[2:], right[2:]
            return float(score_rows[qid][doc_lookup[did]])
        if right.startswith("q:") and left.startswith("d:"):
            qid, did = right[2:], left[2:]
            return float(score_rows[qid][doc_lookup[did]])
        return 0.0

    def neighbors(anchor: str, k: int):
        if not anchor.startswith("q:"):
            return ()
        qid = anchor[2:]
        take = min(max(0, int(k)), len(doc_ids))
        order = np.argsort(-score_rows[qid])[:take]
        return tuple(f"d:{doc_ids[int(index)]}" for index in order)

    oracle = CallbackSemanticOracle(
        object_ids=object_ids,
        similarity_fn=similarity,
        neighbors_fn=neighbors,
        implementation="bm25-sparse",
    )
    sparse_report = audit_contract(contract, oracle)
    test_scores = {qid: score_rows[qid] for qid in test_ids if qid in score_rows}

    result = {
        "dataset": "mteb/scifact",
        "contract_digest": contract.digest,
        "contract_clauses": len(contract.clauses),
        "same_contract_as_dense": True,
        "dense": {
            "implementation": dense["new_model"],
            "semantic_abi_score": dense["semantic_abi"]["candidate_score"],
            "hard_pass": dense["semantic_abi"]["candidate_hard_pass"],
            "retrieval": dense["direct_new"],
        },
        "sparse": {
            "implementation": "BM25 lexical sparse ranker",
            "semantic_abi_score": float(sparse_report.score),
            "hard_pass": bool(sparse_report.hard_pass),
            "evaluated_clauses": sparse_report.evaluated_clauses,
            "missing_clauses": sparse_report.missing_clauses,
            "retrieval": retrieval_metrics(test_scores, test_ids, doc_ids, test_qrels),
        },
        "interpretation": (
            "The same coordinate-free contract digest was audited against a dense neural encoder and a lexical BM25 ranker. "
            "Score differences measure implementation behavior; contract identity does not depend on vector coordinates."
        ),
        "warning": (
            "This proves executable inter-paradigm portability for this contract shape and dataset, not universal portability to every sparse/graph/multimodal system."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
