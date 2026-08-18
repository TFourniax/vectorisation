# Semantic ABI v0.6 RC — Product Readiness

**Status:** release-candidate productization branch, not 1.0 and not merged.  
**Product surface:** `semantic_atlas.product` + `semantic-abi` CLI.  
**Core principle:** passing tests is evidence about the tested surface, not a universal production-readiness claim.

## Evidence labels

| Label | Meaning |
|---|---|
| `LIVE-CI` | exercised against a real ephemeral external system in GitHub Actions |
| `UNIT` | deterministic automated tests cover the contract/wire behavior without a real external service |
| `RESEARCH-EVIDENCE` | promoted empirical result already bound to repository evidence artifacts |
| `OPEN` | important product or scientific gate not yet demonstrated |

## Current product matrix

| Capability | Status | What is actually demonstrated |
|---|---|---|
| Semantic Contract v1 | `RESEARCH-EVIDENCE` + `UNIT` | versioned, digest-bound triplet/neighbor/mutual-neighbor clauses |
| Protocol-v1 compiler/audit | `RESEARCH-EVIDENCE` + `UNIT` | coordinate-free compiled execution through contains/score/neighbors batches |
| BM25 → ColBERTv2 portability | `RESEARCH-EVIDENCE` | one unchanged SciFact contract executed across lexical sparse and real late-interaction retrieval |
| Backend-independent semantic diff | `UNIT` | clause-level regression/fix/missing/improvement classification without common coordinates |
| Release policy | `UNIT` | hard/soft regression gates, aggregate score floor/drop, newly missing clause gate, explicit grandfathering |
| Normative policy precedence | `UNIT` | declared application policy cannot be overturned by click volume; policy-policy conflict fails closed |
| Evidence-gated Contract Forge | `UNIT` | heterogeneous evidence aggregation, confidence/opposition, review queue, lineage |
| Human review workflow | `UNIT` | digest-bound proposal bundle, exact clause reconstruction, accept/reject lineage, explicit hard promotion |
| OpenInference-style telemetry | `UNIT` | retrieval observations + explicit feedback join; ranking alone produces no semantic truth |
| Raw OTLP JSON normalization | `UNIT` | AnyValue/KeyValue decoding, resourceSpans traversal, duplicate attribute rejection |
| Data-minimized query identity | `UNIT` | tenant-secret HMAC-SHA256 stable IDs; raw query retention off by default |
| Qdrant adapter | `LIVE-CI` | real Qdrant v1.18.2 collection; query anchor, point anchor, pair scores, top-k, logical↔native ID mapping |
| pgvector adapter | `LIVE-CI` | real PostgreSQL/pgvector 0.8.6 table; cosine scoring, query anchor and row anchor audit |
| OpenSearch adapter | `UNIT` + live gate pending/current branch | `_mget`, `_msearch`, Query DSL catalog and BM25-style `_score`; live authenticated TLS job added on v3.7.0 |
| Remote Protocol-v1 client/server dispatcher | `UNIT` + `RESEARCH-EVIDENCE` | bounded batches, response-size limits, missing/duplicate/nonfinite response rejection; existing protocol TCK |
| Declarative provider configuration | `UNIT` | secrets referenced via environment variables; HTTPS default for non-local HTTP providers |
| Contract adequacy artifact | `UNIT` + existing research | requirements are explicit; missing evidence remains insufficient rather than silently passing |
| Risk calibration artifact | `UNIT` + existing research | split calibration/certification logic plus digest-bound serialization |
| Protocol attestation | `UNIT` + existing research | binds contract, manifest, execution plan, snapshot, audit, conformance, adequacy and risk evidence |
| Strict production release gate | `UNIT` | release requires both safe semantic diff and deployment-eligible attestation bound to the exact candidate audit |
| Python compatibility | `LIVE-CI` | repository test suite runs on Python 3.10, 3.12 and 3.13 |
| Historical evidence freshness | `LIVE-CI` | promoted research evidence remains bound to expected source blobs after productization changes |
| Wheel/sdist packaging | current branch CI gate | build + install outside checkout + CLI smoke test added |

## What v0.6 RC can credibly be used for

### 1. Retrieval migration preflight

Given one stable Semantic Contract and two provider configurations, `semantic-abi check` can execute both implementations and emit a clause-level semantic diff. This is useful for embedding, index, vector-store, lexical/vector or reranking migrations where aggregate IR metrics remain separately mandatory.

### 2. Controlled contract acquisition

`forge-safe` and `forge-otlp` can turn explicit policy, human judgments, corrections and weaker behavioral evidence into an auto-promoted contract plus an auditable review bundle. Normative policy is kept separate from empirical popularity.

### 3. CI release blocking

`semantic-abi release` returns a non-zero process status when the candidate violates the declared change policy or when its certified attestation is absent, stale, inadequate, non-conformant or not risk-certified.

### 4. Provider-independent application semantics

A contract can refer to stable logical IDs such as `q:delete-account` and `doc:gdpr-erasure` while provider-local catalogs/materialization map those IDs to OpenSearch Query DSL, Qdrant query vectors/native point IDs, pgvector vectors, or a remote Protocol-v1 implementation.

## What is deliberately **not** claimed yet

### Contract-acquisition economics — `OPEN`

The most important commercial/scientific gate is still unproven: Contract Forge has not yet demonstrated, on independent real-world datasets and expert-time budgets, that it catches more important regressions per expert-minute than manual golden-set curation, ordinary retrieval evaluation, incumbent snapshots or LLM-generated eval candidates.

This is the next decisive experiment, not a documentation issue.

### Universal provider coverage — `OPEN`

The adapters prove the protocol can span materially different systems, not every mode of those systems. In particular:

- Qdrant live CI currently validates a dense-vector fixture, not every hybrid/sparse/multivector Query API construction;
- pgvector live CI currently validates a small exact-search fixture, not every HNSW/IVFFlat tuning regime;
- OpenSearch live CI targets a BM25-style Query DSL fixture, not every neural/hybrid/search-pipeline configuration;
- Vespa and typed graph adapters are not yet implemented on this product branch.

### Signed trust root — `OPEN`

Current protocol attestations are tamper-evident digest envelopes. They are **not yet cryptographically signed, expiring or revocable trust statements**. A production enterprise control plane should integrate KMS/PKI signing, key rotation, expiry and revocation rather than invent a bespoke cryptosystem in this Python package.

### Multi-language independent implementation — `OPEN`

The existing language-neutral TCK is useful, but an independently implemented Rust/Go/TypeScript Protocol-v1 client/server has not yet been promoted as evidence. Python is still the reference implementation.

### Production fleet / SaaS control plane — `OPEN`

The repository is now close to a deployable **engine/CLI**, not a complete hosted enterprise product. A commercial control plane would still need tenant isolation, OIDC/RBAC, audit-log retention, organization/project model, contract registry, artifact storage, dashboards, GitHub/GitLab checks, secrets/KMS integration, billing and operational SLOs.

### Regulatory compliance — `OPEN`

Semantic ABI can produce useful change-control evidence. It must not be marketed as automatically establishing compliance with the EU AI Act, medical-device rules, financial regulation or any other legal regime.

## Release criteria for a credible 1.0 engine

A 1.0 label should require, at minimum:

1. all standard CI and live provider integration jobs green on the release commit;
2. distributable wheel smoke-tested outside the source checkout;
3. Qdrant, pgvector and OpenSearch live provider gates green;
4. strict attestation/release CLI end-to-end tests green;
5. one independent non-Python TCK implementation;
6. a signed-attestation integration contract suitable for external KMS/PKI;
7. at least one independent acquisition-economics experiment with preregistered baselines and kill criteria;
8. no unresolved critical/high security findings from a focused external review;
9. professional novelty/IP review before strong patent or standards claims.

Until those gates pass, `0.6.0rc*` is a more truthful product label than `1.0.0`.
