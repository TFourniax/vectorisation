# Research basis and falsifiable claims

Date of review: 2026-08-16.

This project is deliberately a synthesis rather than a claim that every component is novel. The research question is whether their composition into a local, topology-aware retrieval/storage abstraction provides a measurable advantage over the dominant "one object = one vector + metadata" design.

## Established findings we build on

### Approximate nearest-neighbor graphs are excellent candidate generators

DiskANN and related graph indices show that billion-scale ANN can achieve high recall with SSD-aware graph structures, while FreshDiskANN addresses real-time updates. This is a systems layer we should reuse, not reinvent.

### High-dimensional nearest-neighbor geometry has failure modes

Hubness causes a small set of points to appear in many neighbor lists. Recent work has shown that this can become a security/reliability weakness in vector databases. Local scaling methods such as CSLS can reduce hub dominance in some settings.

### One vector can be too lossy

ColBERT's late interaction demonstrates that retaining multiple token-level vectors can materially improve retrieval expressiveness while keeping document representations precomputable. Later work continues to explore pruning and weighting to manage the storage cost.

### Capacity should be adaptive

Matryoshka Representation Learning encodes useful representations at nested dimensionalities, enabling coarse-to-fine retrieval and lower storage/compute budgets when a task does not need the full dimension.

### Hierarchies are not naturally Euclidean

Hyperbolic embeddings can represent hierarchical structure compactly, and hyperbolic nearest-neighbor methods exist. Recent HyperbolicRAG work explores fusing Euclidean semantics with hierarchical geometry.

### Global corpus questions need structure

GraphRAG showed that plain local RAG underperforms for corpus-level sensemaking and that graph/community structure adds a different capability from nearest-neighbor retrieval.

### Local geometry can differ sharply from global geometry

Local Intrinsic Dimensionality is a meaningful predictor of nearest-neighbor-search difficulty. Recent embedding-geometry work reports locally rotating tangent spaces and much lower effective local dimension than raw embedding dimension in a large real-world foundation-model dataset. This motivates local charts rather than one global projection.

### Topology can summarize high-dimensional shape

Mapper/TDA constructs graphs from overlapping covers of high-dimensional data. Persistent-homology work also shows that topology preservation is a distinct property from ordinary embedding-distance preservation.

## Project hypotheses

**H1 — local charts:** routing and calibration with overlapping local charts will improve retrieval robustness on corpora with heterogeneous local geometry, especially under distribution shift.

**H2 — reciprocal topology:** mutual-kNN topology plus local-density scoring will reduce hub-dominated false positives without unacceptable recall loss.

**H3 — multi-representation cells:** optional facet vectors will improve fine-grained matching on compositional queries compared with a single pooled vector.

**H4 — topology as an API:** bridge, boundary, cluster-overlap and drift queries will enable useful workloads that cannot be expressed naturally as top-k vector search.

**H5 — adaptive dimensionality:** Matryoshka-compatible coarse routing followed by full-dimensional local ranking can reduce compute while preserving quality.

None of these should be marketed as proven until benchmarked against strong baselines.

## Falsification plan

The next stage must compare SMA against exact cosine search, HNSW/DiskANN, a production vector DB with filtering, BM25+dense hybrid retrieval, multi-vector late interaction and graph-enhanced retrieval where explicit relations exist.

Datasets should cover BEIR/MTEB retrieval, filtered ANN workloads, multilingual corpora, streaming updates and adversarial hub injection. Report Recall@k, nDCG@10, MRR, latency p50/p95/p99, build time, memory, disk footprint, write amplification and cost where measurable.

A claimed improvement is accepted only if it survives repeated seeds, a held-out dataset and an ablation removing the corresponding SMA component.

## Primary sources

1. Microsoft Research, DiskANN project and publications: https://www.microsoft.com/en-us/research/project/project-akupara-approximate-nearest-neighbor-search-for-large-scale-semantic-search/
2. Khattab & Zaharia, *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT*: https://arxiv.org/abs/2004.12832
3. Kusupati et al., *Matryoshka Representation Learning*: https://arxiv.org/abs/2205.13147
4. Edge et al., *From Local to Global: A Graph RAG Approach to Query-Focused Summarization*: https://arxiv.org/abs/2404.16130
5. Aumüller & Ceccarello, *The Role of Local Intrinsic Dimensionality in Benchmarking Nearest Neighbor Search*: https://arxiv.org/abs/1907.07387
6. Cao et al., *Topological Information Retrieval with Dilation-Invariant Bottleneck Comparative Measures*: https://arxiv.org/abs/2104.01672
7. Madukpe et al., *A Comprehensive Review of the Mapper Algorithm ... (2007-2025)*: https://arxiv.org/abs/2504.09042
8. Li et al., *Can You Trust the Vectors in Your Vector Database? Black-Hole Attack from Embedding Space Defects*: https://arxiv.org/abs/2604.05480
9. Sakhawat et al., *Hubness, Not Anisotropy, Drives Cross-Lingual Retrieval Asymmetry in Multilingual Embedding Models*: https://arxiv.org/abs/2605.26575
10. Rahman et al., *Characterizing AlphaEarth Embedding Geometry for Agentic Environmental Reasoning*: https://arxiv.org/abs/2604.18715
11. Wu & Charikar, *Nearest Neighbor Search for Hyperbolic Embeddings*: https://arxiv.org/abs/2009.00836
12. *HyperbolicRAG: Enhancing Retrieval-Augmented Generation with Hyperbolic Representations*: https://arxiv.org/abs/2511.18808
13. Iff et al., *Benchmarking Filtered Approximate Nearest Neighbor Search Algorithms on Transformer-based Embedding Vectors*: https://arxiv.org/abs/2507.21989
