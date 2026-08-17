# Semantic ABI — portable meaning contracts with explicit adequacy

## Thesis

A vector is neither the identity nor the meaning of a data object. It is one representation emitted by one implementation at one point in time.

Semantic ABI asks:

> **What must remain semantically true when a retrieval implementation changes, and how can that requirement be executed, audited and attested without depending on the implementation's coordinate system?**

v0.5 separates specification, execution and evidence:

```text
Application Semantic Contract
     portable normative truth
              |
              v
       Protocol-v1 compiler
              |
              v
 directional BatchSemanticOracleV1
 dense / sparse / hybrid / late-interaction / graph / remote
              |
      Contract Conformity
              |
     +--------+---------+
     |                  |
Contract Adequacy   Implementation Integrity
     |                  |
     +--------+---------+
              |
       support + risk
              |
       rollout/fallback
              |
       repair/re-audit
              |
      protocol attestation
```

This remains a research program, not a claim that Semantic ABI is already an industry standard or patent-novel category.

For exact evidence use [`CURRENT_STATUS.md`](CURRENT_STATUS.md), [`SEMANTIC_ABI_PROTOCOL_V1.md`](SEMANTIC_ABI_PROTOCOL_V1.md) and [`evidence-manifest.json`](evidence-manifest.json).

## 1. Application Semantic Contract

`SemanticContract` operates on stable logical IDs.

Current clause families:

- ordinal triplet: `A must prefer B over C`;
- critical-neighborhood survival;
- reciprocal-neighbor relation.

Clauses can be hard/soft, weighted and provenance-tagged. Contracts have canonical SHA-256 identity, static linting and hash-chained history.

Application semantics, captured legacy behavior and implementation-integrity canaries are intentionally different roles.

## 2. Protocol v1: representation independence becomes executable interoperability

The old `SemanticOracle` proved that an audit need not consume vectors, but its in-process API still named `similarity(left,right)` and did not define a deployment boundary.

v0.5 introduces `Semantic ABI Oracle Protocol v1`:

```text
contains_many(ids)
score_many([(anchor, candidate), ...])
neighbors_many([(anchor, k), ...])
```

`score(anchor,candidate)` is explicitly **directional**. Symmetry is never assumed unless an implementation manifest claims it.

That permits the same contract vocabulary to cover:

- dense cosine retrievers;
- sparse BM25-like rankers;
- hybrid rankers;
- ColBERT/MaxSim late interaction;
- typed graph/relation scorers;
- proprietary remote services.

### Compiler

`compile_contract()` converts the full contract into a canonical `ContractExecutionPlan` containing only unique:

- logical object checks;
- directional pair scores;
- top-k requests.

Repeated clauses reuse backend operations. This is an execution optimization, **not contract compression**.

### Wire boundary

Protocol v1 has an OpenAPI 3.1 reference, remote HTTP client, framework-neutral dispatcher, CLI and language-neutral TCK. A provider can implement the wire contract without importing the Python research engine.

### Compatibility and conformance

`check_plan_compatibility()` can reject unsupported typed operations before execution. `check_oracle_conformance()` verifies ID stability, deterministic behavior when declared, top-k prefix consistency, finite scores and rank/score coherence, without imposing symmetry on asymmetric implementations.

## 3. Real late-interaction proof

The v0.5 gate uses real `lightonai/colbertv2.0` multi-vector representations on SciFact with PyLate/Voyager retrieval and MaxSim scoring.

- 1,800 documents;
- 300 train queries for contract authoring;
- 200 untouched test queries;
- 600 application clauses;
- contract digest `d3dd26211a7a18c8ae8ec07be4e0bcd8e1805024fb8dcd4a67d71506627e1843`.

The exact same digest executes against BM25 and ColBERT:

| implementation | ABI | nDCG@10 | Recall@10 | missing clauses |
|---|---:|---:|---:|---:|
| BM25 sparse | **0.9067** | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | **0.9047** | **0.7337** | **0.8395** | **0** |

ColBERT passes **660/660 Protocol-v1 conformance checks**, zero issues and all hard clauses. Its manifest declares asymmetric `maxsim-sum` scoring.

The compiler collapses the 600-clause audit into:

- 805 object membership checks;
- 600 unique directional score pairs;
- 300 top-k requests;
- **3 backend batch operation families**.

This is evidence that the ABI can cross a materially different retrieval algebra without common coordinates or contract translation. It is not evidence of general ColBERT superiority and not a novelty claim for MaxSim, ANN, OpenAPI or RPC.

## 4. State-bound incremental execution

A protocol is operationally weak if every contract revision requires recomputing every observation.

`execute_contract_plan_incremental()` reuses an earlier snapshot only when:

- the oracle is deterministic;
- it declares `metadata.state_digest`;
- the entire current manifest digest equals the prior snapshot manifest digest;
- the prior snapshot belongs to the prior execution plan.

It may reuse unchanged membership, exact pair scores, exact top-k results and a larger previous top-k as a prefix for a smaller request. Everything else is fetched as a delta.

A changed model/index/state invalidates reuse. No state digest means no cross-audit cache.

## 5. Protocol attestation

`SemanticProtocolAttestation` binds:

- contract digest;
- oracle manifest digest;
- execution-plan digest;
- observed snapshot digest;
- protocol audit digest;
- conformance result;
- optional adequacy result;
- optional risk certificate;
- external evidence hashes.

The envelope is tamper-evident, not itself a digital signature. Production systems can sign its digest with KMS/PKI.

Deployment eligibility is explicit, never inferred from attractive metrics: current rules require certified status, protocol conformance, hard-clause pass, zero missing clauses, adequate contract evidence and positive risk certification.

## 6. Conformity is not adequacy

A `ContractReport` answers whether an implementation satisfies **the clauses that exist**. It cannot prove the clauses are sufficient for the release claim.

Real neural repair found states where ABI conformity approached clean values while held-out nDCG remained damaged.

`ContractAdequacyEvidence` therefore keeps separate axes such as:

- object coverage;
- mutation kill/localization;
- independent predictive association;
- comparison with ordinary validation;
- held-out case count;
- dataset count;
- fault-family count.

There are deliberately no universal passing thresholds. Application/release policy must declare them; missing required evidence remains `insufficient_evidence`.

## 7. ABI does not replace nDCG

A preregistered SciFact/NFCorpus/FiQA campaign compared Semantic ABI with ordinary train-query nDCG for predicting untouched test nDCG across dense, sparse, hybrid and controlled-degradation variants.

| metric | ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman | **0.9697** | **0.9757** |
| pooled delta Spearman | **0.9573** | **0.9724** |
| pooled delta Pearson | **0.9519** | **0.9850** |

**No general predictive superiority.** Ordinary IR evaluation remains mandatory. Semantic ABI's differentiated claim is specification/change-control, not aggregate benchmark replacement.

## 8. Progressive audit and selective rollout

The full contract remains normative. Progressive Audit samples weighted soft clauses only to reduce execution cost, always checks hard clauses, and falls back to exhaustive audit when statistical evidence is insufficient.

Evidence:

- 1,500 clauses: 15/15 exact decisions, 12/15 early;
- 10k/100k/250k procedural contracts: 10/10 decisions, 9/10 early;
- representative 250k cases away from the SLA boundary inspect ~0.04–0.3992% of clauses.

Selective SciFact/BGE risk evidence has AUC ~0.7875; current methods reject a 10% failure SLA and a preregistered exact rule certifies 15% with 98.5% accepted held-out traffic and ~10.15% realized accepted risk.

These are transparent statistical baselines; sequential/LTT/conformal risk control is established prior art.

## 9. Implementation integrity and repair

Targeted repair on 10% corrupted SciFact/BGE document embeddings strongly enriches corrupted documents over random, but no tested planner reaches the preregistered 90% downstream-recovery target.

Implementation canaries increase observed document coverage from 32.3% application-only to 67.0%/72.5% and improve repair, but remain implementation-specific diagnostics rather than portable application semantics.

A fixed role-weighted clause-incidence planner looked strong on its development fault but failed independent validation across new permutation/noise/collapse/hub faults: mean recovery ~0.215 vs ~0.237 best baseline, lift ~-0.022, wins/ties 2/4. It is not promoted.

## 10. Negative results that shaped the architecture

- local BGE→MiniLM SCF mapping loses to global;
- fixed Semantic Witness does not robustly dominate random;
- learned fixed Diagnostic Panel overfits and gets 0% held-out regression recall;
- ABI is not a generally better nDCG predictor than ordinary validation;
- current repair does not recover 90% downstream quality;
- fixed-prior repair attribution does not generalize.

These are retained as first-class evidence.

## 11. Relationship to SCF

SCF remains supporting coordinate-migration machinery. It answers whether queries/observations can be transported during a representation migration.

Protocol v1 answers a different, broader question: whether **the semantic requirements themselves** can execute above unrelated retrievers without sharing a coordinate algebra.

This distinction matters because close prior art already exists for cross-model embedding translation; v0.5 does not rely on translation novelty.

## 12. Next research gates

1. real Elasticsearch/Qdrant/pgvector/Vespa adapters behind Protocol v1;
2. an external Rust/Go/TypeScript TCK implementation proving language independence;
3. a typed graph/relation retriever as the next distinct scoring algebra;
4. adequacy under multilingual/domain/temporal/rare-slice shift;
5. Progressive Audit vs Adaptive Learn-Then-Test/e-process baselines;
6. signed/expiring/revocable attestations and provider-state governance;
7. contract-acquisition economics with humans;
8. professional novelty/IP review before strong claims.

## Kill / narrow rule

Semantic ABI should collapse toward ordinary regression tooling if representative deployments show that portable hard invariants, explicit adequacy, cross-provider execution, selective fallback or attested change control add little operational value beyond conventional benchmark suites.

The objective is not to defend the phrase **Semantic ABI**. The objective is to determine whether a portable, executable semantic interface can make retrieval changes materially safer, cheaper and more auditable.