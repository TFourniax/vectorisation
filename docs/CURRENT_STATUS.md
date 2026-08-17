# Current research status

**Status date:** 2026-08-17  
**Package:** `semantic-manifold-atlas` **0.5.0**  
**Branch:** `agent/semantic-manifold-atlas`  
**Posture:** evidence-gated research; draft PR; no production-readiness or broad patent-novelty claim.

This is the authoritative dated summary. Promoted positive **and negative** evidence is bound to exact workflows, artifacts and evidence-sensitive Git blobs in [`evidence-manifest.json`](evidence-manifest.json).

## Major v0.5 advance — Semantic ABI Oracle Protocol v1

The project has crossed an architectural boundary: Semantic ABI is no longer only a Python-level coordinate-free audit abstraction. It now has a **compiled, directional, batchable, remotely executable protocol** for heterogeneous retrieval systems.

```text
Application Semantic Contract
        |
        v
compile_contract()
        |
ContractExecutionPlan
(deduplicated IDs / directional scores / top-k requests)
        |
        +--> compatibility preflight
        |
        v
Semantic ABI Oracle Protocol v1
contains_many / score_many / neighbors_many
        |
        +--> dense
        +--> sparse / BM25
        +--> hybrid
        +--> late interaction / MaxSim
        +--> graph / provider adapters
        +--> remote HTTP/service
        |
        v
OracleSnapshot + Contract Conformity
        |
        +--> Contract Adequacy
        +--> conformance suite
        +--> support/risk + selective rollout
        +--> implementation integrity / repair
        +--> protocol attestation
```

The primitive is **directional `score(anchor, candidate)`**, not cosine or a symmetric `similarity`. This matters for BM25, ColBERT/MaxSim, typed graph traversal, hybrid rankers and proprietary remote retrievers.

### Protocol/compiler capabilities

Implemented in v0.5:

- `OracleManifest`: implementation identity, scoring semantics/directionality, capabilities, determinism and provider metadata with canonical digest;
- `compile_contract()`: deduplicates the full contract into stable logical-ID checks, directional pair scores and top-k requests;
- `execute_contract_plan()`: one batch per operation family rather than one backend call per clause;
- `OracleSnapshot`: tamper-evident observed execution state;
- `audit_contract_v1()`: preserves existing Semantic Contract clause semantics over the directional protocol;
- `RemoteSemanticOracleV1` + framework-neutral dispatcher + stdlib HTTP reference transport;
- OpenAPI 3.1 specification: `spec/semantic-abi-oracle-v1.openapi.yaml`;
- CLI: `semantic-abi plan`, `remote-audit`, `remote-conformance`;
- `check_oracle_conformance()`: deterministic/top-k/ID/score checks without imposing symmetry on asymmetric systems;
- `check_plan_compatibility()`: typed/capability preflight before backend execution;
- state-bound incremental execution: safely reuses unchanged observations only when the complete oracle manifest/state digest is unchanged;
- `SemanticProtocolAttestation`: binds contract, backend manifest, execution plan, snapshot, audit, conformance and optional adequacy/risk evidence;
- language-neutral TCK with canonical contract/plan/manifest/snapshot/audit digests.

The standard CI exercises these mechanisms on Python 3.10/3.12/3.13.

## Real late-interaction gate — PASSED

The central v0.5 empirical gate uses public SciFact and real `lightonai/colbertv2.0` multi-vector representations through PyLate/Voyager + MaxSim.

Protocol:

- **1,800 documents**;
- **300 train queries** for contract construction;
- **200 untouched test queries** for downstream retrieval metrics;
- **600-clause application contract**;
- contract digest: `d3dd26211a7a18c8ae8ec07be4e0bcd8e1805024fb8dcd4a67d71506627e1843`;
- test qrels are not used to author the contract.

The **same contract digest** executes unchanged against lexical BM25 and real asymmetric ColBERT late interaction.

| implementation | ABI | nDCG@10 | Recall@10 | missing |
|---|---:|---:|---:|---:|
| BM25 sparse | **0.9067** | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | **0.9047** | **0.7337** | **0.8395** | **0** |

ColBERT also:

- passes all hard clauses;
- passes **660/660 Protocol-v1 conformance checks with zero issues**;
- declares `score_directionality=asymmetric`, `score_semantics=maxsim-sum`;
- audits **805 logical IDs + 600 directional score pairs + 300 top-k requests** using only **3 batch operation families**;
- has manifest digest `6b112c18cc879232e6a1464034068ac27b7098ea7e781cfcbf84db6c0887e0bc`.

### What this proves — and what it does not

This is strong evidence that one Semantic Contract can survive a change from a lexical sparse scorer to a real multi-vector late-interaction scorer **without common coordinates, symmetric distance or contract translation**.

It does **not** establish that ColBERT is generally better than BM25, that the protocol is an industry standard, or that MaxSim/RPC/OpenAPI/batching are novel inventions. The promoted claim is narrower: **portable semantic change control can cross a materially different retrieval algebra through the same compiled contract interface.**

## Conformity is not adequacy

`ContractReport` answers whether a candidate satisfies the clauses that exist. It cannot prove that the contract observes every downstream failure mode.

Real neural repair exposed states where application conformity returned near its clean value while held-out nDCG remained damaged. Therefore v0.5 keeps these separate:

- **Conformity:** candidate vs declared clauses;
- **Adequacy:** is the contract/test surface sufficient for the release claim?;
- **Implementation Integrity:** is one concrete implementation/index silently damaged?;
- **Risk certification:** where may a candidate safely serve?;
- **Attestation:** what exact contract/backend/evidence produced the release decision?

`ContractAdequacyEvidence` can include coverage, mutation kill/localization, predictive association, baseline comparison, held-out count, datasets and fault families. Missing required evidence remains `insufficient_evidence`; there is no hidden universal adequacy threshold.

## Predictive-validity falsification retained

A separate preregistered SciFact/NFCorpus/FiQA campaign asked whether Semantic ABI predicts held-out nDCG better than ordinary train-query nDCG across dense, sparse, hybrid and controlled-degradation variants.

| metric | Semantic ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman → test nDCG | **0.9697** | **0.9757** |
| pooled delta Spearman vs BGE | **0.9573** | **0.9724** |
| pooled delta Pearson | **0.9519** | **0.9850** |
| pooled pairwise concordance | **0.9172** | **0.9400** |

**Conclusion:** Semantic ABI is not a replacement for nDCG/Recall validation. Its surviving value proposition is normative/operational: portable hard invariants, heterogeneous execution, adequacy, local support/risk, fallback, integrity and change governance.

## Progressive Semantic Audit

The full contract remains normative. Hard clauses are exhaustive; weighted soft clauses may be sampled with predeclared statistical looks and exact fallback.

Evidence:

- Digits, 1,500 clauses: **15/15** exact decisions, **12/15** early, mean early unique-clause fraction **7.17%**;
- procedural 10k/100k/250k: **10/10** exact decisions, **9/10** early;
- representative 250k away-from-boundary cases inspect about **0.04–0.3992%** of clauses.

This is a scaling/mechanism result. Sequential testing has substantial prior art; the open question is operational value when attached to a portable Semantic Contract.

## Selective rollout

On SciFact/BGE, support-aware failure-ranking AUC is **0.7875**. Current methods reject a 10% failure SLA. A rule frozen before independent certification labels are inspected certifies 15% with:

- empirical certification risk **8.05%**;
- exact upper bound **13.159%**;
- held-out acceptance **197/200 = 98.5%**;
- realized accepted risk **10.15%**.

These are transparent statistical baselines, not new statistical theory.

## Repair / integrity — useful but not solved

SciFact/BGE 10% document-embedding corruption:

- clean nDCG **0.7875**;
- corrupted ~**0.6970**;
- at budget 25, coverage planner selects **88% actually corrupted documents** and restores ~**33.9%** of lost nDCG;
- random selects ~**7.3%** corrupted and restores ~**1.5%**.

No tested planner reaches the preregistered **90% downstream recovery** target.

Implementation-specific canaries, built without test qrels, raise observed document coverage from **32.3%** application-only to **67.0%** random-integrity and **72.5%** coverage-oriented integrity, and improve larger-budget repair — but still not to 90%.

### Clause-incidence repair — independent gate FAILED

A fixed role-weighted planner looked strong on the development corruption, then was frozen and tested on four unseen fault families: new-seed permutation, Gaussian noise, local collapse and hub pull.

Predeclared budget-50 gate: +0.05 mean lost-nDCG recovery over best baseline and ≥3/4 wins/ties.

Observed:

- incidence mean recovery ~**0.215**;
- best baseline ~**0.237**;
- lift ~**-0.022**;
- wins/ties **2/4**.

**Not promoted.** The anchor-vs-neighbor attribution problem is real, but fixed blame priors do not generalize enough. Future repair attribution must be learned/structural with untouched fault families for validation.

## Other retained falsifications

- real BGE→MiniLM local SCF translation loses to global: target-neighbor overlap@10 **0.3680 vs 0.4745**;
- fixed Semantic Witness does not robustly dominate random subsets;
- learned fixed Diagnostic Panel gets perfect training separation then **0% held-out regression recall**;
- ABI aggregate predictive superiority over ordinary validation is not supported;
- current repair does not restore 90% downstream quality;
- fixed-prior clause-incidence repair does not generalize.

Negative evidence remains first-class because it removes unjustified complexity.

## Evidence / CI discipline

CI covers Python **3.10 / 3.12 / 3.13**, full pytest, the hubness regression benchmark and `evidence-freshness`.

The new late-interaction proof is promoted in `evidence-manifest.json` with:

- workflow run **32039368503**;
- artifact `semantic-abi-late-interaction-scifact-v1`;
- artifact SHA-256 `032067da95c6eab107d0300c98b93c5e8331a1da5e1ecbeae64483a963add68f`;
- exact source blob identities for the benchmark, protocol/compiler, MaxSim adapter, conformance, contract builder and workflow.

Changing any pinned source makes the evidence stale until regenerated.

## Claims explicitly not made

The repository does not claim that it replaces SQL; that 3-D coordinates are semantic truth; that SMA universally beats mature ANN engines; that SCF invented embedding translation; that local mapping is generally superior; that Semantic ABI replaces ordinary IR metrics; that high conformity proves adequacy; that current repair is complete; that ColBERT/MaxSim/OpenAPI/RPC/batching/sequential testing/AI attestation were invented here; or that the project is already production-ready or legally patent-novel.

## Highest-value next gates after v0.5

1. **Real provider/back-end adapters:** Elasticsearch, Qdrant, pgvector and Vespa behind Protocol v1, measuring latency/cost and verifying no ANN rebuild is required by the control plane.
2. **External-language conformance:** implement the TCK in Rust/Go/TypeScript and prove digest/wire interoperability independently of the Python package.
3. **Graph retrieval:** execute the same application contract on a typed graph/relation scorer, the next genuinely different algebra after sparse/dense/late-interaction.
4. **Adequacy under shift:** multilingual, domain, temporal and rare/high-criticality slices.
5. **Progressive Audit vs Adaptive Learn-Then-Test/e-processes** under realistic non-iid fault structures and heterogeneous backend costs.
6. **Release governance:** signed attestations, expiry/revocation, provider state digests and independent verification.
7. **Human contract-acquisition economics:** judgments/regressions caught per expert-minute.
8. **Professional novelty/IP search** before strong publication/patent claims.

## Current assessment

v0.5 is a **major technical advance** because the core research thesis is now an executable interoperability boundary rather than only a conceptual abstraction:

> **A stable Semantic Contract can be compiled, transported, audited and attested across replaceable retrieval implementations — including a real asymmetric multi-vector ColBERT system — while keeping adequacy and deployment evidence explicit.**

The next challenge is no longer “can the idea cross another embedding model?” It is whether this protocol can become a useful, backend-independent control plane across real providers, languages, operational costs and distribution shift.