# Roadmap — semantic change control, evidence first

The roadmap is evidence-gated. **Code does not complete a phase; surviving a falsification gate does.** Negative results change the architecture instead of being hidden.

See [`CURRENT_STATUS.md`](CURRENT_STATUS.md) for exact dated evidence and [`evidence-manifest.json`](evidence-manifest.json) for machine-bound provenance.

## Track A — supporting retrieval/migration research

### A0. Semantic Manifold Atlas — supporting mechanism kernel

Implemented local charts, mutual-kNN topology, hubness/density diagnostics, CSLS-inspired ranking, facet interaction, `bridge`/`boundary` and hybrid persistence.

Status: useful supporting machinery; **not** a claim to replace mature ANN engines.

### A1. Semantic Coordinate Fabric — implemented, novelty narrowed

Implemented global/local transitions, held-out diagnostics, routing/cycle checks, partial migration, virtual materialization, drift/fault-lines and `EvidenceGatedTransition`.

Real BGE→MiniLM SciFact result:

- global target-neighbor overlap@10 **0.4745**;
- local atlas **0.3680**;
- held-out selector chooses **global**.

Status: local superiority falsified on this pair. SCF remains optional migration machinery and must beat simpler adapters on holdout.

## Track B — Semantic ABI core

### B0. Portable application contract — first cross-paradigm gate crossed

Implemented:

- ordinal/neighborhood/reciprocal clauses;
- hard/soft requirements, weights, provenance;
- canonical digest, ledger, linting;
- `SemanticOracle` abstraction;
- dense/callback adapters;
- full and single-clause audit.

Real SciFact evidence:

- same 650-clause digest executes against BGE dense and BM25 sparse;
- BGE ABI ~**0.9467**;
- BM25 ~**0.8913**;
- BM25 evaluates 650/650 clauses without exposing dense vectors.

Status: **dense↔sparse executable portability crossed**. Portability is not predictive-validity proof.

Next gates:

1. graph/late-interaction implementation;
2. production hybrid implementation;
3. multimodal implementation;
4. multiple domain/language datasets.

### B1. Contract conformity vs contract adequacy — new core distinction

The neural repair experiments show that an application contract can recover its clean ABI score while held-out nDCG remains damaged outside the contract's observation surface.

Implemented:

- `ContractAdequacyEvidence`;
- `ContractAdequacyRequirements`;
- `ContractAdequacyReport`;
- explicit `adequate` / `failed` / `insufficient_evidence` states;
- no universal library-wide adequacy threshold.

Current adequacy axes:

- object coverage;
- mutation kill/localization;
- predictive correlation;
- predictive lift over ordinary validation;
- held-out cases;
- datasets;
- fault families.

Status: **architecturally required by evidence; predictive gate still being replicated.**

Next gates:

1. finish SciFact/NFCorpus/FiQA ABI-vs-nDCG baseline study;
2. predeclare adequacy policies before final held-out evaluation;
3. test whether mutation/coverage metrics actually predict real blind spots;
4. develop slice-specific adequacy for rare domains/languages.

### B2. Support-aware selective rollout — first neural gate crossed

Implemented support/OOD-aware local risk, `CertifiedSemanticABIGate`, slice portfolios, conservative family-wise calibration and preregistered exact-binomial calibration.

SciFact:

- held-out failure-risk AUC ~**0.7875**;
- 10% SLA rejected by both methods;
- 15% preregistered exact rule certified, upper ~**13.16%**;
- held-out accepted coverage **98.5%**, realized accepted risk ~**10.15%**.

Next baselines:

- Learn-Then-Test;
- Adaptive LTT/e-processes;
- conformal/selective risk control;
- domain/language/time/configuration shift;
- calibration-size/sample-complexity curves.

### B3. Progressive Semantic Audit — strong mechanism/scale gate

Implemented:

- exhaustive hard clauses;
- weight-proportional soft sampling with replacement;
- cached oracle evaluation;
- predeclared batch looks;
- finite-sample upper/lower bounds with global error allocation;
- early PASS/FAIL on soft-clause violation SLA;
- exact fallback near the boundary.

Evidence:

- real Digits 1,500 clauses: **15/15** exact decision agreement, **12/15** early, mean early unique fraction **7.17%**;
- procedural 10k/100k/250k: **10/10** agreement, **9/10** early;
- at 250k, representative far-from-boundary decisions use **0.04–0.3992%** of clauses.

Status: **strongest current audit-cost mechanism**. Sequential testing itself is prior art; novelty cannot rest on early stopping.

Next gates:

1. Adaptive LTT/e-process baseline;
2. stratified/slice-aware sampling;
3. non-iid sparse-fault stress;
4. heterogeneous remote-oracle costs;
5. million-clause scale;
6. wall-clock/API-cost measurements.

### B4. Contract acquisition — promising, not solved

`Semantic Diff` currently yields ~**5–6×** enrichment of label-resolvable questions on Digits.

Next gates:

- human/domain expert study;
- random, uncertainty, coverage-guided and active-learning baselines;
- annotation-cost curves;
- anti-model-leakage checks;
- clauses gained per real downstream regression caught.

### B5. Mutation / adequacy testing

Current controlled mutations: identity permutation, local collapse, hub pull, coordinate noise.

Current contracts kill the tested Digits families globally; localization is weaker.

Next gates:

- realistic retriever/index faults;
- dense/sparse/graph-specific faults;
- relation between mutation adequacy and downstream predictive adequacy;
- held-out mutation families.

## Track C — typed implementation integrity

### C0. Integrity canaries — positive but incomplete

A separate implementation-integrity role was added experimentally after application conformity proved too sparse for corruption recovery.

SciFact/BGE 10% corruption:

- application-only document coverage **32.3%**;
- + random integrity anchors **67.0%**;
- + coverage-oriented anchors **72.5%**.

At repair budget 100, best lost-nDCG recovery improves from ~**62.3%** application-only to ~**70.2–70.8%** with integrity canaries; at budget 180, coverage-oriented integrity reaches ~**71.2%**.

Status: useful observability signal, **not portable application truth** and not a complete repair solution.

Critical issue: naive highest-object-risk can target a healthy neighborhood anchor while a damaged neighbor is causal.

Next gates:

1. formal contract-role typing;
2. clause-incidence / causal fault attribution;
3. implementation-specific integrity release policy;
4. integrity canaries for sparse/hybrid indexes;
5. compare random vs coverage vs graph-centrality canary placement.

## Track D — failed fixed-compression experiments retained as evidence

### D0. Fixed Semantic Witness — not promoted

Held-out stress on 1,500 clauses:

- 10 clauses: TPR 62.5%, FPR 0%;
- 25: TPR 100%, FPR 28.6%;
- 100: TPR 100%, FPR 42.9%.

### D1. Learned Diagnostic Panel — falsified in current form

Perfect training discrimination → **0% held-out regression recall**.

Conclusion: the full normative contract remains; cost reduction uses statistically controlled sampling, not unproved deterministic equivalence.

## Track E — active repair economics

### Real neural gate — targeted >> random, 90% recovery not reached

SciFact/BGE, 1,800 docs, 350 train queries, 200 untouched test queries.

At 10% corruption:

- nDCG **0.7875 → 0.6970**;
- budget25 cost-aware selection: **88%** corrupted docs, ~**33.9%** nDCG-gap recovery;
- random: ~**7.3%** corrupted, ~**1.5%** recovery;
- budget180 targeted best ~**50%** recovery vs random ~**9%**.

No tested planner reaches **90%** lost-nDCG recovery. Application conformity can saturate before downstream repair.

Status: **economic targeting signal is real, full repair claim fails.**

Next gates:

1. clause-role/incidence-aware repair;
2. multiple real fault families, not only identity permutation;
3. highest-risk/random/submodular baselines;
4. certified-coverage gained per euro/token/GPU-second;
5. joint re-embedding/fallback stopping policy.

## Track F — multi-dataset predictive-validity falsification

Current protocol:

- SciFact, NFCorpus, FiQA;
- MiniLM, BGE, BM25, BGE+BM25 hybrid;
- controlled degradations;
- train qrels only for contract authoring;
- untouched test qrels for downstream quality;
- compare ABI→test quality with **ordinary train nDCG→test quality**.

FiQA first completed result:

- ABI Spearman **0.9636**;
- train-nDCG baseline **0.9522**;
- lift only **+0.0115**;
- baseline Pearson **0.9945** > ABI **0.9823**;
- natural-only both Spearman **0.80**.

Status: **FiQA narrows aggregate-predictive superiority.** ABI tracks quality strongly but is not clearly better than normal validation. SciFact/NFCorpus remain required for cross-dataset conclusion.

Interpretation rule is fixed in advance: if ABI does not beat ordinary validation, do not move the goalposts. Its remaining value must be evaluated as normative hard-invariant portability, local support/risk and controlled deployment.

## Track G — real infrastructure adapters

Do not reimplement ANN.

Priority:

1. Elasticsearch/BM25+dense hybrid — fastest way to validate non-vector implementation semantics in a real engine;
2. Qdrant;
3. pgvector;
4. Vespa/late interaction;
5. HNSW/DiskANN benchmark adapters.

Required observability:

- direct/virtual representation provenance;
- application vs integrity contract roles;
- quarantine/fallback/rollback;
- query/audit p50/p95/p99;
- backfill cost avoided;
- evidence digests.

## Track H — richer invariants only when evidence demands them

Candidates:

- typed relations/hyperedges;
- temporal/freshness constraints;
- contradictions/contested regions;
- provenance/trust;
- monotonic domain constraints;
- multimodal consistency;
- distributional uncertainty;
- causal/counterfactual assertions.

Rule: every richer clause must buy measurable adequacy/predictive/operational value per unit authoring and audit cost.

## Track I — release governance / open interchange

Generic AI attestation/certificates already have prior art. The narrower research target is retrieval-specific evidence bound to a portable Semantic ABI.

If evidence survives:

- explicit adequacy profile in release governance;
- application/integrity role manifests;
- signed certificates;
- expiry/revocation;
- transparency log;
- reviewer identity;
- contract semantic versioning;
- retriever conformance suite.

## Track J — evidence freshness — implemented baseline

Promoted evidence is bound to:

- GitHub Actions run ID/head SHA;
- artifact SHA-256;
- Git blob identity of evidence-sensitive sources.

`tools/check_evidence_freshness.py` runs independently in CI. Relevant source changes invalidate promoted evidence until regenerated.

## Current highest-value sequence

1. finish SciFact/NFCorpus multi-dataset predictive-validity runs;
2. freeze first cross-dataset `ContractAdequacy` evidence profile;
3. implement clause-role/incidence-aware repair and retest neural corruption economics;
4. benchmark Progressive Audit against Adaptive LTT/e-processes;
5. add graph/late-interaction representation paradigm;
6. connect real Elasticsearch/Qdrant/pgvector/Vespa backends;
7. run multilingual/domain-shift adequacy and rollout tests;
8. run human contract-acquisition study;
9. only then consider protocol standardization, publication or IP claims.

## End-state hypothesis

Not “a better vector table”, but a system where semantic infrastructure has:

**stable identity + portable application invariants + explicit contract adequacy + typed implementation integrity + replaceable representations + support/risk + evidence-gated rollout + repair + provenance + controlled semantic evolution.**
