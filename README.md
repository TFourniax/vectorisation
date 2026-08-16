# Semantic Manifold Atlas

**Research toward a semantic data layer that can outlive any one embedding model, vector database, or representation implementation.**

A vector is not meaning. It is one coordinate assigned to a logical object by one model at one time.

This repository now investigates three layers:

1. **Semantic Manifold Atlas (SMA)** — topology-aware retrieval over overlapping local semantic charts rather than treating the corpus as unrelated points.
2. **Semantic Coordinate Fabric (SCF)** — interoperability between different representation spaces through audited local transitions, uncertainty and migration-time routing.
3. **Semantic ABI** — coordinate-free, versioned invariants of the meaning an application actually requires, so a new representation can be certified or rejected independently of whether it reproduces the old coordinates.

The intended architecture is a semantic control layer **above** mature ANN engines such as Qdrant, DiskANN, HNSW or pgvector—not a reinvention of their low-level indexing work.

> SQL still belongs in the control plane for transactions, constraints, metadata and logical identity. SMA does **not** compress knowledge to XYZ: local 3-D coordinates are inspection views only; full-dimensional representations remain retrieval coordinates.

## The key abstraction shift

Traditional vector infrastructure effectively couples:

```text
logical object -> embedding model -> vector -> index
```

The research direction here separates them:

```text
                         Semantic ABI
                 meaning / behavior contracts
                           |
                    stable object ID
                 /         |          \
          observation A  observation B  graph/sparse/etc.
               |             |
            space A <== Semantic Coordinate Fabric ==> space B
               \             /
                mature ANN / retrieval engines
```

A candidate model can therefore change geometry substantially yet still pass the application contract. Conversely, a geometrically well-aligned model can be blocked if it violates a critical semantic invariant.

## Phase 0 — Semantic Manifold Atlas

The original kernel includes:

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

Fixed-seed synthetic hubness stress test:

- exact cosine precision@10: **0.6300**, injected hubs/query: **3.3687**;
- SMA precision@10: **0.8519**, injected hubs/query: **0.0000**.

This is a mechanism test, not a production superiority claim.

## Phase 1 — Semantic Coordinate Fabric

The v0.2/v0.3 research kernel includes:

- rectangular scaled-Procrustes maps across different dimensions;
- piecewise local transition atlases;
- deterministic held-out transition diagnostics;
- local support radius + held-out local-risk calibration;
- **query-dependent routing**: the same model graph may choose different translation paths in different semantic regions;
- multi-hop transition graph and cycle-consistency audits;
- concurrent cross-space search;
- coverage-corrected rank fusion during partial migrations;
- `SemanticCell` barycenters with dispersion and provenance;
- virtual target-space materialization before full re-embedding;
- `fault_lines()` for representation-sensitive objects;
- coordinate-aware drift reports;
- portable `semantic-coordinate-transition` format v2.

### Deterministic mechanism tests

| Test | Simple baseline | Current SCF |
|---|---:|---:|
| Region-dependent cross-model warp, held-out pair cosine | global Procrustes **0.7042** | local atlas **0.9414** |
| Target index only 25% migrated, top-10 overlap vs legacy SMA oracle | new-only **0.2080** | fabric **0.8460** |
| Transition-cycle integrity | good **~1.0000** | corrupted **-0.0760** |
| Exact-rotation toy migration with 20% direct target vectors | direct coverage **0.20** | virtual coverage **1.00** |

The virtual-materialization case is intentionally easy. It validates mechanics, not equivalence between real neural embedding models.

### First real-data coordinate test

`digits_coordinate_benchmark.py` uses 1,797 real handwritten-digit observations with two different coordinate systems: 64-D normalized pixels and 324-D HOG descriptors. With 1,400 indexed images and 397 held-out queries, the local transition improves same-digit precision@10 over one global map from **0.4897 -> 0.7353** at 20% anchor coverage and **0.4741 -> 0.7776** at 40%.

Exact HOG-neighbor imitation remains much lower (**0.1685** and **0.2161**), which is an important result rather than an inconvenience: **target-ranking fidelity and downstream semantic relevance are different metrics and must both be reported.**

This is real data but not yet a neural embedding-model benchmark.

## Phase 2 — Semantic ABI

Cross-model embedding interoperability is already an active 2025–2027 research area. The repository therefore no longer treats “mapping one embedding space to another” as its strongest novelty hypothesis. See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

The new layer asks a different question:

> **What must remain semantically true when the representation implementation changes?**

`SemanticContract` expresses assertions over stable logical IDs rather than coordinates:

- ordinal triplets: `A must prefer B over C`;
- critical-neighborhood survival budgets;
- reciprocal-neighbor/topological edges;
- hard vs soft requirements;
- provenance/source for each clause.

Two compatibility dimensions are deliberately separate:

- **application semantic compatibility** — meaning the product/domain requires;
- **legacy behavior compatibility** — selected retrieval behavior we may want to preserve or consciously break.

Contracts have canonical SHA-256 identities and can be versioned in a tamper-evident `ContractLedger` hash chain.

### Local certification and selective rollout

An audit does not return only one global score. Violated clauses create a local risk field over logical objects. `SemanticABIGate` interpolates that risk around a query and can:

- use the new implementation in certified regions;
- fall back to the legacy implementation in locally broken regions;
- refuse all implementations when hard contract requirements fail.

That enables **region-wise semantic rollout** instead of one global “model passed / model failed” switch.

### Real-data Semantic ABI benchmark

On 1,400 real handwritten digits:

**Application contract — 1,400 hard-negative ordinal assertions**

- legacy pixels: **0.980**;
- different HOG representation: **0.911**;
- HOG after deliberate 10% identity corruption: **0.813**.

At local-risk threshold 0.15, certified coverage drops from about **76.9%** to **57.0%** after corruption.

**Captured legacy-behavior contract**

- pixels: **1.000**;
- HOG: **0.711**;
- corrupted HOG: **0.610**.

The point is not that HOG is better or worse. The result demonstrates that a representation can preserve application semantics substantially better than it preserves the legacy retriever's exact behavior.

## Phase 3 — active semantic repair

`plan_repairs()` turns contract violations into an ordered sparse backfill/review plan. The transparent V0 greedy combines:

- local semantic risk;
- number of violated clauses touching the object;
- geometric diversity, so one dense fault region does not consume the entire budget.

In the same real-data test, after corrupting 140/1,400 HOG objects:

| Repair/review budget | Corrupted objects among selected | Uniform-random expectation |
|---:|---:|---:|
| 25 | **68%** | 10% |
| 50 | **54%** | 10% |
| 100 | **37%** | 10% |
| 140 | **33.6%** | 10% |

This suggests a path toward **semantic backfill on demand**: re-embed or inspect the small set of objects that maximally reduces uncertified semantic surface instead of blindly recomputing every vector.

The current greedy is a baseline. A real research version should compare submodular selection, active learning, uncertainty reduction and cost-aware planning.

## Minimal Semantic ABI example

```python
from semantic_atlas import (
    SemanticABIGate,
    contract_from_labels,
    plan_repairs,
)

contract = contract_from_labels(
    legacy_vectors,
    domain_labels,
    anchors=critical_ids,
)

legacy_report = contract.audit(legacy_vectors, implementation="legacy")
new_report = contract.audit(new_vectors, implementation="new-model")

# Region-wise deployment decision.
gate = SemanticABIGate(
    {
        "legacy": (legacy_report, legacy_vectors),
        "new-model": (new_report, new_vectors),
    },
    max_local_risk=0.15,
)

decision = gate.choose(
    {
        "legacy": legacy_query_vector,
        "new-model": new_query_vector,
    },
    prefer=("new-model", "legacy"),
)

# Spend a limited re-embedding/review budget where it matters most.
repair_plan = plan_repairs(new_report, new_vectors, limit=100)
```

## Cross-model example

```python
from semantic_atlas import FabricRecord, SemanticFabric, SpaceSpec

fabric = SemanticFabric(chart_size=64, graph_k=10)
fabric.add_space(SpaceSpec("legacy", 1536, version="encoder-v1"))
fabric.add_space(SpaceSpec("next", 1024, version="encoder-v2"))

fabric.add(FabricRecord("doc-1", {"legacy": legacy_vector_1}))
fabric.add(FabricRecord("doc-2", {"legacy": legacy_vector_2, "next": next_vector_2}))

fabric.fit_bidirectional("legacy", "next", anchor_ids=paired_anchor_ids, chart_size=32)
fabric.build()

hits = fabric.search(next_query, query_space="next", top_k=10)
virtual_next = fabric.materialize_virtual_space(
    "next",
    min_cell_confidence=0.85,
    min_transport_confidence=0.80,
)
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python benchmarks/coordinate_fabric_benchmark.py
```

Real-data benchmarks:

```bash
pip install -e '.[bench]'
python benchmarks/digits_coordinate_benchmark.py
python benchmarks/semantic_abi_digits_benchmark.py
```

For precomputed paired embeddings from real neural encoders:

```bash
python benchmarks/npz_upgrade_benchmark.py pair.npz --anchor-fraction 0.10 --k 10
```

## Scientific posture

This is a **falsifiable research program**, not a claim that the repository has already revolutionized vector databases.

The prior-art pass materially narrowed our claims: SIGMOD/ICML work already covers important aspects of cross-model vector integration, local consistency, composable translation and embedding independence. That is why Semantic ABI is deliberately framed above coordinate translation rather than renaming existing work.

The project should be simplified or killed if:

- Semantic ABI predicts downstream failures no better than ordinary held-out evaluation;
- useful contracts require near-corpus-scale annotation;
- local risk is poorly calibrated;
- active repair does not beat simple/random backfill policies economically;
- SCF translation adds complexity without meaningful migration value on real model pairs.

## Research documents

- [`docs/SEMANTIC_ABI.md`](docs/SEMANTIC_ABI.md) — current strongest research hypothesis
- [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) — corrected prior-art map and non-claims
- [`docs/SEMANTIC_FABRIC.md`](docs/SEMANTIC_FABRIC.md) — coordinate-fabric theory
- [`docs/SEMANTIC_COORDINATE_PROTOCOL.md`](docs/SEMANTIC_COORDINATE_PROTOCOL.md) — portable coordinate protocol draft
- [`docs/BENCHMARKS_V2.md`](docs/BENCHMARKS_V2.md) — falsification protocol
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — trust boundaries
- [`docs/RESEARCH.md`](docs/RESEARCH.md) — Phase 0 research basis
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — original SMA architecture
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — evidence-gated roadmap
