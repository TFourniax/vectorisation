# Semantic Manifold Atlas / Semantic ABI

**Research toward an evidence-gated semantic change-control layer that can outlive any one embedding model, vector database or retrieval implementation.**

> A vector is not meaning. It is one representation emitted by one implementation at one point in time.

The project started as an experiment in topology-aware vector retrieval. The strongest surviving direction is now broader:

```text
stable logical objects
        |
   Semantic ABI
(versioned invariants)
        |
  SemanticOracle
 dense / sparse / graph / hybrid / remote
        |
 audit + support + risk
        |
 rollout / fallback / repair
        |
 reproducible release evidence
```

The intended role is **above** mature retrieval/index engines such as Qdrant, HNSW, DiskANN, pgvector, Elasticsearch or Vespa—not to reimplement their low-level ANN work. SQL remains appropriate for transactions, constraints, metadata and logical identity.

**Current source of truth:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md). It records what is implemented, what has real evidence, what has been falsified, and the next research gates.

## What currently survives the evidence

### Semantic ABI

`SemanticContract` expresses coordinate-free requirements over stable logical IDs:

- ordinal assertions such as `A must prefer B over C`;
- critical-neighborhood survival;
- reciprocal-neighbor relations;
- hard/soft requirements, weights and provenance;
- canonical SHA-256 identity, contract linting and a hash-chained history.

Application semantics are deliberately separate from legacy-behavior compatibility. A new retriever may change old rankings substantially while preserving the meaning the application actually requires.

### Representation-independent `SemanticOracle`

The contract does not require vectors. Implementations expose stable-ID membership, affinity and neighborhoods through `SemanticOracle`.

Current adapters include dense cosine vectors and arbitrary callbacks for sparse, graph, hybrid or remote systems.

A real SciFact benchmark now audits the **exact same 650-clause contract digest** against both BGE dense embeddings and a lexical BM25 sparse ranker. BGE scores about **0.9467** on the ABI; BM25 **0.8913**, with all 650 clauses evaluated and zero missing clauses.

### Support-aware selective rollout

The runtime distinguishes:

1. contract score;
2. logical-object/contract coverage;
3. local support / OOD evidence;
4. proxy risk;
5. statistical rollout certification.

A candidate can therefore serve only a certified region with fallback elsewhere instead of relying on one global model switch.

### Statistical certification baselines

Two auditable methods are implemented:

- `calibrate_semantic_risk()` — split selection/certification with a family of thresholds and union-corrected Chernoff/KL bounds;
- `calibrate_semantic_risk_preregistered()` — selection freezes one threshold before certification labels are inspected, then an exact one-sided binomial bound certifies that one rule.

On SciFact, both methods refuse a 10% failure SLA. At **15%**, the simultaneous family remains uncertified, while the pre-registered exact rule certifies an upper bound of about **13.16%**. On 200 held-out queries it accepts **98.5%** and observes about **10.15%** failures in the accepted region.

These are statistical baselines, not new statistical theory; see [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

### Progressive Semantic Audit

A fixed tiny subset of clauses proved too fragile. The current scalable direction instead audits the **entire contract probabilistically**:

- every hard clause is always evaluated;
- soft clauses are sampled proportional to weight;
- repeated samples reuse cached oracle evaluations;
- exact binomial bounds with a predeclared error budget allow early PASS/FAIL;
- ambiguous cases fall back to the exhaustive audit.

On a real Digits benchmark with **1,500 clauses**, 15 scenario/SLA decisions matched the exhaustive audit **15/15**. Twelve decisions stopped early and evaluated on average only **7.17% of unique clauses**; near-boundary cases correctly fell back to 100%.

This policy controls a weighted soft-clause **violation-rate SLA**; it is intentionally distinct from the historical aggregate contract score.

### Semantic Diff, mutation adequacy and active repair

The change-management loop also includes:

- `semantic_diff()` — finds representation disagreements and proposes high-value human/domain questions;
- semantic mutation testing — deliberately injects failures to measure contract adequacy;
- sparse repair planning — prioritizes review/re-embedding where known semantic risk is concentrated;
- `SemanticReleaseCertificate` — binds implementation identity, preprocessing, contract digest, risk certificate and evidence hashes into a reproducible release artifact.

On Digits, the top 25 Semantic Diff questions were label-resolvable **68%** of the time versus about **11.7%** across all disagreements. In a deliberate 10% corruption experiment, the first 25 repair candidates were truly corrupt **68%** of the time versus a 10% random expectation. These remain mechanism results, not production guarantees.

## What was falsified or narrowed

Negative results are first-class evidence in this repository.

### Local cross-model translation is not generally better

On a real BGE→MiniLM SciFact migration, target-neighbor overlap@10 is:

- global map: **0.4745**;
- local atlas: **0.3680**.

Held-out validation also favors global, so `EvidenceGatedTransition` correctly selects the simpler global map. Local SCF is therefore an optional expert that must earn its complexity on held-out data.

### Fixed Semantic Witness sparsification is not solved

A 1,500-clause contract compressed to 10 clauses retained only **62.5%** of held-out regressions. Larger fixed subsets reached 100% sensitivity but produced large false-positive rates. Random same-size subsets remain competitive on the overall trade-off.

The witness module remains a research baseline and is **not** part of the public top-level API.

### Learned fixed Diagnostic Panels overfit object-local faults

A discriminative panel achieved perfect training separation and then **0% held-out regression recall** across budgets 5–100 clauses. It is retained only as a falsified research experiment, not promoted as an API.

These failures motivated Progressive Semantic Audit: do not pretend omitted clauses are universally redundant; sample the full weighted semantic surface and attach the shortcut to an explicit statistical error budget.

## Semantic Manifold Atlas and Coordinate Fabric

The earlier research kernels remain useful supporting machinery.

**SMA** includes overlapping local charts, mutual-kNN topology, hubness/density diagnostics, CSLS-inspired ranking, local intrinsic dimension and `bridge`/`boundary` queries. Its synthetic black-hole stress test improves precision@10 from **0.6300 → 0.8519** while removing injected hubs from the top results. This is a mechanism test, not a universal ANN superiority claim.

**SCF** includes global/local cross-space transitions, held-out diagnostics, cycle consistency, partial-migration fusion, semantic cells, virtual target-space materialization and representation drift/fault lines. Cross-model translation/local-composable methods have substantial 2025–2027 prior art; SCF is migration machinery, not the core novelty claim.

## Minimal usage

```python
from semantic_atlas import (
    CallbackSemanticOracle,
    SemanticContract,
    TripletClause,
    audit_contract,
    progressive_semantic_audit,
)

contract = SemanticContract("product-semantics", "1").add(
    TripletClause("query:refund", "doc:refund-policy", "doc:careers", hard=True)
)

oracle = CallbackSemanticOracle(
    object_ids=frozenset({"query:refund", "doc:refund-policy", "doc:careers"}),
    similarity_fn=my_similarity,
    neighbors_fn=my_neighbors,
    implementation="candidate-retriever",
)

full_report = audit_contract(contract, oracle)

# For large contracts: every hard clause remains exhaustive; soft clauses may
# stop early only when the statistical SLA permits it.
progressive = progressive_semantic_audit(
    contract,
    oracle,
    max_soft_violation_rate=0.05,
    delta=0.05,
)
```

## Validation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
```

Real-data mechanism benchmarks:

```bash
pip install -e '.[bench]'
python benchmarks/semantic_abi_digits_benchmark.py
python benchmarks/semantic_diff_digits_benchmark.py
python benchmarks/semantic_mutation_digits_benchmark.py
python benchmarks/semantic_progressive_audit_digits_benchmark.py
```

Heavy neural/SciFact evidence runs in the isolated GitHub Actions workflow `.github/workflows/real-encoder.yml` so public models are not downloaded on every commit.

## Scientific posture

This repository is a **falsifiable research program**, not a claim that Semantic ABI is already a standard or that the project has revolutionized retrieval infrastructure.

The project should be narrowed or killed if representative experiments show that:

- Semantic ABI predicts regressions no better than ordinary held-out evaluation;
- representation independence collapses outside the current dense↔sparse test;
- useful contracts require near-exhaustive human annotation;
- support/risk certification produces negligible useful coverage;
- Progressive Semantic Audit saves little work at realistic contract scales;
- active repair does not improve certified-coverage-per-cost versus simple backfill;
- the complete abstraction provides little beyond conventional regression suites.

## Documentation

- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) — **authoritative dated research status and evidence**
- [`docs/SEMANTIC_ABI.md`](docs/SEMANTIC_ABI.md) — Semantic ABI and change-control model
- [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) — prior art, narrowed claims and non-claims
- [`docs/BENCHMARKS_V2.md`](docs/BENCHMARKS_V2.md) — falsification/evidence protocol
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — next evidence gates
- [`docs/SEMANTIC_FABRIC.md`](docs/SEMANTIC_FABRIC.md) — cross-coordinate migration research
- [`docs/SEMANTIC_COORDINATE_PROTOCOL.md`](docs/SEMANTIC_COORDINATE_PROTOCOL.md) — transition interchange draft
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — trust boundaries
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — original SMA architecture

The repository is moving to machine-enforced evidence freshness through `docs/evidence-manifest.json`: benchmark claims are tied to workflow artifacts and the Git blobs of the code that produced them, so modifying evidence-sensitive code makes the documented proof stale until it is regenerated.
