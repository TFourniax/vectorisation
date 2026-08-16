# Semantic Manifold Atlas

**Research prototype for a topology-aware vector data engine.**

Today's vector databases are very good at answering *"which stored vectors are nearest to this vector?"* But real knowledge is not a flat cloud of independent points.

Semantic Manifold Atlas (SMA) explores a different abstraction: **objects live in overlapping local semantic charts connected by a topology**. A record can carry a primary embedding, multiple fine-grained facet vectors, provenance and confidence. The engine exposes both retrieval and navigational operations over the resulting semantic structure.

> The goal is not to replace SQL with a 3-D scatter plot. SQL remains the right control plane for transactions, constraints and metadata. Nor do we compress arbitrary embeddings to XYZ. The 3-D coordinates in this prototype are local inspection views; the full vector remains available for retrieval.

## Why this may matter

A single global metric loses information in several ways:

- high-dimensional nearest-neighbor spaces can exhibit **hubness**;
- local intrinsic dimensionality and concept directions can differ across a corpus;
- one pooled vector can hide fine-grained term/facet matches;
- hierarchy, graph structure, time and provenance are not captured by cosine distance;
- top-k similarity cannot naturally answer bridge, boundary, drift or global-shape questions.

SMA combines several research-backed ideas into one falsifiable storage/retrieval hypothesis:

1. overlapping **local charts** rather than one forced global projection;
2. **mutual-kNN topology** and hubness diagnostics;
3. **CSLS-inspired local calibration** alongside ordinary cosine relevance;
4. optional **multi-vector late interaction** for facets/tokens;
5. **multi-scale routing**, compatible with Matryoshka embeddings;
6. a chart-overlap **nerve graph** inspired by topological data analysis;
7. explicit **provenance/confidence** in ranking and explanations.

See [`docs/RESEARCH.md`](docs/RESEARCH.md) for the research basis, hypotheses and falsification plan, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the design.

## Current synthetic stress test

The included hubness benchmark creates an anisotropic 64-D corpus and injects six near-centroid "black-hole" vectors. On the fixed seed used by the benchmark:

- exact cosine: precision@10 **0.6300**, injected hubs/query **3.3687**;
- current SMA prototype: precision@10 **0.8519**, injected hubs/query **0.0000**.

This is a **synthetic falsification test, not evidence of production superiority**. The next milestone is real-corpus benchmarking against strong baselines.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python examples/demo.py
python benchmarks/hubness_benchmark.py
```

The included `FeatureHashEmbedder` is deterministic and API-free so the demo is reproducible. It is **not** a production embedding model; pass vectors from OpenAI, Voyage, Jina, BGE, Qwen, local models or any other encoder to `AtlasRecord`.

## Minimal API

```python
from semantic_atlas import AtlasIndex, AtlasRecord

index = AtlasIndex(chart_size=64, chart_overlap=1.3, graph_k=10)
index.add(AtlasRecord("doc-1", vector_1, metadata={"source": "paper"}))
index.add(AtlasRecord("doc-2", vector_2, facets=token_vectors))
index.build()

hits = index.search(query_vector, facets=query_token_vectors)
path = index.bridge("doc-1", "doc-2")
boundary = index.boundary("doc-1", "doc-2")
shape = index.map()
```

Every search hit contains a decomposed score, chart membership and local 3-D inspection coordinates.

## Status

This is **Phase 0: a research kernel**, not a production database and not yet evidence of a sector-level breakthrough. The next milestone is deliberately harder: beat strong baselines under reproducible benchmarks and survive ablation tests. The project should be killed, narrowed or redesigned if the evidence does not support its hypotheses.

See [`docs/ROADMAP.md`](docs/ROADMAP.md).
