# Product thesis — from Semantic ABI research to a semantic control plane

**Status:** strategic hypothesis, not a valuation claim.  
**Objective:** identify a path where the existing protocol can become infrastructure with very large enterprise and ecosystem value without discarding the research base.

## The category

The strongest category is not "vector database", "RAG evals" or "AI observability".

It is:

> **Semantic Change Control** — prove that the behaviors an application considers meaningful survive changes to models, indexes, retrievers, data and agent memory.

The product promise is intentionally narrow enough to be testable:

> **Change anything in your retrieval/memory stack. Prove that the meaning your application depends on survived.**

That wedge can later expand into a broader **Semantic Control Plane** for AI systems.

## Why the existing project is a credible seed

The repository already contains pieces that are difficult to fake with a dashboard:

- portable, versioned Semantic Contracts;
- a coordinate-free Protocol v1;
- compiled/batched execution plans;
- remote oracle execution;
- conformance/TCK machinery;
- explicit adequacy rather than claiming conformity is sufficient;
- progressive audit;
- risk-aware rollout;
- tamper-evident attestations;
- empirical cross-algebra evidence including BM25 -> ColBERTv2;
- retained negative results that prevent attractive but unsupported mechanisms from becoming product dogma.

This base should remain intact. Product work should wrap it rather than rewrite it.

## The missing economic primitive: contract acquisition

A protocol can be technically elegant and still fail commercially if adoption requires months of expert labeling.

Contract Forge is therefore the highest-leverage v0.6 direction:

```text
existing production system
        |
        +-- retrieval traces
        +-- user selections/clicks
        +-- human corrections
        +-- support incidents
        +-- policy / safety rules
        +-- eval datasets
        +-- relevance judgments
        +-- accepted answer sources
        |
        v
   Contract Forge
        |
        +-- auto-promoted clauses
        +-- conflict detection
        +-- active review queue
        +-- provenance/evidence digest
        |
        v
  Semantic Contract
```

The adoption target is not "zero human involvement". It is **near-zero wasted human involvement**: ask a person only where one judgment meaningfully reduces important semantic uncertainty.

## Initial wedge: migration insurance

The first paid use case should be painfully concrete:

- change an embedding model;
- move Qdrant -> pgvector/OpenSearch/Vespa;
- change chunking;
- add/remove a reranker;
- change hybrid-search weights;
- migrate to late interaction;
- change an agent memory implementation;
- refresh a large corpus/index.

Today teams typically combine aggregate benchmarks, a curated eval set and manual spot checks. Semantic ABI should not replace those. It should add the missing release question:

```text
Which application-specific semantic invariants changed,
where,
why,
and is the candidate allowed to ship?
```

### Developer experience target

```bash
semantic-abi init --from-otel ./traces/
semantic-abi review
semantic-abi connect qdrant://prod
semantic-abi connect pgvector://candidate
semantic-abi diff prod candidate
semantic-abi attest candidate
```

In CI:

```text
PR / config change
    |
unit + integration tests
    |
ordinary IR / LLM evals
    |
Semantic ABI contract
    |
critical regressions? ---- yes ---> BLOCK
    |
    no
    v
signed semantic attestation
    |
canary / rollout
```

## Expansion 1: Semantic SLOs

Once contracts execute continuously, they become operational objectives rather than one-off migration tests.

Examples:

```text
critical semantic conformity = 100%
forbidden retrieval violations = 0
soft contract conformity >= 98.5%
uncertified traffic <= 2%
contract adequacy status = sufficient
semantic drift budget <= 0.3% / release
```

This moves the product toward the same operational budget that observability and security tools occupy.

## Expansion 2: self-optimizing retrieval and agent memory

The larger long-term opportunity is safe autonomous optimization.

```text
agent / optimizer
      |
proposes cheaper/faster/better implementation
      |
      v
candidate memory/retrieval stack
      |
      v
Semantic ABI + ordinary evals + risk gate
      |
 PASS | FAIL
      |
promotion only if external contract survives
```

The agent may change implementation. It may not silently rewrite the definition of success that authorizes its own change.

This separation is a key control primitive for self-improving systems.

## Expansion 3: Semantic Policy / Constitution

Retrieval is the first tractable algebra, not necessarily the final boundary.

A future contract language can add typed relations such as:

- `supports(A, B)`;
- `contradicts(A, B)`;
- `requires(A, B)`;
- `precedes(A, B)`;
- `reachable(A, B)`;
- `forbidden(A, B)`;
- temporal supersession;
- jurisdiction/scope constraints.

Backends could include vectors, sparse search, graphs, SQL-backed rules, multimodal stores and proprietary agent memory systems.

The product would then be an implementation-independent interface between applications and systems that claim to retrieve/represent meaning.

## Open-core architecture

A credible large company should avoid making the protocol itself proprietary.

### Open / standardizable layer

- contract schema;
- Protocol v1+;
- TCK;
- local CLI;
- core adapters;
- attestation verification;
- reference acquisition primitives.

This maximizes adoption and makes `Semantic ABI compatible` valuable to vendors.

### Commercial control plane

- fleet-wide contract registry/versioning;
- connector management;
- large-scale acquisition from telemetry;
- active review UX;
- CI/GitHub integration;
- managed progressive audits;
- change-impact graph;
- Semantic SLO dashboards/alerts;
- signed enterprise attestations;
- policy approval workflows;
- audit/compliance export;
- multi-team/RBAC/data residency;
- rollout/fallback orchestration;
- historical evidence store.

Revenue should come from operating semantic change safely at scale, not from hiding the interface.

## Distribution strategy

### 1. Start where a change already hurts

Migration PRs and model/index upgrades have clear before/after states, budget owners and measurable risk. A GitHub check can deliver value without replacing the customer's existing stack.

### 2. Integrate with existing observability instead of competing with it

Contract Forge should ingest OpenTelemetry/OpenInference, LangSmith, Phoenix and search behavior exports. Customers should not need to re-instrument their application for Semantic ABI.

### 3. Make backend vendors want compatibility

Qdrant, Elastic/OpenSearch, pgvector providers, Vespa, managed retrieval APIs and agent-memory vendors benefit if they can prove compatibility with customer contracts. A TCK/adaptor ecosystem can turn competitors at the storage layer into distribution channels at the control-plane layer.

### 4. Become a release artifact

A semantic attestation attached to a release/PR has much more durable organizational value than another dashboard score. If security, compliance, platform and application teams consume the artifact, Semantic ABI becomes embedded in release governance.

## Moats worth building

The protocol alone is not a moat. Potential compounding assets are:

1. **Contract acquisition data flywheel** — which signal patterns produce useful clauses with minimal expert work.
2. **Fault/mutation library** — realistic semantic failure modes by domain/backend/change type.
3. **Adequacy evidence** — knowledge of which contract surfaces detect which classes of production regressions.
4. **Adapter/TCK network** — verified implementations across retrieval and memory systems.
5. **Attestation trust** — signed, reproducible evidence accepted by enterprise release processes.
6. **Historical semantic graph** — versioned record of what meaning changed, when, and under which release.
7. **Workflow integration** — CI, incident response, canary and rollback loops.

The most defensible asset may become the mapping:

```text
change type -> likely semantic failure modes -> smallest trustworthy evidence surface
```

That mapping gets better with every real migration and incident.

## What must be demonstrated before scaling claims

A multi-billion outcome is only plausible if several hard gates succeed.

### Gate A — acquisition economics

On real production systems, demonstrate materially better **important regressions caught per expert-minute** than ordinary manual eval curation.

### Gate B — incremental value

Demonstrate real regressions where:

- aggregate nDCG/Recall or ordinary eval score looks acceptable;
- the Semantic Contract catches an application-critical failure;
- the clause existed before inspecting the candidate failure.

Otherwise this is merely a different eval syntax.

### Gate C — portability

Run unchanged contracts across real Qdrant, pgvector, OpenSearch/Elastic, Vespa, late-interaction and at least one graph/memory backend.

### Gate D — production cost

Show progressive audit + caching + state digests keep continuous semantic control economically viable at enterprise scale.

### Gate E — organizational adoption

A team that did not author the research code must be able to install, acquire a useful contract, review it and block/approve a migration without bespoke consulting.

### Gate F — independent validation

Third-party TCK implementations and external users must reproduce important protocol/evidence claims.

## Major failure modes

The project should be killed or materially repositioned if any of these remain true after serious testing:

- useful contracts require too much expert labeling;
- inferred contracts mostly preserve current system mistakes;
- ordinary eval datasets catch the same critical regressions at lower cost;
- stable logical IDs are impractical in normal retrieval stacks;
- adapters need so much backend-specific translation that portability becomes fiction;
- semantic conformity produces false confidence because adequacy cannot be established affordably;
- production audit cost/latency is too high;
- customers do not treat semantic change as a distinct budget/problem.

## Near-term build order

1. Contract Forge kernel (this branch).
2. Source-sensitive promotion + policy trust roots.
3. OpenTelemetry/OpenInference importer.
4. LangSmith/Phoenix/OpenSearch import adapters.
5. Real Qdrant + pgvector + OpenSearch Protocol-v1 adapters.
6. `semantic-abi diff` PR-oriented output with critical regression explanations.
7. Acquisition benchmark: expert-minute vs conventional eval curation.
8. Mutation/adequacy benchmark seeded from actual migration failures.
9. Signed attestations + revocation/expiry.
10. Thin hosted control plane only after the local workflow demonstrates clear value.

## North-star

The company-scale thesis is not that every AI system needs another metric.

It is that, as AI systems become continuously changing and increasingly autonomous, organizations will need a durable answer to:

> **What did this system have to keep understanding, and can we prove that the new implementation still does?**

If Semantic ABI becomes the portable artifact used to answer that question across vendors, languages, models and releases, the project can occupy a much larger layer than vector search itself.
