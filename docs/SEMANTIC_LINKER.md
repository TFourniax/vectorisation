# Semantic ABI Linker — proof-carrying dependency resolution for AI

**Research preview — 2026-08-18**

## Thesis

Modern AI infrastructure makes components increasingly easy to *call* and increasingly hard to *trust as substitutes*.

A gateway can route from model A to model B. MCP can describe a tool's input/output JSON schema. An optimizer can search models, prompts and retrieval settings. A regression platform can compare baseline and candidate behavior. None of those abstractions, by itself, turns a probabilistic AI component into a dependency that an application can safely relink against the way conventional software links against an interface/ABI.

The Semantic ABI Linker explores a stronger primitive:

> **An AI application owns semantic slots. Candidate implementations become eligible dependencies only when they carry evidence that they satisfy the exact application contract, in the exact deployment environment, with composition evidence where required.**

The intended end-state is a package/dependency resolver for AI behavior rather than another model router.

## The missing abstraction

Traditional package resolution is possible because dependencies have relatively crisp compatibility surfaces: symbols, versions, types, schemas and tests.

AI applications depend on properties that ordinary schemas cannot express completely:

- which business claims must survive;
- which evidence objects must remain retrievable;
- which effects/tool choices may or may not change;
- which paraphrases/locales/context mutations must be invariant;
- what quality floor is required;
- what side effects remain forbidden;
- what combinations of model + retriever + tool still work together.

A component can therefore be API-compatible and operationally healthy while being behaviorally incompatible with the consuming application.

Semantic ABI already provides an evidence-gated contract layer. The Linker turns the resulting compatibility evidence into a dependency-resolution primitive.

## From tests to proof-carrying dependencies

The v0.6 change-control engine emits an application-specific compatibility report for a baseline/candidate change.

Only a report with `compatible` or explicitly allowed `conditionally_compatible` status can be promoted to a linker certificate. A breaking or insufficient-evidence report cannot become dependency proof.

A certificate binds at minimum:

- logical baseline component;
- candidate component;
- application contract digest;
- evidence digest;
- compatibility verdict;
- probe coverage;
- issuer;
- validity window;
- optional deployment-environment digest.

The current prototype is tamper-evident by digest and issuer-aware, not yet cryptographically signed. KMS/PKI signatures and revocation are a next gate.

## Semantic slots

The application does not ask for `provider-x/model-y`. It declares a logical dependency:

```text
slot: reasoning-model
kind: model
baseline: model:frontier@stable
semantic-contract: support-meaning@7
required-capabilities:
  - tool-use
  - json
allowed-regions:
  - eu
max-p95-latency: 800ms
minimum-evidence-coverage: 100%
```

The same pattern applies to retrievers, rerankers, tools, memory implementations, policy engines and future component kinds.

This separates the application's durable requirements from the vendor implementation that happens to satisfy them today.

## The linker algorithm

The prototype resolver applies four gates before optimization.

### 1. Structural/resource eligibility

The candidate must match the slot kind, required capabilities, region and per-component resource ceilings.

### 2. Exact contract evidence

The candidate must have a non-expired certificate for:

- the exact logical baseline;
- the exact application contract digest;
- the required deployment environment when pinned;
- the minimum evidence coverage;
- a trusted issuer when trust roots are configured.

A cheaper uncertified component is not an eligible candidate.

### 3. Composition compatibility

Individual compatibility is not assumed to compose.

A model may be compatible with the old model under isolated tests and a retriever may be compatible with the old retriever, while their *combination* changes downstream answers. The application can therefore require a joint composition certificate for a concrete set of selected components.

This is a core design choice: **pairwise/subsystem proofs are explicit instead of assuming transitivity or compositionality that has not been demonstrated.**

### 4. Constrained optimization

Only after the evidence gates does the resolver minimize an objective such as:

```text
cost_weight * unit_cost
+ latency_weight * p95_latency
+ conditional_compatibility_penalty
```

Global cost/latency ceilings can also be enforced.

The research implementation currently enumerates combinations for clarity and determinism. A production implementation would need branch-and-bound / SAT/SMT / constraint-programming techniques and incremental re-resolution for large dependency graphs.

## Why this is not a model router

A router asks some variant of:

> Which model/tool should serve this request given price, latency, capability and predicted quality?

The Semantic ABI Linker asks:

> Which implementation graph is admissible as a replacement for the application's current dependencies, given executable semantic contracts and evidence?

Routing can sit *after* linking. The linker establishes the certified candidate set; a router may dynamically choose among that set.

This creates an important separation:

```text
UNVERIFIED CATALOG
      |
      v
Semantic ABI evidence gates
      |
      v
CERTIFIED DEPENDENCY SET
      |
      +--> cost optimizer
      +--> latency router
      +--> failover
      +--> region policy
```

Optimization never gets permission to trade away an undeclared semantic invariant merely because a cheaper model scores well on a generic benchmark.

## Why this is not just regression testing

Regression testing answers whether a candidate passed a test suite.

The Linker makes that evidence *portable and composable as dependency metadata*:

- certificates have identity and validity;
- applications reference semantic slots rather than vendors;
- resolution can be rerun when prices, availability, region policy or providers change;
- individually valid dependencies can still be rejected when joint composition proof is missing;
- the resulting link plan has its own deterministic digest.

The long-term system can therefore continuously relink an application to cheaper/faster/sovereign implementations without reopening the full migration problem by hand, provided adequate fresh certificates already exist.

## The category: Semantic Dependency Management

The commercial thesis is larger than a release gate.

### Developer layer

- open Semantic ABI contract format;
- component manifest format;
- compatibility certificate format;
- local linker/resolver;
- CI integration;
- Technology Compatibility Kit.

### Compatibility registry

Providers and enterprises publish or privately retain evidence-bound substitute certificates. A registry answers queries such as:

```text
Which EU-hosted models are certified substitutes for support-model@7
under contract digest 4c83... with 100% hard-clause coverage?
```

### Enterprise control plane

- private trust roots;
- signing/revocation/expiry;
- approved-provider catalogs;
- contract and certificate registry;
- policy-as-code;
- compatibility graph;
- change lineage;
- continuous recertification;
- deployment integration.

### Autonomous relinking

The mature product receives an objective such as:

> Reduce inference spend by 40%, keep p95 below 700 ms, process data only in the EU, and do not change application contract `payments@12`.

It searches only candidates that can obtain valid evidence, proposes/executes the needed compatibility campaigns, then emits a new link plan. If a provider degrades or becomes unavailable, the resolver can choose another already-certified graph.

That is closer to a **compiler/linker for replaceable AI infrastructure** than an eval platform.

## Strategic importance

If this abstraction works, vendor choice becomes an implementation detail below an application-owned behavioral contract.

That creates value on both sides:

- enterprises gain negotiating leverage and lower migration cost;
- providers gain a standard way to prove drop-in compatibility for high-value workloads;
- infrastructure platforms can route only among certified substitutes;
- regulated teams gain traceable release evidence;
- open-model/on-prem providers can compete on certified application compatibility rather than broad benchmark claims.

The most valuable network effect would be a growing compatibility graph connecting application contract classes to proven component substitutions.

## Competitive boundary as of 2026-08-18

The surrounding market is active and close enough that novelty must be stated narrowly.

Observed adjacent categories include:

- AI/agent regression and release gates (for example AgentClash, Shadow, AgentAssay, Zowie Tester);
- behavior/runtime contracts and deployment certificates (for example GuardPrompt and recent academic work on agent behavioral/runtime contracts);
- prompt/model versioning and migration tooling;
- model gateways and cost/latency routers;
- whole-agent configuration optimization;
- AI skill/package registries;
- proof-carrying governance for consequential agent actions.

The prototype therefore **does not claim novelty for contracts, certificates, SemVer, regression gates, routing, optimization, or proof-carrying AI individually.**

The narrower hypothesis is the combination of:

1. application-owned, representation-agnostic semantic ABI contracts;
2. evidence-bound substitute certificates tied to exact baseline + contract + environment;
3. explicit non-assumption of composition, with joint composition certificates;
4. dependency resolution that excludes uncertified candidates *before* cost/latency optimization;
5. continuous relinking of heterogeneous AI implementations under the preserved application contract.

The searches performed for this research did not identify a public product implementing this exact semantic dependency-resolution model end-to-end. That is a research finding, not proof of worldwide novelty or patentability. A professional prior-art/IP review remains mandatory before strong legal novelty claims.

## Scientific questions that can kill the idea

### Does compatibility compose often enough to be useful?

If every combination needs a full end-to-end recertification, certificate reuse may collapse and the registry becomes little more than an eval cache.

Research target: identify contract fragments and component boundaries where compositional guarantees can be soundly reused, and explicitly fall back to joint evidence elsewhere.

### Are certificates portable enough?

A certificate tied to every microscopic environment detail may be safe but economically useless. One tied too loosely may be unsafe.

Research target: derive the minimum environment fingerprint necessary for reliable reuse.

### Does relinking save more than certification costs?

The economic unit is not eval accuracy; it is migration cost avoided / spend unlocked per expert-hour and compute euro spent on certification.

### Can false admission be bounded?

A false compatible certificate is more dangerous than a false block. Adequacy and mutation testing must remain separate from mere clause conformity.

### Can the graph scale?

Exact composition evidence creates combinatorial pressure. The system needs principled proof reuse, dependency slicing and incremental certification rather than blind Cartesian evaluation.

## Immediate research gates

1. convert v0.6 change reports into linker certificates end-to-end;
2. add Ed25519/KMS signing, revocation and validity verification;
3. implement real OpenAI/Anthropic/open-model offers plus Qdrant/Elasticsearch/pgvector/Vespa adapters;
4. demonstrate a two-slot migration where the cheapest individually compatible pair is jointly incompatible and the linker catches it;
5. benchmark resolver/certification economics against ordinary model-router + eval workflows;
6. study compositional certificate reuse on model × retriever × reranker × tool graphs;
7. ship a CLI (`semantic-abi link`) and GitHub Action;
8. build a private registry prototype.

## Research basis

The design builds on, but is not equivalent to, several active lines of work:

- semantic invariance and metamorphic testing of AI agents;
- metamorphic testing under RAG corpus mutation;
- agent regression testing and compatibility gates;
- behavioral/runtime contracts;
- component routing and whole-agent optimization;
- proof-carrying agent governance;
- traditional semantic versioning, contract testing, ABI compatibility and dependency resolution.

The strongest existing repository evidence remains the v0.5 result that one unchanged application Semantic Contract executed across sparse BM25 and real asymmetric ColBERTv2/MaxSim retrieval without shared coordinates or contract translation. The Linker generalizes that insight into a dependency-management hypothesis: **if application meaning can be separated from implementation algebra, proven-compatible implementations can become resolvable dependencies rather than bespoke migrations.**
