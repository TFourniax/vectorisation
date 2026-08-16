# Prior art and differentiation notes

This is a research map, not a novelty or patent opinion. The relevant literature is moving quickly. Claims below describe the sources reviewed for this prototype and must be revisited before any formal novelty claim.

## Vector-database model migration

Qdrant's current migration guidance supports zero-downtime blue/green migration and named vectors. Both strategies allow serving the old representation while new vectors are generated, but the migration process still re-embeds existing points in the background before the new representation becomes the complete search surface.

Source: Qdrant documentation, *Migrate to a New Embedding Model* and named-vector documentation.

SCF asks a different question: can a new-model query search the complete legacy corpus **before** every legacy point has a new embedding, while a partial new index is fused safely and progressively replaces transported coordinates?

## Drift-Adapter

*Drift-Adapter: A Practical Approach to Near Zero-Downtime Embedding Model Upgrades in Vector Databases* (arXiv:2509.23471) explicitly attacks expensive model upgrades by learning adapters that map new queries into the legacy embedding space. It evaluates orthogonal Procrustes, low-rank affine and residual-MLP adapters and reports large recomputation savings in its experiments.

This is close and important prior art. SCF should not claim that query-space adaptation itself is new.

The research delta being tested here is the **fabric** around adaptation:

- piecewise local rather than necessarily global transitions;
- a directed graph of many coordinate systems rather than one upgrade pair;
- held-out transition confidence as a routing primitive;
- cycle/cocycle consistency across redundant routes;
- concurrent multi-space search with coverage-aware fusion during partial migration;
- semantic cells that preserve cross-model disagreement as uncertainty;
- virtual materialization into a target space;
- fault-line and coordinate-aware drift diagnostics.

Whether that combination is novel enough to matter has to be established experimentally and through broader prior-art/patent review.

## Procrustes theory for model alignment

*When Embedding Models Meet: Procrustes Bounds and Applications* (arXiv:2510.13406) studies conditions under which two embedding spaces can be aligned by an isometry when pairwise inner products are approximately preserved. This provides useful theory for the simple global baseline and explains why orthogonal alignment can work surprisingly well in some settings.

SCF therefore treats global Procrustes as a baseline that local transitions must beat, not as a straw man.

## Local cross-model consistency

*Vector Linking via Cross-Model Local Isometric Consistency* (arXiv:2605.31100) reports that independently trained contrastive encoders can exhibit local geometric consistency: short-range relationships can align even where long-range geometry is distorted. It uses seed anchors to link vector spaces.

This strongly motivates—and also constrains—the local-atlas hypothesis. SCF's local transition layer should be evaluated as one systems realization of this phenomenon, not described as discovery of the phenomenon itself.

## Uncertainty-aware retrieval

*DINOSAUR: Distributional Approximate Nearest Neighbour Search for Uncertainty-Aware Retrieval* (arXiv:2606.04603) argues against collapsing uncertain representations to one point and performs ANN over distributional samples.

SCF's semantic cells approach uncertainty differently: multiple model observations are transported into a target coordinate system and their disagreement becomes cell dispersion. These ideas may be complementary. A future benchmark should compare point, cell and distributional representations directly.

## Hubness and retrieval asymmetry

Recent work including *Hubness, Not Anisotropy, Drives Cross-Lingual Retrieval Asymmetry...* (arXiv:2605.26575) identifies hubness as an important mechanism in high-dimensional retrieval and reports that local scaling such as CSLS closes a substantial retrieval gap in the studied setting.

SMA Phase 0 uses hubness diagnostics and CSLS-inspired correction; this is an application/combination, not a novelty claim for CSLS or hubness mitigation.

## Filtered ANN and query planning

Recent filtered-ANN systems research shows that end-to-end performance depends on query planning/selectivity as well as raw ANN quality. SCF therefore should remain a coordinate/control layer above mature ANN engines rather than attempting to replace their low-level indexing work.

## Patent caution

A targeted patent search also finds earlier disclosures around cross-embedding alignment, latent-space geometric transfer and common latent spaces. That further reinforces the need to avoid claiming the broad idea of "mapping one vector space to another". Any protectable novelty, if it exists, would have to lie in narrower system mechanisms and their interaction, and should be evaluated by qualified patent counsel after a dedicated search.

## Current differentiation hypothesis

The strongest hypothesis is not "a new vector database" and not "a 3-D map". It is:

> **Embedding models can be treated as audited coordinate systems over stable logical objects, connected by local transitions and consistency constraints, so stored knowledge can outlive any one representation model.**

The scientific burden is to demonstrate that this layer yields better migration economics, robust retrieval continuity, useful uncertainty, and failure detection on real models without adding unacceptable latency or operational risk.
