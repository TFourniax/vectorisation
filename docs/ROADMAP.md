# Roadmap: from research prototype to a credible new data engine

## Phase 0 — current branch

- runnable NumPy reference implementation;
- overlapping semantic charts;
- mutual-kNN topology and hubness diagnostics;
- CSLS-inspired hub-robust ranking;
- optional multi-vector facet late interaction;
- local 3-D coordinates for inspection;
- chart-overlap nerve graph;
- `bridge` and `boundary` queries;
- hybrid SQLite/vector persistence;
- tests and a hubness falsification benchmark.

## Phase 1 — benchmark before adding complexity

- MTEB/BEIR harness with reproducible datasets and fixed seeds;
- ANN-Benchmarks compatible harness;
- filtered ANN corpus with metadata selectivity sweeps;
- adversarial/accidental hubness suite;
- baselines: exact cosine, FAISS/HNSW, Qdrant, DiskANN, BM25+dense, ColBERT;
- ablation matrix for charts, reciprocity, CSLS, facets and diversity.

Kill or redesign any component that does not show a repeatable gain.

## Phase 2 — scalable storage kernel

- immutable vector segments + write-ahead log;
- background segment compaction;
- pluggable ANN backend (DiskANN first candidate for SSD scale);
- per-chart quantization and adaptive dimension budgets;
- bitmap metadata filters intersected during candidate expansion;
- transactional IDs/metadata in a relational control plane;
- snapshot isolation for reads;
- online chart split/merge based on density and drift.

## Phase 3 — genuinely new primitives

- persistent-homology summaries for holes/loops and topology drift;
- learned or hyperbolic coordinate channel for hierarchy;
- temporal vector fields: direction and speed of concept drift;
- uncertainty ellipsoids instead of point estimates where encoders support uncertainty;
- typed hyperedges for events involving more than two entities;
- counterfactual traversal: minimum semantic changes connecting A to B;
- provenance-aware evidence paths and trust propagation.

## Phase 4 — agent/data platform

Expose the atlas through a small query language and API:

- `NEAR(query)` — semantic retrieval;
- `BRIDGE(a,b)` — topology path;
- `BOUNDARY(a,b)` — ambiguous transition region;
- `DRIFT(topic,t1,t2)` — movement over time;
- `WHY(result)` — score/provenance/path explanation;
- `MAP(scope)` — topology summary, not merely a 2-D scatter plot.

The target is a data substrate for agents that can *navigate* a corpus rather than repeatedly issuing disconnected nearest-neighbor searches.
