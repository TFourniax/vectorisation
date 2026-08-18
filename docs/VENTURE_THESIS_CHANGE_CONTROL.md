# Venture thesis — Semantic ABI as the AI Change-Control Standard

**Date:** 2026-08-18  
**Status:** experimental thesis, not a forecast or valuation claim.

## The category to build

The proposed category is **Semantic Change Control**: infrastructure that determines whether an AI-system release preserves the application meaning and externally observable effects that its consumers depend on.

The long-term ambition is to make Semantic ABI the compatibility layer between rapidly changing AI components and slow-changing business requirements.

This is a better venture target than a standalone vector database, generic agent harness or generic eval dashboard because:

1. model, prompt, retrieval, data and tool churn are structural rather than temporary;
2. the buyer's pain occurs at every consequential upgrade;
3. the layer is horizontal across AI applications and vendors;
4. it can sit above existing winners instead of replacing them;
5. standardization creates a protocol/network moat that an application-only product does not have.

## Why now

AI engineering stacks are becoming intentionally replaceable: companies compare models/providers, use multiple retrieval techniques, adopt MCP-style tool interoperability and continuously change prompts/data. The technical protocols make components easier to swap, but they do not prove that a swap preserves business meaning.

At the same time, AI eval/observability is already a validated infrastructure market. LangChain announced a $1.25B valuation in 2025 around agent engineering/LangSmith, Braintrust raised an $80M Series B in 2026 around production AI observability, and Dynatrace announced a $915M acquisition of Arize in August 2026. The opportunity is not to copy those products; it is to own the missing compatibility primitive they can integrate with.

## The wedge: Migration Insurance

Sell the first product around one painful event:

> **"We are changing an AI component. Prove what will and will not break before we ship."**

High-value migrations include:

- OpenAI/Anthropic/Google/open-model swaps;
- frontier → small/cheap model routing;
- cloud → on-prem/sovereign model migration;
- embedding-model changes;
- Pinecone/Qdrant/pgvector/Elasticsearch/Vespa retriever changes;
- chunking/reranking changes;
- corpus refreshes;
- system-prompt rewrites;
- MCP/tool/schema upgrades;
- agent-orchestrator changes.

A compatibility report should be usable by both an engineer and a risk owner:

- what changed;
- which application invariants were exercised;
- what survived;
- what broke;
- whether the evidence is adequate;
- the likely blast radius;
- allow / canary / block;
- signed evidence digest.

## Product ladder

### Free / open-source

- Semantic Contract format;
- local SDK + CLI;
- Technology Compatibility Kit;
- adapters for common providers/frameworks/vector stores;
- GitHub Action / CI gate;
- local compatibility certificate.

The open layer should maximize adoption and make the contract format a neutral standard.

### Team / cloud

- hosted run history;
- compatibility matrix across releases;
- contract registry;
- change diffs;
- team approvals;
- dashboards and alerts;
- private adapter execution.

### Enterprise control plane

- SSO/RBAC/ABAC;
- self-hosted/hybrid execution;
- KMS-signed certificates;
- policy-as-code deployment gates;
- audit/export APIs;
- regulated evidence packs;
- fleet-level component/version inventory;
- private Contract Forge;
- SLA and support.

### Autonomous migration optimizer

The highest-value future product searches the configuration space itself:

> "Find the cheapest model/retrieval/tool stack that preserves contract `payments-assistant@7` under p95 < 800ms and EU-only processing."

The output is not a recommendation; it is a candidate configuration plus a compatibility certificate. This turns Semantic ABI from test infrastructure into an optimizer/compiler for safe AI change.

## Business-model logic

A billion-euro outcome requires enterprise ACV plus horizontal adoption, not a large number of tiny developer subscriptions.

The economic value can be tied to:

- avoided incidents;
- engineering time saved during migrations;
- provider cost reductions unlocked safely;
- faster adoption of cheaper models;
- reduced vendor lock-in;
- audit/compliance evidence;
- release velocity.

This supports an enterprise platform model while keeping the standard/SDK open.

## Moat

### 1. Standard gravity

The strongest moat is becoming the default artifact for semantic compatibility, analogous in role (not mechanics) to an ABI compatibility report, SBOM or test certificate.

### 2. Compatibility graph

Over time the platform learns a graph:

`component change -> affected contract surface -> observed failure -> remediation -> accepted release`

For each customer this is proprietary operational knowledge. Across customers, only privacy-preserving aggregate patterns should be used.

### 3. Contract Forge

Authoring useful contracts is the bottleneck. A system that proposes high-value invariants from production traces, incidents, domain schemas, user corrections and expert review can lower the cost dramatically. Human approval remains required for normative business truth.

### 4. Adapter + TCK ecosystem

Providers can publish Semantic ABI adapters and certify them against the TCK. This creates distribution through the ecosystem rather than only direct sales.

### 5. Release evidence

Once compatibility certificates are consumed by deployment systems, procurement controls and auditors, switching the control plane becomes harder than switching an eval UI.

## Competitive boundary

Semantic ABI should integrate with, not initially compete head-on against:

- Braintrust / LangSmith / Arize / Galileo for traces, datasets and eval scores;
- OpenTelemetry/OpenInference for telemetry;
- MCP/A2A for component interoperability;
- Qdrant/pgvector/Elasticsearch/Vespa for retrieval;
- model gateways/providers for inference;
- data observability/lineage platforms for upstream evidence.

Those systems can become evidence providers. Semantic ABI's job is to answer the release-compatibility question above them.

## The non-obvious strategic move

Do **not** start by claiming "we govern all AI".

Start with migration insurance, because the user has a concrete baseline, a concrete candidate and a deadline. That produces measurable ROI and creates the data needed to learn the broader category.

Then expand from a single migration to continuous change control.

## What must be true for >€1B potential

The thesis deserves continued investment only if most of these become true:

1. semantic regressions during AI-stack changes are frequent and materially expensive;
2. contracts catch independently confirmed breakage that ordinary aggregate evals miss;
3. contract-authoring cost can be reduced enough for routine CI use;
4. false blocks remain low enough that engineers do not bypass the gate;
5. the same contract format works across models, retrieval, corpora and tools;
6. customers value signed compatibility evidence, not only dashboards;
7. integrations create ecosystem pull;
8. a meaningful portion of customers expand from one migration into continuous control-plane usage.

If only #1-2 hold, this may still be a good testing product but not a category-defining company. If #3-8 also hold, the platform can plausibly become foundational infrastructure.

## Immediate 90-day commercial/scientific program

### Month 1 — migration proof

- adapters for two model providers and two retrieval backends;
- 3 real migration case studies;
- compare against aggregate eval baselines;
- document regressions uniquely caught and false blocks.

### Month 2 — CI product

- GitHub Action;
- contract registry format;
- signed local certificate;
- one-command baseline/candidate comparison;
- Contract Forge alpha from traces.

### Month 3 — design partners

Target 5-10 teams that already operate production RAG/agents and have a planned migration. Success metric is not signups; it is whether the gate changes a real release decision or safely unlocks a cheaper migration.

## Kill criteria

Stop or materially pivot if:

- ordinary eval suites catch the same failures at lower authoring cost;
- teams refuse to maintain semantic contracts after the first migration;
- compatibility cannot be made representation-agnostic beyond retrieval;
- false-positive blocking is operationally unacceptable;
- the compatibility artifact has no value outside the dashboard.

The project should remain evidence-led. A unicorn thesis is useful only if it survives attempts to falsify it.
