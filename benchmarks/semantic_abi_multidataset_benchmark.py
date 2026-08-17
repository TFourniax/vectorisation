"""Cross-paradigm Semantic ABI falsification benchmark over several MTEB tasks.

This benchmark asks two harder questions than the first SciFact portability run:

1. Does the *same dataset-level Semantic Contract* execute unchanged against
   dense neural, sparse lexical and hybrid retrieval implementations?
2. Across natural implementations and controlled degradations, does Semantic ABI
   compatibility predict held-out retrieval quality any better than an ordinary
   train-query nDCG regression check?

The contract is compiled only from the official training qrels. Retrieval quality
is measured on the official test qrels. No test qrels are used to choose clauses,
negative examples, model variants, or contract weights.

Positive or negative results are both evidence. In particular, if ABI score adds
no predictive information beyond ordinary train retrieval metrics, the report
must say so rather than treating portability alone as sufficient validation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Iterable

import numpy as np

from semantic_atlas import CallbackSemanticOracle, NeighborClause, SemanticContract, TripletClause, audit_contract

_TOKEN = re.compile(r"[A-Za-z0-9]+")
_EPS = 1e-12


def normalize(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), _EPS)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


def qrel_dict(rows: Iterable[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in rows:
        if float(row["score"]) > 0:
            out.setdefault(str(row["query-id"]), set()).add(str(row["corpus-id"]))
    return out


def select_ids(qrels: dict[str, set[str]], limit: int, seed: int) -> list[str]:
    ids = sorted(qrels)
    rng = np.random.default_rng(int(seed))
    rng.shuffle(ids)
    return ids[: min(int(limit), len(ids))]


def stable_seed(*parts: str | int) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**32 - 1)


def choose_corpus(
    corpus_ids: Iterable[str],
    train_ids: list[str],
    test_ids: list[str],
    train_qrels: dict[str, set[str]],
    test_qrels: dict[str, set[str]],
    *,
    max_docs: int,
    seed: int,
) -> list[str]:
    """Retain at least one relevant document/query where possible, then fill corpus.

    MTEB tasks differ sharply in qrel density. Simply taking the union of every
    relevant document can exceed a bounded benchmark corpus, especially on
    NFCorpus. We therefore prioritize one relevant document per selected query,
    then additional relevant documents, then deterministic distractors.
    """
    universe = set(str(x) for x in corpus_ids)
    ordered: list[str] = []
    seen: set[str] = set()

    def add(doc_id: str) -> None:
        if doc_id in universe and doc_id not in seen and len(ordered) < max_docs:
            seen.add(doc_id)
            ordered.append(doc_id)

    # First guarantee representation for as many selected queries as possible.
    for qid in [*train_ids, *test_ids]:
        source = train_qrels if qid in train_qrels else test_qrels
        relevant = sorted(source.get(qid, set()) & universe)
        if relevant:
            add(relevant[0])

    # Then retain additional judged-relevant documents.
    for qid in [*train_ids, *test_ids]:
        source = train_qrels if qid in train_qrels else test_qrels
        for doc_id in sorted(source.get(qid, set()) & universe):
            add(doc_id)
            if len(ordered) >= max_docs:
                return ordered

    distractors = sorted(universe - seen)
    rng = np.random.default_rng(int(seed))
    rng.shuffle(distractors)
    for doc_id in distractors:
        add(doc_id)
        if len(ordered) >= max_docs:
            break
    return ordered


def build_contract(
    dataset_slug: str,
    query_ids: list[str],
    qrels: dict[str, set[str]],
    doc_ids: list[str],
    *,
    seed: int,
) -> SemanticContract:
    rng = np.random.default_rng(int(seed))
    docs = np.asarray(doc_ids, dtype=object)
    universe = set(doc_ids)
    contract = SemanticContract(
        name=f"{dataset_slug}-application-semantics",
        version="1",
        metadata={
            "dataset": f"mteb/{dataset_slug}",
            "semantics": "official training qrels relevance",
            "test_qrels_used_for_contract": False,
        },
    )
    for qid in query_ids:
        relevant = sorted(qrels.get(qid, set()) & universe)
        if not relevant:
            continue
        anchor = f"q:{qid}"
        expected = tuple(f"d:{doc_id}" for doc_id in relevant)
        contract.add(
            NeighborClause(
                anchor,
                expected,
                min_recall=1.0 / len(expected),
                candidate_k=10,
                weight=2.0,
                source=f"mteb/{dataset_slug}:train-qrels",
            )
        )
        nonrelevant = docs[~np.isin(docs, np.asarray(relevant, dtype=object))]
        if len(nonrelevant):
            positive = str(rng.choice(np.asarray(relevant, dtype=object)))
            negative = str(rng.choice(nonrelevant))
            contract.add(
                TripletClause(
                    anchor,
                    f"d:{positive}",
                    f"d:{negative}",
                    weight=1.0,
                    source=f"mteb/{dataset_slug}:train-qrels",
                )
            )
    return contract


class BM25Index:
    """Small inverted BM25 implementation used only as an independent sparse baseline."""

    def __init__(self, doc_ids: list[str], texts: list[str], *, k1: float = 1.2, b: float = 0.75) -> None:
        self.doc_ids = list(doc_ids)
        self.k1 = float(k1)
        self.b = float(b)
        token_rows = [tokenize(text) for text in texts]
        self.lengths = np.asarray([len(row) for row in token_rows], dtype=np.float64)
        self.avgdl = float(np.mean(self.lengths)) if len(self.lengths) else 1.0
        postings_idx: dict[str, list[int]] = defaultdict(list)
        postings_tf: dict[str, list[float]] = defaultdict(list)
        df: Counter[str] = Counter()
        for index, row in enumerate(token_rows):
            counts = Counter(row)
            df.update(counts.keys())
            for term, count in counts.items():
                postings_idx[term].append(index)
                postings_tf[term].append(float(count))
        n = max(1, len(self.doc_ids))
        self.idf = {
            term: math.log(1.0 + (n - count + 0.5) / (count + 0.5))
            for term, count in df.items()
        }
        self.postings = {
            term: (
                np.asarray(postings_idx[term], dtype=np.int32),
                np.asarray(postings_tf[term], dtype=np.float64),
            )
            for term in postings_idx
        }

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.doc_ids), dtype=np.float64)
        terms = Counter(tokenize(query))
        for term, qtf in terms.items():
            if term not in self.postings:
                continue
            idx, tf = self.postings[term]
            norm = self.k1 * (
                1.0 - self.b + self.b * self.lengths[idx] / max(self.avgdl, _EPS)
            )
            contribution = self.idf[term] * (tf * (self.k1 + 1.0)) / np.maximum(tf + norm, _EPS)
            out[idx] += float(qtf) * contribution
        return out


def score_metrics(
    scores: np.ndarray,
    query_ids: list[str],
    doc_ids: list[str],
    qrels: dict[str, set[str]],
    *,
    k: int = 10,
) -> dict[str, float]:
    lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    recalls: list[float] = []
    hits: list[float] = []
    mrrs: list[float] = []
    ndcgs: list[float] = []
    for row_index, qid in enumerate(query_ids):
        relevant = {lookup[doc_id] for doc_id in qrels.get(qid, set()) if doc_id in lookup}
        if not relevant:
            continue
        order = np.argsort(-scores[row_index])[:k]
        found = [int(index) in relevant for index in order]
        recalls.append(sum(found) / len(relevant))
        hits.append(float(any(found)))
        mrrs.append(next((1.0 / rank for rank, ok in enumerate(found, start=1) if ok), 0.0))
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


def make_oracle(
    implementation: str,
    contract_query_ids: list[str],
    doc_ids: list[str],
    score_matrix: np.ndarray,
) -> CallbackSemanticOracle:
    query_lookup = {qid: i for i, qid in enumerate(contract_query_ids)}
    doc_lookup = {doc_id: i for i, doc_id in enumerate(doc_ids)}
    object_ids = frozenset(
        [*(f"d:{doc_id}" for doc_id in doc_ids), *(f"q:{qid}" for qid in contract_query_ids)]
    )

    def similarity(left: str, right: str) -> float:
        if left == right:
            return 1.0
        if left.startswith("q:") and right.startswith("d:"):
            return float(score_matrix[query_lookup[left[2:]], doc_lookup[right[2:]]])
        if right.startswith("q:") and left.startswith("d:"):
            return float(score_matrix[query_lookup[right[2:]], doc_lookup[left[2:]]])
        return 0.0

    def neighbors(anchor: str, k: int):
        if not anchor.startswith("q:") or anchor[2:] not in query_lookup:
            return ()
        row = score_matrix[query_lookup[anchor[2:]]]
        take = min(max(0, int(k)), len(doc_ids))
        order = np.argsort(-row)[:take]
        return tuple(f"d:{doc_ids[int(index)]}" for index in order)

    return CallbackSemanticOracle(object_ids, similarity, neighbors, implementation=implementation)


def rrf_scores(left: np.ndarray, right: np.ndarray, *, k0: float = 60.0) -> np.ndarray:
    if left.shape != right.shape:
        raise ValueError("RRF score matrices must have identical shapes")
    out = np.empty_like(left, dtype=np.float64)
    n_docs = left.shape[1]
    for row in range(left.shape[0]):
        left_order = np.argsort(-left[row])
        right_order = np.argsort(-right[row])
        left_rank = np.empty(n_docs, dtype=np.int32)
        right_rank = np.empty(n_docs, dtype=np.int32)
        left_rank[left_order] = np.arange(1, n_docs + 1)
        right_rank[right_order] = np.arange(1, n_docs + 1)
        out[row] = 1.0 / (k0 + left_rank) + 1.0 / (k0 + right_rank)
    return out


def degrade_dense(
    docs: np.ndarray,
    train_queries: np.ndarray,
    test_queries: np.ndarray,
    *,
    dimension_fraction: float | None = None,
    noise_sigma: float | None = None,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = np.asarray(docs, dtype=np.float32)
    tq = np.asarray(train_queries, dtype=np.float32)
    sq = np.asarray(test_queries, dtype=np.float32)
    if dimension_fraction is not None:
        take = max(2, int(round(d.shape[1] * float(dimension_fraction))))
        d, tq, sq = d[:, :take], tq[:, :take], sq[:, :take]
    if noise_sigma is not None and noise_sigma > 0.0:
        rng = np.random.default_rng(int(seed))
        d = d + rng.normal(0.0, float(noise_sigma), size=d.shape).astype(np.float32)
        tq = tq + rng.normal(0.0, float(noise_sigma), size=tq.shape).astype(np.float32)
        sq = sq + rng.normal(0.0, float(noise_sigma), size=sq.shape).astype(np.float32)
    return normalize(d), normalize(tq), normalize(sq)


def rankdata(values: list[float]) -> np.ndarray:
    """Average ranks for ties, 0-based; sufficient for small benchmark panels."""
    x = np.asarray(values, dtype=np.float64)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=np.float64)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and x[order[end]] == x[order[start]]:
            end += 1
        rank = (start + end - 1) / 2.0
        ranks[order[start:end]] = rank
        start = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    a = np.asarray(x, dtype=np.float64)
    b = np.asarray(y, dtype=np.float64)
    if len(a) < 3 or np.std(a) <= _EPS or np.std(b) <= _EPS:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    return pearson(rankdata(x).tolist(), rankdata(y).tolist())


def pairwise_concordance(x: list[float], y: list[float]) -> float | None:
    correct = total = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if abs(dx) <= _EPS or abs(dy) <= _EPS:
                continue
            total += 1
            correct += int(dx * dy > 0.0)
    return None if total == 0 else correct / total


def qrel_retention(query_ids: list[str], qrels: dict[str, set[str]], doc_ids: list[str]) -> float:
    universe = set(doc_ids)
    total = kept = 0
    for qid in query_ids:
        relevant = qrels.get(qid, set())
        total += len(relevant)
        kept += len(relevant & universe)
    return 1.0 if total == 0 else kept / total


@dataclass
class Variant:
    name: str
    family: str
    contract_scores: np.ndarray
    test_scores: np.ndarray
    natural: bool


def evaluate_dataset(
    slug: str,
    *,
    mini_model,
    bge_model,
    train_query_limit: int,
    test_query_limit: int,
    max_docs: int,
    seed: int,
) -> dict:
    from datasets import load_dataset

    dataset_id = f"mteb/{slug}"
    corpus_rows = load_dataset(dataset_id, "corpus", split="corpus")
    query_rows = load_dataset(dataset_id, "queries", split="queries")
    train_rows = load_dataset(dataset_id, "default", split="train")
    test_rows = load_dataset(dataset_id, "default", split="test")

    corpus = {
        str(row["_id"]): (str(row.get("title") or "") + "\n" + str(row["text"])).strip()
        for row in corpus_rows
    }
    queries = {str(row["_id"]): str(row["text"]) for row in query_rows}
    train_qrels = qrel_dict(train_rows)
    test_qrels = qrel_dict(test_rows)
    train_ids = [qid for qid in select_ids(train_qrels, train_query_limit, seed) if qid in queries]
    test_ids = [qid for qid in select_ids(test_qrels, test_query_limit, seed + 1) if qid in queries]

    doc_ids = choose_corpus(
        corpus,
        train_ids,
        test_ids,
        train_qrels,
        test_qrels,
        max_docs=max_docs,
        seed=seed,
    )
    doc_set = set(doc_ids)
    train_ids = [qid for qid in train_ids if train_qrels.get(qid, set()) & doc_set]
    test_ids = [qid for qid in test_ids if test_qrels.get(qid, set()) & doc_set]
    if len(train_ids) < 20 or len(test_ids) < 20:
        raise RuntimeError(f"{slug}: too few retained qrel queries after corpus sampling")

    doc_texts = [corpus[doc_id] for doc_id in doc_ids]
    train_texts = [queries[qid] for qid in train_ids]
    test_texts = [queries[qid] for qid in test_ids]
    bge_prefix = "Represent this sentence for searching relevant passages: "

    mini_docs = normalize(mini_model.encode(doc_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    mini_train = normalize(mini_model.encode(train_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    mini_test = normalize(mini_model.encode(test_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    bge_docs = normalize(bge_model.encode(doc_texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    bge_train = normalize(bge_model.encode([bge_prefix + text for text in train_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    bge_test = normalize(bge_model.encode([bge_prefix + text for text in test_texts], batch_size=64, show_progress_bar=True, normalize_embeddings=True))

    contract = build_contract(slug, train_ids, train_qrels, doc_ids, seed=seed)
    if len(contract.clauses) < 40:
        raise RuntimeError(f"{slug}: contract unexpectedly small ({len(contract.clauses)} clauses)")

    mini_contract_scores = np.asarray(mini_train @ mini_docs.T, dtype=np.float64)
    mini_test_scores = np.asarray(mini_test @ mini_docs.T, dtype=np.float64)
    bge_contract_scores = np.asarray(bge_train @ bge_docs.T, dtype=np.float64)
    bge_test_scores = np.asarray(bge_test @ bge_docs.T, dtype=np.float64)

    bm25 = BM25Index(doc_ids, doc_texts)
    bm25_contract_scores = np.vstack([bm25.scores(queries[qid]) for qid in train_ids])
    bm25_test_scores = np.vstack([bm25.scores(queries[qid]) for qid in test_ids])
    hybrid_contract = rrf_scores(bge_contract_scores, bm25_contract_scores)
    hybrid_test = rrf_scores(bge_test_scores, bm25_test_scores)

    variants: list[Variant] = [
        Variant("minilm-dense", "dense", mini_contract_scores, mini_test_scores, True),
        Variant("bge-dense", "dense", bge_contract_scores, bge_test_scores, True),
        Variant("bm25-sparse", "sparse", bm25_contract_scores, bm25_test_scores, True),
        Variant("bge-bm25-rrf-hybrid", "hybrid", hybrid_contract, hybrid_test, True),
    ]

    for fraction in (0.50, 0.25):
        d, tq, sq = degrade_dense(
            bge_docs,
            bge_train,
            bge_test,
            dimension_fraction=fraction,
            seed=stable_seed(slug, "truncate", fraction),
        )
        variants.append(
            Variant(
                f"bge-truncate-{int(fraction * 100)}pct",
                "controlled-degradation",
                np.asarray(tq @ d.T, dtype=np.float64),
                np.asarray(sq @ d.T, dtype=np.float64),
                False,
            )
        )
    for sigma in (0.05, 0.15, 0.30):
        d, tq, sq = degrade_dense(
            bge_docs,
            bge_train,
            bge_test,
            noise_sigma=sigma,
            seed=stable_seed(slug, "bge-noise", sigma),
        )
        variants.append(
            Variant(
                f"bge-noise-{sigma:.2f}",
                "controlled-degradation",
                np.asarray(tq @ d.T, dtype=np.float64),
                np.asarray(sq @ d.T, dtype=np.float64),
                False,
            )
        )
    for sigma in (0.10, 0.25):
        d, tq, sq = degrade_dense(
            mini_docs,
            mini_train,
            mini_test,
            noise_sigma=sigma,
            seed=stable_seed(slug, "minilm-noise", sigma),
        )
        variants.append(
            Variant(
                f"minilm-noise-{sigma:.2f}",
                "controlled-degradation",
                np.asarray(tq @ d.T, dtype=np.float64),
                np.asarray(sq @ d.T, dtype=np.float64),
                False,
            )
        )

    rows: list[dict] = []
    for variant in variants:
        oracle = make_oracle(variant.name, train_ids, doc_ids, variant.contract_scores)
        report = audit_contract(contract, oracle)
        train_metrics = score_metrics(variant.contract_scores, train_ids, doc_ids, train_qrels)
        test_metrics = score_metrics(variant.test_scores, test_ids, doc_ids, test_qrels)
        rows.append(
            {
                "implementation": variant.name,
                "family": variant.family,
                "natural": variant.natural,
                "contract_digest": contract.digest,
                "contract_clauses": len(contract.clauses),
                "semantic_abi_score": float(report.score),
                "hard_pass": bool(report.hard_pass),
                "evaluated_clauses": int(report.evaluated_clauses),
                "missing_clauses": int(report.missing_clauses),
                "train_retrieval": train_metrics,
                "heldout_test_retrieval": test_metrics,
            }
        )

    def correlation_block(subset: list[dict]) -> dict:
        abi = [float(row["semantic_abi_score"]) for row in subset]
        train_ndcg = [float(row["train_retrieval"]["ndcg@10"]) for row in subset]
        test_ndcg = [float(row["heldout_test_retrieval"]["ndcg@10"]) for row in subset]
        test_recall = [float(row["heldout_test_retrieval"]["recall@10"]) for row in subset]
        return {
            "implementations": len(subset),
            "abi_vs_test_ndcg": {
                "pearson": pearson(abi, test_ndcg),
                "spearman": spearman(abi, test_ndcg),
                "pairwise_concordance": pairwise_concordance(abi, test_ndcg),
            },
            "train_ndcg_vs_test_ndcg": {
                "pearson": pearson(train_ndcg, test_ndcg),
                "spearman": spearman(train_ndcg, test_ndcg),
                "pairwise_concordance": pairwise_concordance(train_ndcg, test_ndcg),
            },
            "abi_vs_test_recall": {
                "pearson": pearson(abi, test_recall),
                "spearman": spearman(abi, test_recall),
                "pairwise_concordance": pairwise_concordance(abi, test_recall),
            },
        }

    natural_rows = [row for row in rows if row["natural"]]
    all_corr = correlation_block(rows)
    natural_corr = correlation_block(natural_rows)
    abi_s = all_corr["abi_vs_test_ndcg"]["spearman"]
    baseline_s = all_corr["train_ndcg_vs_test_ndcg"]["spearman"]
    incremental = None if abi_s is None or baseline_s is None else float(abi_s - baseline_s)

    return {
        "dataset": dataset_id,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "train_qrel_retention_in_sampled_corpus": qrel_retention(train_ids, train_qrels, doc_ids),
        "test_qrel_retention_in_sampled_corpus": qrel_retention(test_ids, test_qrels, doc_ids),
        "contract_digest": contract.digest,
        "contract_clauses": len(contract.clauses),
        "implementations": rows,
        "correlations_all_variants": all_corr,
        "correlations_natural_only": natural_corr,
        "abi_spearman_minus_train_ndcg_baseline_all_variants": incremental,
        "warning": (
            "Controlled dense degradations expand the quality range and are useful for falsification, but are not independent production systems. "
            "Natural-only correlations contain only four implementations and therefore have high uncertainty."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-dataset dense/sparse/hybrid Semantic ABI falsification benchmark")
    parser.add_argument("--datasets", default="scifact,nfcorpus,fiqa")
    parser.add_argument("--mini-model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--bge-model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=140)
    parser.add_argument("--test-queries", type=int, default=100)
    parser.add_argument("--max-docs", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=271)
    parser.add_argument("--output", default="artifacts/multidataset_semantic_abi.json")
    args = parser.parse_args()

    from huggingface_hub import model_info
    from sentence_transformers import SentenceTransformer

    dataset_slugs = [item.strip() for item in args.datasets.split(",") if item.strip()]
    mini_revision = str(model_info(args.mini_model).sha or "unknown")
    bge_revision = str(model_info(args.bge_model).sha or "unknown")
    mini_model = SentenceTransformer(args.mini_model)
    bge_model = SentenceTransformer(args.bge_model)

    datasets = []
    for offset, slug in enumerate(dataset_slugs):
        datasets.append(
            evaluate_dataset(
                slug,
                mini_model=mini_model,
                bge_model=bge_model,
                train_query_limit=args.train_queries,
                test_query_limit=args.test_queries,
                max_docs=args.max_docs,
                seed=args.seed + offset * 101,
            )
        )

    all_rows = [row for dataset in datasets for row in dataset["implementations"]]
    natural_rows = [row for row in all_rows if row["natural"]]

    # Pooled deltas relative to the BGE baseline remove most dataset-level scale
    # differences before asking whether ABI and held-out quality move together.
    pooled_abi_delta: list[float] = []
    pooled_test_delta: list[float] = []
    pooled_train_delta: list[float] = []
    pooled_natural_abi_delta: list[float] = []
    pooled_natural_test_delta: list[float] = []
    pooled_natural_train_delta: list[float] = []
    for dataset in datasets:
        base = next(row for row in dataset["implementations"] if row["implementation"] == "bge-dense")
        base_abi = float(base["semantic_abi_score"])
        base_train = float(base["train_retrieval"]["ndcg@10"])
        base_test = float(base["heldout_test_retrieval"]["ndcg@10"])
        for row in dataset["implementations"]:
            if row["implementation"] == "bge-dense":
                continue
            pooled_abi_delta.append(float(row["semantic_abi_score"]) - base_abi)
            pooled_train_delta.append(float(row["train_retrieval"]["ndcg@10"]) - base_train)
            pooled_test_delta.append(float(row["heldout_test_retrieval"]["ndcg@10"]) - base_test)
            if row["natural"]:
                pooled_natural_abi_delta.append(float(row["semantic_abi_score"]) - base_abi)
                pooled_natural_train_delta.append(float(row["train_retrieval"]["ndcg@10"]) - base_train)
                pooled_natural_test_delta.append(float(row["heldout_test_retrieval"]["ndcg@10"]) - base_test)

    pooled = {
        "all_variant_deltas_vs_bge": {
            "points": len(pooled_abi_delta),
            "abi_vs_heldout_ndcg": {
                "pearson": pearson(pooled_abi_delta, pooled_test_delta),
                "spearman": spearman(pooled_abi_delta, pooled_test_delta),
                "pairwise_concordance": pairwise_concordance(pooled_abi_delta, pooled_test_delta),
            },
            "train_ndcg_vs_heldout_ndcg": {
                "pearson": pearson(pooled_train_delta, pooled_test_delta),
                "spearman": spearman(pooled_train_delta, pooled_test_delta),
                "pairwise_concordance": pairwise_concordance(pooled_train_delta, pooled_test_delta),
            },
        },
        "natural_variant_deltas_vs_bge": {
            "points": len(pooled_natural_abi_delta),
            "abi_vs_heldout_ndcg": {
                "pearson": pearson(pooled_natural_abi_delta, pooled_natural_test_delta),
                "spearman": spearman(pooled_natural_abi_delta, pooled_natural_test_delta),
                "pairwise_concordance": pairwise_concordance(pooled_natural_abi_delta, pooled_natural_test_delta),
            },
            "train_ndcg_vs_heldout_ndcg": {
                "pearson": pearson(pooled_natural_train_delta, pooled_natural_test_delta),
                "spearman": spearman(pooled_natural_train_delta, pooled_natural_test_delta),
                "pairwise_concordance": pairwise_concordance(pooled_natural_train_delta, pooled_natural_test_delta),
            },
        },
    }

    per_dataset_abi = [dataset["correlations_all_variants"]["abi_vs_test_ndcg"]["spearman"] for dataset in datasets]
    per_dataset_train = [dataset["correlations_all_variants"]["train_ndcg_vs_test_ndcg"]["spearman"] for dataset in datasets]
    valid_pairs = [
        (a, b)
        for a, b in zip(per_dataset_abi, per_dataset_train)
        if a is not None and b is not None
    ]
    mean_abi = float(np.mean([pair[0] for pair in valid_pairs])) if valid_pairs else None
    mean_train = float(np.mean([pair[1] for pair in valid_pairs])) if valid_pairs else None

    result = {
        "benchmark": "semantic-abi-multidataset-cross-paradigm-v1",
        "datasets": datasets,
        "models": {
            "minilm": {"id": args.mini_model, "revision": mini_revision},
            "bge": {"id": args.bge_model, "revision": bge_revision},
        },
        "natural_implementation_families": ["dense", "sparse", "hybrid"],
        "pooled_delta_analysis": pooled,
        "mean_per_dataset_spearman_all_variants": {
            "semantic_abi_vs_heldout_ndcg": mean_abi,
            "ordinary_train_ndcg_vs_heldout_ndcg": mean_train,
            "semantic_abi_minus_train_baseline": None if mean_abi is None or mean_train is None else mean_abi - mean_train,
        },
        "interpretation_guardrail": (
            "Executable portability and predictive validity are separate claims. A contract can run over dense/sparse/hybrid systems yet still add no predictive value beyond ordinary IR validation. "
            "The report therefore exposes both results and treats a weaker ABI correlation as a narrowing signal rather than hiding it."
        ),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
