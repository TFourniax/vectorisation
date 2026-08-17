"""Real neural active-repair economics benchmark on SciFact/BGE.

A clean BGE index is deliberately corrupted by permuting a subset of document
embeddings. The Semantic ABI sees only the corrupted implementation and its
contract violations. Given a bounded document re-embedding budget, we compare:

- uniform random re-embedding;
- highest object-risk first;
- risk/centrality/diversity planning;
- cost-aware violation-coverage planning.

Selected documents are then restored from the clean BGE representation and the
same untouched held-out SciFact test qrels measure nDCG/Recall recovery.

This is a controlled fault-injection economics test. It does not assume real
production failures are identity permutations, and planner superiority is not a
success criterion for the workflow itself: weak or negative results must remain
visible.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from semantic_atlas import audit_contract, plan_repairs, plan_repairs_by_coverage
from semantic_abi_multidataset_benchmark import (
    build_contract,
    choose_corpus,
    make_oracle,
    normalize,
    qrel_dict,
    score_metrics,
    select_ids,
)

_EPS = 1e-12


def corrupt_by_permutation(clean_docs: np.ndarray, *, fraction: float, seed: int) -> tuple[np.ndarray, tuple[int, ...]]:
    rng = np.random.default_rng(int(seed))
    count = max(2, int(round(len(clean_docs) * float(fraction))))
    selected = np.sort(rng.choice(len(clean_docs), size=count, replace=False))
    permuted = selected.copy()
    for _ in range(20):
        rng.shuffle(permuted)
        if np.all(permuted != selected):
            break
    if np.any(permuted == selected):
        permuted = np.roll(selected, 1)
    corrupted = np.asarray(clean_docs, dtype=np.float32).copy()
    corrupted[selected] = clean_docs[permuted]
    return corrupted, tuple(int(index) for index in selected)


def evaluate_state(contract, train_ids, test_ids, doc_ids, train_qrels, test_qrels, train_q, test_q, docs, label: str) -> dict:
    train_scores = np.asarray(train_q @ docs.T, dtype=np.float64)
    test_scores = np.asarray(test_q @ docs.T, dtype=np.float64)
    report = audit_contract(contract, make_oracle(label, train_ids, doc_ids, train_scores))
    return {
        "label": label,
        "report": report,
        "train_scores": train_scores,
        "test_scores": test_scores,
        "contract_score": float(report.score),
        "hard_pass": bool(report.hard_pass),
        "train_retrieval": score_metrics(train_scores, train_ids, doc_ids, train_qrels),
        "heldout_test_retrieval": score_metrics(test_scores, test_ids, doc_ids, test_qrels),
    }


def apply_repairs(corrupted: np.ndarray, clean: np.ndarray, doc_ids: list[str], selected_object_ids: list[str]) -> np.ndarray:
    lookup = {f"d:{doc_id}": i for i, doc_id in enumerate(doc_ids)}
    out = np.asarray(corrupted, dtype=np.float32).copy()
    for object_id in selected_object_ids:
        index = lookup.get(object_id)
        if index is not None:
            out[index] = clean[index]
    return out


def recovery_fraction(value: float, corrupted: float, clean: float) -> float | None:
    gap = clean - corrupted
    if abs(gap) <= _EPS:
        return None
    return float((value - corrupted) / gap)


def selected_corruption_precision(selected: list[str], corrupted_indices: set[int], doc_ids: list[str]) -> float:
    lookup = {f"d:{doc_id}": i for i, doc_id in enumerate(doc_ids)}
    if not selected:
        return 0.0
    hits = sum(1 for object_id in selected if lookup.get(object_id) in corrupted_indices)
    return hits / len(selected)


def planner_selection(report, corrupted_docs: np.ndarray, doc_ids: list[str], *, planner: str, budget: int, seed: int) -> list[str]:
    document_ids = [f"d:{doc_id}" for doc_id in doc_ids]
    if planner == "highest-risk":
        return sorted(document_ids, key=lambda object_id: (-float(report.object_risk.get(object_id, 0.0)), object_id))[:budget]
    if planner == "risk-diversity":
        vectors = {object_id: corrupted_docs[i] for i, object_id in enumerate(document_ids)}
        plan = plan_repairs(report, vectors, limit=budget, diversity_weight=0.35, min_risk=0.0)
        chosen = [candidate.object_id for candidate in plan.candidates]
        if len(chosen) < budget:
            remaining = [object_id for object_id in document_ids if object_id not in set(chosen)]
            chosen.extend(remaining[: budget - len(chosen)])
        return chosen[:budget]
    if planner == "coverage":
        costs = {object_id: 1.0 for object_id in document_ids}
        for object_id in report.object_risk:
            if object_id.startswith("q:"):
                costs[object_id] = float(budget + 1_000_000)
        plan = plan_repairs_by_coverage(report, budget=float(budget), costs=costs, risk_bonus_weight=0.15)
        chosen = [candidate.object_id for candidate in plan.candidates if candidate.object_id.startswith("d:")]
        if len(chosen) < budget:
            remaining = sorted(
                [object_id for object_id in document_ids if object_id not in set(chosen)],
                key=lambda object_id: (-float(report.object_risk.get(object_id, 0.0)), object_id),
            )
            chosen.extend(remaining[: budget - len(chosen)])
        return chosen[:budget]
    if planner == "random":
        rng = np.random.default_rng(int(seed))
        indices = rng.choice(len(document_ids), size=min(budget, len(document_ids)), replace=False)
        return [document_ids[int(index)] for index in indices]
    raise ValueError(planner)


def summarize_random(rows: list[dict]) -> dict:
    keys = [
        "contract_score",
        "heldout_ndcg",
        "heldout_recall",
        "ndcg_recovery_fraction",
        "corruption_precision",
    ]
    summary = {"repeats": len(rows)}
    for key in keys:
        values = [float(row[key]) for row in rows if row[key] is not None]
        summary[key] = {
            "mean": float(np.mean(values)) if values else None,
            "std": float(np.std(values)) if values else None,
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic ABI active-repair economics on real SciFact/BGE")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=350)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--corruption-fractions", default="0.05,0.10")
    parser.add_argument("--budgets", default="10,25,50,100,180")
    parser.add_argument("--random-repeats", type=int, default=12)
    parser.add_argument("--seed", type=int, default=619)
    parser.add_argument("--output", default="artifacts/scifact_repair_economics.json")
    args = parser.parse_args()

    from datasets import load_dataset
    from huggingface_hub import model_info
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
    doc_ids = choose_corpus(
        corpus,
        train_ids,
        test_ids,
        train_qrels,
        test_qrels,
        max_docs=args.max_docs,
        seed=args.seed,
    )
    doc_set = set(doc_ids)
    train_ids = [qid for qid in train_ids if train_qrels.get(qid, set()) & doc_set]
    test_ids = [qid for qid in test_ids if test_qrels.get(qid, set()) & doc_set]

    model_revision = str(model_info(args.model).sha or "unknown")
    model = SentenceTransformer(args.model)
    prefix = "Represent this sentence for searching relevant passages: " if "bge" in args.model.lower() else ""
    clean_docs = normalize(model.encode([corpus[doc_id] for doc_id in doc_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    train_q = normalize(model.encode([prefix + queries[qid] for qid in train_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))
    test_q = normalize(model.encode([prefix + queries[qid] for qid in test_ids], batch_size=64, show_progress_bar=True, normalize_embeddings=True))

    contract = build_contract("scifact-repair", train_ids, train_qrels, doc_ids, seed=args.seed)
    clean_state = evaluate_state(contract, train_ids, test_ids, doc_ids, train_qrels, test_qrels, train_q, test_q, clean_docs, "clean-bge")
    clean_ndcg = float(clean_state["heldout_test_retrieval"]["ndcg@10"])
    budgets = [int(value) for value in args.budgets.split(",") if value.strip()]
    fractions = [float(value) for value in args.corruption_fractions.split(",") if value.strip()]
    scenario_reports = []

    for scenario_index, fraction in enumerate(fractions):
        corrupted_docs, corrupted_tuple = corrupt_by_permutation(
            clean_docs,
            fraction=fraction,
            seed=args.seed + scenario_index * 1009,
        )
        corrupted_indices = set(corrupted_tuple)
        corrupted_state = evaluate_state(
            contract,
            train_ids,
            test_ids,
            doc_ids,
            train_qrels,
            test_qrels,
            train_q,
            test_q,
            corrupted_docs,
            f"corrupt-{fraction:.3f}",
        )
        corrupted_ndcg = float(corrupted_state["heldout_test_retrieval"]["ndcg@10"])
        report = corrupted_state["report"]
        curves = []
        for budget in budgets:
            deterministic = {}
            for planner in ("highest-risk", "risk-diversity", "coverage"):
                selected = planner_selection(
                    report,
                    corrupted_docs,
                    doc_ids,
                    planner=planner,
                    budget=budget,
                    seed=args.seed + budget,
                )
                repaired_docs = apply_repairs(corrupted_docs, clean_docs, doc_ids, selected)
                state = evaluate_state(
                    contract,
                    train_ids,
                    test_ids,
                    doc_ids,
                    train_qrels,
                    test_qrels,
                    train_q,
                    test_q,
                    repaired_docs,
                    f"{planner}-b{budget}",
                )
                ndcg = float(state["heldout_test_retrieval"]["ndcg@10"])
                deterministic[planner] = {
                    "selected_documents": len(selected),
                    "corruption_precision": selected_corruption_precision(selected, corrupted_indices, doc_ids),
                    "contract_score": float(state["contract_score"]),
                    "heldout_ndcg": ndcg,
                    "heldout_recall": float(state["heldout_test_retrieval"]["recall@10"]),
                    "ndcg_recovery_fraction": recovery_fraction(ndcg, corrupted_ndcg, clean_ndcg),
                }

            random_rows = []
            for repeat in range(args.random_repeats):
                selected = planner_selection(
                    report,
                    corrupted_docs,
                    doc_ids,
                    planner="random",
                    budget=budget,
                    seed=args.seed + scenario_index * 100_003 + budget * 997 + repeat,
                )
                repaired_docs = apply_repairs(corrupted_docs, clean_docs, doc_ids, selected)
                state = evaluate_state(
                    contract,
                    train_ids,
                    test_ids,
                    doc_ids,
                    train_qrels,
                    test_qrels,
                    train_q,
                    test_q,
                    repaired_docs,
                    f"random-b{budget}-r{repeat}",
                )
                ndcg = float(state["heldout_test_retrieval"]["ndcg@10"])
                random_rows.append(
                    {
                        "contract_score": float(state["contract_score"]),
                        "heldout_ndcg": ndcg,
                        "heldout_recall": float(state["heldout_test_retrieval"]["recall@10"]),
                        "ndcg_recovery_fraction": recovery_fraction(ndcg, corrupted_ndcg, clean_ndcg),
                        "corruption_precision": selected_corruption_precision(selected, corrupted_indices, doc_ids),
                    }
                )
            curves.append(
                {
                    "budget": budget,
                    "budget_fraction_of_corpus": budget / len(doc_ids),
                    "deterministic": deterministic,
                    "random": summarize_random(random_rows),
                }
            )

        target_ndcg = corrupted_ndcg + 0.90 * (clean_ndcg - corrupted_ndcg)
        cost_to_90 = {}
        for planner in ("highest-risk", "risk-diversity", "coverage"):
            achieved = [row["budget"] for row in curves if row["deterministic"][planner]["heldout_ndcg"] >= target_ndcg - 1e-12]
            cost_to_90[planner] = min(achieved) if achieved else None
        random_achieved = [row["budget"] for row in curves if (row["random"]["heldout_ndcg"]["mean"] or -1.0) >= target_ndcg - 1e-12]
        cost_to_90["random_mean"] = min(random_achieved) if random_achieved else None

        scenario_reports.append(
            {
                "corruption_fraction": fraction,
                "corrupted_documents": len(corrupted_indices),
                "corrupted_contract_score": float(corrupted_state["contract_score"]),
                "corrupted_heldout_test_retrieval": corrupted_state["heldout_test_retrieval"],
                "clean_to_corrupt_ndcg_loss": clean_ndcg - corrupted_ndcg,
                "target_90pct_ndcg_recovery": target_ndcg,
                "budget_to_90pct_ndcg_recovery": cost_to_90,
                "curves": curves,
            }
        )

    result = {
        "benchmark": "semantic-active-repair-scifact-bge-v1",
        "dataset": "mteb/scifact",
        "model": args.model,
        "model_revision": model_revision,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "contract_digest": contract.digest,
        "contract_clauses": len(contract.clauses),
        "clean": {
            "contract_score": float(clean_state["contract_score"]),
            "heldout_test_retrieval": clean_state["heldout_test_retrieval"],
        },
        "scenarios": scenario_reports,
        "warning": (
            "Identity-permutation corruption is a controlled observability test, not a model of every production failure. "
            "Economic claims should be promoted only if targeted planners beat random and simple highest-risk baselines across additional failure families and datasets."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
