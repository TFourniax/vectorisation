# V2 benchmark protocol

Synthetic tests are mechanism tests. They are useful for proving that an implementation can detect or recover a constructed condition; they are not evidence of production superiority.

## Current deterministic mechanism tests

`benchmarks/coordinate_fabric_benchmark.py` covers four independent mechanisms.

| Mechanism | Baseline | SCF result | Interpretation |
|---|---:|---:|---|
| Piecewise cross-model warp | global Procrustes held-out cosine 0.7042 | local atlas 0.9414 | local mapping recovers deliberately region-dependent geometry |
| 25% new-index migration | new-only overlap@10 vs legacy SMA oracle 0.2080 | fabric 0.8460 | complete legacy evidence remains usable from a new-space query |
| Corrupted transition cycle | good cycle cosine ~1.0000 | corrupted -0.0760 | redundant coordinate routes expose corruption |
| 20% direct new vectors | direct coverage 0.20 | virtual coverage 1.00, overlap@10 1.00 | exact synthetic rotation can be virtually materialized |

The final row is intentionally easy for alignment: the spaces differ by an exact rotation. It tests mechanics, not realistic embedding-model equivalence.

## First real-data representation test

`benchmarks/digits_coordinate_benchmark.py` uses the 1,797 handwritten images shipped with `sklearn.datasets.load_digits`. This is **real observed data**, but deliberately not described as a neural embedding-model benchmark.

The same logical image is represented in two genuinely different coordinate systems:

- legacy: normalized raw 8x8 pixels, 64 dimensions;
- target: HOG descriptors, 324 dimensions.

A fixed split uses 1,400 documents and 397 held-out query images. Query images are never transition anchors. The benchmark measures both exact HOG-neighborhood imitation and a task-level relevance metric: whether retrieved documents have the same digit label as the query.

| Anchor coverage | Global same-digit precision@10 | Local atlas same-digit precision@10 | Global HOG-neighbor overlap@10 | Local HOG-neighbor overlap@10 |
|---:|---:|---:|---:|---:|
| 5% | 0.4418 | 0.4889 | 0.0720 | 0.0806 |
| 10% | 0.4970 | 0.6259 | 0.0856 | 0.1217 |
| 20% | 0.4897 | 0.7353 | 0.0788 | 0.1685 |
| 40% | 0.4741 | 0.7776 | 0.0811 | 0.2161 |
| 70% | 0.4280 | 0.8526 | 0.0741 | 0.2809 |

Native target HOG retrieval has same-digit precision@10 **0.8343**; native pixel retrieval has **0.9476**.

This result is both encouraging and cautionary. The local atlas consistently beats one global map on the task-level relevance metric and improves as anchor coverage grows. However, exact target-neighborhood overlap remains low even at high anchor coverage. Therefore **target-ranking imitation is not enough as the only success metric, and task relevance cannot be ignored either**. Real embedding-model experiments must report both.

The optional benchmark dependencies are installed with `pip install -e '.[bench]'`.

## Real paired-model benchmark harness

`benchmarks/npz_upgrade_benchmark.py` accepts a database-neutral NPZ:

- `old_docs`: N x D_old;
- `new_docs`: N x D_new;
- `new_queries`: Q x D_new.

It samples paired document anchors, fits both a local transition atlas and a global Procrustes baseline, then evaluates retrieval against the exact full-new-space top-k oracle.

Required future additions:

- query relevance labels where available, not only full-new nearest-neighbor imitation;
- multiple random anchor samples and confidence intervals;
- domain-held-out anchors;
- multilingual and cross-modal model pairs;
- 1%, 5%, 10%, 25%, 50% migration coverage curves;
- p50/p95/p99 latency and memory;
- transition fit cost vs full re-embedding cost;
- failure calibration: observed retrieval quality as a function of declared confidence.

## Strong baselines

At minimum:

1. full re-embedding + exact cosine (quality ceiling for a chosen target encoder);
2. legacy exact / ANN retrieval;
3. global orthogonal Procrustes;
4. low-rank affine adapter;
5. learned residual adapter where training data justifies it;
6. new-index-only at each migration coverage;
7. ordinary reciprocal-rank fusion without coverage correction;
8. SCF local atlas + confidence + coverage correction;
9. SCF virtual materialization.

Where practical, candidate generation should be measured with Qdrant/HNSW and DiskANN rather than NumPy exact search.

## Ablations

Remove one component at a time:

- local maps -> global map only;
- held-out confidence -> train-fit quality;
- route confidence -> uniform route weight;
- coverage correction -> naive RRF;
- cycle audit;
- cell dispersion;
- cross-space consensus;
- hubness correction in the underlying SMA retriever.

A component that repeatedly fails to improve quality, safety, cost or explainability should be removed.

## Kill / narrow criteria

The broad SCF hypothesis should be narrowed if one or more of these persist across representative model pairs:

- local transitions do not materially beat simple global adapters;
- useful transition confidence cannot be calibrated from affordable anchor counts;
- transported retrieval loses too much target-model quality before economically meaningful migration savings appear;
- virtual materialization produces unstable neighborhoods under modest domain shift;
- added latency/complexity dominates the saved re-embedding work;
- graph composition compounds error too quickly for routes longer than one hop.

A negative result is useful: the protocol can still collapse to a simpler audited one-hop migration adapter if that is what the evidence supports.
