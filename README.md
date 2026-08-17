# Semantic Manifold Atlas / Semantic ABI

**Research toward an evidence-gated semantic change-control layer that can outlive any one embedding model, vector database or retrieval implementation.**

> A vector is not meaning. It is one representation emitted by one implementation at one point in time.

The project started as an experiment in topology-aware vector retrieval. The strongest surviving direction is now broader:

```text
stable logical objects
        |
 Application Semantic Contract
  (portable normative invariants)
        |
  SemanticOracle
 dense / sparse / graph / hybrid / remote
        |
 Contract Conformity
        |
 +------+-----------------------+
 |                              |
Contract Adequacy         Implementation Integrity
(is the contract           (canaries for one concrete
observant enough?)          implementation)
 |                              |
 +-------------+----------------+
               |
       support + risk
               |
       rollout / fallback
               |
       repair / re-audit
               |
        release evidence
```

The intended role is **above** mature retrieval/index engines such as Qdrant, HNSW, DiskANN, pgvector, Elasticsearch or Vespa—not to reimplement their low-level ANN work. SQL remains appropriate for transactions, constraints, metadata and logical identity.

**Current source of truth:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md). It records what is implemented, what has real evidence, what has been falsified and which experiments are still pending.

## The key correction: conformity is not adequacy

`SemanticContract` expresses coordinate-free requirements over stable logical IDs. A candidate **conforms** when it satisfies those clauses.

The latest real neural repair experiment exposed an important limitation: a contract can recover its clean ABI score while held-out retrieval quality is still damaged outside the contract's observed surface. A high conformity score therefore does **not** prove that the contract itself is adequate for a broader claim.

`ContractAdequacyEvidence` / `ContractAdequacyReport` now separate those questions. Adequacy may include:

- logical-object coverage;
- mutation sensitivity/localization;
- predictive association with held-out outcomes;
- predictive lift over an ordinary validation baseline;
- number of independent cases, datasets and fault families.

There is intentionally **no hidden universal passing score**. Applications must declare adequacy requirements explicitly; missing evidence remains `insufficient_evidence`.

## Representation-independent Semantic ABI

The contract can contain:

- ordinal assertions such as `A must prefer B over C`;
- critical-neighborhood survival;
- reciprocal-neighbor relations;
- hard/soft requirements, weights and provenance;
- canonical SHA-256 identity, linting and hash-chained history.

`SemanticOracle` means the audit engine does not require vectors. Implementations expose stable-ID membership, affinity and neighborhoods.

A real SciFact benchmark audits the **exact same 650-clause contract digest** against both BGE dense embeddings and a lexical BM25 sparse ranker:

| implementation | Semantic ABI | nDCG@10 | Recall@10 |
|---|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 |

BM25 evaluates 650/650 clauses with zero missing clauses. This is the first real cross-paradigm portability evidence; it is not universal proof across every representation family.

## Selective rollout and finite-sample risk

The runtime distinguishes:

1. contract conformity;
2. contract/object coverage;
3. local support/OOD evidence;
4. proxy risk;
5. statistical rollout certification.

Two auditable risk-control baselines are implemented. On SciFact, both correctly refuse a 10% failure SLA. At **15%**, a rule selected entirely before the independent certification labels are inspected passes an exact one-sided binomial bound: upper risk about **13.16%**. On 200 held-out queries it accepts **98.5%** and observes about **10.15%** failures in the accepted region.

These procedures are baselines, not claims of new statistical theory; Learn-Then-Test, adaptive/sequential testing and conformal/selective risk control are explicit prior art/baselines.

## Progressive Semantic Audit

Fixed deterministic contract compression failed on held-out localized faults. The scalable direction now keeps the **full contract normative** and reduces evaluation cost probabilistically:

- every hard clause is always evaluated;
- soft clauses are sampled proportional to weight;
- repeated draws reuse cached oracle evaluations;
- finite-sample bounds are checked at predeclared looks;
- ambiguous cases fall back to exhaustive audit.

### Real Digits result

On a 1,500-clause contract, 15 scenario/SLA decisions match exhaustive audit **15/15**. Twelve terminate early; those early decisions inspect on average **7.17% of unique clauses**.

### Scale result

On procedural weighted contracts of 10k, 100k and 250k clauses:

- exact decision agreement: **10/10**;
- early decisions: **9/10**;
- the deliberately boundary-adjacent case falls back to full audit.

Away from the boundary, examples include:

- 100k healthy contract: PASS after **200 unique clauses (0.20%)**;
- 100k 20%-violation case: FAIL after **100 (0.10%)**;
- 250k healthy: PASS after **200 (0.08%)**;
- 250k ~20%-violation: FAIL after **100 (0.04%)**.

This validates the sampling mechanics and an important scaling property: far from the SLA boundary, decision cost can be driven more by statistical margin than total contract size. It does **not** prove production semantic faults follow the procedural distribution.

## Active repair: strong enrichment, incomplete recovery

A real SciFact/BGE experiment deliberately permutes 5% or 10% of 1,800 document embeddings, then restores only the documents selected by a bounded repair planner.

For 10% corruption:

- corrupted ABI falls to about **0.8429**;
- held-out nDCG falls from **0.7875 → 0.6970**.

At budget 25:

- the cost-aware coverage planner selects **88% truly corrupted documents**;
- it recovers about **33.9%** of lost nDCG;
- random finds about **7.3%** corruption and recovers only about **1.5%**.

At budget 180, targeted repair reaches about **50%** nDCG recovery versus roughly **9%** for random.

But **none of the tested methods reaches 90% downstream recovery**, and application-contract conformity can saturate before held-out nDCG is fully repaired. That negative result is why contract adequacy is now a first-class concept.

## Application semantics vs implementation integrity

A second repair experiment keeps portable application truth separate from **implementation-specific integrity canaries** built from the clean BGE document graph, without test qrels.

Document coverage rises from:

- application-only: **32.3%**;
- + random integrity anchors: **67.0%**;
- + coverage-oriented integrity anchors: **72.5%**.

For 10% corruption, best nDCG recovery at budget 100 improves from about **62.3%** with application-only diagnosis to about **70.2–70.8%** with integrity canaries. At budget 180, coverage-oriented integrity reaches about **71.2%**.

This supports a typed architecture:

- **Application Semantic Contract** — portable normative truth;
- **Implementation Integrity Contract** — canaries for silent corruption of one concrete implementation;
- **Contract Adequacy Evidence** — evidence that the selected observation surface is sufficient for the deployment claim.

The risk fields must not simply be fused. A failed neighborhood can implicate a healthy anchor while a damaged neighbor is causal, so repair needs clause-role/incidence reasoning rather than one naive scalar risk ranking.

## Other surviving mechanisms

`semantic_diff()` finds implementation disagreements and turns them into high-value human/domain questions. On Digits, the top 25 proposed questions are label-resolvable **68%** of the time versus about **11.7%** across all disagreements.

Semantic mutation testing deliberately injects identity permutation, collapse, hub-pull and noise to measure contract adequacy. Current Digits contracts detect all tested mutation families globally; localization remains weaker.

`SemanticReleaseCertificate` binds exact implementation/preprocessing identity, contract identity, audit/risk state and evidence hashes. Generic AI attestation/certification has substantial prior art; the open question is the retrieval-specific integration with a portable semantic contract, adequacy evidence, fallback and repair.

## What was falsified or narrowed

Negative results are first-class evidence.

### Local cross-model translation is not generally better

On real BGE→MiniLM SciFact translation:

- global target-neighbor overlap@10: **0.4745**;
- local atlas: **0.3680**.

Held-out validation also favors global; `EvidenceGatedTransition` correctly selects the simpler map.

### Fixed Semantic Witness sparsification is not solved

A 1,500-clause contract compressed to 10 clauses retains only **62.5%** of held-out regressions. Larger fixed subsets reach 100% sensitivity but produce large false-positive rates. Random same-size subsets remain competitive.

### Learned fixed Diagnostic Panels overfit

A discriminative panel achieves perfect training separation then **0% held-out regression recall** across tested budgets. It is not exposed as a production API.

These failures motivated Progressive Semantic Audit rather than hiding omitted semantic surface.

## Supporting SMA / SCF machinery

**SMA** retains overlapping local charts, mutual-kNN topology, hubness/density diagnostics, CSLS-inspired ranking, intrinsic-dimension estimates and topological `bridge`/`boundary` queries. Its synthetic black-hole stress test improves precision@10 from **0.6300 → 0.8519** and removes injected hubs; this is a mechanism test, not an ANN superiority claim.

**SCF** retains global/local transitions, held-out diagnostics, cycle consistency, partial migration, virtual materialization and drift/fault-line analysis. Cross-model translation has strong 2025–2027 prior art, so SCF is supporting migration machinery rather than the primary novelty thesis.

## Minimal usage

```python
from semantic_atlas import (
    CallbackSemanticOracle,
    ContractAdequacyEvidence,
    ContractAdequacyRequirements,
    SemanticContract,
    TripletClause,
    assess_contract_adequacy,
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

conformity = audit_contract(contract, oracle)
progressive = progressive_semantic_audit(
    contract,
    oracle,
    max_soft_violation_rate=0.05,
    delta=0.05,
)

# Adequacy is a different claim and requires an explicit application policy.
adequacy = assess_contract_adequacy(
    ContractAdequacyEvidence(
        contract_digest=contract.digest,
        object_coverage=measured_coverage,
        mutation_kill_rate=mutation_score,
        predictive_correlation=heldout_correlation,
        baseline_predictive_correlation=validation_baseline,
        heldout_cases=n_heldout,
        datasets=n_datasets,
    ),
    ContractAdequacyRequirements(
        min_object_coverage=0.70,
        min_mutation_kill_rate=0.90,
        min_predictive_correlation=0.70,
        min_heldout_cases=500,
        min_datasets=3,
    ),
)
```

The example thresholds are application policy examples, **not library defaults**.

## Validation and evidence freshness

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python tools/check_evidence_freshness.py
```

Current CI covers Python 3.10/3.12/3.13 plus a separate evidence-freshness gate. Promoted benchmark claims are bound in `docs/evidence-manifest.json` to GitHub Actions artifacts and the Git blobs of evidence-sensitive source files. Changing a relevant algorithm/benchmark therefore makes its documented evidence stale until it is regenerated.

## Current highest-priority falsification gate

A multi-dataset campaign is currently running on **SciFact, NFCorpus and FiQA** across MiniLM dense, BGE dense, BM25 sparse, BGE+BM25 hybrid and controlled degradations. Contracts use official train qrels only; official test qrels remain untouched held-out evaluation.

The critical question is intentionally hard:

> **Does Semantic ABI predict held-out retrieval quality better than an ordinary train-query nDCG validation baseline?**

Portability and predictive validity are separate claims. The result will be promoted even if it narrows the ABI thesis.

## Scientific posture

This is a **falsifiable research program**, not a claim that Semantic ABI is already an industry standard or a proven patent-novel category.

The project should be narrowed if representative experiments show that:

- portable ABI compatibility adds no useful information beyond ordinary validation;
- contract adequacy requires near-exhaustive annotation/testing;
- support/risk certification has negligible useful coverage;
- progressive audit loses its sample-efficiency advantage on realistic fault distributions;
- integrity/repair economics do not beat simple baselines;
- the integrated control layer offers little beyond conventional regression suites.

## Documentation

- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md) — **authoritative dated research status**
- [`docs/evidence-manifest.json`](docs/evidence-manifest.json) — promoted/pending evidence and source hashes
- [`docs/SEMANTIC_ABI.md`](docs/SEMANTIC_ABI.md) — Semantic ABI / change-control model
- [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) — narrowed claims and explicit non-claims
- [`docs/BENCHMARKS_V2.md`](docs/BENCHMARKS_V2.md) — falsification protocol
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — evidence-gated next steps
- [`docs/SEMANTIC_FABRIC.md`](docs/SEMANTIC_FABRIC.md) — coordinate-migration research
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — trust boundaries
