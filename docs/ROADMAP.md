# Roadmap — semantic change control, evidence first

The roadmap is evidence-gated. **Code does not complete a phase; surviving its falsification gate does.** Negative results change the architecture instead of being hidden.

See [`CURRENT_STATUS.md`](CURRENT_STATUS.md) for exact dated evidence and [`evidence-manifest.json`](evidence-manifest.json) for machine-bound provenance.

## A. Supporting retrieval/migration research

### A0. Semantic Manifold Atlas — supporting kernel

Implemented local charts, mutual-kNN topology, hubness/density diagnostics, CSLS-inspired ranking, intrinsic dimension, `bridge`/`boundary` and hybrid persistence.

Status: useful supporting machinery; **not** a claim to replace mature ANN engines.

### A1. Semantic Coordinate Fabric — implemented, novelty narrowed

Implemented global/local transitions, held-out diagnostics, cycle checks, partial migration, virtual materialization, drift/fault-lines and `EvidenceGatedTransition`.

Real BGE→MiniLM SciFact:

- global target-neighbor overlap@10 **0.4745**;
- local atlas **0.3680**.

Status: local superiority falsified on this pair. SCF remains optional migration machinery.

## B. Semantic ABI core

### B0. Portable application contract — inter-paradigm gate crossed

Implemented coordinate-free clauses, hard/soft requirements, weights/provenance, canonical digest, ledger/linting and `SemanticOracle`.

Real SciFact:

- same 650-clause digest executes against BGE dense and BM25 sparse;
- BGE ABI ~0.9467;
- BM25 ~0.8913;
- BM25 evaluates 650/650 clauses without dense vectors.

Three-dataset experiments additionally execute contracts across MiniLM/BGE dense, BM25 sparse and BGE+BM25 hybrid implementations.

Next representation gates: graph/late-interaction, production hybrid engines, multimodal, multilingual/domain-specific systems.

### B1. Contract conformity vs adequacy — now core architecture

Implemented `ContractAdequacyEvidence`, `ContractAdequacyRequirements`, `ContractAdequacyReport` and explicit `adequate` / `failed` / `insufficient_evidence` states, with no universal hidden threshold.

The three-dataset predictive-validity gate is complete.

Canonical results:

- mean all-variant Spearman ABI→test nDCG **0.9697**;
- train nDCG→test nDCG **0.9757**;
- pooled delta Spearman ABI **0.9573** vs baseline **0.9724**.

**Result:** aggregate predictive-superiority claim is not supported. ABI remains strongly associated with quality but is not a replacement for ordinary IR validation.

Next adequacy gates:

1. determine which coverage/mutation/localization axes predict real blind spots;
2. predeclare application adequacy policies before final held-out evaluation;
3. adequacy under multilingual/domain/temporal shift;
4. slice-specific adequacy for rare/critical regions;
5. hard-invariant failures that aggregate nDCG can miss.

### B2. Support-aware selective rollout — first neural gate crossed

SciFact/BGE:

- failure-risk AUC ~0.7875;
- 10% SLA rejected;
- 15% preregistered exact rule certified with upper bound ~13.16%;
- held-out accepted coverage 98.5%, realized accepted failure ~10.15%.

Next baselines: Learn-Then-Test, Adaptive LTT/e-processes, conformal/selective risk control and shift-aware calibration.

### B3. Progressive Semantic Audit — strong scale gate

Implemented exhaustive hard clauses, weighted soft sampling, cached oracle calls, predeclared looks, finite-sample bounds and exact fallback.

Evidence:

- Digits 1,500 clauses: **15/15** agreement, **12/15** early, mean early unique fraction **7.17%**;
- procedural 10k/100k/250k: **10/10** agreement, **9/10** early;
- representative 250k decisions use **0.04–0.3992%** clauses away from the boundary.

Next: aLTT/e-process baseline, stratified/slice-aware sampling, non-iid sparse faults, heterogeneous oracle costs, million-clause scale.

### B4. Contract acquisition — promising, not solved

Semantic Diff currently gives roughly 5–6× enrichment of label-resolvable questions on Digits.

Next: human/domain study; random, uncertainty, coverage-guided and active-learning baselines; annotation-cost curves; expert judgments per real regression caught.

### B5. Mutation / adequacy testing

Current mutations: identity permutation, local collapse, hub pull, noise. Current Digits contracts kill tested mutation families globally; localization is weaker.

Next: realistic retriever/index faults, dense/sparse/graph-specific failures and correlation between mutation adequacy and downstream adequacy.

## C. Typed implementation integrity

### C0. Integrity canaries — positive but incomplete

SciFact/BGE 10% corruption:

- application-only document coverage 32.3%;
- + random integrity anchors 67.0%;
- + coverage-oriented anchors 72.5%.

At budget 100, best nDCG-gap recovery improves from ~62.3% to ~70.2–70.8%. Budget 180 coverage-oriented integrity reaches ~71.2%.

Still no 90% recovery.

### C1. Clause-incidence-aware repair — **current gate**

Naive object risk can blame a healthy neighborhood anchor while a corrupted expected/intruding neighbor is causal.

A new planner re-inspects violated clauses and assigns explicit role-weighted blame to missing expected neighbors, intruding neighbors, triplet members, reciprocal endpoints and anchors with a lower diagnostic prior.

It is being tested on the same SciFact/BGE corruption regime against highest-risk, risk/diversity and existing coverage planners.

**Promotion rule:** keep only if held-out corruption precision and/or downstream recovery improves materially over simple baselines. Otherwise delete or retain only as failed evidence.

## D. Fixed-compression experiments — negative evidence

### D0. Fixed Semantic Witness

Held-out stress:

- 10 clauses: TPR 62.5%, FPR 0%;
- 25 clauses: TPR 100%, FPR 28.6%;
- 100 clauses: TPR 100%, FPR 42.9%.

### D1. Learned Diagnostic Panel

Perfect training discrimination → **0% held-out regression recall**.

Conclusion: keep the full normative contract; reduce cost through statistically controlled sampling.

## E. Repair economics

SciFact/BGE 10% corruption:

- nDCG 0.7875 → 0.6970;
- budget25 coverage planner: 88% corrupted docs, ~33.9% nDCG-gap recovery;
- random: ~7.3% corrupted, ~1.5% recovery;
- budget180 targeted best ~50% vs random ~9%.

No tested planner reaches **90%** lost-nDCG recovery. Application conformity can saturate before downstream repair.

Next: clause-incidence-aware repair, multiple fault families, certified-coverage gained per cost, joint repair/fallback stopping policy.

## F. Predictive validity — gate closed / claim narrowed

Canonical SciFact/NFCorpus/FiQA campaign:

| metric | ABI | train nDCG |
|---|---:|---:|
| mean per-dataset Spearman | 0.9697 | **0.9757** |
| pooled delta Spearman | 0.9573 | **0.9724** |
| pooled delta Pearson | 0.9519 | **0.9850** |

Status: **do not pursue “ABI as better global ranking metric.”** Retain ordinary nDCG/Recall and focus ABI research on portable hard invariants, support/risk, adequacy, integrity and change governance.

## G. Real infrastructure adapters

Do not reimplement ANN.

Priority: Elasticsearch/BM25+dense hybrid, Qdrant, pgvector, Vespa/late interaction, then HNSW/DiskANN benchmark adapters.

Required observability: representation provenance, application vs integrity roles, quarantine/fallback/rollback, p50/p95/p99, backfill cost avoided and evidence digests.

## H. Richer invariants only when evidence demands them

Candidates: typed relations/hyperedges, temporal/freshness constraints, contradictions, provenance/trust, monotonic domain constraints, multimodal consistency, uncertainty and causal/counterfactual assertions.

Rule: every richer clause must buy measurable adequacy or operational value per authoring/audit cost.

## I. Release governance / open interchange

Generic AI attestation/certificates have prior art. The narrower target is retrieval-specific evidence bound to a portable Semantic ABI.

If evidence survives: explicit adequacy profiles, typed contract-role manifests, signed certificates, expiry/revocation, transparency log, reviewer identity, semantic versioning and retriever conformance suite.

## J. Evidence freshness — implemented

Promoted evidence is bound to GitHub Actions run/head identity, artifact SHA-256 and Git blob identity of evidence-sensitive sources. `tools/check_evidence_freshness.py` enforces freshness in CI.

## Current highest-value sequence

1. finish clause-incidence-aware repair gate;
2. graph/late-interaction portability;
3. adequacy under shift;
4. Progressive Audit vs aLTT/e-processes;
5. real Elasticsearch/Qdrant/pgvector/Vespa backends;
6. human contract-acquisition study;
7. only then consider protocol standardization, publication or IP claims.

## End-state hypothesis

Not “a better vector table” and not “a better nDCG score”, but a system where semantic infrastructure has:

**stable identity + portable application invariants + explicit contract adequacy + typed implementation integrity + replaceable representations + support/risk + evidence-gated rollout + repair + provenance + controlled semantic evolution.**
