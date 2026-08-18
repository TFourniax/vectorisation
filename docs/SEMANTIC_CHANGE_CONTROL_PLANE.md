# Semantic ABI v0.6 — Semantic Change Control Plane

## One-line thesis

**Make AI-system changes backwards-compatible by contract, not by hope.**

Semantic ABI v0.6 extends the retrieval-level ABI into a representation-agnostic change-control plane for complete AI applications. A model, prompt, corpus, embedding model, retriever, reranker, tool, schema, policy or code path may change internally; deployment is authorized only when the application-specific semantic/effect contracts still hold with adequate evidence.

This is intentionally different from a generic eval dashboard. The desired primitive is closer to a machine-verifiable **semantic compatibility boundary**: a release artifact can answer whether a candidate is compatible with a particular baseline and contract, which invariants broke, what change facets are implicated, and whether rollout should be allowed, canaried or blocked.

## Why this is a distinct problem

Modern AI release engineering lacks an analogue of an ABI or backwards-compatibility checker for meaning.

Traditional software already separates implementation from contract:

- an HTTP/OpenAPI schema can stay compatible while internals change;
- an ABI can stay compatible while a library implementation changes;
- SemVer communicates whether consumers should expect breakage.

AI applications break differently. A response can remain valid JSON, the endpoint can stay up, latency can improve and aggregate eval scores can rise while a critical business meaning silently changes for a subset of users.

Existing AI eval/observability systems are valuable, but generally organize around datasets, scorers and traces. For example, Braintrust documents its core loop as data + task + scorers and promotes production failures into regression datasets. Arize Phoenix provides tracing, evaluations, datasets/experiments and embedding drift analysis. Amazon Bedrock supports model migration through prompt datasets and evaluators. These are necessary capabilities, not a portable semantic compatibility protocol.

MCP standardizes how tools/resources are exposed and called, including JSON schemas, but it does not establish that two versions of a tool, model-backed workflow or context source preserve the same application meaning.

The research literature is also converging on pieces of the problem. Recent work on semantic invariance and metamorphic testing shows that semantically equivalent input transformations can expose failures missed by canonical benchmarks. Recent RAG mutation work reports strong fault-detection results from metamorphic relations under corpus changes. Runtime-contract research argues for evidence-gated agent behavior. Semantic ABI v0.6 composes these ideas into a release-engineering primitive focused on **change compatibility**.

## Core innovation: Behavioral Compatibility Versioning

A Semantic ABI compatibility report emits a machine-derived compatibility class:

- **patch** — hard semantic/effect invariants are preserved and no soft rule regresses;
- **minor** — hard invariants are preserved, but a declared soft regression occurs within the contract's explicit error budget; rollout is canary-only;
- **major** — a hard invariant breaks, the soft budget is exceeded, or evidence is insufficient; rollout is blocked.

This is not ordinary SemVer applied to prompts. It is computed from executable evidence.

The intended long-term artifact is a signed **Semantic Compatibility Certificate** bound to:

1. baseline system manifest;
2. candidate system manifest;
3. change-set digest;
4. semantic contract digest;
5. probe/evidence digests;
6. compatibility witnesses;
7. adequacy/conformance evidence;
8. rollout decision.

The existing Semantic ABI attestation machinery can become the cryptographic envelope for that certificate.

## Representation-agnostic observation: `MeaningFrame`

The control plane does not hard-code embeddings, cosine distance, LLM judges or natural-language similarity.

Adapters normalize application behavior into stable surfaces:

- `claims` — canonical proposition IDs such as `refund:30-days`;
- `entities` — canonical entity IDs;
- `retrieved` — logical corpus-object IDs;
- `citations` — source IDs;
- `tools` — invoked capability IDs;
- `effects` — normalized externally observable effects;
- `scores` — domain-specific numeric evidence;
- `labels` — domain-specific categorical evidence;
- `output_schema_digest` — structural compatibility when relevant.

This matters because the old and new systems need not share a vector space, provider, model family or retrieval algebra. The contract is expressed above implementation details.

## Two kinds of executable invariants

### 1. Cross-version invariants

Compare the same probe on baseline and candidate.

Examples:

- candidate must preserve 100% of legally required claim IDs;
- candidate must retain at least 90% of the baseline evidence set;
- side-effect set must remain exactly identical;
- groundedness must stay above 0.93;
- cost must remain below a declared ceiling;
- output schema digest must remain stable.

### 2. Metamorphic invariants

Compare semantically related probe variants inside the candidate, without requiring a unique ground-truth answer.

Examples:

- paraphrasing a question must preserve canonical claims;
- reordering irrelevant facts must preserve tool/effect selection;
- adding non-conflicting context must not remove required claims;
- equivalent locale formatting must preserve the normalized business result.

This attacks the oracle problem directly: many important AI properties are relations among executions rather than exact target strings.

## Evidence is fail-closed

A missing probe is not a pass.

A failed execution is not silently skipped.

An unavailable score is not coerced to zero and averaged away.

If required evidence is absent or coverage is below the contract threshold, status becomes `insufficient_evidence` and rollout is `block`.

This is essential for a product intended to become deployment infrastructure rather than a reporting UI.

## Change attribution without pretending causality

Each rule can declare which change kinds it depends on. When a violation occurs, the report returns the changed facets that are plausible suspects.

Example:

- a retrieval-claim preservation rule depends on `retriever` and `corpus`;
- a release changes `retriever`, `corpus` and `model`;
- if the rule breaks, only the first two are surfaced as suspects.

This is impact localization, not a causal proof. Future work can add controlled counterfactual replay to promote suspected attribution into evidence-backed causal localization.

## Product architecture

```text
Git / CI / deployment system
          |
          v
   Change Manifest
(model/prompt/data/retrieval/tools/policy/code)
          |
          +-------------------------------+
          |                               |
          v                               v
 baseline system                    candidate system
          |                               |
          v                               v
  Adapter / Oracle                  Adapter / Oracle
          |                               |
          +----------> MeaningFrames <----+
                           |
                           v
                   Semantic Contract
                    /             \
          cross-version         metamorphic
            invariants           invariants
                    \             /
                     v           v
                    Evidence Engine
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
       witnesses       blast radius     adequacy refs
          |                |                |
          +----------------+----------------+
                           |
                           v
                Compatibility Certificate
                 patch / minor / major
                           |
                 allow / canary / block
```

## The commercial wedge

The first product should not try to govern every AI system on day one.

The wedge is **migration insurance**.

A team wants to:

- move from one model provider to another;
- adopt a cheaper/faster model;
- refresh or re-chunk a RAG corpus;
- swap an embedding model;
- change vector DB/retriever/reranker;
- upgrade a tool/MCP server;
- rewrite a system prompt;
- change agent orchestration.

Today the release owner typically asks: *"Did we break anything important?"*

Semantic ABI should answer:

> **This candidate is backwards-compatible with contract X for 99.2% of required evidence; two soft retrieval relations changed; no hard business claim or effect invariant broke; canary rollout is authorized.**

or:

> **Blocked: the model upgrade loses `refund:original-method` under paraphrased requests in EU locale. The failure is linked to the model/prompt change set and was not visible in the canonical probe.**

That is a budget-saving and risk-saving moment that can justify enterprise spend before the product becomes a broader governance platform.

## Expansion path to a control plane

### Phase A — Open standard + CLI/SDK

- contract format;
- adapter protocol;
- local differential runner;
- CI gate;
- compatibility certificate format;
- public Technology Compatibility Kit.

### Phase B — Hosted enterprise control plane

- immutable compatibility registry;
- fleet-level view of contracts and releases;
- RBAC, approvals, KMS/PKI signing;
- change graph across prompts/models/retrievers/tools/data;
- historical compatibility matrix;
- policy-as-code and release gates;
- private trace-to-contract mining.

### Phase C — Contract Forge

Use production traces, incidents, domain schemas and human corrections to propose candidate semantic invariants. Human owners approve normative contracts; the system should not silently convert statistical observations into business truth.

### Phase D — Autonomous safe migration

Given a target constraint (lower cost, lower latency, on-prem, new provider), search candidate stacks and automatically produce only candidates that obtain a compatibility certificate.

The product then becomes a **compiler for safe AI-system change** rather than merely a testing tool.

## Defensibility

The moat should not be "we have an LLM judge". That is commoditized.

Potential durable assets are:

1. **Open compatibility standard** — if Semantic ABI becomes the artifact other tools emit/consume, the protocol gains ecosystem gravity.
2. **Adapter/TCK ecosystem** — model providers, vector databases, agent frameworks and MCP servers can certify compatibility surfaces.
3. **Private compatibility graph** — enterprise history of what changed, which semantic requirements broke and what remediations restored compatibility.
4. **Cross-customer failure ontology** — privacy-preserving taxonomy of change patterns and contract templates, without collecting customer raw data.
5. **Contract Forge economics** — reducing the human cost of authoring high-value contracts is likely more defensible than running evals themselves.
6. **Signed release evidence** — compatibility certificates can become inputs to procurement, audit, internal platform policy and regulated release workflows.

## What is new here — and what is not

Not claimed as new:

- regression testing;
- LLM-as-a-judge;
- metamorphic testing;
- semantic invariance as a research property;
- embedding drift detection;
- runtime contracts;
- cryptographic hashing;
- Semantic Versioning;
- MCP/OpenAPI schemas.

The product hypothesis being tested is the **composition** of these ideas into a stable, representation-agnostic, evidence-gated compatibility layer for arbitrary AI-system changes, with a portable contract/certificate that survives replacement of internal implementations.

A professional novelty/IP review is still required before any patent claim.

## Scientific falsification plan

The thesis should be killed or narrowed if it cannot beat simpler alternatives on operational value.

### Gate 1 — independently confirmed breakage recall

Across real model/prompt/retrieval/corpus migrations, compare:

- conventional aggregate eval metrics;
- production trace score deltas;
- Semantic ABI compatibility rules.

Primary question: does the ABI find important regressions that independent downstream validation confirms and ordinary aggregate evals miss?

### Gate 2 — contract-authoring economics

Measure human minutes required to obtain useful protection.

If teams need weeks to author contracts for a one-day migration, the wedge fails. Contract Forge should reduce this to hours/minutes while preserving human approval of normative requirements.

### Gate 3 — portability

The same contract must survive at least:

- provider/model changes;
- dense ↔ sparse ↔ late-interaction retrieval;
- corpus/index changes;
- at least one tool/schema migration.

### Gate 4 — false-block rate

A control plane that blocks safe releases too often will be bypassed. Measure false blocks on independently accepted changes and require explicit error budgets.

### Gate 5 — causal localization

Test whether counterfactual replay can reduce time-to-root-cause compared with ordinary trace inspection.

## Research and market basis consulted, August 2026

- Semantic invariance in agentic AI — https://arxiv.org/abs/2603.13173
- RAG metamorphic testing under corpus mutation — https://arxiv.org/abs/2607.26843
- Metamorphic testing + LLM systematic survey — https://arxiv.org/abs/2605.13898
- Agent safety as runtime contract — https://arxiv.org/abs/2608.11274
- Alignment contracts for agentic security — https://arxiv.org/abs/2605.00081
- Query Drift Compensation for embedding-model compatibility — https://arxiv.org/abs/2506.00037
- MCP specification — https://modelcontextprotocol.io/specification/2025-11-25
- Braintrust evaluation workflow — https://www.braintrust.dev/docs/evaluate
- Arize Phoenix observability/evaluation docs — https://arize.com/docs/phoenix
- Amazon Bedrock model/prompt migration evaluation — https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-optimization-migration.html

The competitive research performed for this prototype did not identify a public system offering this exact end-to-end compatibility artifact. That is a working market hypothesis, not proof of global novelty.
