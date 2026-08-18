# Current research status

**Status date:** 2026-08-18  
**Package:** `semantic-manifold-atlas` **0.7.0**  
**Branch:** `agent/semantic-change-control-plane`  
**Draft PR:** #4 → `agent/semantic-abi-contract-forge`  
**Posture:** evidence-gated research; no production-readiness, guaranteed business outcome, or legal patent-novelty claim.

This branch preserves the prior Semantic ABI work and adds two new experimental layers: whole-application change control and proof-carrying semantic dependency resolution.

## Current thesis

Semantic ABI is no longer framed merely as a vector/retrieval abstraction or as a generic agent release gate.

The stronger hypothesis is:

> **Application-owned semantic contracts can become a compatibility boundary above replaceable AI implementations. Evidence-bound compatibility certificates can then turn models, retrievers, rerankers and tools into resolvable dependencies rather than bespoke migration projects.**

The proposed category is **Semantic Dependency Management**.

## v0.7 — Semantic Linker

Implemented:

- `SemanticSlot`: logical application dependency independent from a vendor implementation;
- `ComponentOffer`: candidate implementation metadata including kind, provider, cost, p95 latency, capabilities and regions;
- `CompatibilityCertificate`: exact baseline + contract + evidence + coverage + issuer + validity/environment binding;
- `CompositionCertificate`: explicit evidence for concrete multi-component combinations;
- fail-closed rejection of uncertified, stale, wrong-contract, wrong-environment or insufficient-coverage candidates;
- resource/capability/region filtering before optimization;
- cost/latency objective only after the evidence gate;
- penalty/policy handling for conditionally compatible candidates;
- explicit non-assumption of compositionality;
- deterministic `LinkPlan` digest;
- JSON request/result layer;
- CLI command: `semantic-abi link`;
- runnable examples and focused tests.

The current resolver enumerates candidate combinations. This is acceptable for the research prototype and deliberately transparent, but not scalable enough for a production registry; branch-and-bound / SAT/SMT / constraint programming and incremental resolution are explicit next gates.

### Critical security limitation

Current linker certificates are content-digest-bound and issuer-aware but **not yet cryptographically signed**. The issuer field alone is not a trust root. Ed25519/KMS/PKI signing, verification, expiry/revocation and trust policy must land before external certificates are treated as secure attestations.

## v0.6 — Semantic Change Control

Implemented:

- `MeaningFrame` representation-agnostic behavior/effect observations;
- change manifests across model, prompt, corpus, embedding, retriever, reranker, tool, policy, schema, code and config changes;
- cross-version invariants;
- metamorphic invariants for semantically related probe variants;
- exact/set/numeric comparators;
- hard vs soft rules with explicit regression budget;
- fail-closed evidence coverage;
- evidence-derived `patch` / `minor` / `major` compatibility class;
- `allow` / `canary` / `block` rollout recommendation;
- rule-driven suspicious-change localization without claiming causal proof;
- deterministic evidence digest;
- conversion of passing reports into linker certificates;
- refusal to promote breaking or insufficient-evidence reports into dependency proof.

## v0.5 — retrieval interoperability foundation remains valid

The strongest promoted retrieval result remains the public SciFact experiment using real `lightonai/colbertv2.0` multi-vector representations via PyLate/Voyager + MaxSim:

- 1,800 documents;
- 300 train queries for contract construction;
- 200 untouched test queries;
- 600 application clauses;
- one unchanged contract digest across lexical BM25 and asymmetric ColBERT late interaction.

| implementation | Semantic ABI | nDCG@10 | Recall@10 | missing clauses |
|---|---:|---:|---:|---:|
| BM25 sparse | **0.9067** | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | **0.9047** | **0.7337** | **0.8395** | **0** |

ColBERT passed all hard clauses and 660/660 Protocol-v1 conformance checks with zero issues.

The promoted claim remains narrow: one application-level semantic contract survived a materially different retrieval algebra without common coordinates or contract translation.

## Protocol-v1 foundation

Still present and part of the architecture:

- `OracleManifest`;
- `compile_contract()`;
- directional/batchable `contains_many`, `score_many`, `neighbors_many`;
- `OracleSnapshot`;
- protocol-v1 audit;
- remote HTTP transport;
- OpenAPI spec;
- compatibility preflight;
- conformance suite;
- state-bound incremental execution;
- semantic protocol attestation;
- language-neutral TCK.

See [`SEMANTIC_ABI_PROTOCOL_V1.md`](SEMANTIC_ABI_PROTOCOL_V1.md).

## Conformity, adequacy and dependency proof remain separate

A high conformity score is not automatically adequate evidence. A compatible component is not automatically compatible in every composition.

The architecture therefore keeps separate:

1. clause conformity;
2. contract adequacy;
3. backend/implementation integrity;
4. calibrated risk;
5. attestation/evidence identity;
6. component substitution compatibility;
7. joint composition compatibility;
8. dependency-resolution policy.

Missing required evidence fails closed.

## Negative evidence retained

Previous falsifications remain first-class and must not be erased by the product pivot:

- local BGE→MiniLM SCF mapping loses to global;
- fixed Semantic Witness does not robustly dominate random subsets;
- learned fixed Diagnostic Panel overfits and produces 0% held-out regression recall;
- aggregate Semantic ABI is not generally a better nDCG predictor than ordinary validation;
- current repair does not reach the preregistered 90% downstream-recovery goal;
- fixed-prior repair attribution does not generalize.

These results are important because the project is explicitly trying to discover a durable primitive rather than accumulate attractive but unsupported claims.

## Competitive correction made on 2026-08-18

Research found that a generic "AI release gate" would not be sufficiently differentiated. Adjacent public products/research now cover combinations of:

- agent regression tests and CI gates;
- behavioral contracts;
- runtime contracts;
- deployment certificates;
- prompt/agent semantic versioning;
- model routing;
- whole-agent optimization;
- proof-carrying agent governance.

The project therefore narrows its novelty hypothesis to **evidence-bound semantic dependency resolution**: application-owned semantic slots, exact substitute certificates, explicit composition proof, and optimization only inside the certified dependency set.

This remains a hypothesis rather than proof of worldwide novelty.

## Validation status

Performed during this branch's development:

- isolated v0.6 change-control suite: **7 focused tests passed**;
- isolated v0.7 linker core: **5 focused tests passed**;
- additional repository tests were added for certificate bridging and JSON link I/O;
- Draft PR #4 was opened so the repository's full pull-request CI matrix can validate the combined branch.

Do not claim the full repository CI is green until GitHub reports it.

## Highest-value next gates

1. full PR CI green across existing Python/benchmark matrix;
2. cryptographic certificate signing, verification and revocation;
3. real model-provider and retrieval-provider adapters;
4. empirical composition study: when can proof be reused vs when is joint recertification mandatory?;
5. private compatibility registry and graph;
6. scalable constraint resolver;
7. automatic Contract Forge with human approval of normative requirements;
8. real migration studies against conventional eval + router workflows;
9. measure false admission, false block, certification cost and spend/migration savings;
10. independent TCK implementation and professional prior-art/IP review.

## Key documents

- [`../README.md`](../README.md) — current product/research overview;
- [`SEMANTIC_CHANGE_CONTROL_PLANE.md`](SEMANTIC_CHANGE_CONTROL_PLANE.md) — v0.6 compatibility design;
- [`SEMANTIC_LINKER.md`](SEMANTIC_LINKER.md) — v0.7 proof-carrying dependency resolver;
- [`VENTURE_THESIS_CHANGE_CONTROL.md`](VENTURE_THESIS_CHANGE_CONTROL.md) — commercial thesis and kill criteria;
- [`SEMANTIC_ABI_PROTOCOL_V1.md`](SEMANTIC_ABI_PROTOCOL_V1.md) — retrieval protocol foundation.
