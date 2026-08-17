# Current research status

**Status date:** 2026-08-17  
**Research package:** `semantic-manifold-atlas` **0.4.0**  
**Branch:** `agent/semantic-manifold-atlas`  
**Posture:** evidence-gated research; draft PR; no production-readiness or broad novelty claim.

This file is the shortest authoritative answer to **what currently survives the evidence**. Historical documents explain earlier hypotheses, but current claims must agree with this page and [`evidence-manifest.json`](evidence-manifest.json).

## Current thesis

The project is no longer primarily trying to invent another vector index. The strongest current hypothesis is a **semantic change-control layer above retrieval implementations**:

```text
stable logical objects
        |
   Semantic ABI
(portable application invariants)
        |
  SemanticOracle
 dense / sparse / graph / hybrid / remote
        |
  Contract Conformity Audit
        |
  +-----+---------------------+
  |                           |
Contract Adequacy       Implementation Integrity
(is the contract         (canaries for one concrete
 observant enough?)       implementation; not app truth)
  |                           |
  +----------+----------------+
             |
      support + risk
             |
      rollout / fallback
             |
      repair / re-audit
             |
       release evidence
```

A vector is one representation of meaning, not the canonical identity or meaning itself.

The most important correction from the latest experiments is:

> **Contract conformity is not contract adequacy.**

A candidate can satisfy every observed clause while the contract still fails to observe downstream damage outside its support. `ContractAdequacyEvidence` / `ContractAdequacyReport` therefore make adequacy a separate, policy-declared evidence problem rather than inferring it from a high ABI score.

## What is implemented and still promoted

### Coordinate-free Semantic Contract

`SemanticContract` expresses requirements over stable logical IDs:

- ordinal triplets;
- critical-neighborhood survival;
- reciprocal-neighbor relations;
- hard/soft requirements;
- weights and provenance;
- canonical SHA-256 identity;
- append-only hash-chained `ContractLedger`;
- static linting for contradictions/impossible requirements.

Application-semantic contracts and legacy-behavior regression contracts remain intentionally separate.

### Representation-independent audit

`SemanticOracle` is the executable boundary between the ABI and an implementation. A compatible system exposes stable-ID membership, pairwise affinity and ranked neighborhoods. The current adapters cover dense vectors and arbitrary callback-backed sparse/graph/hybrid/remote behavior.

### Contract adequacy — new explicit layer

`ContractAdequacyEvidence` records evidence that the contract itself is sufficiently observant for a declared deployment claim. Available axes include:

- logical-object coverage;
- mutation kill rate;
- mutation localization;
- predictive association with held-out outcomes;
- predictive lift over an ordinary validation baseline;
- number of held-out cases, datasets and fault families.

There is deliberately **no universal adequacy score or hidden default threshold**. `ContractAdequacyRequirements` must state the application policy explicitly. Missing evidence yields `insufficient_evidence`; a high conformity score cannot silently substitute for absent adequacy evidence.

### Support-aware rollout risk

The project keeps separate:

1. contract conformity;
2. contract/object coverage;
3. support/OOD evidence;
4. proxy risk;
5. statistical risk certification.

A candidate may therefore serve only a certified region while legacy fallback remains active elsewhere.

### Statistical certification baselines

`calibrate_semantic_risk()` is a conservative split + Chernoff/KL family-corrected baseline. `calibrate_semantic_risk_preregistered()` freezes one selection-split rule before certification labels are inspected and uses a one-sided exact binomial bound on the independent holdout.

These are auditable baselines, not claims of new statistical theory. Current prior art requires comparison with Learn-Then-Test, adaptive LTT/e-processes, conformal/selective risk control and shift-aware methods.

### Progressive Semantic Audit

`progressive_semantic_audit()` is the current answer to large-contract audit cost:

- every hard clause is always evaluated;
- positive-weight soft clauses are sampled with replacement proportional to weight;
- repeated draws reuse cached clause evaluations;
- exact-binomial bounds are checked only at declared batch looks;
- the global error budget is spent across both tails and all possible looks;
- PASS/FAIL can occur early for a weighted soft-clause violation-rate SLA;
- ambiguous cases fall back to the exact full audit.

The full contract remains normative. This replaces the failed idea that a tiny deterministic clause subset could be treated as equivalent to the full contract.

### Active semantic repair

Two transparent planners remain research baselines:

- risk / violation-centrality / diversity;
- cost-aware known-violation coverage.

The latest neural experiment shows that targeted planning is highly enriched over random re-embedding, but it also exposes a contract-adequacy blind spot and does **not** justify claiming that current planners solve full downstream recovery.

### Implementation-integrity canaries — separate from application truth

The latest repair experiment adds a second contract role: implementation-specific integrity canaries built from the clean behavior of one index. They are useful for detecting/repairing silent corruption of that same implementation but must **not** be used as portable application truth during a model migration.

This distinction is now architectural:

- **Application Semantic Contract:** portable normative requirements.
- **Implementation Integrity Contract:** concrete implementation canaries.
- **Contract Adequacy Evidence:** evidence that the chosen contracts/tests observe enough of the claimed behavior.

Naively merging their object-risk fields is not sufficient; a failed neighborhood can implicate a healthy anchor even when the corrupted neighbor is the causal object. Role-aware/causal repair is an open research problem.

### Semantic Diff / mutation adequacy / release evidence

`Semantic Diff` prioritizes representation disagreements for human/domain contract acquisition. Controlled semantic mutations test whether a contract notices deliberately introduced damage. `SemanticReleaseCertificate` binds exact implementation identity, contract identity, audit/risk state and evidence hashes, but generic AI attestation/certificate ideas have substantial prior art and are not claimed as novel by themselves.

### Evidence-gated coordinate migration

SCF remains useful migration machinery, but local translation is not a default. `EvidenceGatedTransition` selects it only when an independent holdout demonstrates a required gain over a simpler global adapter.

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

### Semantic ABI

The application contract contains **650 clauses**, exact digest `59d34bc071273dbaa06ce03df1a3b66a2686b6b8c5f240bb49075054909c7b9f`, with logical-object coverage about **41.6%**.

- MiniLM ABI score: about **0.9035**;
- BGE ABI score: **0.9467**;
- held-out support-aware proxy-risk AUC for hit@10 failure ranking: **0.7875**.

AUC is discrimination, not calibrated failure probability.

### Statistical rollout certification

Calibration events: **175**; certification split: **87**; `delta=0.10`.

| requested failure SLA | simultaneous KL family | preregistered exact |
|---:|---|---|
| 5% | not certified | not certified |
| 10% | not certified | not certified |
| 15% | not certified | **certified** |
| 20% | certified | certified |

For the 15% preregistered certificate:

- certification empirical risk: **8.05%**;
- exact one-sided upper bound: **13.159%**;
- held-out test coverage: **98.5%** (197/200);
- held-out realized failure rate inside the accepted region: **10.15%**.

### First real dense-vs-sparse portability test

The exact same contract digest and all **650 clauses** execute against lexical BM25 through `CallbackSemanticOracle` with no dense vectors exposed.

| implementation | Semantic ABI | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** | **0.8900** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 | 0.8400 |

BM25 evaluates **650/650** clauses with zero missing clauses. This is real cross-paradigm executable evidence, not universal portability proof.

### SCF falsification on the same neural pair

BGE→MiniLM target-neighbor overlap@10:

- global map: **0.4745**;
- local atlas: **0.3680**.

Held-out transition validation:

- global: **0.5533**;
- local: **0.4939**;
- local gain: **-0.0594**.

`EvidenceGatedTransition` correctly selects global. “Local is generally better” is therefore false.

## Progressive Semantic Audit evidence

### Real Digits contract

On a **1,500-clause** Digits contract, baseline plus four controlled corruption families, three SLAs and `delta=0.05`:

- exact decision agreement: **15/15**;
- **12/15** decisions finish without full audit;
- mean unique-clause fraction among early decisions: **7.17%**.

Near-boundary cases correctly fall back to all 1,500 clauses.

### Scaling mechanism — 10k / 100k / 250k clauses

A procedural weighted-contract benchmark now tests larger scales with weights `0.5/1/2/5`, `delta=0.05`, batch size 100 and a 5% SLA.

Across **10 cases**:

- progressive vs exact decision agreement: **10/10**;
- **9/10** terminate early;
- the one deliberately near-boundary case falls back to the exact 10,000-clause audit.

Far from the boundary:

| contract size | healthy PASS | 20% violation FAIL | ~10% violation FAIL |
|---:|---:|---:|---:|
| 10,000 | 192 unique (1.92%) | 98 (0.98%) | 384 (3.84%) |
| 100,000 | 200 (0.20%) | 100 (0.10%) | 200 (0.20%) |
| 250,000 | 200 (0.08%) | 100 (0.04%) | 998 (0.3992%) |

This is a strong mechanism/scaling result: away from the SLA boundary, decision cost can depend much more on statistical margin than on total contract size. It is **not** evidence that production semantic faults are iid or distributed like the procedural generator, and sequential early-stopping statistics have clear prior art.

## Real neural repair economics — important mixed result

A separate SciFact/BGE benchmark uses **1,800 documents**, **350 train queries**, **200 untouched test queries**, then deliberately permutes 5% or 10% of document embeddings. Repair budgets restore only selected documents to their clean BGE embedding.

Clean state:

- ABI score: **0.9480**;
- held-out nDCG@10: **0.7875**;
- Recall@10: **0.8970**.

### 10% corruption

180/1,800 documents are corrupted:

- corrupted ABI: about **0.8429**;
- corrupted held-out nDCG: about **0.6970**.

At a budget of 25 documents:

- cost-aware coverage planner selects **88% actually corrupted documents**;
- nDCG recovery: about **33.9%** of the lost gap;
- random same-budget selection finds about **7.3%** corrupted documents and recovers only about **1.5%** of the nDCG gap.

At budget 180, the best targeted method recovers about **50%** of the lost nDCG, versus roughly **9%** for random.

### Critical negative finding

**No tested planner reaches 90% recovery of the lost nDCG within the tested budgets.** More importantly, the application-contract ABI score can return to approximately its clean value while held-out nDCG remains below the clean state.

This is the empirical reason `ContractAdequacy` now exists. Conformity to a sparse application contract does not prove that the contract observes all downstream damage.

The current claim is therefore narrow:

> targeted ABI-guided repair strongly enriches the investigation/re-embedding budget over random in this controlled corruption test, but the current contract/planners do not yet restore the full downstream behavior economically.

## Implementation-integrity canaries — second repair experiment

Using the same 10% corruption regime, the application contract is compared with two separate integrity-canary sets built **without test qrels** from the clean BGE document graph.

Document coverage:

- application-only: **32.3%**;
- application + random integrity anchors: **67.0%**;
- application + coverage-oriented integrity anchors: **72.5%**.

Held-out nDCG:

- clean: **0.7875**;
- corrupted: **0.7338**.

At repair budget 100, the best recovery rises from about **62.3%** of the lost nDCG gap under application-only diagnosis to about **70.2–70.8%** with integrity canaries. At budget 180, coverage-oriented integrity reaches about **71.2%**, versus about **60.1%** for application-only diagnosis.

This supports keeping implementation-integrity canaries as a distinct diagnostic role. It does **not** solve repair completeness: 90% downstream recovery remains unreached.

A cautionary result is equally important: naive `highest-risk` can perform extremely poorly at small budgets after adding neighborhood canaries because a violated neighborhood can assign high risk to a healthy anchor while the damaged expected neighbor is causal. Future repair must become **clause-role-aware and causal/incidence-aware**, not simply merge every risk field into one scalar.

## Other positive real-data mechanisms

### Application semantics vs legacy behavior

On Digits pixels vs HOG:

- application contract: pixels ~**0.980**, HOG ~**0.911**, corrupted HOG ~**0.813**;
- captured legacy behavior: pixels **1.000**, HOG ~**0.711**, corrupted HOG ~**0.610**.

### Semantic Diff

Across pixels↔HOG disagreements, only about **11.7%** of all questions are label-resolvable under the benchmark oracle versus **68%** in the top 25 and **60%** in the top 50, roughly **5–6x enrichment**.

### Semantic mutation adequacy

The tested Digits contract kills all four controlled mutation families. Localization remains materially weaker than global detection.

## Negative / narrowed results that remain part of the evidence

### Fixed Semantic Witness sparsification — not solved

On a 1,500-clause contract with changed IDs, footprints/severities and an unseen drift family:

- 10 clauses: TPR **62.5%**, FPR **0%**;
- 25 clauses: TPR **100%**, FPR **28.6%**;
- 100 clauses: TPR **100%**, FPR **42.9%**.

Random same-size subsets remain competitive. Fixed witness sparsification is not a production mechanism.

### Learned Diagnostic Panel — falsified in current form

A panel that perfectly separates its training regressions from benign controls obtains **0% held-out TPR** across tested budgets. It overfits object-local fault identities and is not exported as a production API.

### Why these failures matter

They changed the architecture. The full contract remains normative; cost reduction is pursued through probabilistic progressive audit rather than claiming deterministic equivalence of a tiny clause subset.

## Multi-dataset predictive-validity gate — currently running

A new falsification campaign is running on **SciFact, NFCorpus and FiQA**. It uses:

- MiniLM dense;
- BGE-small dense;
- BM25 sparse;
- BGE+BM25 RRF hybrid;
- controlled BGE/MiniLM degradations.

Contracts are compiled from official **train qrels only**; official **test qrels are untouched held-out quality evidence**.

The critical comparison is deliberately unfavorable to hype:

> Does Semantic ABI compatibility predict held-out nDCG/Recall better than an ordinary train-query nDCG validation baseline?

Executable portability and predictive validity are separate hypotheses. If ABI does not add predictive information beyond ordinary IR validation, this document will record that as a narrowing result rather than reinterpret the gate after seeing the data.

A serial 3-dataset run and a parallel per-dataset replication are in progress. No multi-dataset claim is promoted until an artifact is available.

## Current software / evidence validation

Current CI covers Python **3.10, 3.12 and 3.13**, `pytest`, the synthetic hubness benchmark, and an independent `evidence-freshness` job.

Promoted benchmark evidence is now bound in `docs/evidence-manifest.json` to:

- exact GitHub Actions run IDs;
- artifact SHA-256 digests;
- Git blob hashes of evidence-sensitive source files.

`tools/check_evidence_freshness.py` recomputes those source identities in CI. A relevant algorithm/benchmark change therefore makes promoted evidence stale until that benchmark is regenerated and the manifest is updated.

The most recent CI after adding explicit Contract Adequacy evidence is green across all three supported Python versions and the evidence-freshness gate.

## Claims we explicitly do not make

The repository does **not** currently claim:

- that it replaces SQL;
- that 3-D coordinates encode semantic truth;
- that SMA universally beats mature ANN engines;
- that SCF invented cross-model translation;
- that local translation is generally better than global;
- that sequential testing, conformal/LTT risk control, coverage-guided testing or AI release certificates were invented here;
- that Semantic ABI is a proven standard or patent-novel abstraction;
- that one high ABI score proves contract adequacy;
- that implementation-integrity canaries are portable application semantics;
- that targeted repair currently restores 90%+ of real downstream quality;
- that present risk-control methods guarantee arbitrary distribution shift;
- that deterministic contract sparsification has been solved;
- that the project is production-ready.

## Highest-value next gates

1. **Finish the current multi-dataset predictive-validity gate.** Portability is not enough; compare ABI against ordinary held-out-validation baselines.
2. **Contract adequacy as first-class evidence.** Replicate coverage/mutation/predictive-validity axes across datasets and require application-declared adequacy policies before strong release claims.
3. **Role-aware repair.** Separate application, integrity and other clause roles; infer likely causal damaged objects from clause incidence rather than blindly sorting merged object risk.
4. **Stronger progressive-audit statistics.** Compare the current transparent alpha-spending baseline with Adaptive Learn-Then-Test/e-process approaches and stratified/slice-aware sampling.
5. **Third representation paradigm.** Run the exact same application contract against graph/late-interaction and production hybrid retrievers.
6. **Multilingual/domain shift.** Measure adequacy, support and selective risk under language, temporal and domain shifts.
7. **Real backend integrations.** Qdrant/pgvector/Elasticsearch/Vespa adapters without rebuilding ANN.
8. **Contract acquisition economics.** Compare Semantic Diff against random, uncertainty, coverage-guided and active-learning baselines using actual human/domain judgments.
9. **Release governance.** Bind adequacy evidence, expiry/revocation, signatures/transparency and reviewer identity without claiming generic attestation novelty.
10. **Professional novelty/IP search.** Especially retrieval semantic contracts, specification-driven gates, adequacy and retrieval-specific behavior attestations.
