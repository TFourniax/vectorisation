"""Independent validation for the clause-incidence repair heuristic.

The role weights in ``plan_repairs_by_clause_incidence`` were designed after the
first SciFact integrity-canary corruption experiment exposed anchor-blame
misattribution. Therefore the original corruption seed is development evidence,
not an independent validation set.

This benchmark freezes those weights and evaluates them without modification on
new corruption seeds and several document-level fault families. Test qrels are
never used for contract construction, diagnosis or repair selection.

Promotion gate is declared before execution:

- at budget 50, clause-incidence mean lost-nDCG recovery must exceed the best
  competing planner's mean by at least 0.05 absolute;
- clause-incidence must win or tie the best competing planner on at least 3/4
  fault scenarios at budget 50.

The workflow succeeds even when the promotion gate fails; a failed gate is
scientific evidence, not a CI failure.
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


def choose_indices(n: int, fraction: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    count = max(2, int(round(n * float(fraction))))
    return np.sort(rng.choice(n, size=count, replace=False)).astype(int)


def gaussian_noise(clean: np.ndarray, *, fraction: float, sigma: float, seed: int):
    selected = choose_indices(len(clean), fraction, seed)
    rng = np.random.default_rng(int(seed) + 1)
    out = np.asarray(clean, dtype=np.float32).copy()
    out[selected] = normalize(
        out[selected] + rng.normal(0.0, sigma, size=out[selected].shape).astype(np.float32)
    )
    return out, tuple(int(i) for i in selected)


def local_collapse(clean: np.ndarray, *, fraction: float, strength: float, seed: int):
    selected = choose_indices(len(clean), fraction, seed)
    out = np.asarray(clean, dtype=np.float32).copy()
    center = normalize(np.mean(out[selected], axis=0, keepdims=True))[0]
    out[selected] = normalize((1.0 - strength) * out[selected] + strength * center)
    return out, tuple(int(i) for i in selected)


def hub_pull(clean: np.ndarray, *, fraction: float, strength: float, seed: int):
    selected = choose_indices(len(clean), fraction, seed)
    rng = np.random.default_rng(int(seed) + 2)
    candidates = np.setdiff1d(np.arange(len(clean)), selected, assume_unique=False)
    hub_index = int(rng.choice(candidates))
    hub = clean[hub_index]
    out = np.asarray(clean, dtype=np.float32).copy()
    out[selected] = normalize((1.0 - strength) * out[selected] + strength * hub)
    return out, tuple(int(i) for i in selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Independent clause-incidence repair validation")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--train-queries", type=int, default=350)
    parser.add_argument("--test-queries", type=int, default=200)
    parser.add_argument("--max-docs", type=int, default=1800)
    parser.add_argument("--integrity-anchors", type=int, default=250)
    parser.add_argument("--budgets", default="25,50,100")
    parser.add_argument("--seed", type=int, default=619)
    parser.add_argument("--output", default="artifacts/scifact_repair_incidence_validation.json")
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
    document_objects = [f"d:{doc_id}" for doc_id in doc_ids]
    budgets = [int(value) for value in args.budgets.split(",") if value.strip()]

    scenarios = [
        ("permutation-new-seed", *corrupt_by_permutation(clean_docs, fraction=0.10, seed=701)),
        ("gaussian-noise", *gaussian_noise(clean_docs, fraction=0.10, sigma=0.45, seed=911)),
        ("local-collapse", *local_collapse(clean_docs, fraction=0.10, strength=0.80, seed=1237)),
        ("hub-pull", *hub_pull(clean_docs, fraction=0.10, strength=0.72, seed=1451)),
    ]

    rows = []
    planner_names = ("highest-risk", "risk-diversity", "coverage", "clause-incidence")
    for scenario_name, corrupted_docs, corrupted_tuple in scenarios:
        corrupted_indices = set(int(i) for i in corrupted_tuple)
        corrupted_metrics = test_retrieval(test_q, corrupted_docs, test_ids, doc_ids, test_qrels)
        corrupted_ndcg = float(corrupted_metrics["ndcg@10"])
        oracle = QueryDocumentOracle(train_ids, doc_ids, train_q, corrupted_docs, implementation=f"corrupted:{scenario_name}")
        report = audit_contract(contract, oracle)
        budget_rows = []
        for budget in budgets:
            selections = {
                planner: planner_selection(
                    report,
                    corrupted_docs,
                    doc_ids,
                    planner=planner,
                    budget=budget,
                    seed=args.seed + budget,
                )
                for planner in ("highest-risk", "risk-diversity", "coverage")
            }
            incidence = plan_repairs_by_clause_incidence(
                contract,
                report,
                oracle,
                budget=float(budget),
                repairable_ids=set(document_objects),
            )
            selections["clause-incidence"] = [candidate.object_id for candidate in incidence.candidates]

            methods = {}
            for planner, selected in selections.items():
                repaired = apply_repairs(corrupted_docs, clean_docs, doc_ids, selected)
                metrics = test_retrieval(test_q, repaired, test_ids, doc_ids, test_qrels)
                ndcg = float(metrics["ndcg@10"])
                methods[planner] = {
                    "corruption_precision": selected_corruption_precision(selected, corrupted_indices, doc_ids),
                    "heldout_ndcg": ndcg,
                    "heldout_recall": float(metrics["recall@10"]),
                    "ndcg_recovery_fraction": recovery_fraction(ndcg, corrupted_ndcg, clean_ndcg),
                }
            budget_rows.append({"budget": budget, "methods": methods})

        rows.append({
            "scenario": scenario_name,
            "corrupted_documents": len(corrupted_indices),
            "corrupted_retrieval": corrupted_metrics,
            "budget_rows": budget_rows,
        })

    aggregate = {}
    for budget in budgets:
        aggregate[str(budget)] = {}
        for planner in planner_names:
            values = []
            precisions = []
            for scenario in rows:
                brow = next(row for row in scenario["budget_rows"] if row["budget"] == budget)
                value = brow["methods"][planner]["ndcg_recovery_fraction"]
                if value is not None:
                    values.append(float(value))
                precisions.append(float(brow["methods"][planner]["corruption_precision"]))
            aggregate[str(budget)][planner] = {
                "mean_ndcg_recovery_fraction": float(np.mean(values)) if values else None,
                "mean_corruption_precision": float(np.mean(precisions)),
            }

    target_budget = 50
    target = aggregate[str(target_budget)]
    incidence_mean = float(target["clause-incidence"]["mean_ndcg_recovery_fraction"])
    competitor_means = {
        planner: float(target[planner]["mean_ndcg_recovery_fraction"])
        for planner in ("highest-risk", "risk-diversity", "coverage")
    }
    best_competitor = max(competitor_means.values())
    scenario_wins = 0
    for scenario in rows:
        brow = next(row for row in scenario["budget_rows"] if row["budget"] == target_budget)
        incidence_value = float(brow["methods"]["clause-incidence"]["ndcg_recovery_fraction"] or 0.0)
        best_other = max(
            float(brow["methods"][planner]["ndcg_recovery_fraction"] or 0.0)
            for planner in ("highest-risk", "risk-diversity", "coverage")
        )
        if incidence_value + 1e-12 >= best_other:
            scenario_wins += 1

    promotion_gate = {
        "budget": target_budget,
        "required_mean_recovery_lift": 0.05,
        "observed_mean_recovery_lift": incidence_mean - best_competitor,
        "required_scenario_wins_or_ties": 3,
        "observed_scenario_wins_or_ties": scenario_wins,
        "passed": bool((incidence_mean - best_competitor) >= 0.05 and scenario_wins >= 3),
    }

    result = {
        "benchmark": "semantic-repair-clause-incidence-independent-validation-v1",
        "dataset": "mteb/scifact",
        "model": args.model,
        "documents": len(doc_ids),
        "train_queries": len(train_ids),
        "heldout_test_queries": len(test_ids),
        "combined_contract_digest": contract.digest,
        "clean_retrieval": clean_metrics,
        "scenarios": rows,
        "aggregate": aggregate,
        "promotion_gate": promotion_gate,
        "guardrail": (
            "Incidence role weights were frozen before these corruption seeds/families were executed. The faults remain controlled synthetic corruptions of real neural embeddings, not production incident distributions."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
