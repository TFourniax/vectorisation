# Semantic ABI Oracle Protocol v1

## Why this exists

A portable Semantic Contract is only useful if it can be executed against retrieval systems that do **not** share an embedding geometry, process, programming language, or even a symmetric scoring function.

The original in-process `SemanticOracle` abstraction proved representation independence at the Python level. It was not yet a deployment protocol. Practical retrievers are often directional:

- BM25: query → document;
- ColBERT / MaxSim: query-token matrix → document-token matrix;
- hybrid rankers: query → fused evidence;
- typed graph traversal: source node/type → candidate node/type;
- remote proprietary rankers: implementation-defined relevance.

Protocol v1 therefore defines **`score(anchor, candidate)`**, not distance or cosine.

## Compiler model

```text
SemanticContract
      |
      v
compile_contract()
      |
      +-- unique logical object IDs
      +-- unique directional score pairs
      +-- unique top-k neighborhood requests
      |
      v
ContractExecutionPlan (canonical digest)
      |
      v
compatibility preflight
      |
      v
contains_many()   score_many()   neighbors_many()
      \               |               /
       +--------------+--------------+
                      |
                      v
               OracleSnapshot
                      |
                      v
                audit_snapshot()
                      |
                      v
             protocol attestation
```

Repeated clauses share backend operations. A 10,000-clause contract does not imply 10,000 network calls. With the default executor, a plan requiring all three operation families uses one batch call for membership, one for directional scores and one for rankings.

This is **execution deduplication, not semantic compression**: the full contract remains normative.

## Oracle manifest

Every Protocol-v1 implementation exposes a canonical `OracleManifest` containing:

- protocol/version;
- implementation identity/kind;
- score semantics;
- score directionality: `symmetric`, `asymmetric`, or `unknown`;
- determinism claim;
- capabilities;
- provider metadata.

The manifest itself has a SHA-256 digest. Provider metadata may declare typed namespaces such as `score_anchor_prefixes`, `score_candidate_prefixes`, and `neighbor_anchor_prefixes`.

## Static plan compatibility

`check_plan_compatibility()` rejects unsupported contracts **before execution**.

For example, a query/document late-interaction backend can declare:

```json
{
  "score_anchor_prefixes": ["q:"],
  "score_candidate_prefixes": ["d:"],
  "neighbor_anchor_prefixes": ["q:"]
}
```

A normal `q: -> d:` retrieval contract is accepted. A clause asking that backend to compute document→document neighborhoods is rejected rather than silently assigning a made-up interpretation.

The preflight also checks required batch capabilities.

## Wire operations

The reference HTTP shape is specified in [`../spec/semantic-abi-oracle-v1.openapi.yaml`](../spec/semantic-abi-oracle-v1.openapi.yaml).

### `GET /v1/manifest`
Returns the oracle manifest.

### `POST /v1/contains`
Batch membership over stable logical object IDs.

### `POST /v1/score`
Batch **directional** pairs:

```json
{"pairs":[{"anchor":"q:123","candidate":"d:456"}]}
```

The reverse pair is neither required nor assumed equal.

### `POST /v1/neighbors`
Batch top-k requests using the same logical namespace as the contract.

## Conformance suite

`check_oracle_conformance()` tests provider claims without imposing vector-specific assumptions:

- anchors exist;
- top-k response length;
- no duplicate or unknown neighbor IDs;
- no self-neighbor unless explicitly declared;
- deterministic repeatability when declared;
- top-k prefix consistency;
- rank/score coherence when scoring is exposed;
- finite scores;
- symmetry **only when the provider explicitly claims symmetry**.

An asymmetric late-interaction oracle can therefore be fully conformant.

## Late interaction / MaxSim

`LateInteractionOracleV1` keeps separate query-token and document-token matrices and evaluates ColBERT-style MaxSim:

```text
score(q, d) = sum_i max_j <q_i, d_j>
```

It may consume rankings produced by an external candidate engine such as PLAID, Voyager, Vespa or WARP while evaluating triplet clauses directly from token matrices. This prevents ordinal clauses from depending on whether both compared documents happened to appear in a top-k retrieval result.

`explain(anchor, candidate)` returns each query token's best matching document-token index and contribution. This is diagnostic evidence, not application truth.

## Remote execution

`dispatch_protocol_request()` is a framework-neutral reference dispatcher.

`RemoteSemanticOracleV1` accepts any transport callable. Included transports:

- `InProcessProtocolTransport` for deterministic integration/conformance tests;
- `HttpJsonTransport` as a zero-dependency JSON-over-HTTP client.

The payloads can therefore be exposed through FastAPI, Flask, a gRPC gateway, serverless functions, Unix sockets, an internal service mesh or a provider bridge without changing the contract.

The installed CLI exposes:

```bash
semantic-abi plan contract.json
semantic-abi remote-audit https://oracle.example contract.json
semantic-abi remote-conformance https://oracle.example --anchors q:1,q:2
```

## State-bound incremental audit

Versioned contracts often share most of their operations. `execute_contract_plan_incremental()` can reuse a previous `OracleSnapshot`, but only under strict conditions:

1. the oracle declares `deterministic=true`;
2. its manifest contains `metadata.state_digest`;
3. the **complete manifest digest is identical** to the previous snapshot;
4. the previous snapshot is cryptographically bound to the previous execution plan.

Under those conditions it reuses:

- previous membership checks for unchanged IDs;
- exact previous directional score pairs;
- exact top-k results;
- a larger old top-k as evidence for a smaller new prefix.

Only the delta is fetched from the backend. A changed model/index/state digest invalidates all reuse. No `state_digest` means **no cross-audit cache**.

This makes contract evolution cheaper without weakening the meaning of the observation.

## Protocol attestation

`SemanticProtocolAttestation` binds one observed execution to:

- contract digest;
- oracle-manifest digest;
- compiled plan digest;
- observed snapshot digest;
- protocol-audit digest;
- conformance digest/status;
- optional Contract Adequacy digest/status;
- optional risk-certificate digest/status;
- external evidence hashes.

It is a tamper-evident SHA-256 envelope, **not a digital signature**. Production systems can sign the final attestation digest with their own KMS/signature system.

Deployment eligibility is deliberately strict: good-looking metrics alone do not imply approval. The current envelope requires explicit `status="certified"`, protocol conformance, hard-clause pass, zero missing clauses, `adequacy_status="adequate"`, and an explicitly certified risk result.

## Backward compatibility

`LegacyOracleBatchAdapter` wraps the evidence-pinned historical `SemanticOracle` without changing it. Legacy score directionality is reported as `unknown` because the old word `similarity` never established symmetry as a contract.

Protocol v1 is additive: older evidence remains reproducible while new integrations use the stronger execution boundary.

## Current validation status

The Protocol-v1 compiler, remote transport, directional MaxSim adapter, conformance suite, compatibility preflight, attestation, CLI, and incremental reuse are covered by the standard Python 3.10/3.12/3.13 CI. The separate real ColBERTv2/SciFact portability gate is intentionally tracked as independent neural evidence rather than being inferred from unit tests.

## What this changes strategically

Before Protocol v1, “representation independent” meant that the audit function did not require dense vectors.

Protocol v1 tests a stronger infrastructure claim:

> **One versioned Semantic Contract can be compiled once and executed through a small, inspectable, directional wire protocol against local or remote retrievers whose internal representations and scoring algebra are unrelated.**

## Non-claims

Protocol v1 does not claim to invent RPC, OpenAPI, batching, caching, ColBERT, MaxSim, retrieval conformance testing, sequential statistics, or release attestation in general. The research question is whether their integration around a portable, versioned semantic contract materially improves retrieval change control.