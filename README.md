# Semantic Manifold Atlas

**A research engine for knowledge that can outlive its embedding model.**

Vector databases are excellent at answering *"which stored vectors are nearest to this vector?"* They are much less explicit about a deeper fact: a vector is not the object or its meaning. It is a coordinate produced by one representation model.

Semantic Manifold Atlas (SMA) explores two connected abstractions:

1. **Semantic Manifold Atlas** — a corpus is represented by overlapping local semantic charts, reciprocal topology, local-density diagnostics and navigational primitives beyond top-k similarity.
2. **Semantic Coordinate Fabric (SCF)** — different embedding models are treated as different coordinate systems over stable logical objects, connected by audited local transition functions.

The long-term goal is not another HNSW implementation. It is a model-independent semantic layer that can sit above Qdrant, DiskANN, pgvector or another ANN engine.

> SQL still belongs in the control plane for transactions, constraints and metadata. And SMA does **not** compress arbitrary knowledge to XYZ: local 3-D coordinates are inspection views only. Full-dimensional representations remain the retrieval coordinates.

## Why the coordinate layer matters

Today an embedding upgrade commonly means generating a new vector for every existing object. Infrastructure can hide the downtime, but the stored corpus remains coupled to the encoder that produced it.

SCF tests a different model:

```text
stable logical object
       |
       +-- observation in embedding-space A
       +-- observation in embedding-space B
       +-- observation in embedding-space C

A <==== audited local transitions ====> B <====> C
```

With enough paired anchors, the engine learns local transitions between spaces, validates them on held-out anchors, routes only through sufficiently reliable paths and can search a complete legacy index from a new-model query while the new index is still partial.

It can also build a **SemanticCell**: a confidence-weighted target coordinate plus dispersion from several direct or transported observations. That makes disagreement between models explicit instead of silently averaging it away.

See [`docs/SEMANTIC_FABRIC.md`](docs/SEMANTIC_FABRIC.md) and the draft [`Semantic Coordinate Protocol`](docs/SEMANTIC_COORDINATE_PROTOCOL.md).

## Phase 0: topology-aware retrieval

The original SMA kernel remains intact:

- overlapping local charts with local PCA inspection coordinates;
- local intrinsic-dimension estimates;
- mutual-kNN topology;
- hubness and density diagnostics;
- CSLS-inspired robust scoring;
- optional multi-vector facet late interaction;
- multi-scale/coarse routing;
- provenance and confidence in result evidence;
- `bridge(A, B)` for topological paths;
- `boundary(A, B)` for transition regions;
- a chart-overlap nerve graph.

The deterministic hubness stress test currently gives, on its fixed synthetic seed:

- exact cosine precision@10: **0.6300**, injected hubs/query: **3.3687**;
- SMA precision@10: **0.8519**, injected hubs/query: **0.0000**.

This is a mechanism test, not a production superiority claim.

## Phase 1: Semantic Coordinate Fabric

New in v0.2:

- rectangular scaled-Procrustes maps for different source/target dimensions;
- **piecewise local transition atlases** instead of one forced global adapter;
- deterministic held-out transition diagnostics;
- multi-hop transition graph with confidence-aware routing;
- **cycle consistency** audits for corrupted/incompatible routes;
- concurrent cross-space search;
- coverage-corrected rank fusion during partial migrations;
- **SemanticCell** barycenters with dispersion and provenance;
- virtual target-space materialization before full re-embedding;
- cross-model `fault_lines()` for representation-sensitive objects;
- coordinate-aware semantic drift reports;
- portable transition serialization (`semantic-coordinate-transition` v1).

### Current deterministic V2 stress tests

| Test | Simple baseline | Current SCF |
|---|---:|---:|
| Region-dependent cross-model warp, held-out pair cosine | global Procrustes **0.7042** | local atlas **0.9414** |
| Only 25% of target index migrated, top-10 overlap vs legacy SMA oracle | new index only **0.2080** | fabric **0.8460** |
| Closed good/corrupted transition cycle, mean cosine | good **~1.0000** | corrupted **-0.0760** |
| Exact-rotation toy migration with only 20% direct target vectors | direct coverage **0.20** | virtual coverage **1.00** |

The exact-rotation virtual-materialization result is intentionally an easy synthetic case. It proves plumbing, not real-model equivalence. See [`docs/BENCHMARKS_V2.md`](docs/BENCHMARKS_V2.md).

## Minimal cross-model example

```python
from semantic_atlas import FabricRecord, SemanticFabric, SpaceSpec

fabric = SemanticFabric(chart_size=64, graph_k=10)
fabric.add_space(SpaceSpec("legacy", 1536, version="encoder-v1"))
fabric.add_space(SpaceSpec("next", 1024, version="encoder-v2"))

fabric.add(FabricRecord("doc-1", {"legacy": legacy_vector_1}))
fabric.add(FabricRecord("doc-2", {"legacy": legacy_vector_2, "next": next_vector_2}))
# ...

fabric.fit_bidirectional(
    "legacy",
    "next",
    anchor_ids=paired_anchor_ids,
    chart_size=32,
)
fabric.build()

# A query produced only by the new encoder can already use both spaces.
hits = fabric.search(next_query, query_space="next", top_k=10)

# Build a confidence-gated temporary target-space index while migration continues.
virtual_next = fabric.materialize_virtual_space(
    "next",
    min_cell_confidence=0.85,
    min_transport_confidence=0.80,
)
```

A transition artifact can be saved independently of a database:

```python
from semantic_atlas import save_transition, load_transition

save_transition(fabric.transitions.transitions[("next", "legacy")], "next-to-legacy.npz")
transition = load_transition("next-to-legacy.npz")
```

## Run the research kernel

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python benchmarks/coordinate_fabric_benchmark.py
```

For real paired embeddings:

```bash
python benchmarks/npz_upgrade_benchmark.py pair.npz --anchor-fraction 0.10 --k 10
```

The NPZ expects `old_docs`, `new_docs` and `new_queries`. It compares the local transition atlas with a global Procrustes baseline against an exact full-new-space retrieval oracle.

## Scientific posture

This repository contains a **falsifiable research hypothesis**, not evidence that SMA has already revolutionized vector search.

Relevant prior work already establishes important pieces: Procrustes alignment, migration adapters, local cross-model geometric consistency, hubness mitigation and uncertainty-aware retrieval. The possible contribution is the systems combination into an audited, composable coordinate fabric with continuity, uncertainty and integrity semantics. See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

The project should be simplified, narrowed or killed if real-model experiments show that the extra layer does not create repeatable gains in retrieval continuity, migration economics, safety or semantic diagnostics.

## Research documents

- [`docs/RESEARCH.md`](docs/RESEARCH.md) — Phase 0 basis and falsification plan
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — original atlas architecture
- [`docs/SEMANTIC_FABRIC.md`](docs/SEMANTIC_FABRIC.md) — cross-model theory and mechanisms
- [`docs/SEMANTIC_COORDINATE_PROTOCOL.md`](docs/SEMANTIC_COORDINATE_PROTOCOL.md) — portable protocol draft
- [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) — prior-art map and non-claims
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — new trust boundaries
- [`docs/BENCHMARKS_V2.md`](docs/BENCHMARKS_V2.md) — real-model benchmark protocol and kill criteria
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — roadmap
