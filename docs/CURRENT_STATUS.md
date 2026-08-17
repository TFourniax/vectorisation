# Current research status

**Status date:** 2026-08-17  
**Research package:** `semantic-manifold-atlas` **0.4.0**  
**Branch:** `agent/semantic-manifold-atlas`  
**Posture:** evidence-gated research; draft PR; no production-readiness or broad novelty claim.

This file is the shortest authoritative answer to **what currently survives the evidence**. Historical documents may explain earlier hypotheses, but current claims must agree with this page and `evidence-manifest.json`.

## Current thesis

The project is no longer primarily trying to invent another vector index.

The strongest current hypothesis is a **semantic change-control layer above retrieval implementations**:

```text
stable logical objects
        |
   Semantic ABI
(versioned invariants)
        |
  SemanticOracle
 dense / sparse / graph / hybrid / remote
        |
 audit + support + risk
        |
  +-----+---------+
  |               |
rollout         fallback
  |               |
release          repair
certificate       |
  +------ re-audit/re-certify
```

A vector is one representation of meaning, not the canonical identity or meaning itself.

## What is implemented and still promoted

### 1. Coordinate-free Semantic Contract

`SemanticContract` expresses requirements over stable logical IDs:

- ordinal triplets;
- critical-neighborhood survival;
- reciprocal-neighbor relations;
- hard/soft requirements;
- weights and provenance;
- canonical SHA-256 identity;
- append-only hash-chained `ContractLedger`;
- static contract linting for contradictions/impossible requirements.

Application-semantic contracts and legacy-behavior regression contracts remain intentionally separate.

### 2. Representation-independent audit interface

`SemanticOracle` is the executable boundary between the ABI and an implementation. A compatible implementation only needs stable-ID membership, affinity and neighborhoods.

Adapters currently include:

- `DenseVectorOracle` — dense cosine representation;
- `CallbackSemanticOracle` — sparse, graph, hybrid, remote or other behavior providers.

The full contract audit no longer requires a vector coordinate system.

### 3. Support-aware local rollout risk

The project separates:

1. contract score;
2. contract/object coverage;
3. query support / OOD evidence;
4. proxy risk;
5. statistical risk certification.

A candidate may therefore serve only a certified region while legacy fallback remains active elsewhere.

### 4. Two explicit statistical certification baselines

`calibrate_semantic_risk()` is the conservative baseline:

- selection/certification split;
- several candidate thresholds;
- independent certification;
- Chernoff/KL upper bounds;
- family-wise union correction.

`calibrate_semantic_risk_preregistered()` is the sample-efficiency baseline:

- the selection split chooses **one** threshold under an internal slack budget;
- that threshold is frozen before certification labels are inspected;
- one-sided exact binomial certification is then applied to that single rule;
- no post-holdout fallback to another threshold is allowed.

Neither method is claimed as new statistical theory. They are auditable baselines to be compared with Learn-Then-Test, conformal/selective risk-control and shift-aware methods.

### 5. Progressive Semantic Audit

`progressive_semantic_audit()` is the current answer to the contract-cost problem.

Policy:

- every hard clause is always evaluated;
- positive-weight soft clauses are sampled with replacement proportional to weight;
- cached clause evaluations avoid repeating expensive oracle work;
- exact binomial bounds are evaluated at pre-declared batch looks;
- the global error budget is split across both tails and all possible looks;
- PASS/FAIL may be returned early for a weighted soft-clause violation-rate SLA;
- ambiguous cases fall back to the exact full audit.

This is deliberately a different policy from the historical aggregate contract score. It gives a probabilistic audit-cost trade-off instead of pretending a tiny deterministic clause subset is equivalent to the full contract.

### 6. Active semantic repair

Two transparent repair baselines remain:

- risk/centrality/diversity planning;
- cost-aware known-violation coverage planning.

The intended optimization target is **certified semantic surface gained per unit cost**, not raw percentage of vectors recomputed.

### 7. Semantic Diff / active contract acquisition

`semantic_diff()` and `propose_contract_questions()` identify high-value representation disagreements and turn them into human/domain ordinal questions.

The goal is to acquire a useful contract from a much smaller number of explicit judgments than exhaustive labeling.

### 8. Semantic mutation adequacy

Controlled identity permutation, local collapse, hub-pull and noise mutations test whether a contract can notice deliberately introduced semantic damage.

Mutation testing is an adequacy instrument, not a novelty claim.

### 9. Semantic Release Certificate

`SemanticReleaseCertificate` binds:

- exact implementation/provider/model revision;
- representation dimension/modality;
- preprocessing digest;
- contract digest;
- audit state and coverage;
- risk certificate;
- benchmark/evidence hashes;
- release status.

The manifest is hash-addressed. Cryptographic issuer signatures/transparency logs remain future work.

### 10. Evidence-gated coordinate migration

SCF remains available as migration machinery:

- global scaled Procrustes;
- local transition atlases;
- held-out diagnostics;
- multi-hop routes/cycle checks;
- partial migration fusion;
- virtual target-space materialization;
- drift/fault-line diagnostics.

But **local translation is not a default**. `EvidenceGatedTransition` may choose local only if held-out evidence shows a required gain over global.

## Strongest real neural evidence — SciFact

Public dataset: `mteb/scifact`  
Documents: **1,800**  
Train queries: **500**  
Held-out test queries: **200**

Encoders:

- legacy: `sentence-transformers/all-MiniLM-L6-v2`;
- candidate: `BAAI/bge-small-en-v1.5`, revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.

### Direct retrieval

| implementation | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|
| MiniLM | 0.7387 | 0.8515 | 0.8600 |
| BGE-small | **0.7821** | **0.8840** | **0.8900** |

BGE is the stronger direct retriever on this experiment.

### Semantic ABI

Contract:

- **650 clauses**;
- exact contract digest `59d34bc071273dbaa06ce03df1a3b66a2686b6b8c5f240bb49075054909c7b9f`;
- logical-object coverage about **41.6%**.

Scores:

- MiniLM: about **0.9035**;
- BGE-small: **0.9467**.

The held-out support-aware proxy-risk field has AUC **0.7875** for ranking hit@10 failures in this experiment. This is encouraging discrimination, not proof of calibrated probability.

### Statistical rollout certification

Calibration events: **175**. Certification split: **87**. `delta = 0.10`.

| requested failure SLA | simultaneous KL family | preregistered exact |
|---:|---|---|
| 5% | not certified | not certified |
| 10% | not certified | not certified |
| 15% | not certified; upper 19.19% | **certified; upper 13.16%** |
| 20% | certified | certified |

For the 15% pre-registered exact certificate:

- selected certification empirical risk: **8.05%**;
- exact one-sided upper bound: **13.159%**;
- held-out test coverage: **98.5%** (197/200 queries);
- held-out realized failure rate inside the accepted region: **10.15%**.

This is a useful sample-efficiency result. It does **not** make the 10% SLA certifiable; both methods correctly abstain there.

### First real dense-vs-sparse portability test

The exact same contract digest and all **650 clauses** were audited against a lexical BM25 implementation through `CallbackSemanticOracle`, with no dense vectors exposed.

| implementation | Semantic ABI score | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** | **0.8900** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 | 0.8400 |

BM25 evaluated **650/650** clauses with zero missing clauses and passed all hard requirements in this contract.

This is the first executable evidence that the Semantic ABI can survive a change of **representation paradigm**, not only an embedding-model change. It is one dataset/contract shape, not universal proof across graphs, hybrid rankers or multimodal systems.

### SCF falsification on the same neural pair

BGE→MiniLM target-neighbor overlap@10:

- global map: **0.4745**;
- local atlas: **0.3680**.

Held-out transition validation score:

- global: **0.5533**;
- local: **0.4939**;
- local gain: **-0.0594**.

`EvidenceGatedTransition` correctly selects **global**. Therefore “local is better” is empirically false on this pair; local SCF remains an optional expert that must win a holdout before use.

## Progressive Semantic Audit evidence — Digits

Real dataset: `sklearn.datasets.load_digits`  
Logical objects: **1,000**  
Semantic contract: **1,500 soft clauses**  
Scenarios: baseline + four controlled corruptions  
SLAs: 2%, 5%, 10% weighted soft-clause violation rate  
Confidence budget: `delta = 0.05`.

Across **15 scenario/SLA decisions**:

- decision agreement with exact exhaustive audit: **15/15 = 100%**;
- **12/15** decisions finished without a full audit;
- among those early decisions, mean unique-clause evaluation fraction: **7.17%**.

Examples:

- identity permutation, 5% SLA: FAIL after **49/1,500 clauses (3.27%)**;
- coordinate noise, 5% SLA: FAIL after **49/1,500 (3.27%)**;
- hub-pull, 5% SLA: FAIL after **140/1,500 (9.33%)**;
- healthy baseline, 10% SLA: PASS after **186/1,500 (12.4%)**.

Three near-boundary cases correctly fell back to **1,500/1,500** clauses. This fallback behavior is a feature: the method buys cost savings when the semantic margin is large and refuses to manufacture confidence near the SLA boundary.

The baseline contract itself has an exact soft-clause violation rate of about **4.73%**, so its 5% SLA is intentionally a difficult near-boundary case and requires full evaluation in this run.

## Other positive real-data mechanisms

### Application semantics vs legacy behavior

On Digits pixels vs HOG:

- application contract: pixels about **0.980**, HOG about **0.911**, deliberately corrupted HOG about **0.813**;
- captured legacy behavior: pixels **1.000**, HOG about **0.711**, corrupted HOG about **0.610**.

The experiment demonstrates why application meaning should not be collapsed into exact legacy-ranking imitation.

### Active repair

With 140/1,400 HOG objects deliberately corrupted (10%):

- budget 25: **68%** of selected objects truly corrupt;
- 50: **54%**;
- 100: **37%**;
- 140: **33.6%**.

Uniform-random expectation is 10%.

### Semantic Diff

On pixels↔HOG representation disagreements, only about **11.7%** of all disagreement questions are label-resolvable under the benchmark oracle, versus:

- top 25 proposed questions: **68%**;
- top 50: **60%**.

That is roughly **5–6x enrichment** for the highest-priority questions in this mechanism test.

### Mutation adequacy

The current Digits contract kills all four controlled mutation families in the tested densities. Localization is materially weaker than global detection and remains an open problem.

## Negative / narrowed results that must remain visible

### Fixed Semantic Witness sparsification — not solved

A 1,500-clause contract was compressed using fault-driven greedy selection and evaluated on changed IDs, 3–10% fault footprints, changed severities and an unseen coherent-drift family.

Representative held-out results:

- 10 clauses (150x nominal compression): TPR **62.5%**, FPR **0%**;
- 25 clauses: TPR **100%**, FPR **28.6%**;
- 100 clauses: TPR **100%**, FPR **42.9%**.

Random same-size subsets remain competitive on the specificity/sensitivity trade-off. Therefore deterministic witness sparsification is **not promoted as a production mechanism**.

### Learned discriminative Diagnostic Panel — falsified in current form

A panel trained to separate four known regressions from twelve full-contract-approved micro-drifts achieved perfect training separation, then **0% TPR on eight held-out regressions** across budgets 5–100 clauses.

This is strong evidence of object-local overfitting. The top-level API does not expose this experimental panel.

### Why these failures matter

They changed the architecture. A tiny fixed set attached to specific logical objects cannot guarantee detection of arbitrary sparse regressions elsewhere. The project therefore moved from **deterministic contract compression** toward **randomized progressive audit with statistical guarantees**.

## Current software validation

Current CI validates Python **3.10, 3.12 and 3.13**. On the current 0.4 research kernel before evidence-manifest tests are added:

- `pytest`: **65 passed**;
- hubness benchmark executes successfully;
- scientific neural/real-data workflows are isolated from the lightweight CI.

## Claims we explicitly do not make

The repository does **not** currently claim:

- that it replaces SQL;
- that 3-D coordinates encode semantic truth;
- that SMA universally beats mature ANN engines;
- that SCF invented cross-model translation;
- that local translation is generally better than global;
- that Semantic ABI is a proven industry standard or patent-novel abstraction;
- that the present risk-control procedures provide arbitrary distribution-shift guarantees;
- that the dense↔sparse SciFact result proves portability to every representation family;
- that deterministic contract sparsification has been solved;
- that the project is production-ready.

## Highest-value next gates

1. **Multi-dataset / multi-model replication.** Repeat neural evidence on several unrelated encoder pairs, BEIR/MTEB tasks and seeds.
2. **Multilingual and domain shift.** Measure support/risk certification under language, temporal and domain shifts.
3. **Third representation paradigm.** Audit the exact same contract against a graph/hybrid/late-interaction implementation.
4. **Progressive audit scaling.** Test 10k/100k/million-clause synthetic-or-replayed contracts, weighted clauses, heterogeneous costs and stratified/slice sampling.
5. **Stronger statistical baselines.** Compare preregistered exact certification with Learn-Then-Test, conformal/selective risk-control and shift-aware reweighting.
6. **Repair economics.** Optimize certified-coverage gained per dollar/token/GPU-second and compare against full re-embedding.
7. **Real integrations.** Qdrant/pgvector/Elasticsearch/Vespa adapters without reimplementing ANN.
8. **Contract acquisition.** Continue Semantic Diff with human/domain judgments and evaluate annotation cost vs downstream regression prediction.
9. **Release governance.** Signed certificates, expiry/revocation, transparency log and reviewer identity.
10. **Professional novelty/IP search.** Especially semantic regression contracts, specification-driven IR gates and semantic release attestations.

## Evidence freshness

The repository is moving toward machine-enforced evidence freshness:

- benchmark outputs are GitHub Actions artifacts with SHA-256 digests;
- `docs/evidence-manifest.json` binds claims to workflow runs and source Git blobs;
- CI verifies that evidence-sensitive source blobs still match the manifest;
- changing an algorithm/benchmark therefore makes its documented evidence stale until the corresponding benchmark is regenerated and the manifest is updated.

This is intentionally stricter than manually remembering to edit a README.
