# Semantic ABI — portable meaning contracts with explicit adequacy

## Thesis

A vector is neither the identity nor the meaning of a data object. It is one representation emitted by one implementation at one point in time.

Semantic ABI asks:

> **What must remain semantically true when a retrieval implementation changes, and what evidence is required before that statement is trusted?**

The current architecture separates four concepts:

```text
Application Semantic Contract
     portable normative truth
              |
        SemanticOracle
 dense / sparse / graph / hybrid / remote
              |
      Contract Conformity
              |
     +--------+---------+
     |                  |
Contract Adequacy   Implementation Integrity
is the contract      canaries for one concrete
observant enough?     implementation/index
     |                  |
     +--------+---------+
              |
       support + risk
              |
       rollout/fallback
              |
       repair/re-audit
```

This is a semantic change-control research program, not a claim that Semantic ABI is already a standard or patent-novel abstraction.

For exact current evidence, use [`CURRENT_STATUS.md`](CURRENT_STATUS.md) and [`evidence-manifest.json`](evidence-manifest.json).

## 1. Application Semantic Contract

`SemanticContract` operates on stable logical IDs rather than required vector coordinates.

Current clauses:

- ordinal triplet — `A must prefer B over C`;
- critical neighborhood — important neighbors must survive above a configured recall floor;
- mutual-neighbor relation — a reciprocal relation must survive.

Clauses can be hard/soft, weighted and provenance-tagged. Contracts have canonical SHA-256 identity, static consistency linting and hash-chained history.

Ordinal constraints themselves are established mathematics; they are used here as one contract primitive, not claimed as new.

## 2. Application semantics, legacy behavior and integrity are different

### Application semantics

Portable requirements from relevance judgments, domain rules, ontologies, expert decisions, safety constraints or observed outcomes.

### Legacy behavior

Selected old ranking/neighborhood behavior consciously preserved during a migration. It must not automatically become permanent application truth.

### Implementation integrity

Canaries describing expected behavior of **one concrete implementation** so silent corruption can be detected. They must not be used to reject a legitimate migration to a different representation family.

This separation is evidence-driven. On Digits, HOG preserves the application contract (~0.911) much better than captured legacy behavior (~0.711). On real SciFact repair, application conformity can recover before all downstream retrieval damage is repaired, motivating a separate integrity role.

## 3. `SemanticOracle`: vectors are optional

The executable ABI boundary is:

```python
contains(object_id)
similarity(left, right)
neighbors(anchor, k)
```

Current adapters include dense cosine vectors and callback-backed arbitrary retrieval behavior.

### Real cross-paradigm evidence

On SciFact, the same 650-clause contract digest executes against:

| implementation | ABI | nDCG@10 | Recall@10 |
|---|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 |

BM25 exposes no dense vectors and evaluates **650/650 clauses** with zero missing clauses.

A larger three-dataset campaign additionally executes contracts across MiniLM dense, BGE dense, BM25 sparse and BGE+BM25 hybrid systems on SciFact, NFCorpus and FiQA.

## 4. Conformity is not adequacy

A `ContractReport` answers:

> Does this implementation satisfy the clauses that exist?

It does **not** answer:

> Are the clauses sufficient to justify the claim we want to make?

Real neural repair exposed states where application ABI returns near its clean score while held-out nDCG remains below the clean index.

`ContractAdequacyEvidence` therefore records separate evidence axes:

- object coverage;
- mutation kill/localization;
- predictive association with independent held-out outcomes;
- predictive lift over an ordinary validation baseline;
- held-out cases, datasets and fault families.

`ContractAdequacyRequirements` deliberately has no hidden defaults. `assess_contract_adequacy()` returns:

- `adequate` only when every declared requirement is observed and passes;
- `failed` when any observed requirement fails;
- `insufficient_evidence` when a required axis is missing.

## 5. Predictive validity: ABI does not replace nDCG

A predeclared campaign compared ABI compatibility with ordinary train-query nDCG for predicting untouched test nDCG across SciFact, NFCorpus and FiQA.

Natural systems: MiniLM, BGE, BM25 and BGE+BM25 hybrid. Seven controlled dense degradations per dataset broadened the quality range. Train qrels alone authored contracts; test qrels were evaluation-only.

### Canonical result

Across 11 systems/variants per dataset:

| metric | ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman → test nDCG | **0.9697** | **0.9757** |
| pooled delta Spearman vs BGE | **0.9573** | **0.9724** |
| pooled delta Pearson | **0.9519** | **0.9850** |
| pooled pairwise concordance | **0.9172** | **0.9400** |

Per-dataset all-variant Spearman:

- SciFact: ABI 0.9364 vs baseline 0.9704;
- NFCorpus: ABI 0.9818 vs baseline 0.9727;
- FiQA: ABI 0.9909 vs baseline 0.9841.

The mean still favors ordinary validation. Natural-only points are near parity but too few for a superiority claim.

### Consequence

**Semantic ABI is not a replacement for nDCG/Recall validation and is not claimed to be a superior global quality predictor.**

Its differentiated hypothesis is narrower:

- explicit portable hard invariants;
- one contract across heterogeneous retriever paradigms;
- local support/risk and fallback;
- adequacy evidence;
- typed integrity diagnostics;
- auditable semantic change governance.

## 6. Support and rollout risk

Conformity, adequacy, object coverage, local support, proxy risk and statistical certification are different claims.

`estimate_local_semantic_risk()` combines sparse contract risk with unsupported-region penalties; this is a diagnostic rather than an arbitrary-shift theorem.

### SciFact selective certification

For BGE on SciFact:

- failure-risk ranking AUC ~**0.7875**;
- 10% SLA is rejected by both current methods;
- a rule frozen before certification labels are inspected certifies a 15% SLA with exact upper bound ~**13.16%**;
- held-out acceptance **197/200 = 98.5%**;
- realized accepted failure rate ~**10.15%**.

Current procedures are auditable baselines. Learn-Then-Test, adaptive LTT/e-processes and conformal/selective risk control are explicit prior art/baselines.

## 7. Progressive Semantic Audit

Fixed deterministic contract compression failed. The full contract remains normative.

`progressive_semantic_audit()` instead defines a weighted soft-clause violation-rate SLA:

1. evaluate every hard clause;
2. sample soft clauses with replacement proportional to weight;
3. reuse cached oracle evaluations;
4. inspect only at predeclared looks;
5. allocate the global error budget across looks/tails;
6. early PASS/FAIL only when finite-sample bounds separate from the SLA;
7. otherwise execute the full exact audit.

Evidence:

- Digits 1,500 clauses: **15/15** agreement with full audit, **12/15** early, mean early unique fraction **7.17%**;
- procedural 10k/100k/250k: **10/10** agreement, **9/10** early;
- representative 250k healthy PASS after **0.08%** unique clauses;
- representative 250k 20%-violation FAIL after **0.04%**.

This is a mechanism/scaling result. Sequential testing itself is not new.

## 8. Why fixed contract compression was demoted

### Semantic Witness

Held-out 1,500-clause stress test:

- 10 clauses: TPR 62.5%, FPR 0%;
- 25 clauses: TPR 100%, FPR 28.6%;
- 100 clauses: TPR 100%, FPR 42.9%.

Random same-size subsets remain competitive.

### Fixed Diagnostic Panel

Perfect training separation produced **0% held-out regression recall**. It overfit object-local faults and is not promoted as a production API.

## 9. Contract acquisition and adequacy testing

`semantic_diff()` converts representation disagreements into prioritized domain questions. Digits evidence: only ~11.7% of all disagreements are label-resolvable, versus 68% in the top 25 and 60% in the top 50 (~5–6× enrichment).

Mutation testing deliberately injects identity permutation, local collapse, hub pull and noise. Current Digits contracts kill all tested mutation families globally; localization is weaker.

Active acquisition and mutation testing both have substantial prior art. Their role here is to build/evaluate a portable contract, not to claim those methods as inventions.

## 10. Active repair and implementation integrity

### Neural repair economics

SciFact/BGE, 1,800 docs, 350 train queries, 200 untouched test queries.

Clean: ABI ~0.9480, nDCG ~0.7875.  
10% corruption: ABI ~0.8429, nDCG ~0.6970.

At budget 25:

- coverage planner selects **88% actually corrupted docs**;
- recovers ~**33.9%** of lost nDCG;
- random selects ~**7.3%** corruption and recovers ~**1.5%**.

No tested planner reaches 90% lost-nDCG recovery. Conformity can recover before downstream quality.

### Integrity canaries

Without test qrels, clean-index canaries raise document coverage from **32.3%** application-only to **67.0%** random-integrity and **72.5%** coverage-oriented integrity.

At budget 100, best nDCG-gap recovery rises from ~62.3% to ~70.2–70.8%; at budget 180 coverage-oriented integrity reaches ~71.2%.

Still no 90% recovery.

Naive object risk can blame a healthy neighborhood anchor while an expected/intruding neighbor is causal. A clause-incidence-aware planner is currently being falsified against the same neural benchmark.

## 11. Release evidence

`SemanticReleaseCertificate` binds exact implementation/preprocessing identity, contract identity, audit/risk state and evidence hashes. Generic AI attestation and pre-deployment certificates have substantial prior art; they are not a novelty claim.

`docs/evidence-manifest.json` separately binds promoted research claims to exact GitHub Actions artifacts and evidence-sensitive source blobs. CI invalidates stale promoted evidence automatically.

## 12. Relationship to SCF

The layers answer different questions:

- **SCF:** can observations/queries move between coordinate systems during migration?
- **Conformity:** does an implementation satisfy declared application invariants?
- **Adequacy:** is the contract surface sufficient for the claim?
- **Integrity:** is one concrete implementation silently damaged?
- **rollout certification:** where may a candidate serve traffic?
- **Progressive Audit:** how cheaply can a large contract be audited?

On BGE→MiniLM SciFact, global translation beats local; complexity is evidence-gated rather than assumed.

## 13. Research questions now worth pursuing

1. Can the same application contract work across graph/late-interaction/multimodal systems after dense/sparse/hybrid?
2. Which adequacy axes predict when conformity can be trusted downstream?
3. Can clause-incidence-aware repair beat simple highest-risk/coverage baselines?
4. Can Adaptive LTT/e-processes improve Progressive Audit under realistic non-iid faults?
5. How does adequacy/risk behave under language/domain/temporal shift?
6. Which acquisition policy minimizes expert judgments per real regression caught?
7. Can retrieval-specific release evidence become independently verifiable across providers/backends?

## Kill / narrow criteria

Semantic ABI should collapse toward ordinary regression testing if representative systems show that portable invariants, adequacy, local risk/fallback, progressive audit or repair governance add little operational value beyond conventional benchmark suites.

The objective is not to preserve the phrase **Semantic ABI**. The objective is to discover whether a portable, auditable semantic interface can make retrieval changes materially safer and cheaper.
