# Semantic ABI Oracle Protocol v1

## Why this exists

A portable Semantic Contract is only useful if it can be executed against retrieval systems that do **not** share an embedding geometry, process, programming language, or even a symmetric scoring function.

The original in-process `SemanticOracle` abstraction was enough to prove representation independence at the Python level. It was not yet a deployment protocol. In particular, the word `similarity` silently suggests a symmetric metric even though practical retrieval systems often implement a directional relation:

- BM25: query → document;
- ColBERT / MaxSim: query-token matrix → document-token matrix;
- hybrid rankers: query → fused candidate evidence;
- typed graph traversal: source node/type → candidate node/type;
- remote proprietary rankers: implementation-defined relevance scores.

Protocol v1 therefore defines the primitive as **`score(anchor, candidate)`**, not distance or cosine.

## Compiler model

A `SemanticContract` is compiled before execution.

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
contains_many()   score_many()   neighbors_many()
      \               |               /
       +--------------+--------------+
                      |
                      v
               OracleSnapshot
                      |
                      v
                audit_snapshot()
```

Repeated clauses can share the same backend operations. A 10,000-clause contract does not imply 10,000 network calls.

For a contract that needs membership, directional scores, and rankings, `execute_contract_plan()` makes **at most one batch call per operation family**. A remote client therefore needs one manifest request plus up to three data round trips for the whole compiled plan.

This is an execution optimization, not semantic compression: the full contract remains normative.

## Wire operations

The normative HTTP-shaped reference surface is described in [`../spec/semantic-abi-oracle-v1.openapi.yaml`](../spec/semantic-abi-oracle-v1.openapi.yaml).

### `GET /v1/manifest`

Declares:

- protocol/version;
- implementation identity;
- implementation kind;
- score semantics;
- score directionality: `symmetric`, `asymmetric`, or `unknown`;
- determinism claim;
- capabilities;
- provider metadata.

The canonical manifest has a SHA-256 digest and can be attached to audit/release evidence.

### `POST /v1/contains`

Batch membership over stable logical object IDs.

### `POST /v1/score`

Batch directional score pairs:

```json
{
  "pairs": [
    {"anchor": "q:123", "candidate": "d:456"}
  ]
}
```

The protocol does not require the reverse pair to exist or have the same score.

### `POST /v1/neighbors`

Batch top-k requests. Returned IDs must use the same logical namespace used by the contract.

## Conformance suite

`check_oracle_conformance()` checks claims made by the implementation rather than imposing vector-specific assumptions.

Current checks include:

- declared anchors exist;
- top-k response length;
- unique neighbor IDs;
- no self-neighbor unless explicitly declared;
- returned IDs are known to the oracle;
- deterministic repeatability when `deterministic=true`;
- top-k prefix consistency;
- returned ranking is coherent with `score_many` when the score capability is declared;
- finite scores;
- symmetry only when the manifest explicitly claims symmetry.

A late-interaction oracle may therefore be fully conformant while being intentionally asymmetric.

## Late interaction / MaxSim

`LateInteractionOracleV1` stores separate query-token and document-token matrices and evaluates classic ColBERT-style MaxSim:

```text
score(q, d) = sum_i max_j <q_i, d_j>
```

It can consume rankings produced by an external candidate engine such as PLAID, Voyager, Vespa, or WARP while evaluating contract triplets directly from token matrices. This keeps `NeighborClause` candidate generation scalable without making ordinal clauses depend on whether both compared documents appeared in the retrieved top-k.

The adapter exposes `explain(anchor, candidate)`, returning the best matching document-token index and score for each query token. This is useful evidence for contract failures but is **not** promoted to application truth.

## Remote execution

`dispatch_protocol_request()` is the reference server-side dispatcher. It is deliberately framework-neutral.

`RemoteSemanticOracleV1` accepts any transport callable. The repository includes:

- `InProcessProtocolTransport` for deterministic conformance/integration tests;
- `HttpJsonTransport` as a standard-library JSON-over-HTTP reference client.

The same payloads can be carried through FastAPI, Flask, gRPC gateways, serverless functions, Unix sockets, internal service meshes, or provider-specific bridges.

## Backward compatibility

`LegacyOracleBatchAdapter` wraps the historical Python `SemanticOracle` without changing previous evidence-sensitive code. It reports score directionality as `unknown` because the legacy `similarity` name did not establish symmetry as a contract.

Protocol v1 is therefore additive: existing evidence remains reproducible while new integrations can use the stronger model.

## What this changes strategically

Before Protocol v1, “representation independent” meant that the audit function did not require dense vectors.

After Protocol v1, the stronger claim being tested is:

> **One versioned Semantic Contract can be compiled once and executed through a small, inspectable wire protocol against local or remote retrievers whose internal representations and scoring algebra are unrelated.**

That is the interoperability boundary required before Semantic ABI can plausibly become infrastructure rather than a Python research abstraction.

## Non-claims

This protocol does not claim to invent RPC, OpenAPI, batch APIs, ColBERT, MaxSim, or retrieval conformance testing in general. Its research question is whether this minimal execution boundary is sufficient and useful for portable semantic change control across heterogeneous retrieval implementations.
