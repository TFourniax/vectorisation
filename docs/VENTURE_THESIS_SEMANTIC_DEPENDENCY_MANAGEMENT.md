# Venture Thesis — Semantic Dependency Management

**Date:** 2026-08-18  
**Status:** experimental venture + research thesis. This is not a valuation forecast, production-readiness statement, or legal novelty claim.

## Category thesis

The proposed category is **Semantic Dependency Management**.

Traditional software can depend on an interface, package version or ABI while remaining relatively indifferent to which internal implementation supplies it. AI applications cannot safely do this today: two models, retrievers or tools may expose compatible APIs yet differ in the business claims, evidence, decisions or side effects that the application actually depends on.

Semantic ABI's proposed primitive is therefore not another generic evaluator or router. It is an **application-owned compatibility boundary** plus a proof-carrying resolver:

```text
application requirement
        |
        v
semantic slot + contract
        |
        v
candidate implementations
        |
        v
compatibility evidence
        |
        v
certified substitute set
        |
        v
composition proof
        |
        v
linker / optimizer
        |
        v
proven link plan
```

The strategic claim is:

> **If application meaning can be separated from vendor implementation, AI components can become safely replaceable dependencies rather than bespoke migration projects.**

## Why the pain is structural

AI components change faster than the business requirements above them. Models are replaced, deprecated and repriced; prompts need retuning across model families; corpora and retrieval indexes evolve; tools and agent orchestrators change. API compatibility is insufficient because the failure may be semantic rather than structural.

Amazon's own 2026 model-migration tooling is direct evidence of the problem. AWS says customers can spend **days to weeks** optimizing prompts and re-evaluating responses when migrating models. Its July 2026 technical guidance names **model lock-in**, **regression blindness**, and **slow iteration cycles** as migration chokepoints. Advanced Prompt Optimization compares a baseline model with up to four candidates and reports evaluation, cost and latency. This validates the migration pain while also establishing a high competitive bar: Semantic ABI must solve something broader than prompt optimization or side-by-side model evaluation.

Sources:

- https://aws.amazon.com/about-aws/whats-new/2026/05/amazon-bedrock-advanced-prompt-optimization-migration-tool/
- https://aws.amazon.com/blogs/machine-learning/migrate-your-prompts-to-new-models-and-optimize-them-on-amazon-bedrock/
- https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-optimization-migration.html

## Why this can be a large infrastructure category

The market has already shown that reliability infrastructure around non-deterministic AI systems can support very large companies. LangChain announced a $125M financing at a $1.25B valuation in October 2025 for its agent-engineering platform, explicitly framing production agents as complex systems that require new tooling and infrastructure.

Source:

- https://www.langchain.com/blog/series-b

This does **not** imply Semantic ABI will reach a billion-euro valuation. It establishes only that horizontal AI engineering/control-plane infrastructure can attract sufficient enterprise demand and capital to make the ceiling plausible.

## Competitive correction: why a release gate is not enough

The surrounding market has moved quickly. Public products and research already cover pieces such as:

- regression tests across prompts/models/tools/retrieval;
- behavior contracts and runtime enforcement;
- release gates and deployment certificates;
- semantic/prompt versioning;
- model routing and cost/latency optimization;
- whole-agent configuration search;
- proof-carrying governance for agent actions.

Therefore **"AI regression testing with contracts" is not a defensible category thesis by itself**.

Semantic ABI's narrower differentiation is the dependency abstraction:

1. the application owns logical semantic slots rather than vendor names;
2. substitute certificates bind the exact baseline, exact application contract, evidence, environment and validity window;
3. uncertified candidates are excluded before optimization;
4. compatibility is not assumed to compose — joint component combinations may require additional evidence;
5. the output is a reusable dependency/link plan rather than merely a test report;
6. the long-term system can continuously re-resolve the implementation graph as prices, latency, regions, availability and providers change.

A professional prior-art and patentability search is still required. Public web/GitHub searches performed during this experiment did not reveal an exact end-to-end implementation of this model, but search failure is not evidence of worldwide novelty.

## The initial wedge: Migration Insurance

The first customer should not be asked to adopt an abstract new standard. They should have an urgent, measurable event:

> **"We need to switch an AI component. Prove whether we can do it without breaking our application."**

Examples include model/provider migration, frontier-to-small-model cost reduction, cloud-to-sovereign/on-prem migration, retriever/vector-database replacement, embedding-model changes, corpus re-indexing, prompt rewrites and tool/MCP upgrades.

The output should be a decision artifact:

```text
candidate: model-small-eu@3
baseline: model-frontier@stable
contract: support-production@7
coverage: 100%
hard semantic violations: 0
soft regressions: 1 within declared budget
environment: eu-prod-v4
verdict: conditional-compatible
rollout: canary
certificate: <digest/signature>
```

The buyer pays to reduce migration labor/risk and, critically, to unlock cheaper or strategically preferable providers.

## The expansion loop

A successful migration creates the exact assets required for the larger platform: contracts, probes, certificates, dependency metadata and accepted release history.

The product can then expand naturally from one migration into **continuous compatibility management**. Once multiple substitutes have certificates, the linker can re-resolve the stack under new constraints without reopening every migration from zero.

A mature request becomes:

> **"Reduce this application's inference cost by at least 35%, keep p95 below 700 ms, use EU processing only, and preserve payments-contract@12."**

The resolver may search models, retrieval implementations and tools, but it is never permitted to optimize outside the certified semantic boundary.

## Product ladder

### Open protocol / developer wedge

Open-source or freely usable components should include the contract format, local evaluator, certificate format, Technology Compatibility Kit, CLI, CI gate and basic linker. The objective is protocol adoption, not immediate seat revenue.

### Private compatibility registry

The first commercial control plane stores application contracts, provider/component manifests, evidence lineage, certificate validity, composition proofs and historical link plans. It answers which substitutes are currently admissible for a given application contract.

### Enterprise trust and policy plane

Enterprise value comes from private execution, SSO/RBAC/ABAC, trust roots, KMS/PKI signatures, revocation, policy-as-code, audit export, deployment gates, region/provider policies and continuous recertification.

### Autonomous relinking

The highest-value future layer searches for cheaper/faster/sovereign configurations, requests missing compatibility campaigns, reuses sound evidence where possible, and emits a signed link plan only if the application contract remains satisfied.

## The potential network effect

The strongest long-term moat is not an LLM judge. Judges and eval runners commoditize.

The defensible graph is:

```text
application contract class
        x
baseline component
        x
candidate component
        x
environment
        x
observed compatibility evidence
        x
composition outcomes
        x
accepted/rejected release history
```

At enterprise level this graph is private operational knowledge. At ecosystem level, providers could publish TCK-backed compatibility surfaces or certificates for standardized contract classes. The more applications define reusable contracts and the more providers certify implementations against them, the more valuable the registry becomes.

Any cross-customer learning must preserve customer confidentiality and should default to aggregate/federated/privacy-preserving patterns rather than centralizing raw proprietary traces.

## What would justify >€1B *potential*

A billion-euro outcome is plausible only if Semantic ABI becomes infrastructure rather than consulting or a one-shot migration tester.

A useful illustrative revenue scale is **€100M ARR**. That can be reached, for example, with 250 enterprise customers averaging €400k ARR, or with a smaller number of large platform customers plus usage/registry revenue. Whether that revenue supports a >€1B valuation depends on growth, margins, retention and market multiples at the time; no valuation multiple should be treated as guaranteed.

The more important strategic requirements are:

- horizontal applicability across industries and providers;
- high expansion from first migration into continuous control-plane usage;
- direct ROI from migration labor avoided and inference spend unlocked;
- protocol/registry adoption beyond the company's own UI;
- high switching cost from accumulated compatibility history and deployment-policy integration;
- low enough false-block rate that engineers keep the gate enabled;
- low enough false-admission rate for security/risk owners to trust it.

## A deliberately asymmetric business model

The protocol should be open enough to become standard infrastructure. The high-value trust/control plane should be commercial.

Potential monetization surfaces:

- enterprise platform subscription;
- certificate/compatibility campaign compute usage;
- private registry/API usage;
- self-hosted/hybrid enterprise deployment;
- provider certification/TCK services without pay-to-pass conflicts;
- regulated evidence/retention modules;
- autonomous optimization where savings create a measurable value pool.

Avoid a business model where a provider can simply pay to be labelled "compatible". Compatibility must remain an evidence outcome or the category loses credibility.

## Scientific foundation

The design is informed by active research, but no individual research primitive is claimed as invented here.

Relevant 2026 work includes:

- **Semantic Invariance in Agentic AI** — tests semantically equivalent input transformations and shows canonical benchmarks miss a reliability dimension: https://arxiv.org/abs/2603.13173
- **When Knowledge Changes: Metamorphic Testing of RAG Systems with Mutations** — tests RAG behavior under corpus mutation and reports strong fault-detection results for metamorphic oracles: https://arxiv.org/abs/2607.26843
- **Agent Behavioral Contracts** — formal/runtime contracts for agent behavior, including composition questions: https://arxiv.org/abs/2602.22302

These works strengthen the case for semantic/metamorphic contracts while simultaneously limiting what Semantic ABI can claim as novel. The product-level hypothesis is the use of such evidence as a **portable substitute/dependency proof consumed by a resolver**.

## Critical research risk: compositionality

This is the most important technical risk in the company thesis.

If model A→B is compatible and retriever X→Y is compatible, it does not follow automatically that B+Y is compatible end-to-end. Requiring a full joint campaign for every possible combination is safe but can create combinatorial explosion and destroy the economics of a compatibility registry.

The research objective is therefore not to assume composition. It is to discover **when proof can be reused soundly**.

Potential mechanisms to test include dependency slicing, assume/guarantee-style contracts, effect typing, contract-fragment independence, counterfactual replay, mutation-based adequacy and hierarchical subsystem certificates. Every proof-reuse mechanism must be validated against unseen joint faults.

## Critical research risk: adequacy

A component can pass every declared rule because the contract is incomplete.

This repository already separates clause conformity from adequacy. That separation must remain architectural. Mutation testing, held-out cases, production incidents, rare/high-criticality slices and independent downstream validation should determine whether a contract is strong enough to support a certificate.

A certificate with unknown adequacy should fail closed or carry a deliberately weaker status; a strong aggregate score must never silently promote inadequate coverage.

## Critical product risk: contract-authoring economics

If every customer needs weeks of expert work to write a useful contract, Semantic ABI becomes consulting software.

`Contract Forge` should propose invariants from production traces, incidents, corrections, domain schemas and accepted behavior — but statistical regularity is not automatically normative business truth. Human owners should approve or reject proposed hard requirements.

The KPI is **useful regression protection per expert-minute**, not number of generated rules.

## Kill criteria

This venture thesis should be narrowed or abandoned if repeated real-world studies show any of the following:

- conventional eval suites detect the same important migration failures at materially lower total cost;
- teams do not maintain contracts after the first migration;
- certificates are too environment-specific to reuse economically;
- meaningful compatibility almost never composes, causing near-complete Cartesian recertification;
- false admissions remain too high for consequential workloads;
- false blocks are high enough that engineers bypass the system;
- the cost of certification exceeds the provider/inference savings it unlocks;
- providers and infrastructure platforms have no incentive to emit/consume a neutral compatibility artifact;
- the compatibility graph has no value outside Semantic ABI's own dashboard.

## 90-day falsification program

The next phase should optimize for evidence, not feature count.

### Gate A — real model migration

Take a production-like RAG/agent workload and migrate across at least two materially different providers/model families. Compare Semantic ABI against conventional held-out evals. Record unique regressions caught, false blocks, human authoring time and compute cost.

### Gate B — real retrieval migration

Preserve the application contract across at least two actual backends/algebras (building on the existing BM25→ColBERT evidence), including provider/index changes and measured latency/cost.

### Gate C — joint incompatibility

Construct and then find naturally occurring cases where individually passing model and retriever substitutions fail as a composition. Test whether joint certificates and dependency slicing catch them without brute-force recertification of everything.

### Gate D — economic proof

For each migration, compute:

```text
migration engineering hours avoided
+ monthly infrastructure savings unlocked
+ incident/risk value if measurable
- certification compute cost
- expert contract-authoring cost
```

The product thesis becomes much stronger only when this number is repeatedly positive.

### Gate E — design partners

Work with teams that already have a planned migration. The success metric is not signups. It is whether Semantic ABI changes a real release decision, catches a confirmed break, or safely unlocks a cheaper/sovereign substitute the team otherwise would not have deployed.

## Bottom line

The billion-euro hypothesis is **not** "build a better eval dashboard".

It is:

> **Become the neutral semantic compatibility layer that lets enterprises and AI infrastructure safely treat models, retrievers and tools as replaceable dependencies.**

If that becomes a standard boundary used by CI/CD, model gateways, providers, registries and enterprise policy engines, the product can sit above — rather than compete directly with — a fast-changing ecosystem of models and infrastructure.

That is the scale opportunity. The next job is to try hard to falsify it.