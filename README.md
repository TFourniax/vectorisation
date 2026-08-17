# Semantic Manifold Atlas / Semantic ABI

**Research toward an evidence-gated semantic change-control layer that can outlive any one embedding model, vector database or retrieval implementation.**

> A vector is not meaning. It is one representation emitted by one implementation at one point in time.

The project began as topology-aware vector retrieval research. The strongest surviving direction is now broader:

```text
stable logical objects
        |
Application Semantic Contract
(portable normative invariants)
        |
SemanticOracle
 dense / sparse / graph / hybrid / remote
        |
Contract Conformity
        |
+-------+--------------------------+
|                                  |
Contract Adequacy            Implementation Integrity
is the contract               canaries for one concrete
observant enough?              implementation/index
|                                  |
+---------------+------------------+
                |
         support + risk
                |
        rollout / fallback
                |
        repair / re-audit
                |
         release evidence
```

The intended role is **above** mature retrieval/index engines such as Qdrant, HNSW, DiskANN, pgvector, Elasticsearch or Vespa—not to reimplement their ANN work. SQL remains appropriate for transactions, constraints, metadata and logical identity.

**Authoritative current status:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).  
**Machine-bound evidence:** [`docs/evidence-manifest.json`](docs/evidence-manifest.json).

## Core distinction: conformity is not adequacy

`SemanticContract` expresses coordinate-free requirements over stable IDs. A candidate **conforms** when it satisfies those clauses.

The latest neural repair experiments showed that conformity can recover while held-out retrieval quality is still damaged outside the contract's observed surface. A high ABI score therefore does **not** prove that the contract itself is adequate for a broader deployment claim.

`ContractAdequacyEvidence` / `ContractAdequacyReport` now separate those questions using policy-declared axes such as object coverage, mutation sensitivity, predictive validity, lift over ordinary validation, held-out cases, datasets and fault families. Missing required evidence yields `insufficient_evidence`.

## Representation-independent Semantic ABI

Current contract primitives include:

- ordinal assertions: `A must prefer B over C`;
- critical-neighborhood survival;
- reciprocal-neighbor relations;
- hard/soft requirements, weights and provenance;
- canonical SHA-256 identity, linting and hash-chained history.

`SemanticOracle` means the audit engine does not require vectors. A real SciFact benchmark audits the **exact same 650-clause contract digest** against both BGE dense embeddings and a lexical BM25 sparse ranker:

| implementation | Semantic ABI | nDCG@10 | Recall@10 |
|---|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 |

BM25 evaluates 650/650 clauses with zero missing clauses and exposes no dense vectors.

## Semantic ABI is **not** a better nDCG replacement

A predeclared three-dataset falsification campaign now covers **SciFact, NFCorpus and FiQA** across:

- MiniLM dense;
- BGE dense;
- BM25 sparse;
- BGE+BM25 RRF hybrid;
- seven controlled dense degradations per dataset.

Contracts use official **train qrels only**. Official **test qrels** are untouched held-out quality evidence.

The question was deliberately hard:

> Does Semantic ABI predict held-out nDCG better than ordinary train-query nDCG?

### Answer: no general superiority

Across 11 systems/variants per dataset:

| metric | Semantic ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman → test nDCG | **0.9697** | **0.9757** |
| pooled delta Spearman vs BGE | **0.9573** | **0.9724** |
| pooled delta Pearson vs BGE | **0.9519** | **0.9850** |
| pooled pairwise concordance | **0.9172** | **0.9400** |

Per dataset, all-variant Spearman:

- SciFact: ABI **0.9364** vs baseline **0.9704**;
- NFCorpus: ABI **0.9818** vs baseline **0.9727**;
- FiQA: ABI **0.9909** vs baseline **0.9841**.

The mean still favors ordinary validation. Natural-only evidence is near parity and too small for a superiority claim.

**Consequently, Semantic ABI is not positioned as a replacement for nDCG/Recall.** Its differentiated hypothesis is normative/operational: portable hard invariants, cross-paradigm execution, local support/risk, selective fallback, explicit adequacy, integrity diagnostics and auditable change control.

## Selective rollout

The runtime separates conformity, contract coverage, local support/OOD, proxy risk and finite-sample certification.

On SciFact/BGE, support-aware failure-ranking AUC is **0.7875**. At `delta=0.10`, both current methods refuse 10% risk. A rule frozen before certification labels are inspected certifies a **15%** failure SLA with:

- empirical certification risk ~**8.05%**;
- exact upper bound ~**13.16%**;
- held-out coverage **98.5%**;
- realized held-out accepted risk ~**10.15%**.

These are statistical baselines, not new statistical theory.

## Progressive Semantic Audit

Fixed deterministic contract compression failed on held-out localized faults. The scalable direction keeps the **full contract normative** and reduces evaluation cost probabilistically:

- every hard clause is always evaluated;
- soft clauses are sampled proportional to weight;
- repeated draws reuse cached oracle evaluations;
- finite-sample bounds are checked only at predeclared looks;
- ambiguous cases fall back to exhaustive audit.

Evidence:

- real Digits, 1,500 clauses: **15/15** exact decision agreement; **12/15** early; early decisions inspect on average **7.17%** of unique clauses;
- procedural 10k/100k/250k contracts: **10/10** agreement, **9/10** early;
- representative 250k healthy PASS: **200 unique clauses = 0.08%**;
- representative 250k 20%-violation FAIL: **100 = 0.04%**.

This is a mechanism/scaling result, not proof that production faults are iid. Sequential testing has substantial prior art.

## Active repair: useful targeting, incomplete recovery

A real SciFact/BGE test deliberately corrupts 10% of 1,800 document embeddings.

- clean nDCG: **0.7875**;
- corrupted nDCG: **0.6970**;
- corrupted ABI: ~**0.8429**.

At repair budget 25:

- cost-aware coverage planner selects **88% truly corrupted documents**;
- restores ~**33.9%** of lost nDCG;
- random selects ~**7.3%** corrupted and restores ~**1.5%**.

At budget 180, targeted repair reaches roughly **50%** lost-gap recovery versus ~**9%** random.

But **no tested planner reaches the predeclared 90% recovery target**, and ABI conformity can saturate before downstream quality is restored. This is why adequacy is now first-class.

## Application semantics vs implementation integrity

Implementation-specific canaries built from the clean BGE document graph, without test qrels, increase document coverage:

- application-only: **32.3%**;
- + random integrity anchors: **67.0%**;
- + coverage-oriented anchors: **72.5%**.

At repair budget 100, best nDCG-gap recovery improves from ~**62.3%** application-only to ~**70.2–70.8%** with integrity canaries; at budget 180, coverage-oriented integrity reaches ~**71.2%**.

Integrity canaries are **not portable application truth**. They diagnose one concrete implementation.

A new clause-incidence-aware repair planner is being falsified against the same neural corruption benchmark because naive object risk can blame a healthy neighborhood anchor while a damaged expected neighbor is causal.

## Important negative results

Negative evidence changed the architecture:

- **Local SCF translation loses to global** on real BGE→MiniLM SciFact: target-neighbor overlap@10 **0.3680 vs 0.4745**.
- **Fixed Semantic Witness** does not robustly preserve held-out regression detection; random same-size subsets remain competitive.
- **Learned fixed Diagnostic Panel** gets perfect training separation then **0% held-out regression recall**.
- **Aggregate predictive superiority** of ABI over ordinary nDCG validation is not supported by the three-dataset campaign.
- **Current neural repair** does not reach 90% downstream recovery.

## Supporting SMA / SCF machinery

**SMA** retains local charts, mutual-kNN topology, hubness/density diagnostics, CSLS-inspired ranking, intrinsic dimension and `bridge`/`boundary`. Its synthetic hubness stress test improves precision@10 from **0.6300 → 0.8519** and removes injected hubs; this is a mechanism test, not an ANN superiority claim.

**SCF** retains global/local transitions, held-out diagnostics, cycle consistency, partial migration, virtual materialization and drift/fault-line analysis. Cross-model translation has strong prior art; SCF is supporting migration machinery rather than the primary novelty thesis.

## Minimal usage

```python
from semantic_atlas import (
    CallbackSemanticOracle,
    ContractAdequacyEvidence,
    ContractAdequacyRequirements,
    SemanticContract,
    TripletClause,
    assess_contract_adequacy,
    audit_contract,
    progressive_semantic_audit,
)

contract = SemanticContract("product-semantics", "1").add(
    TripletClause("query:refund", "doc:refund-policy", "doc:careers", hard=True)
)

oracle = CallbackSemanticOracle(
    object_ids=frozenset({"query:refund", "doc:refund-policy", "doc:careers"}),
    similarity_fn=my_similarity,
    neighbors_fn=my_neighbors,
    implementation="candidate-retriever",
)

conformity = audit_contract(contract, oracle)
progressive = progressive_semantic_audit(
    contract,
    oracle,
    max_soft_violation_rate=0.05,
    delta=0.05,
)

adequacy = assess_contract_adequacy(
    ContractAdequacyEvidence(
        contract_digest=contract.digest,
        object_coverage=measured_coverage,
        mutation_kill_rate=mutation_score,
        predictive_correlation=heldout_correlation,
        baseline_predictive_correlation=validation_baseline,
        heldout_cases=n_heldout,
        datasets=n_datasets,
    ),
    ContractAdequacyRequirements(
        min_object_coverage=0.70,
        min_mutation_kill_rate=0.90,
        min_predictive_correlation=0.70,
        min_heldout_cases=500,
        min_datasets=3,
    ),
)
```

The example adequacy thresholds are application-policy examples, **not library defaults**.

## Validation / evidence freshness

```bash
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python tools/check_evidence_freshness.py
```

CI covers Python 3.10/3.12/3.13 plus an independent evidence-freshness job. Promoted scientific claims are bound to GitHub Actions artifact identities and Git blob hashes of evidence-sensitive sources; modifying a relevant implementation invalidates its old promoted evidence until regeneration.

## Current highest-value next gates

1. clause-incidence-aware repair;
2. graph/late-interaction contract portability;
3. adequacy under multilingual/domain/temporal shift;
4. Progressive Audit vs Adaptive Learn-Then-Test/e-process baselines;
5. real Elasticsearch/Qdrant/pgvector/Vespa integrations;
6. human contract-acquisition economics;
7. retrieval-specific release governance and professional novelty/IP search.

## Scientific posture

This remains a **falsifiable research program**, not a claim that Semantic ABI is already an industry standard or a proven patent-novel category.

The surviving hypothesis is not “a better vector DB” or “a better nDCG metric.” It is:

> **Can semantic requirements become a portable, versioned interface above replaceable retrieval implementations, with explicit adequacy, statistical audit/rollout, integrity diagnostics and controlled repair?**

See [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) for the full current evidence and limitations.
