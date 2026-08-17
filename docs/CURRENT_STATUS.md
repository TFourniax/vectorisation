# Current research status

**Status date:** 2026-08-17  
**Package:** `semantic-manifold-atlas` **0.4.0**  
**Branch:** `agent/semantic-manifold-atlas`  
**Posture:** evidence-gated research; draft PR; no production-readiness or broad novelty claim.

This is the authoritative dated summary of what currently survives the evidence. Promoted results and exact source/artifact identities are recorded in [`evidence-manifest.json`](evidence-manifest.json).

## Current thesis

The project is no longer primarily a vector-index experiment. The strongest surviving hypothesis is a **semantic change-control layer above retrieval implementations**:

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

The critical correction from the latest experiments is:

> **Conformity is not adequacy.**

A candidate can satisfy the clauses that exist while the contract still fails to observe downstream damage outside its semantic/test surface.

## Implemented core

### Portable Semantic Contract

`SemanticContract` supports ordinal triplets, critical neighborhoods, reciprocal-neighbor clauses, hard/soft requirements, weights/provenance, canonical SHA-256 identity, hash-chained history and static consistency linting.

Application semantics and captured legacy behavior remain separate roles.

### Representation-independent execution

`SemanticOracle` exposes stable-ID membership, affinity and ranked neighborhoods. The audit engine therefore does not require vectors. Dense and callback-backed sparse/graph/hybrid/remote systems can implement the same contract interface.

### Contract Adequacy

`ContractAdequacyEvidence`, `ContractAdequacyRequirements` and `ContractAdequacyReport` make adequacy explicit. Supported axes include object coverage, mutation kill/localization, predictive association with independent held-out outcomes, lift over an ordinary validation baseline, held-out sample count, dataset count and fault-family count.

There is deliberately **no universal passing threshold**. A deployment policy must state its requirements; missing required evidence yields `insufficient_evidence`.

### Statistical rollout / fallback

Conformity, coverage, support/OOD, proxy risk and finite-sample certification remain separate. Current statistical procedures are transparent baselines, not claims of new statistical theory.

### Progressive Semantic Audit

All hard clauses are always evaluated. Positive-weight soft clauses can be sampled proportional to weight with cached oracle calls, predeclared looks, explicit error-budget spending and exact fallback when evidence is insufficient.

The full contract remains normative; Progressive Audit reduces average evaluation cost rather than treating a tiny deterministic subset as equivalent.

### Repair / integrity

Targeted repair planners remain research baselines. A separate **Implementation Integrity Contract** role is used for canaries tied to one concrete index and must not be promoted into portable application truth.

A new clause-incidence-aware repair planner is under active falsification. It attempts to distinguish anchors from missing/intruding neighbors when assigning repair priority; it is not promoted until its held-out neural benchmark beats simpler baselines.

## Strongest real neural evidence — SciFact

Public dataset: `mteb/scifact`; **1,800 documents**, **500 train queries**, **200 held-out test queries**.

### Direct retrieval

| implementation | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|
| MiniLM | 0.7387 | 0.8515 | 0.8600 |
| BGE-small | **0.7821** | **0.8840** | **0.8900** |

### Semantic ABI / portability

650-clause contract digest:

`59d34bc071273dbaa06ce03df1a3b66a2686b6b8c5f240bb49075054909c7b9f`

- MiniLM ABI ~**0.9035**;
- BGE ABI **0.9467**;
- logical-object coverage ~**41.6%**;
- support-aware failure-ranking AUC **0.7875**.

The exact same contract executes against lexical BM25 with no dense vectors exposed:

| implementation | ABI | nDCG@10 | Recall@10 |
|---|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 |

BM25 evaluates **650/650 clauses** with zero missing clauses.

### Selective risk certification

At `delta=0.10`, 5% and 10% failure SLAs are not certified. At 15%, the conservative family rule still refuses, while the pre-registered exact-binomial rule certifies:

- empirical certification risk **8.05%**;
- exact upper bound **13.159%**;
- held-out acceptance **197/200 = 98.5%**;
- realized held-out accepted risk **10.15%**.

### SCF neural falsification

BGE→MiniLM target-neighbor overlap@10:

- global map **0.4745**;
- local atlas **0.3680**.

Held-out validation also favors global. `EvidenceGatedTransition` correctly chooses the simpler global map; “local is generally better” is false.

## Three-dataset predictive-validity gate — completed

Canonical campaign:

- **SciFact, NFCorpus, FiQA**;
- MiniLM dense, BGE dense, BM25 sparse, BGE+BM25 RRF hybrid;
- seven controlled dense degradations per dataset;
- official **train qrels only** for contract construction;
- untouched official **test qrels** for downstream evaluation.

Predeclared question:

> **Does Semantic ABI predict held-out nDCG better than ordinary train-query nDCG?**

### Result: predictive-superiority claim is not supported

Across 11 implementations/variants per dataset:

| metric | Semantic ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman → test nDCG | **0.9697** | **0.9757** |
| pooled delta Spearman vs BGE | **0.9573** | **0.9724** |
| pooled delta Pearson vs BGE | **0.9519** | **0.9850** |
| pooled pairwise concordance | **0.9172** | **0.9400** |

Per-dataset all-variant Spearman:

- SciFact: ABI **0.9364** vs baseline **0.9704**;
- NFCorpus: ABI **0.9818** vs baseline **0.9727**;
- FiQA: ABI **0.9909** vs baseline **0.9841**.

The mean still favors ordinary validation. A separate parallel replication with different NFCorpus/FiQA query seeds reaches the same qualitative narrowing conclusion.

Natural-only evidence is small: nine non-BGE comparison points across three datasets. Pooled Spearman is ABI **0.8333** vs baseline **0.8167**, while Pearson is ABI **0.9513** vs baseline **0.9553**. This is near parity with too little evidence for a superiority claim.

### Consequence

**Semantic ABI is not positioned as a replacement for nDCG/Recall benchmark validation.** Its differentiated hypothesis is narrower:

- portable hard/application invariants that aggregate ranking metrics do not explicitly encode;
- one contract executable across dense/sparse/hybrid paradigms;
- local support/risk and selective fallback;
- explicit adequacy evidence;
- implementation-integrity diagnostics;
- auditable semantic change governance.

## Progressive Semantic Audit evidence

### Real Digits — 1,500 clauses

- exact decision agreement **15/15**;
- early decisions **12/15**;
- mean unique-clause fraction among early decisions **7.17%**.

### Scale — 10k / 100k / 250k clauses

Across 10 procedural weighted-contract cases:

- exact decision agreement **10/10**;
- early decisions **9/10**;
- the deliberately near-boundary case falls back to exhaustive audit.

Representative far-from-boundary clause fractions:

| contract size | healthy PASS | 20% violation FAIL | ~10% violation FAIL |
|---:|---:|---:|---:|
| 10,000 | 1.92% | 0.98% | 3.84% |
| 100,000 | 0.20% | 0.10% | 0.20% |
| 250,000 | 0.08% | 0.04% | 0.3992% |

This is a strong scaling/mechanism result, not evidence that production faults are iid. Sequential testing itself has substantial prior art.

## Real neural repair economics — mixed result

SciFact/BGE, 1,800 documents, 350 train queries, 200 untouched test queries.

Clean: ABI **0.9480**, nDCG **0.7875**.

10% document-embedding corruption: ABI ~**0.8429**, nDCG ~**0.6970**.

At repair budget 25:

- cost-aware coverage planner selects **88% actually corrupted documents**;
- restores ~**33.9%** of lost nDCG;
- random selects ~**7.3%** corrupted and restores ~**1.5%**.

At budget 180, targeted repair reaches roughly **50%** lost-gap recovery versus ~**9%** random.

### Negative gate

**No tested planner reaches the predeclared 90% lost-nDCG recovery target.** Application conformity can return close to its clean score before held-out nDCG is fully repaired. This is the direct empirical motivation for Contract Adequacy.

## Implementation-integrity canaries

On the same 10% BGE corruption, canaries built from the clean document graph without test qrels increase observed document coverage:

- application-only **32.3%**;
- + random integrity anchors **67.0%**;
- + coverage-oriented integrity anchors **72.5%**.

At budget 100, best nDCG-gap recovery rises from ~**62.3%** application-only to ~**70.2–70.8%** with integrity canaries. At budget 180, coverage-oriented integrity reaches ~**71.2%**.

Still no 90% recovery.

A neighborhood violation can blame a healthy anchor while a corrupted expected neighbor is causal. This motivated the clause-incidence-aware repair experiment now running.

## Other useful real-data mechanisms

### Application semantics vs legacy behavior

Digits pixels/HOG:

- application contract: pixels ~**0.980**, HOG ~**0.911**, corrupted HOG ~**0.813**;
- legacy-behavior contract: pixels **1.000**, HOG ~**0.711**, corrupted HOG ~**0.610**.

### Semantic Diff

Only ~**11.7%** of all pixels↔HOG disagreements are label-resolvable in the benchmark oracle, versus **68%** of the top 25 and **60%** of the top 50 (~5–6× enrichment).

### Mutation adequacy

The current Digits contract kills all four controlled mutation families globally. Localization remains weaker than detection.

## Falsified / narrowed mechanisms

### Fixed Semantic Witness

On 1,500 clauses with held-out IDs/severities and an unseen drift family:

- 10 clauses: TPR **62.5%**, FPR **0%**;
- 25 clauses: TPR **100%**, FPR **28.6%**;
- 100 clauses: TPR **100%**, FPR **42.9%**.

Random same-size subsets remain competitive.

### Learned fixed Diagnostic Panel

Perfect training discrimination → **0% held-out regression recall** across tested budgets.

### Aggregate predictive superiority

The three-dataset gate explicitly rejects the claim that current Semantic ABI is generally a better aggregate nDCG predictor than ordinary IR validation.

## Evidence / CI discipline

CI covers Python **3.10 / 3.12 / 3.13**, full `pytest`, the fixed hubness benchmark and an independent `evidence-freshness` gate.

`docs/evidence-manifest.json` binds promoted evidence to GitHub Actions run/head identity, artifact SHA-256 and Git blob hashes of evidence-sensitive source files. Changing a promoted algorithm/benchmark makes its evidence stale until regenerated.

## Claims we explicitly do not make

The repository does **not** currently claim that it replaces SQL; that 3-D coordinates are semantic truth; that SMA universally beats mature ANN engines; that SCF invented cross-model translation; that local mapping is generally superior; that Semantic ABI replaces ordinary IR metrics; that ABI is a superior global nDCG predictor; that high conformity proves adequacy; that integrity canaries are portable application truth; that current repair restores 90%+ of downstream quality; that sequential testing/risk control/AI attestation were invented here; or that the project is production-ready/patent-novel.

## Highest-value next gates

1. **Clause-incidence-aware repair** — current experiment: identify missing/intruding neighbors rather than blindly blaming anchors.
2. **Graph / late-interaction representation** — same application contract beyond dense/sparse/hybrid.
3. **Adequacy under shift** — multilingual, domain, temporal and long-tail slices.
4. **Progressive Audit vs Adaptive Learn-Then-Test / e-processes** under realistic non-iid faults.
5. **Real backends** — Elasticsearch, Qdrant, pgvector, Vespa/late interaction without rebuilding ANN.
6. **Human contract-acquisition economics** — Semantic Diff vs random, uncertainty and coverage-guided baselines.
7. **Release governance** — adequacy evidence, typed contract roles, signatures/expiry/revocation.
8. **Professional novelty/IP search** before strong publication/patent claims.

## Current assessment

The project has **narrowed but strengthened**. The surviving question is not “did we invent a better quality metric?” It is:

> **Can semantic requirements become a portable, versioned interface above replaceable retrieval implementations, with explicit adequacy, statistical audit/rollout, integrity diagnostics and controlled repair?**

The evidence is strong enough to continue that question and strong enough to reject several weaker/overbroad versions of it.
