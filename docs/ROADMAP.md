# Roadmap — semantic change control, evidence first

The roadmap is evidence-gated. **Code does not complete a phase; surviving a falsification gate does.** Negative results change the architecture instead of being hidden.

See [`CURRENT_STATUS.md`](CURRENT_STATUS.md) for the exact dated evidence.

## Track A — historical retrieval/migration research

### A0. Semantic Manifold Atlas — implemented mechanism kernel

Implemented:

- overlapping local charts;
- mutual-kNN topology;
- hubness/density and intrinsic-dimension diagnostics;
- CSLS-inspired hub-robust scoring;
- facet late interaction;
- `bridge`, `boundary`, chart nerve graph;
- hybrid SQLite/vector persistence.

Evidence: strong synthetic hubness stress result.  
Status: **supporting research**, not a claim to replace mature ANN engines.

### A1. Semantic Coordinate Fabric — implemented, novelty narrowed

Implemented:

- global scaled Procrustes;
- local transition atlases;
- held-out global/local diagnostics;
- query-dependent routes and cycle checks;
- partial migration fusion;
- semantic cells and virtual materialization;
- drift/fault-line diagnostics;
- transition format v2;
- `EvidenceGatedTransition`.

Real neural result on BGE→MiniLM SciFact:

- global target-neighbor overlap@10: **0.4745**;
- local atlas: **0.3680**;
- held-out selector chooses **global**.

Status: **local superiority falsified on this pair**. SCF remains migration machinery whose complexity must win a holdout. Cross-model translation/local-composable methods have strong 2025–2027 prior art.

## Track B — Semantic ABI / change-control core

### B0. Coordinate-free Semantic ABI — first inter-paradigm gate crossed

Implemented:

- ordinal, neighborhood and reciprocal-neighbor clauses;
- hard/soft requirements, weights and provenance;
- application-semantic vs legacy-behavior separation;
- canonical digest and contract ledger;
- contract linting;
- per-object risk;
- `SemanticOracle` abstraction;
- dense and callback adapters;
- full and single-clause audit.

Real SciFact evidence:

- exact same **650-clause contract digest** audits BGE dense and BM25 sparse;
- BGE ABI ~**0.9467**;
- BM25 ABI ~**0.8913**;
- BM25 evaluates 650/650 clauses with no vectors exposed.

Status: **first real dense↔sparse portability gate crossed**.  
Next gate: repeat with graph/hybrid/late-interaction/multimodal implementations and multiple datasets.

### B1. Support-aware selective rollout — first neural gate crossed

Implemented:

- contract coverage;
- support/OOD-aware local risk;
- `CertifiedSemanticABIGate`;
- global + slice risk portfolios;
- conservative family-wise Chernoff/KL calibration;
- single-rule pre-registered exact-binomial calibration.

SciFact evidence:

- held-out failure-risk AUC ~**0.7875**;
- 10% SLA: both methods correctly abstain;
- 15% SLA: simultaneous family remains uncertified, pre-registered exact rule certifies upper risk ~**13.16%**;
- held-out accepted coverage **98.5%**, realized accepted risk ~**10.15%**.

Status: **promising first sample-efficiency result**.  
Next gates:

1. Learn-Then-Test baseline;
2. conformal/selective risk-control baselines;
3. confidence-sequence/e-value baselines;
4. domain/language/time/configuration shift;
5. calibration-size curves and required sample complexity.

### B2. Progressive Semantic Audit — first cost gate crossed

Problem: a useful contract may eventually contain tens of thousands or millions of clauses. A fixed tiny subset proved unsafe.

Implemented policy:

- every hard clause evaluated exhaustively;
- weighted soft clauses sampled with replacement;
- cached oracle evaluation;
- predeclared batch looks;
- exact-binomial upper/lower bounds;
- global alpha split across looks/tails;
- early PASS/FAIL for a weighted soft-clause violation-rate SLA;
- exact full fallback near the boundary.

Digits evidence with 1,500 clauses:

- **15/15** decisions match exhaustive audit;
- **12/15** finish early;
- mean unique-clause fraction for early decisions: **7.17%**;
- near-boundary cases correctly fall back to 100%.

Status: **promoted research mechanism**. Sequential auditing itself has substantial prior art; the research question is whether it makes Semantic ABI audits economically scalable.

Next gates:

1. 10k / 100k / 1M clause replay/synthetic scale;
2. heterogeneous evaluation costs;
3. weighted/sliced/stratified sampling;
4. finite-population without-replacement methods;
5. confidence sequences / e-processes instead of simple alpha spending;
6. adversarial sparse-fault simulations;
7. real remote-oracle latency/cost measurements.

### B3. Contract acquisition — promising, not solved

Implemented:

- `semantic_diff()`;
- high-value ordinal question generation;
- provenance-ready clauses.

Digits mechanism evidence:

- all disagreements label-resolvable: ~11.7%;
- top 25 questions: **68%**;
- top 50: **60%**.

Next gates:

- human/domain expert study;
- active preference/query baselines;
- annotation-cost curves;
- downstream failure-prediction gain per judgment;
- anti-model-leakage tests so current retriever quirks are not frozen as truth.

### B4. Contract adequacy — implemented mutation baseline

Implemented semantic mutations:

- identity permutation;
- local collapse;
- hub pull;
- coordinate noise.

Current contracts kill the tested mutation families on Digits, but localization remains materially weaker than detection.

Next gates:

- richer fault families;
- dense/sparse/graph-specific mutants;
- contract adequacy threshold for release;
- relation between mutation score and real downstream regressions.

## Track C — failed compression experiments retained as evidence

### C0. Fixed Semantic Witness Set — **not promoted**

Held-out stress results on a 1,500-clause contract:

- 10 clauses: TPR 62.5%, FPR 0%;
- 25 clauses: TPR 100%, FPR 28.6%;
- 100 clauses: TPR 100%, FPR 42.9%.

Random same-size panels remain competitive overall.

Conclusion: a tiny deterministic clause subset is not evidence of semantic equivalence.

### C1. Discriminative fixed Diagnostic Panel — **falsified in current form**

Perfect training discrimination → **0% held-out regression recall** across budgets 5–100.

Conclusion: object-local clauses overfit the location of training faults. Do not revive this approach without a fundamentally different coverage model.

These negative results directly motivated Progressive Semantic Audit.

## Track D — active repair and migration economics

Current repair baselines:

- risk × violation centrality × diversity;
- cost-aware known-violation coverage.

Digits deliberate corruption evidence:

- 25-object budget: **68%** truly corrupt vs 10% random;
- 50: **54%**;
- 100: **37%**.

### Next objective

Replace “corrupt-object precision” with the economically meaningful target:

> **certified semantic coverage gained per euro / token / GPU-second / human-review minute.**

Required baselines:

- random;
- highest risk;
- uncertainty only;
- submodular/facility-location selection;
- full re-embedding;
- partial re-embedding + fallback;
- joint anchor/re-embedding selection.

Kill rule: remove planner sophistication if it does not beat simple policies on cost-to-certified-coverage.

## Track E — real infrastructure adapters

Do not reimplement ANN.

Priority adapters:

1. Qdrant;
2. pgvector;
3. Elasticsearch/BM25 + dense hybrid;
4. Vespa or equivalent hybrid/late-interaction engine;
5. HNSW/DiskANN benchmark adapters.

Required observability:

- direct vs virtual representation provenance;
- contract/risk canaries;
- quarantine/fallback/rollback;
- p50/p95/p99 query and audit latency;
- artifact and memory size;
- backfill cost avoided.

## Track F — richer invariants only when simpler clauses fail

Candidates:

- typed relations/hyperedges;
- temporal order and freshness;
- contradiction/contested-semantic regions;
- provenance/trust requirements;
- monotonic/domain constraints;
- multimodal consistency;
- distributional uncertainty;
- topological invariants;
- causal/counterfactual assertions.

Rule: every new clause family must buy measurable downstream predictive power per unit authoring/audit complexity.

## Track G — release governance / open interchange

If multi-system evidence survives:

- immutable implementation/preprocessing fingerprints;
- signed Semantic Release Certificates;
- expiry and revocation;
- transparency log;
- reviewer identity and approval policy;
- contract semantic-versioning rules;
- evidence bundles;
- conformance suite for retrievers;
- representation-neutral clause/interchange schema.

The strategic objective is **representation independence under explicit semantic obligations**.

## Track H — evidence freshness

Documentation itself must become auditable.

In progress:

- GitHub Actions artifact digests;
- `docs/evidence-manifest.json`;
- source Git-blob fingerprints for evidence-sensitive algorithms/benchmarks;
- CI failure when those blobs change without regenerated evidence.

Once enabled, a benchmark number cannot remain silently “current” after its implementation changes.

## Current highest-value sequence

1. finish machine-enforced evidence manifest;
2. replicate SciFact results on several BEIR/MTEB datasets and encoder pairs;
3. add a third representation paradigm (graph/hybrid/late interaction);
4. scale Progressive Audit by two to three orders of magnitude;
5. benchmark LTT / confidence-sequence / shift-aware certification;
6. connect Qdrant + pgvector + Elasticsearch/Vespa;
7. measure end-to-end migration/re-certification economics;
8. only then consider protocol standardization, publication or IP claims.

## End-state hypothesis

The project is no longer aiming for “a better vector table”. The end-state hypothesis is a system in which data has:

**stable identity + replaceable representations + declared invariants + uncertainty/support + evidence-gated rollout + provenance + controlled semantic evolution.**
