# Prior art and differentiation notes

This is a research map, not a novelty or patent opinion. The literature is moving extremely quickly. The correct posture is to narrow claims whenever stronger prior art appears.

## The important correction after the first prototype

The original V0.2 thesis—embedding models as interoperable coordinate systems—overlaps materially with a fast-moving research program from the University of Edinburgh and with earlier compatibility work. **SMA/SCF must not claim that cross-model translation, local alignment, composable translation, or embedding-independent vector-database representations are broadly new.**

That discovery changed the project direction. The strongest current research hypothesis is now the **Semantic ABI** layer: a coordinate-free, versioned contract of semantic invariants used to certify, localize and route representation implementations.

## Integrating Vector Databases across Embedding Models — SIGMOD 2026

Beining Yang, Yang Cao and Yang Ren, *Integrating Vector Databases across Embedding Models*, ACM SIGMOD 2026 (Best Paper Honorable Mention).

This work directly studies integrating vector databases produced by different embedding models without assuming access to raw objects or model internals. It is rooted in local cross-model geometric consistency and evaluates real embedding models.

This is direct prior art against any broad claim that SCF invented cross-model vector-database interoperability.

## Generalizable and Composable Multi-Model Embedding Translation — ICML 2026

Beining Yang and Yang Cao, *Generalizable and Composable Multi-Model Embedding Translation*, ICML 2026 Spotlight.

This is particularly important prior art for the most recent SCF direction. It studies multi-model translation, out-of-distribution behavior, composed/chained translations, a geometry-aware confidence metric and localized adaptation through a hierarchical mixture-of-experts design.

Therefore SCF must **not** claim novelty for:

- local embedding translation by itself;
- query/model-specific translation confidence by itself;
- chaining translations across several representation models;
- localized experts for cross-model interoperability.

Our local-risk field and query-aware graph routing remain useful executable research mechanisms, but the scientific contribution cannot rest on those ideas alone.

## Vector Linking via Cross-Model Local Isometric Consistency — ICML 2026

Ziying Chen, Yang Cao, He Sun, Beining Yang and Tianjian Yang, *Vector Linking via Cross-Model Local Isometric Consistency*, ICML 2026.

The work provides theoretical/empirical support for local geometric consistency between independently trained contrastive encoders and uses anchor correspondences to link vector spaces.

This strongly supports local methods while constraining novelty claims around the "atlas" metaphor.

## Metric Algebra: Embedding-Independence in Vector Databases — accepted SIGMOD 2027

Tianjian Yang, Yang Cao, Beining Yang, Ziying Chen and Tiejun Ma, *Metric Algebra: Embedding-Independence in Vector Databases*, accepted for SIGMOD 2027.

The authors describe it as an intermediate representation bringing physical/logical independence—embedding independence—to vector database systems. As of this research pass, the accepted-paper listing and author research page are public, but we did not find a public full preprint through ordinary search.

This title and positioning are close enough to the broad SCF vision that we should assume significant overlap until the full paper can be reviewed.

## Drift-Adapter — EMNLP 2025

Harshil Vejendla, *Drift-Adapter: A Practical Approach to Near Zero-Downtime Embedding Model Upgrades in Vector Databases*, EMNLP 2025.

It maps new queries into a legacy space using paired anchors and evaluates orthogonal Procrustes, low-rank affine and residual-MLP adapters. The reported experiments recover most full-reembedding retrieval quality with very small query-time overhead.

This is strong prior art for zero/near-zero-downtime upgrades through query transformation.

## Backward/forward compatible representation learning

A substantial vision/retrieval literature predates the database-oriented work:

- backward-compatible training;
- Forward Compatible Training (CVPR 2022);
- Bidirectional Compatible Training;
- Learning Compatible Embeddings;
- Neighborhood Consensus Contrastive Learning;
- Darwinian Model Upgrades / selective compatibility;
- compatibility-aware heterogeneous visual search.

These works establish that representation compatibility is a long-standing problem, not a new problem created by this repository.

## Query Drift Compensation — CoLLAs 2026

*Query Drift Compensation: Enabling Compatibility in Continual Learning of Retrieval Embedding Models* studies continual updates of text retrieval encoders and projects new queries into old embedding spaces to continue using already indexed corpora.

This further narrows any claim around migration-time query projection.

## Ordinal embedding as a basis for coordinate-free contracts

Ordinal-embedding literature studies representations from constraints such as "object A is closer to B than to C" rather than requiring absolute coordinates. Results include uniqueness/reconstruction theory and local ordinal embedding.

Semantic ABI borrows this mathematical primitive as a **contract clause**, not as a claim to have invented ordinal constraints.

The proposed systems hypothesis is different: use ID-level ordinal and topological invariants as a stable compatibility interface across changing retrieval implementations, combine them with provenance/versioning/local risk, and use them to control rollout/fallback.

## Vector Annotation Databases

A 2026 SSRN paper, *Vector Annotation Databases: An Architecture for Auditable Semantic Retrieval*, argues for explicit data objects and deterministic semantic metadata as a stable retrieval core, with vectors as replaceable annotations.

It is relevant conceptual prior art for treating embeddings as derived/replaceable rather than canonical data. Because it is a recent SSRN publication rather than a mature consensus reference, it should be treated as useful prior art rather than definitive validation.

## Uncertainty-aware retrieval

*DINOSAUR: Distributional Approximate Nearest Neighbour Search for Uncertainty-Aware Retrieval* argues against collapsing uncertain representations to a single point and performs ANN over distributional samples.

SCF SemanticCells encode cross-representation disagreement differently, but uncertainty-aware vector retrieval itself is not novel.

## Hubness

SMA Phase 0 uses hubness diagnostics and CSLS-inspired correction. Hubness and local-scaling remedies predate this work and remain mechanisms, not novelty claims.

## What remains potentially differentiated

The current strongest systems hypothesis is:

> **A data system should expose a stable Semantic ABI above embedding implementations: versioned, coordinate-free assertions of application meaning and selected behavior, with local certification risk, tamper-evident history and runtime rollout/fallback semantics.**

This differs from merely translating embeddings because a candidate implementation can:

- satisfy application semantics without reproducing the old ranking;
- reproduce geometry yet fail a hard semantic clause;
- be certified in one semantic region and rejected in another;
- be dense, sparse, graph-based or otherwise non-isomorphic to the previous representation, provided it can evaluate the contract.

This is a hypothesis, not a novelty conclusion. A broader paper/patent search may still find close work.

## Next prior-art target

Before any IP or strong novelty claim, specifically search:

- semantic regression contracts for retrieval/ranking systems;
- invariant-based model deployment gates;
- specification-driven IR evaluation;
- regional/selective model rollout based on semantic tests;
- coordinate-free IR intermediate representations;
- patents on embedding compatibility certification and semantic regression testing.

## Kill criterion

If Semantic ABI reduces empirically to ordinary fixed benchmark/regression testing—without useful portability, local risk calibration or rollout economics—the abstraction should be simplified rather than protected for its own sake.
