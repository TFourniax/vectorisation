# Semantic ABI v0.6 RC — Product Security Boundary

This document describes security properties implemented by the engine/CLI and the controls that remain the responsibility of the deployment environment.

## 1. Trust model

Semantic ABI deliberately separates four kinds of truth:

1. **normative application policy** — what the application/business explicitly requires;
2. **empirical acquisition evidence** — judgments, corrections, clicks and runtime behavior;
3. **provider observations** — what a concrete backend returned for one exact execution;
4. **certification evidence** — adequacy, risk, conformance and attestation artifacts used to authorize release.

A weaker layer must not silently overwrite a stronger one. In particular:

- production clicks cannot overturn explicit policy;
- a provider ranking alone creates no semantic requirement;
- an aggregate score improvement cannot hide a new hard-clause regression;
- a textual `certified` label cannot replace recomputed adequacy/risk/conformance evidence;
- a stale attestation cannot authorize a different candidate audit.

## 2. Data minimization

### Query text

Raw query retention is disabled by default in OTLP/OpenInference ingestion. When a tenant-scoped secret is supplied, query text becomes a stable HMAC-SHA256 logical ID.

HMAC protects against straightforward offline guessing that would be possible with an unsalted plain hash of low-entropy query text. The secret must be managed outside the repository and rotated according to the deployment's key-management policy.

A query HMAC is still an identifier and may still be personal data under applicable law. Data minimization is not the same thing as legal anonymization.

### Documents

The contract normally contains logical document IDs and relational requirements, not raw document bodies or vector coordinates. Provider-local query catalogs may contain query vectors or Query DSL and should be protected according to their sensitivity.

### Telemetry

A raw OTLP span is normalized only as needed for retrieval observations. Production deployments should filter unrelated span attributes before persistence and define retention periods separately from Semantic ABI.

## 3. Secrets

Declarative provider configs reference secrets by environment-variable **name**:

- Qdrant `api_key_env`;
- OpenSearch/remote `authorization_env` or `headers_json_env`;
- pgvector `dsn_env`;
- OTLP query HMAC via CLI `--query-secret-env`.

Do not commit secret values, DSNs containing credentials or long-lived Authorization headers into provider configuration files.

The package does not implement a secret store. Enterprise deployments should source these environment values from their existing secret manager/KMS/runtime identity mechanism.

## 4. Transport security

Product configuration requires HTTPS by default for non-local HTTP provider endpoints. Plain HTTP is accepted for localhost integration/development endpoints.

The reference Protocol-v1 and provider clients enforce:

- absolute HTTP(S) URLs;
- explicit timeouts;
- bounded response sizes;
- JSON shape checks;
- rejection of missing, duplicate or non-finite score responses where relevant.

The reference Protocol-v1 **dispatcher is not a web server**. A production server wrapping it must add:

- authentication and authorization;
- request-body size limits at the HTTP layer;
- rate limits / concurrency limits;
- tenant routing and isolation;
- TLS termination or mutual TLS where required;
- access logs without leaking secrets or sensitive payloads.

The dispatcher itself additionally limits batch item count, neighbor `k` and logical ID length to prevent unbounded provider fanout after parsing.

## 5. PostgreSQL / pgvector

The pgvector adapter restricts configurable table/column names to simple SQL identifiers and quotes them. Runtime values are sent as DB-API parameters rather than interpolated into SQL.

Recommended production controls still include:

- a dedicated least-privilege database role;
- read-only access for release/audit execution where possible;
- statement timeout;
- network allowlisting / private connectivity;
- TLS and certificate verification;
- connection pool limits;
- explicit transaction/isolation policy for the snapshot being certified.

Semantic ABI does not make a mutable database snapshot immutable. If provider state can change during an audit, the deployment must use an appropriate snapshot/build identity.

## 6. Qdrant logical identities

Qdrant native point IDs are a provider implementation detail. `object_id_map` lets the portable Semantic ABI contract retain names such as `doc:gdpr-erasure` while the provider uses numeric or UUID identities.

The map is required to be one-to-one. A collision fails configuration rather than aliasing two semantic objects to one provider point.

Treat the map as deployment metadata. If logical-to-native identity changes, the provider manifest/state identity should change as well.

## 7. OpenSearch Query DSL

OpenSearch query catalogs are trusted deployment configuration. The adapter sends the stored Query DSL as a query body; it does not attempt to sandbox arbitrary Query DSL.

Therefore:

- only trusted build/deployment principals should modify query catalogs;
- the OpenSearch credential should have only the index/search permissions required;
- expensive query types should be restricted by organizational policy where relevant;
- query catalogs should be code-reviewed and versioned alongside release configuration.

## 8. Contract acquisition and policy poisoning

The acquisition layer treats different evidence sources with different reliability and exposes contradictions. It is still possible for a compromised feedback pipeline to generate large amounts of misleading empirical evidence.

Mitigations implemented:

- explicit policy is separated from empirical voting;
- policy-policy contradiction fails closed;
- behavioral evidence cannot become hard merely through volume;
- review proposals retain evidence lineage and exact clause semantics;
- hard promotion from human review requires an explicit authorization flag.

Additional production controls should include signed source provenance, authenticated feedback producers, abuse detection and per-source rate/budget limits.

## 9. Review integrity

Review bundles are digest-bound to the auto-generated parent contract and acquisition evidence. Decision files reference proposal IDs derived from proposal semantics/evidence.

Applying review:

- rejects a bundle belonging to another parent contract;
- rejects unknown or duplicate proposal decisions;
- creates a new child contract with the parent digest;
- records bundle and decision digests;
- requires `--allow-hard` for a reviewed hard-clause promotion.

The current local artifact does not authenticate the identity of the reviewer cryptographically. A hosted control plane should bind reviewer identity to OIDC/RBAC and sign the resulting approval event.

## 10. Adequacy and risk evidence integrity

Adequacy reports are recomputed from their evidence/requirements on load. A mismatching contract digest, status or report digest is rejected.

Risk certificate files contain a digest of the serialized certificate; tampering causes load failure. The certificate's statistical `certified` field must result from the calibration procedure used to create it; `attest` additionally requires that it is true.

These digests detect modification. They do **not** establish who created the artifact.

## 11. Attestations

`SemanticProtocolAttestation` binds the exact:

- Semantic Contract digest;
- provider manifest digest;
- compiled execution-plan digest;
- observed snapshot digest;
- Protocol-v1 audit digest;
- conformance result;
- adequacy result;
- risk certificate reference.

`semantic-abi release` re-executes the candidate and rejects an attestation that no longer matches that observed candidate.

### Current limitation: no external signature trust root

The v0.6 RC attestation is tamper-evident but **not yet a signed PKI/KMS statement**. Do not treat its digest alone as proof that a trusted organization approved the release.

The intended production design is an external signer (cloud KMS/HSM/PKI or Sigstore-like organizational trust policy) over the attestation digest, with key ID, algorithm, expiry and revocation managed outside this core package.

## 12. State identity and incremental reuse

A configured `state_digest` is trusted only if it is generated from an authoritative immutable provider/model/index build identity. A human-maintained constant is unsafe.

Do not enable deterministic state reuse when:

- documents can mutate in place without changing the state identity;
- model weights/configuration can change behind the same endpoint;
- ANN index rebuild/tuning can change rankings behind the same identity;
- query rewriting/reranking behavior changes outside the manifest.

When in doubt, omit `state_digest`; the system should recompute observations instead of reusing stale ones.

## 13. Recommended external security review before 1.0

A 1.0 production claim should include an independent review focused on:

- Protocol-v1 server authentication/tenant isolation in the chosen hosting layer;
- SSRF/egress policy around configurable provider URLs;
- Query DSL and provider-specific resource exhaustion;
- artifact provenance/signing and replay protection;
- secret leakage in logs/errors;
- OTLP PII/data-retention controls;
- PostgreSQL snapshot/isolation correctness;
- dependency/supply-chain policy and pinned release artifacts;
- organization/RBAC approval semantics for hard policy changes.
