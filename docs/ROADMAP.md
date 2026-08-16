# Roadmap: from vector retrieval to semantic change management

The roadmap is evidence-gated. Code does not complete a phase; the phase completes only when its hypothesis survives the attached falsification gate.

## Phase 0 — Semantic Manifold Atlas — implemented reference kernel

- overlapping local semantic charts;
- mutual-kNN topology, hubness and density diagnostics;
- CSLS-inspired hub-robust ranking;
- optional multi-vector facet late interaction;
- local 3-D coordinates for inspection only;
- `bridge`, `boundary`, chart nerve graph;
- hybrid SQLite/vector persistence;
- deterministic black-hole/hubness stress benchmark.

## Phase 1 — Semantic Coordinate Fabric — implemented research kernel

- logical identity independent of embedding identity;
- explicit representation-space registry;
- rectangular scaled-Procrustes baseline;
- piecewise local transition atlases;
- held-out global + local transition confidence;
- support-radius/OOD confidence decay;
- query-dependent route selection across representation spaces;
- cycle/cocycle consistency audits;
- partial-migration search with coverage-aware fusion;
- semantic cells: center + dispersion + provenance;
- virtual target-space materialization;
- representation `fault_lines` and coordinate-aware drift;
- portable transition artifact format v2.

Prior-art review materially narrowed novelty claims here: cross-model translation, local consistency, composable translation and embedding-independent vector-database IRs are already active research areas.

## Phase 2 — Semantic ABI — implemented V0.3 hypothesis

Make the **meaning required by the application** a stable interface above all representation implementations.

Implemented:

- coordinate-free ordinal triplet clauses;
- critical-neighborhood clauses;
- reciprocal-neighbor clauses;
- hard/soft requirements and provenance/source fields;
- separate application-semantic vs legacy-behavior contracts;
- canonical contract digests;
- tamper-evident hash-chained contract ledger;
- per-object violation/risk field;
- query-local risk interpolation;
- `SemanticABIGate` for region-wise rollout/fallback;
- real-data digits/HOG mechanism benchmark.

Critical falsification questions:

- does ABI score predict downstream failures better than ordinary held-out evaluation?
- can useful application contracts be built from a tiny fraction of a corpus?
- are local risk estimates calibrated enough for deployment decisions?
- do contracts transfer across dense, sparse, graph and multimodal implementations?
- can application semantics remain stable without freezing obsolete ranking quirks?

## Phase 3 — active semantic repair — implemented transparent baseline, research next

Close the loop:

```text
Contract -> Audit -> Gate -> Repair -> Re-certify
```

Current baseline:

- priority = semantic risk x violation centrality x diversity;
- sparse review/re-embedding plan rather than uniform backfill;
- real-data corruption benchmark shows strong enrichment over random selection at small budgets.

Next research:

- submodular facility-location selection;
- Bayesian/active-learning uncertainty reduction;
- expected certified-surface gain per dollar/token/GPU-second;
- transition-anchor selection and direct re-embedding selection as one joint optimization;
- stop conditions: repair until requested semantic SLA, not until 100% corpus backfill;
- counterfactual repair: identify the smallest observation/transition changes needed to satisfy the contract.

**Kill rule:** if active repair cannot beat random, uncertainty sampling, or simple highest-risk selection on cost-to-certified-coverage, remove the extra planner complexity.

## Phase 4 — real neural encoder falsification gate — highest priority

Use unrelated encoder families and several datasets; do not optimize around one favorable model pair.

Required axes:

- text retrieval with relevance labels;
- multilingual retrieval;
- image/multimodal retrieval;
- domain shift and long-tail concepts;
- dimension changes;
- model-family changes;
- partial migration coverage: 1%, 5%, 10%, 25%, 50%, 75%;
- anchor budgets and domain-held-out anchors.

Report separately:

1. target-neighborhood fidelity;
2. downstream relevance (nDCG/MRR/Recall);
3. Semantic ABI score and hard failures;
4. risk calibration;
5. certified corpus/query coverage;
6. active-repair cost-to-certification;
7. p50/p95/p99 latency;
8. memory/artifact size;
9. full re-embedding cost avoided.

Baselines must include:

- full re-embedding;
- legacy retrieval;
- new-index-only under partial coverage;
- Drift-Adapter-style global adapters;
- local/composable translation baselines from current literature;
- naive vs coverage-aware fusion;
- uniform/random backfill;
- uncertainty-only and highest-risk repair.

## Phase 5 — mature ANN adapters, never needless reinvention

- Qdrant adapter;
- HNSW adapter;
- DiskANN adapter;
- pgvector adapter;
- filtered-query selectivity sweeps;
- direct vs virtual vector observability;
- transition and ABI canaries, quarantine and rollback;
- query planner using ANN cost + transition risk + ABI risk + coverage.

Only measured evidence could justify a custom low-level index.

## Phase 6 — richer semantic invariants

Only when ablations show points/triplets are insufficient:

- anisotropic/covariance semantic cells;
- distributional uncertainty;
- temporal semantic fields;
- persistent topological invariants;
- typed graph/hyperedge clauses;
- contradictions and contested-semantic regions;
- provenance/trust propagation;
- causal hypotheses and counterfactual traversal.

Each richer invariant must buy measurable predictive power per unit of contract/storage complexity.

## Phase 7 — open Semantic ABI + coordinate protocol

If the evidence survives:

- immutable model/preprocessing fingerprints;
- signed contract and transition manifests;
- clause/interchange schema;
- contract semantic versioning rules;
- transition expiry/revocation;
- audit evidence bundles;
- calibrated local-risk interchange;
- direct/virtual observation status;
- anchor/contract provenance and privacy metadata;
- conformance suite for vector stores and retrievers.

The strategic objective is **representation independence**: an application should declare what semantic behavior it requires, while the underlying implementation remains replaceable.

## Phase 8 — semantic substrate for agents and data systems

Potential query language:

- `NEAR(query)` — retrieval;
- `BRIDGE(a,b)` — semantic/topological path;
- `BOUNDARY(a,b)` — transition region;
- `FAULT_LINES(scope)` — representation disagreement;
- `DRIFT(scope,t1,t2)` — coordinate-aware change;
- `CERTIFY(implementation, contract)` — semantic ABI audit;
- `WHY_UNSAFE(query)` — violated clauses and local evidence;
- `REPAIR(budget)` — cost-aware active repair plan;
- `MATERIALIZE(target_space)` — virtual coordinates;
- `MAP(scope)` — topology/contract/risk summary.

The end-state is not “a better vector table”. It is a system where data has **identity, representations, invariants, uncertainty, provenance and controlled semantic evolution**.
