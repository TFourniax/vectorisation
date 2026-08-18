# Semantic ABI

**A proof-carrying linker for replaceable AI infrastructure.**

> APIs tell us whether two components can communicate. Semantic ABI asks whether one component can replace another **without breaking the application meaning and effects that consumers depend on**.

Semantic ABI began as topology-aware vector research, then became a portable semantic contract above heterogeneous retrieval systems. The current experimental branch advances the idea into two layers:

1. **v0.6 Semantic Change Control** — executable, representation-agnostic compatibility contracts for model/prompt/data/retrieval/tool changes;
2. **v0.7 Semantic Linker** — dependency resolution that only considers components carrying evidence for the exact application contract, and can require proof that selected components remain compatible when composed.

The long-term category is **Semantic Dependency Management**: applications depend on semantic slots, not vendors; implementations compete to become proven-compatible substitutes.

```text
                       APPLICATION
                           |
                           v
                    Semantic Slots
        model / retriever / reranker / tool / ...
                           |
                           v
                   Semantic Contracts
                           |
              +------------+------------+
              |                         |
              v                         v
        candidate catalog        change-control runs
  cost/latency/region/caps       semantic + effect evidence
              |                         |
              |                         v
              |               Compatibility Certificates
              |                         |
              +------------+------------+
                           |
                           v
                    SEMANTIC LINKER
         rejects uncertified / stale / wrong-env
                           |
                  composition evidence
                           |
                           v
                 Proven Link Plan
                           |
             +-------------+-------------+
             |             |             |
          routing        failover     optimization
```

## v0.7 — Semantic Linker

A normal model router may choose a candidate because it is cheap, fast and scores well. Semantic ABI reverses the order:

1. **prove admissibility first**;
2. **optimize second**.

A candidate is eligible only if it satisfies the slot constraints and carries a compatibility certificate for the exact:

- logical baseline component;
- Semantic ABI contract digest;
- required evidence coverage;
- deployment environment when pinned;
- validity window;
- trusted issuer when configured.

Only then may cost/latency optimization consider it.

### Composition is not assumed

Two replacements can each be compatible in isolation and still fail together.

The v0.7 resolver can therefore require a `CompositionCertificate` for the concrete selected set. A cheaper model + retriever pair is rejected if the application requires end-to-end evidence and that pair has not earned it.

This is a deliberate scientific constraint: Semantic ABI does **not** assume compatibility is transitive or compositional unless evidence justifies reuse.

### Proof chain

`src/semantic_atlas/certificate_bridge.py` connects the layers. Only `compatible` or explicitly conditional change-control reports can be promoted into linker certificates. `breaking` and `insufficient_evidence` reports cannot become dependency proof.

The current certificate is digest-bound and issuer-aware. Cryptographic signatures, trust roots, expiry/revocation infrastructure and KMS/PKI integration are next gates; this branch does not pretend a string issuer is already a secure signature system.

### Minimal dependency model

```python
from semantic_atlas.linker import (
    ComponentKind,
    SemanticSlot,
    LinkPolicy,
    resolve_semantic_dependencies,
)

slot = SemanticSlot(
    slot_id="reasoning-model",
    kind=ComponentKind.MODEL,
    baseline_component_id="model:frontier@stable",
    contract_digest="contract:support-meaning@7",
    required_capabilities=frozenset({"tool-use", "json"}),
    allowed_regions=frozenset({"eu"}),
    minimum_probe_coverage=1.0,
)

result = resolve_semantic_dependencies(
    [slot],
    offers,
    certificates,
    policy=LinkPolicy(
        cost_weight=1.0,
        latency_weight=0.001,
        environment_digest="support-prod-eu-v7",
    ),
)
```

Runnable demo: [`examples/semantic_linker_demo.py`](examples/semantic_linker_demo.py)

Full design: [`docs/SEMANTIC_LINKER.md`](docs/SEMANTIC_LINKER.md)

## v0.6 — Behavioral Compatibility Versioning

The linker depends on the change-control engine rather than replacing it.

A model, prompt, corpus, embedding model, retriever, reranker, tool, schema, policy or code path can change internally. Adapters normalize observable application behavior into a representation-agnostic `MeaningFrame` containing surfaces such as:

- canonical claim IDs;
- entity IDs;
- retrieved logical-object IDs;
- citations;
- tool capability IDs;
- externally observable effects;
- domain-specific numeric scores/labels;
- output-schema digest.

The engine supports two rule families.

### Cross-version invariants

Compare the same probe on baseline and candidate, for example:

- preserve 100% of required business/legal claim IDs;
- retain at least 90% of required evidence objects;
- keep side effects exactly unchanged;
- maintain a groundedness floor;
- remain below a declared cost ceiling.

### Metamorphic invariants

Compare semantically related executions without requiring one exact expected string, for example:

- paraphrases preserve required claims;
- irrelevant fact reordering preserves effect selection;
- equivalent locale formatting preserves normalized business result;
- adding non-conflicting context does not remove required claims.

### Evidence-derived compatibility version

The report emits an executable compatibility class:

- **patch** — hard invariants preserved, no soft regression;
- **minor** — hard invariants preserved, declared soft regression stays within budget; canary only;
- **major** — hard break, soft budget exceeded, or evidence insufficient; block.

This is not ordinary prompt SemVer. The classification is derived from an evidence run.

Runnable demo: [`examples/change_control_demo.py`](examples/change_control_demo.py)

Full design: [`docs/SEMANTIC_CHANGE_CONTROL_PLANE.md`](docs/SEMANTIC_CHANGE_CONTROL_PLANE.md)

## The product thesis

The first commercial wedge remains **migration insurance**:

> **We are changing an AI component. What important behavior will break, and which substitutes are actually safe for this application?**

After enough certificates exist, the product can move from migration testing to continuous dependency resolution:

> **Reduce inference cost by 40%, keep p95 under 700 ms, process only in the EU, and preserve contract `payments@12`.**

The system searches candidate implementations, obtains or reuses adequate compatibility evidence, and emits a new link plan. A router can then choose dynamically only inside the certified set.

This is the strategic difference between the end-state and a generic eval dashboard, agent release gate or LLM gateway.

Commercial/falsification thesis: [`docs/VENTURE_THESIS_CHANGE_CONTROL.md`](docs/VENTURE_THESIS_CHANGE_CONTROL.md)

## Why this is not just an eval platform or router

Evals, traces, observability, gateways and optimizers are evidence/input providers.

Their questions are typically:

- **Eval:** how did this candidate score?
- **Observability:** what happened in production?
- **Router:** which model should serve this request?
- **Optimizer:** which configuration maximizes an objective?

Semantic ABI's intended question is different:

> **Which implementation graph is admissible as a backwards-compatible dependency of this application?**

Optimization happens only after the compatibility boundary.

## Existing v0.5 interoperability evidence

The v0.7 thesis is not starting from a blank page.

A public SciFact experiment used real `lightonai/colbertv2.0` multi-vector representations through PyLate/Voyager + MaxSim:

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

The promoted claim is narrow: one application-level semantic contract survived a materially different retrieval algebra without common coordinates or contract translation. It does not prove that Semantic ABI replaces nDCG, that ColBERT is universally superior, or that compatibility automatically composes.

## Protocol-v1 retrieval ABI

The existing retrieval protocol remains a concrete backend interoperability layer:

```text
SemanticContract
     |
     v
Protocol-v1 compiler
     |
ContractExecutionPlan
     |
     +--> dense
     +--> BM25 / sparse
     +--> hybrid
     +--> ColBERT / MaxSim
     +--> graph / provider adapter
     +--> remote HTTP service
     |
     v
Conformity + Adequacy + Risk + Integrity
     |
     v
Attestation / rollout / fallback / repair
```

Protocol: [`docs/SEMANTIC_ABI_PROTOCOL_V1.md`](docs/SEMANTIC_ABI_PROTOCOL_V1.md)

OpenAPI: [`spec/semantic-abi-oracle-v1.openapi.yaml`](spec/semantic-abi-oracle-v1.openapi.yaml)

## Conformity is not adequacy

A candidate can satisfy every clause that exists while the contract still misses important downstream damage.

The project therefore keeps separate:

- **conformity** — candidate vs declared clauses;
- **adequacy** — is the observed/tested surface sufficient for the release claim?;
- **implementation integrity** — is one backend/index silently damaged?;
- **risk certification** — where may a candidate safely serve?;
- **attestation** — what exact contract/system/evidence produced the decision?;
- **dependency compatibility** — may a component or composition enter the linkable set?

Missing required evidence fails closed.

## Negative results remain first-class

The repository deliberately preserves findings that killed attractive ideas:

- local BGE→MiniLM SCF mapping loses to global;
- fixed Semantic Witness does not robustly dominate random subsets;
- learned fixed Diagnostic Panel overfits and gets 0% held-out regression recall;
- aggregate Semantic ABI score is not generally a better nDCG predictor than ordinary validation;
- current repair does not reach the preregistered 90% downstream-recovery target;
- fixed-prior repair attribution does not generalize.

The project is intentionally evidence-gated rather than novelty-by-assertion.

## Validation

```bash
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python tools/check_evidence_freshness.py
```

The new branch adds focused coverage for:

- model swap under preserved meaning;
- hard semantic claim loss;
- metamorphic/paraphrase instability;
- missing-evidence fail-closed behavior;
- soft-regression canary decisions;
- numeric quality/cost constraints;
- deterministic evidence digests;
- uncertified dependency rejection;
- certificate expiry/resource constraints;
- conditional-evidence penalty;
- mandatory joint composition evidence;
- blocking promotion of breaking change reports into linker certificates.

## Highest-value next gates

1. **real providers:** model-provider + retrieval-provider adapters under the same change-control surface;
2. **cryptographic trust:** Ed25519/KMS signing, revocation, validity and verifier tooling;
3. **composition science:** quantify when certificates can be safely reused vs when full joint recertification is mandatory;
4. **registry:** private compatibility graph and content-addressed certificate store;
5. **resolver scale:** branch-and-bound / SAT/SMT / incremental re-resolution instead of Cartesian enumeration;
6. **CI product:** `semantic-abi link` plus GitHub Action and machine-readable deploy gate;
7. **Contract Forge:** propose high-value invariants from traces/incidents while keeping human approval of normative truth;
8. **economic proof:** demonstrate migration/spend savings net of certification cost;
9. **external TCK:** independent Rust/Go/TypeScript compatibility implementation;
10. **professional novelty/IP review** before patent claims.

## Scientific posture

This repository does **not** claim that contracts, regression testing, metamorphic testing, proof-carrying systems, routing, optimization, semantic versioning or certificates were invented here.

The v0.7 research hypothesis is narrower:

> **Can application-owned semantic contracts turn probabilistic AI implementations into evidence-bound, resolvable dependencies, such that a system can safely relink models, retrievers and tools without coupling business meaning to a vendor implementation?**

If the answer is yes at acceptable certification cost and false-admission rate, Semantic ABI can become a compatibility standard and control plane rather than another testing product. If not, the linker thesis should be narrowed or killed.