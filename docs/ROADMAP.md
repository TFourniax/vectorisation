# Roadmap: from research prototype to a durable semantic data layer

The roadmap is evidence-gated. A phase is not complete because code exists; its hypotheses must survive the benchmark gates attached to it.

## Phase 0 — Semantic Manifold Atlas kernel — implemented

- runnable NumPy reference implementation;
- overlapping semantic charts;
- mutual-kNN topology and hubness diagnostics;
- CSLS-inspired hub-robust ranking;
- optional multi-vector facet late interaction;
- local 3-D coordinates for inspection only;
- chart-overlap nerve graph;
- `bridge` and `boundary` queries;
- hybrid SQLite/vector persistence;
- deterministic hubness falsification benchmark.

## Phase 1 — Semantic Coordinate Fabric — implemented as research V0.2

- stable logical object identity independent of embedding identity;
- explicit representation-space registry;
- rectangular scaled-Procrustes baseline;
- piecewise local transition atlases;
- deterministic held-out transition diagnostics;
- confidence-aware graph routing across representation spaces;
- cycle/cocycle consistency audits;
- partial-migration search with coverage-aware rank fusion;
- semantic cells: center + dispersion + provenance;
- confidence-gated virtual target-space materialization;
- representation `fault_lines` and coordinate-aware drift;
- portable transition artifact format;
- draft Semantic Coordinate Protocol and threat model.

Mechanism tests and the first real-data representation benchmark now exist. This phase is **not** evidence of neural embedding-model superiority.

## Phase 2 — real encoder falsification gate — next critical gate

Use the database-neutral NPZ harness and add reproducible corpus adapters. Test several unrelated model families, dimensions, languages and domains rather than one favorable pair.

Required measurements:

- full-target relevance: nDCG@10, Recall@k, MRR where labels exist;
- exact target-neighborhood fidelity separately from relevance;
- migration coverage curves: 1%, 5%, 10%, 25%, 50%, 75%;
- anchor-count curves and anchor-domain transfer;
- confidence calibration: declared transition confidence vs observed retrieval loss;
- p50/p95/p99 transport and search latency;
- transition fit cost and artifact size;
- cost/time saved relative to full re-embedding;
- failure under multilingual shift, long-tail concepts and domain shift.

Baselines:

- full re-embedding;
- legacy retrieval;
- new-index only at partial coverage;
- global orthogonal/scaled Procrustes;
- low-rank affine mapping;
- learned residual adapter when data volume makes it fair;
- naive RRF vs coverage-aware fusion;
- local SCF with every component ablated.

**Kill/narrow rule:** if local transitions and the Fabric do not create repeatable relevance, continuity, safety or economic value over simpler one-hop adapters, reduce the project to the simpler mechanism rather than preserving complexity.

## Phase 3 — mature ANN integration, not reinvention

Keep SCF database-neutral and delegate candidate generation to mature engines.

- Qdrant adapter with named-vector / migration experiments;
- HNSW reference adapter;
- DiskANN adapter for SSD-scale experiments;
- pgvector adapter for relational deployments;
- filtered-query selectivity sweeps;
- calibrated fusion across indexes with different coverage and ANN recall;
- direct-vs-virtual vector observability;
- transition canaries, quarantine and rollback.

Only after these measurements should any custom storage kernel be justified.

## Phase 4 — from points to semantic cells and fields

If cross-model cells prove useful on real encoders:

- covariance / anisotropic uncertainty instead of scalar dispersion;
- distributional or sample-based cells where warranted;
- temporal semantic cells and vector fields for concept movement;
- persistent-homology summaries for topology changes;
- typed relation/hyperedge overlays for events and causal hypotheses;
- contradiction and representation-disagreement regions;
- provenance-aware trust propagation;
- counterfactual traversal: minimum semantic changes connecting states.

Every richer representation needs an ablation showing why a point is insufficient.

## Phase 5 — open semantic coordinate protocol

If Phase 2–4 evidence supports the abstraction, separate the protocol from the reference engine.

- immutable model + preprocessing fingerprints;
- signed transition manifests;
- portable held-out diagnostics;
- transition expiry/revocation;
- cycle-audit interchange format;
- virtual/direct coordinate status;
- anchor provenance and privacy metadata;
- adapters for independent vector stores;
- conformance suite.

The strategic objective would be interoperability: a logical corpus should not have to be permanently coupled to the embedding model or vector database that first encoded it.

## Phase 6 — agent/data substrate

Expose a small query language over geometry, topology, time, provenance and coordinate systems:

- `NEAR(query)` — semantic retrieval;
- `BRIDGE(a,b)` — topology path;
- `BOUNDARY(a,b)` — transition / ambiguity region;
- `FAULT_LINES(scope)` — representation-sensitive regions;
- `DRIFT(scope,t1,t2)` — coordinate-aware semantic movement;
- `WHY(result)` — score, transition path, uncertainty and provenance;
- `MAP(scope)` — topology summary, not merely a 2-D scatter plot;
- `MATERIALIZE(target_space)` — confidence-gated virtual coordinates during migration.

The long-term target is a substrate where agents can navigate **objects, relationships, uncertainty and changing coordinate systems**, instead of treating every corpus as a static bag of nearest-neighbor vectors.
