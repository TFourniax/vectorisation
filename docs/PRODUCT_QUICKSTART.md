# Semantic ABI v0.6 RC — Product Quickstart

This guide exercises the intended product path from observed/application evidence to a strict production release decision.

## 1. Install

From a checkout:

```bash
python -m pip install -e '.[dev]'
semantic-abi --help
```

For PostgreSQL/pgvector support:

```bash
python -m pip install -e '.[postgres]'
```

The package is not assumed to be published to PyPI by this document. CI builds a wheel and smoke-tests it outside the source checkout.

## 2. Forge the initial contract

`evidence.jsonl` can mix normative policy and empirical evidence:

```jsonl
{"type":"policy","anchor":"q:delete-account","preferred":"doc:gdpr-erasure","rejected":"doc:newsletter-unsubscribe","criticality":1.0,"hard_eligible":true,"event_id":"policy-delete-v1"}
{"type":"preference","anchor":"q:invoice","preferred":"doc:invoice-help","rejected":"doc:marketing","source":"human_judgment","confidence":0.95,"event_id":"judgment-42"}
```

Forge the automatically promotable clauses and retain the ambiguous cases as a digest-bound review bundle:

```bash
semantic-abi forge-safe evidence.jsonl \
  --name customer-support \
  --version 1 \
  --output contract-v1.json \
  --review-bundle review-v1.json \
  --report acquisition-v1.json
```

An explicit `policy` is normative. Behavioral evidence can reveal disagreement but cannot vote down that policy. Contradictory explicit policies fail closed.

## 3. Optional: acquire evidence from OTLP/OpenInference traces

Production rankings alone are **observations, not semantic truth**. `forge-otlp` requires explicit feedback to derive preference evidence.

```bash
export SEMANTIC_ABI_QUERY_HMAC='tenant-specific-secret'

semantic-abi forge-otlp traces.otlp.jsonl \
  --feedback feedback.jsonl \
  --evidence policies-and-judgments.jsonl \
  --query-secret-env SEMANTIC_ABI_QUERY_HMAC \
  --output contract-v1.json \
  --review-bundle review-v1.json \
  --report acquisition-v1.json
```

Raw query text is not retained unless `--retain-query-text` is explicitly supplied. With `--query-secret-env`, logical query IDs use HMAC-SHA256.

## 4. Apply human review

A review decision file references proposal IDs from the review bundle:

```jsonl
{"proposal_id":"<digest>","decision":"accept","reviewer":"domain-expert","reason":"correct business behavior"}
{"proposal_id":"<digest>","decision":"reject","reviewer":"domain-expert","reason":"historical click bias"}
```

Apply decisions into a new child contract:

```bash
semantic-abi apply-review \
  --parent contract-v1.json \
  --bundle review-v1.json \
  --decisions decisions.jsonl \
  --version 2 \
  --output contract-v2.json \
  --report review-application.json
```

Promoting a reviewed clause to `hard` requires both `"hard": true` in the decision and the explicit CLI flag `--allow-hard`.

## 5. Configure providers

The Semantic Contract contains stable logical IDs. Provider-local configuration materializes those IDs into native queries or native object IDs.

### Qdrant

`qdrant.json`:

```json
{
  "kind": "qdrant",
  "url": "https://qdrant.example.internal",
  "collection": "support-kb-v42",
  "api_key_env": "QDRANT_API_KEY",
  "query_catalog": "qdrant-queries.json",
  "object_id_map": "qdrant-object-ids.json",
  "score_directionality": "symmetric",
  "deterministic": true,
  "state_digest": "immutable-index-build-42"
}
```

`qdrant-queries.json` may map a logical query to its provider-local vector/query representation:

```json
{
  "q:delete-account": [0.12, -0.08, 0.31]
}
```

`qdrant-object-ids.json` keeps Semantic ABI logical IDs independent of Qdrant native point IDs:

```json
{
  "doc:gdpr-erasure": 101,
  "doc:newsletter-unsubscribe": 102
}
```

Only declare `score_directionality: symmetric` when the configured scoring semantics genuinely support that claim. The product default is `unknown`.

### OpenSearch

`opensearch.json`:

```json
{
  "kind": "opensearch",
  "url": "https://opensearch.example.internal",
  "index": "support-kb-v42",
  "authorization_env": "OPENSEARCH_AUTHORIZATION",
  "query_catalog": "opensearch-queries.json",
  "deterministic": true,
  "state_digest": "immutable-index-build-42"
}
```

`opensearch-queries.json` stores Query DSL, not an implementation detail in the portable contract:

```json
{
  "q:delete-account": {
    "match": {
      "content": "delete my account GDPR erasure"
    }
  }
}
```

### pgvector

`pgvector.json`:

```json
{
  "kind": "pgvector",
  "dsn_env": "SEMANTIC_ABI_PG_DSN",
  "table": "support_documents",
  "id_column": "id",
  "vector_column": "embedding",
  "query_catalog": "pgvector-queries.json",
  "metric": "cosine",
  "deterministic": true,
  "state_digest": "immutable-index-build-42"
}
```

The DSN remains in the environment, not in the checked-in config.

### Remote Protocol-v1 implementation

```json
{
  "kind": "remote",
  "url": "https://semantic-oracle.example.internal",
  "authorization_env": "SEMANTIC_ORACLE_AUTHORIZATION"
}
```

## 6. Preflight a candidate

A preflight does not require adequacy/risk certification. It is the semantic equivalent of a diff:

```bash
semantic-abi check contract-v2.json \
  --baseline prod.json \
  --candidate candidate.json \
  --output semantic-change.json \
  --markdown semantic-change.md
```

Default release-diff policy is conservative:

- zero newly failing hard clauses;
- zero newly failing soft clauses;
- zero newly missing clauses;
- zero aggregate semantic score drop;
- candidate must satisfy all hard clauses.

Explicit flags can loosen selected soft/change constraints. Those flags do **not** turn `check` into a certified production release.

## 7. Assess contract adequacy

Adequacy answers a different question from conformance: is the contract/test surface sufficient evidence for the release claim?

`adequacy-spec.json`:

```json
{
  "evidence": {
    "contract_digest": "<contract digest>",
    "object_coverage": 0.97,
    "mutation_kill_rate": 0.91,
    "heldout_cases": 1200,
    "datasets": 3,
    "fault_families": 6
  },
  "requirements": {
    "min_object_coverage": 0.90,
    "min_mutation_kill_rate": 0.85,
    "min_heldout_cases": 500,
    "min_datasets": 2,
    "min_fault_families": 4
  }
}
```

```bash
semantic-abi assess-adequacy contract-v2.json \
  --spec adequacy-spec.json \
  --output adequacy.json
```

Missing required evidence produces `insufficient_evidence` and a non-zero exit status.

## 8. Calibrate a rollout-risk certificate

Each held-out calibration row contains a predeployment proxy risk and independently observed binary semantic loss:

```jsonl
{"proxy_risk":0.03,"observed_loss":0,"object_id":"case-001","group":"billing"}
{"proxy_risk":0.18,"observed_loss":1,"object_id":"case-002","group":"deletion"}
```

```bash
semantic-abi calibrate-risk calibration.jsonl \
  --target-risk 0.10 \
  --delta 0.05 \
  --output risk-certificate.json
```

Failure to statistically certify the requested budget produces a valid **failed** certificate and a non-zero exit status. It is not silently converted into a pass.

## 9. Attest the candidate

```bash
semantic-abi attest contract-v2.json \
  --oracle candidate.json \
  --adequacy adequacy.json \
  --risk-certificate risk-certificate.json \
  --output candidate-attestation.json \
  --report candidate-attestation-summary.json
```

`attest` executes the candidate again, checks Protocol-v1 conformance, recomputes the evidence bindings and emits `status=certified` only when:

- protocol conformance passes;
- all hard clauses pass;
- there are no missing clauses;
- adequacy status is `adequate`;
- the risk certificate is certified.

Otherwise the attestation is emitted as `blocked` and the command returns non-zero.

## 10. Strict production release gate

```bash
semantic-abi release contract-v2.json \
  --baseline prod.json \
  --candidate candidate.json \
  --attestation candidate-attestation.json \
  --output release.json \
  --markdown release.md
```

A production release passes only when both conditions hold:

1. the backend-independent semantic change policy passes; and
2. the supplied certified attestation is bound to the **exact candidate contract, manifest, execution plan, observed snapshot and protocol audit** produced by the release check.

A stale attestation for a different index/model/provider state fails closed.

## Exit codes

| Command | Pass | Controlled block/failure |
|---|---:|---:|
| `check` | 0 | 4 |
| `release` | 0 | 5 |
| `attest` | 0 | 6 |
| `assess-adequacy` | 0 | 7 |
| `calibrate-risk` | 0 | 8 |

Parsing/configuration/network errors use ordinary non-zero process termination and should be treated as CI failure.

## Important operational note on `state_digest`

`state_digest` is only trustworthy if your deployment process derives it from an immutable, authoritative model/index build identity. Do not manually reuse a convenient string after provider state changes. Incremental observation reuse is intentionally rejected unless deterministic implementation identity and state digest remain stable.
