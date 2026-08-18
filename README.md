# Semantic ABI

**Backwards compatibility for AI meaning.**

> APIs can remain valid while an AI application silently changes meaning. Semantic ABI makes the meaning/effect contract of an AI system executable, versioned and evidence-gated.

Semantic ABI began as topology-aware vector research, then became a portable contract above heterogeneous retrieval systems. **v0.6 takes the next step:** a representation-agnostic **Semantic Change Control Plane** for complete AI applications.

A model, prompt, corpus, embedding model, retriever, reranker, tool, schema, policy or code path can change internally. The release is allowed only when the application-specific semantic and externally observable effect contracts still hold with adequate evidence.

```text
                     AI RELEASE
                         |
                         v
                  Change Manifest
      model / prompt / data / retrieval / tools / code
                         |
           +-------------+-------------+
           |                           |
           v                           v
    baseline system             candidate system
           |                           |
           v                           v
       adapter                     adapter
           |                           |
           +-------> MeaningFrames <---+
                         |
                         v
                 Semantic Contract
                /                 \
       cross-version           metamorphic
         invariants             invariants
                \                 /
                 v               v
              evidence + adequacy
                         |
                         v
             Compatibility Report
             patch / minor / major
                         |
               allow / canary / block
```

## v0.6 — Behavioral Compatibility Versioning

Traditional SemVer describes intended API compatibility. Semantic ABI v0.6 introduces an executable compatibility class for AI behavior:

- **patch** — required semantic/effect invariants survive and no soft rule regresses;
- **minor** — hard invariants survive, but a declared soft regression occurs within the explicit error budget; rollout is canary-only;
- **major** — a hard invariant breaks, the soft budget is exceeded, or required evidence is missing; rollout is blocked.

The classification is derived from evidence, not from a prompt author deciding that a change "looks small".

### Representation-agnostic `MeaningFrame`

Adapters normalize application behavior into stable, application-owned surfaces:

- canonical claim IDs;
- entity IDs;
- retrieved logical-object IDs;
- citations;
- tool capability IDs;
- externally observable effects;
- domain-specific numeric scores and labels;
- output-schema digest.

The compatibility layer does **not** require baseline and candidate systems to share embeddings, coordinates, provider, model family or retrieval algebra.

### Cross-version invariants

Compare the same probe on baseline and candidate.

Examples:

- preserve 100% of required legal/business claims;
- retain at least 90% of baseline evidence IDs;
- keep the effect set exactly unchanged;
- groundedness >= 0.93;
- cost <= declared ceiling;
- output schema remains identical.

### Metamorphic invariants

Compare semantically related probe variants inside the candidate, without requiring one exact target string.

Examples:

- paraphrase must preserve canonical claims;
- irrelevant fact reordering must preserve tool/effect selection;
- locale-format variants must preserve normalized business result;
- adding non-conflicting context must not remove required claims.

This attacks the oracle problem directly: many important AI properties are relations among executions, not literal expected strings.

### Fail-closed evidence

Missing probes, failed executions or unavailable required surfaces are not silently averaged away. If required evidence is missing or probe coverage falls below the contract threshold, status becomes `insufficient_evidence` and rollout is blocked.

### Change localization

Rules can declare the component kinds they depend on. When a rule breaks, the report returns changed facets that are plausible suspects. This is impact localization, not a causal proof; controlled counterfactual replay is a future gate.

## Minimal v0.6 usage

```python
from semantic_atlas.change_control import (
    ChangeFacet,
    ChangeKind,
    ChangeSet,
    Comparator,
    CompatibilityContract,
    CompatibilityRule,
    MeaningFrame,
    ProbeObservation,
    SystemRun,
    evaluate_change,
)

contract = CompatibilityContract(
    name="support-agent",
    version="1.0",
    rules=(
        CompatibilityRule(
            rule_id="required-claims",
            target="claims",
            comparator=Comparator.BASELINE_RECALL,
            threshold=1.0,
            depends_on=(ChangeKind.MODEL, ChangeKind.RETRIEVER),
        ),
    ),
)

baseline = SystemRun(
    "prod@1",
    "manifest-old",
    (
        ProbeObservation(
            "refund",
            "refund-policy",
            "canonical",
            MeaningFrame(claims=frozenset({"refund:30-days"})),
        ),
    ),
)

candidate = SystemRun(
    "candidate@2",
    "manifest-new",
    (
        ProbeObservation(
            "refund",
            "refund-policy",
            "canonical",
            MeaningFrame(claims=frozenset({"refund:30-days", "refund:original-method"})),
        ),
    ),
)

changes = ChangeSet(
    baseline_system="prod@1",
    candidate_system="candidate@2",
    facets=(ChangeFacet(ChangeKind.MODEL, "provider-model"),),
)

report = evaluate_change(contract, changes, baseline, candidate)
print(report.status, report.semantic_version_bump, report.rollout)
```

Runnable example: [`examples/change_control_demo.py`](examples/change_control_demo.py)

Full design: [`docs/SEMANTIC_CHANGE_CONTROL_PLANE.md`](docs/SEMANTIC_CHANGE_CONTROL_PLANE.md)

Venture thesis and falsification gates: [`docs/VENTURE_THESIS_CHANGE_CONTROL.md`](docs/VENTURE_THESIS_CHANGE_CONTROL.md)

## The first commercial wedge: migration insurance

The initial product should answer one concrete question:

> **We are changing an AI component. What important behavior will break if we ship?**

Target migrations include:

- one model/provider to another;
- frontier model to cheaper/smaller model;
- cloud to on-prem/sovereign model;
- embedding-model changes;
- BM25/dense/hybrid/late-interaction retrieval changes;
- vector database or reranker changes;
- corpus refresh/re-chunking;
- prompt rewrites;
- MCP/tool/schema upgrades;
- agent orchestration changes.

The long-term product is not merely a test dashboard. It is a signed **Semantic Compatibility Certificate** consumed by CI/CD, deployment systems, enterprise policy and eventually procurement/audit workflows.

## Why this is not another eval platform

Evals, traces and observability remain necessary. Semantic ABI is designed to consume their evidence.

The intended boundary is different:

- eval platforms answer **how did this experiment score?**;
- observability answers **what happened in production?**;
- Semantic ABI aims to answer **is this candidate backwards-compatible with the application contract that production depends on?**

OpenTelemetry/OpenInference, Braintrust, LangSmith, Arize/Phoenix, Galileo, Bedrock evaluation, MCP and existing vector/search systems are potential evidence providers or integration surfaces rather than things Semantic ABI must replace.

## Existing v0.5 retrieval proof still matters

The v0.6 product direction is built on a concrete interoperability result from v0.5.

A public SciFact benchmark used real `lightonai/colbertv2.0` multi-vector representations through PyLate/Voyager + MaxSim:

- 1,800 documents;
- 300 train queries to author the contract;
- 200 untouched test queries;
- 600 application clauses;
- one unchanged contract digest across lexical BM25 and asymmetric ColBERT late interaction.

| implementation | Semantic ABI | nDCG@10 | Recall@10 | missing clauses |
|---|---:|---:|---:|---:|
| BM25 sparse | **0.9067** | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | **0.9047** | **0.7337** | **0.8395** | **0** |

ColBERT passed all hard clauses and **660/660 Protocol-v1 conformance checks with zero issues**.

This does not prove universal superiority over ordinary IR metrics. It demonstrates that one application-level semantic contract can survive a materially different retrieval algebra without common coordinates or contract translation.

## Protocol-v1 retrieval layer

The existing retrieval ABI remains part of the stack:

```text
SemanticContract
     |
     v
Protocol-v1 compiler
     |
ContractExecutionPlan
     |
     +--> dense vector retriever
     +--> sparse BM25
     +--> hybrid
     +--> ColBERT / MaxSim late interaction
     +--> graph / provider adapter
     +--> remote HTTP service
     |
     v
Conformity + Adequacy + Risk + Integrity
     |
     v
Protocol Attestation / rollout / fallback / repair
```

Protocol v1 uses three directional/batchable primitives:

```text
contains_many(ids)
score_many((anchor, candidate) ...)
neighbors_many((anchor, k) ...)
```

It includes compiler deduplication, remote transport, OpenAPI, conformance, state-bound incremental execution, tamper-evident attestation and a language-neutral TCK.

Protocol: [`docs/SEMANTIC_ABI_PROTOCOL_V1.md`](docs/SEMANTIC_ABI_PROTOCOL_V1.md)

OpenAPI: [`spec/semantic-abi-oracle-v1.openapi.yaml`](spec/semantic-abi-oracle-v1.openapi.yaml)

## Conformity is not adequacy

A candidate can satisfy every clause that exists while the contract still misses important downstream damage.

Semantic ABI therefore keeps separate:

- **Conformity** — candidate vs declared clauses;
- **Adequacy** — is the contract/test surface sufficient for the release claim?;
- **Implementation integrity** — is a concrete backend/index silently damaged?;
- **Risk certification** — where may a candidate safely serve?;
- **Attestation** — what exact contract/system/evidence produced the decision?

Missing required adequacy evidence remains `insufficient_evidence`.

## Important negative results retained

The repo deliberately preserves results that killed attractive ideas:

- local BGE→MiniLM SCF mapping loses to global;
- fixed Semantic Witness does not robustly dominate random subsets;
- learned fixed Diagnostic Panel overfits and produces 0% held-out regression recall;
- Semantic ABI is not a generally better aggregate nDCG predictor than ordinary validation;
- current repair does not reach 90% downstream recovery;
- fixed-prior repair attribution does not generalize.

Negative evidence removes unjustified complexity and is part of the product discipline.

## Validation

```bash
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python tools/check_evidence_freshness.py
```

v0.6 adds focused unit coverage for:

- safe model swap under preserved meaning;
- hard claim loss;
- metamorphic/paraphrase instability;
- missing-probe fail-closed behavior;
- soft-regression canary decisions;
- numeric quality/cost constraints;
- deterministic evidence digests.

## Highest-value next gates

1. two real model-provider adapters and two production retrieval adapters under the change-control API;
2. signed Semantic Compatibility Certificate bound into existing attestation machinery;
3. GitHub Action that blocks/canaries/allows a candidate release;
4. trace-to-contract **Contract Forge** with human approval of normative requirements;
5. independently confirmed model/prompt/corpus/tool migrations where ABI catches regressions ordinary aggregate evals miss;
6. false-block measurement on accepted releases;
7. controlled counterfactual replay for stronger root-cause localization;
8. external Rust/Go/TypeScript implementation of the compatibility/TCK surface;
9. professional novelty/IP review before patent claims.

## Scientific posture

This remains a falsifiable research and product program, not a claim that Semantic ABI is already an industry standard, production-ready, legally patent-novel, or guaranteed to become a large company.

The v0.6 hypothesis is now:

> **Can one stable, executable semantic/effect contract become the backwards-compatibility boundary for replaceable AI systems, and can the resulting compatibility certificate create enough operational value to become standard release infrastructure?**

The existing BM25→ColBERT result says the idea can already cross a materially different retrieval implementation. v0.6 tests whether the same principle can expand to the full AI change surface.