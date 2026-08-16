# Semantic Manifold Atlas — architecture

## The thesis

A conventional vector store treats each object as a point in one globally fixed metric space. That is an excellent primitive for nearest-neighbor lookup, but it silently assumes that one distance function is meaningful everywhere and that the user's task can be reduced to top-k similarity.

The Semantic Manifold Atlas (SMA) instead treats the corpus as an **atlas of overlapping local coordinate systems** plus a topology connecting them.

The term *atlas* is borrowed from differential geometry: a complex space can be represented by local charts whose overlaps encode how local neighborhoods relate. We do **not** claim embeddings are a smooth mathematical manifold. The atlas is an engineering hypothesis that can be falsified by retrieval and systems benchmarks.

## Data model

Each logical object is an `AtlasRecord` with a primary dense vector, optional facet/token vectors, metadata, provenance, timestamp and confidence, plus membership in one or more overlapping local charts.

The 3-D coordinates exposed by the prototype are local PCA projections for inspection. **They are a visualization layer, not the storage representation.** Compressing a 768/1536/3072-D semantic vector to literal XYZ coordinates would destroy information.

## Build path

1. Normalize original vectors.
2. Build a mutual-kNN graph. Reciprocity removes many one-way nearest-neighbor edges and exposes hubness.
3. Select chart anchors with farthest-first traversal.
4. Assign points to overlapping charts using a data-derived local radius.
5. Compute a local PCA basis, a 3-D inspection coordinate and a local intrinsic-dimension diagnostic.
6. Build the chart-overlap (nerve) graph.

Production versions can replace exact matrix operations with HNSW, DiskANN, ScaNN, FAISS, cuVS or another candidate generator without changing the semantic layer.

## Query path

1. **Multi-scale routing** — rank chart centroids, optionally using a shortened prefix when the source embeddings are Matryoshka-compatible.
2. **Candidate union** — gather candidates from several overlapping charts plus a global safety net.
3. **Hub-robust scoring** — combine cosine relevance with a CSLS-inspired local-density correction.
4. **Late interaction** — optional query facets are matched independently against record facets and pooled by max-similarity.
5. **Trust-aware scoring** — provenance confidence is a first-class signal rather than payload ignored by the ranker.
6. **Diversity** — greedily reduce redundant near-duplicates in the final set.
7. **Explainability** — expose score components, chart membership and local coordinates for every hit.

## New query primitives

Nearest-neighbor search remains available, but topology makes additional operations natural:

- `bridge(A, B)`: a path through reciprocal semantic neighborhoods;
- `boundary(A, B)`: records in a transition region between two anchors;
- chart overlap: where concepts meet or split;
- hubness diagnostics: points disproportionately retrieved as neighbors;
- local intrinsic dimension: areas where the corpus is geometrically simple or complex;
- future: drift fields, uncertainty regions, holes/loops via persistent homology, and causal/temporal paths.

## Why SQL remains

Relational storage is still the correct control plane for IDs, constraints, transactions, metadata and auditability. The prototype deliberately stores durable metadata in SQLite and vector geometry separately. The proposed innovation is a **new discovery plane**, not an attempt to make vector distance perform relational semantics.
