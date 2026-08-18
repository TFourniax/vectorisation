# Telemetry ingestion — OpenInference first, no proprietary tracing requirement

**Status:** experimental Contract Forge input adapter.

Semantic ABI should not require customers to replace their observability stack or add a proprietary tracing SDK. The first telemetry adapter therefore consumes OpenInference-compatible retrieval exports.

OpenInference defines `RETRIEVER` / `RERANKER` spans and standardized retrieval document attributes on top of OpenTelemetry. That makes it a useful ingestion boundary for systems already instrumented through Phoenix or another OTEL-compatible collector.

## Critical epistemic rule

A retrieval trace is **not semantic truth**.

```text
query -> current retriever -> [A, B, C]
```

must never be converted into:

```text
A > B > C
```

just because the current implementation emitted that order.

Doing so would preserve current mistakes and make Semantic ABI a snapshot test for the incumbent backend.

The adapter therefore produces a `RetrievalObservation` only. A semantic evidence event is emitted only after the observation is joined to an independent signal such as:

- an explicit user selection;
- a click with observable skipped results above it;
- a human correction;
- an explicit negative result;
- accepted answer/source IDs.

No matching feedback means **zero acquired clauses**.

## Stable IDs without raw query retention

If the span already includes a stable application-level ID such as:

```text
semantic_abi.query_id = q:delete-account
```

that ID is preserved.

Otherwise the adapter can derive a deterministic query ID from `input.value`.

For sensitive production data, use an HMAC key:

```bash
export SEMANTIC_ABI_QUERY_KEY='tenant-scoped-secret'
```

and run:

```bash
semantic-abi forge-openinference spans.jsonl \
  --feedback feedback.jsonl \
  --query-secret-env SEMANTIC_ABI_QUERY_KEY \
  --name customer-support \
  --version 1 \
  --output contract.json \
  --report acquisition-report.json \
  --review review-queue.jsonl
```

The contract then contains HMAC-derived logical query IDs rather than raw query strings. Raw query text is not retained by default in intermediate observations.

Plain SHA-256 remains available when no secret is supplied, but it **must not be described as anonymization**: low-entropy text can be dictionary-guessed. HMAC is the recommended production path when no stable business ID is available.

## Span example

```json
{
  "trace_id": "trace-1",
  "span_id": "span-1",
  "attributes": {
    "openinference.span.kind": "RETRIEVER",
    "input.value": "How do I delete my account?",
    "retrieval.documents": [
      {"document.id": "doc:newsletter", "document.score": 0.91},
      {"document.id": "doc:gdpr-delete", "document.score": 0.88},
      {"document.id": "doc:identity-check", "document.score": 0.80}
    ]
  }
}
```

The importer requires stable `document.id` values. Document content is not needed to create the observation and should not be retained merely for Semantic ABI if IDs already exist.

Flattened OpenInference document attributes such as:

```text
retrieval.documents.0.document.id
retrieval.documents.1.document.id
```

are also accepted.

## Feedback sidecar

Feedback is deliberately a separate joinable artifact so the customer's existing product analytics, support system or review tool can remain the source of truth.

```json
{
  "span_id": "span-1",
  "selected": ["doc:gdpr-delete"],
  "explicit_negative": ["doc:newsletter"],
  "accepted_sources": ["doc:gdpr-delete", "doc:identity-check"],
  "criticality": 0.9,
  "event_id": "human-review-1842"
}
```

Span identity has precedence over trace identity. Trace-level feedback is supported when no span-specific record exists.

## What is and is not standardized

The adapter relies on OpenInference for the retrieval observation surface. Product-specific actions such as “selected result” or “accepted source” are intentionally supplied as a sidecar because their semantics differ by application.

Future adapters should map LangSmith feedback, Phoenix annotations and search behavior exports into the same `RetrievalFeedback` model rather than adding vendor-specific concepts to the Semantic Contract itself.

## Privacy properties

The intended production posture is data minimization:

- stable logical IDs over raw content;
- HMAC query IDs when raw queries cannot be retained;
- no document content required for contract acquisition when document IDs exist;
- no embedding vectors required;
- provenance can contain trace/span IDs without copying full traces into the contract;
- tenant-scoped HMAC secrets prevent the same query from becoming a global cross-customer identifier.

This is pseudonymization/data minimization, not a claim of formal anonymity.

## Next interoperability adapters

The same evidence boundary should support:

1. Phoenix span exports and annotations;
2. LangSmith run/feedback exports;
3. OpenSearch search-behavior / relevance-judgment exports;
4. generic OTLP collector pipelines;
5. customer-defined SQL/Parquet feedback joins.

The principle is constant: **vendors provide observations; users/policies provide evidence; Semantic ABI compiles the evidence into portable requirements.**
