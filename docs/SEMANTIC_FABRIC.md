# Semantic Coordinate Fabric

## Thesis

A vector is not meaning. It is a coordinate emitted by one representation model.

If two embedding models encode the same logical object, the two vectors generally cannot be compared directly: their dimensions, rotations, local distortions, training objectives, language coverage and modalities may differ. Conventional vector infrastructure therefore couples stored data to the encoder that produced it.

Semantic Manifold Atlas (SMA) treats an embedding model as a **coordinate chart** over an unknown semantic object space. A **Semantic Coordinate Fabric (SCF)** is the graph of audited transition functions between those charts.

Let an unknown semantic domain be `M`. Encoder `i` provides a chart

`phi_i : U_i subset M -> R^d_i`.

On an overlap between two charts, SCF learns an approximation of

`tau_ij ~= phi_j o phi_i^-1`.

The transition is not assumed to exist globally. The reference implementation uses overlapping local scaled orthogonal-Procrustes maps and blends the maps nearest to the source query. Other transition families can replace this baseline.

## Why local transitions

A single global transformation is attractive because it is cheap and inspectable. It is also a strong assumption. Independent representation models can preserve local semantic neighborhoods while bending global geometry differently. SCF therefore models the transition as a collection of local maps and measures whether this extra complexity survives held-out validation.

This produces four useful properties:

1. **dimension independence** — source and target spaces may have different dimensions;
2. **locality** — different regions may use different transition maps;
3. **auditability** — every transition has held-out pair and neighborhood metrics;
4. **composability** — transitions form a graph and may be routed across multiple models.

## Transition confidence

A transition is useful only if its reliability is explicit.

With at least ten paired anchors, `TransitionAtlas.fit()` reserves a deterministic hold-out set. It evaluates:

- mean paired cosine after transport;
- 10th-percentile paired cosine;
- paired recall@1;
- kNN-neighborhood Jaccard agreement.

The serving maps are then refit on every anchor, but the transition confidence remains the held-out score. This avoids the common error of reporting fit quality on the anchors used to learn the map.

A transition route multiplies confidence across hops. Low-confidence routes can therefore be rejected instead of silently producing a plausible-looking vector.

## Cocycle / cycle consistency

If the fabric contains transitions `A -> B`, `B -> C` and `C -> A`, a vector should approximately return to its starting coordinate after the full cycle. Large cycle error is evidence that at least one transition, preprocessing configuration or model identity is inconsistent.

This converts redundancy in the fabric into an integrity signal.

The current `cycle_consistency()` audit reports mean and p10 cosine plus mean cycle error. A production implementation should use these audits as gates, not dashboards only.

## Partial migrations without a big-bang re-index

Suppose a corpus has 100 million legacy vectors and a new encoder is introduced. Existing systems can keep serving during a background migration, but the corpus still normally has to be re-embedded before the new representation fully replaces the old one.

SCF permits a different execution plan:

1. collect a small paired anchor set;
2. learn `new_query -> legacy` and, when useful, `legacy -> new` transitions;
3. begin issuing queries from the new encoder immediately;
4. search both the complete legacy index and the partial new index;
5. fuse evidence with transition confidence and index coverage;
6. progressively replace transported coordinates with direct new-model observations.

A rank from a 10%-complete index must not be treated like a rank from a complete corpus. The reference fusion therefore corrects a partial-index rank by coverage before reciprocal-rank fusion and also scales evidence reliability by coverage.

This is deliberately conservative. The objective is continuity without pretending that a partial index is complete.

## Semantic cells: an object is not always a point

A logical record can have direct observations in several coordinate systems. To represent that record in target space `T`, SCF can:

1. use a direct `T` vector when available;
2. transport other observations through trusted paths into `T`;
3. compute a confidence-weighted spherical barycenter;
4. measure disagreement around that center.

The result is a **SemanticCell**:

- `center`: canonical target coordinate;
- `dispersion`: uncertainty caused by disagreement between observations/transitions;
- `confidence`: transition quality, agreement and source confidence combined;
- `observations`: source spaces and transport paths that created the cell.

This is intentionally different from asserting that the transported center is the same thing as a fresh target-model embedding. A virtual coordinate is labelled as virtual and should be replaced by direct observation when the migration reaches that object.

## Virtual materialization

`materialize_virtual_space(target_space)` can construct a temporary full-corpus SMA index in a new coordinate system before every object has been directly re-embedded.

Potential uses:

- zero-big-bang model upgrades;
- expensive or rate-limited re-embedding;
- temporary interoperability between proprietary and local models;
- multimodal bridges when paired anchors exist;
- disaster recovery when an old encoder is no longer available.

A virtual index is an approximation. Admission is gated by cell confidence and route confidence. Production systems should expose virtual/direct status to callers.

## Fault lines

Two models may agree on most of a corpus but disagree sharply around certain objects. These are often more interesting than nearest neighbors.

`neighborhood_disagreement()` compares an object's semantic neighborhood across every space in which it is observed. `fault_lines()` ranks records whose local neighborhoods are representation-sensitive.

This can reveal:

- ambiguous concepts;
- encoder blind spots;
- multilingual mismatch;
- domain drift;
- poisoned or malformed records;
- genuinely contested semantic regions.

## Coordinate-aware drift

Raw `embedding_before - embedding_after` is meaningless when the model changed because the coordinate system itself changed.

`compare_indexes()` first transports the old observation into the new coordinate system and then measures residual vector displacement plus neighborhood churn. In principle this lets operators distinguish **coordinate drift** from remaining content/semantic drift, bounded by transition quality.

## Relationship to ANN databases

SCF is not intended to replace HNSW, DiskANN, Qdrant, pgvector, Vespa, Milvus or another candidate-generation engine. It is a layer above them.

The reference implementation uses `AtlasIndex` because it makes every operation inspectable. A production adapter should delegate candidate retrieval to mature ANN engines while retaining:

- space identity;
- transition routing;
- confidence;
- cycle audits;
- cross-space fusion;
- semantic cells;
- coordinate-aware diagnostics.

## What would make this important

The idea is valuable only if it survives real models and real corpora. Success would mean that embedding infrastructure becomes less like a collection of model-specific vector silos and more like a durable coordinate fabric where representation models can evolve independently of logical data identity.

The claim is falsifiable. If local transitions do not outperform simpler global adapters, if confidence is poorly calibrated, if transported search quality collapses on domain shift, or if migration savings are smaller than the added complexity, SCF should be narrowed or discarded.
