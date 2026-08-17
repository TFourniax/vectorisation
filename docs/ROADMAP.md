# Roadmap — Semantic ABI after Protocol v1

The roadmap is evidence-gated: code does not complete a phase; surviving its falsification gate does. See `CURRENT_STATUS.md` for exact dated results and `evidence-manifest.json` for machine-bound evidence.

## Completed / promoted gates

### Portable Semantic Contract

Coordinate-free application clauses, hard/soft requirements, provenance, canonical digests, ledger and linting are implemented.

### Dense / sparse / hybrid portability

Same application-contract abstraction executes across dense MiniLM/BGE, sparse BM25 and BGE+BM25 hybrid systems on SciFact/NFCorpus/FiQA.

### Predictive-superiority falsification

ABI does **not** generally beat ordinary train-query nDCG as an aggregate predictor of held-out nDCG. That claim is closed. Conventional IR metrics remain required.

### Protocol v1 compiler / wire boundary

v0.5 adds:

- directional `score(anchor,candidate)` semantics;
- batch oracle manifest/capabilities;
- canonical contract compilation;
- OpenAPI/remote client/CLI;
- conformance suite;
- compatibility preflight;
- language-neutral TCK;
- state-bound incremental execution;
- tamper-evident protocol attestation.

### Real late-interaction portability — PASSED

Same 600-clause SciFact contract executes unchanged against BM25 and real ColBERTv2 MaxSim. ColBERT has zero missing clauses, hard pass, 660/660 conformance checks and a three-batch compiled audit.

This closes “late interaction” as a first portability gate. It does not close multi-provider production interoperability.

### Progressive Semantic Audit scale

15/15 exact decisions on the 1,500-clause real-data mechanism test; 10/10 on 10k/100k/250k procedural contracts, 9/10 early. Next work is comparison with stronger sequential baselines and realistic fault dependence.

### Repair baseline / negative gates

Targeted repair beats random but does not restore 90% of downstream quality. Fixed role-weighted clause-incidence repair fails independent validation and is not promoted.

## Phase A — real provider control plane

**Goal:** prove Protocol v1 works above real deployed retrieval backends rather than only local adapters.

Targets:

1. Elasticsearch/OpenSearch BM25 + dense/hybrid adapter;
2. Qdrant adapter;
3. pgvector adapter;
4. Vespa adapter, ideally including late-interaction behavior where practical.

Required evidence per provider:

- manifest + capability preflight;
- TCK/conformance;
- unchanged application-contract execution;
- zero silent missing clauses;
- p50/p95/p99 control-plane latency;
- network payload sizes and batch counts;
- provider/API cost;
- fallback behavior;
- provider state/version identity;
- evidence that the control plane does not require rebuilding the provider's ANN index.

**Kill/narrow rule:** if adapters need provider-specific semantic clauses rather than provider-specific execution adapters, the portability thesis is weaker than claimed.

## Phase B — independent implementation / protocol reality

**Goal:** prove Protocol v1 is not accidentally Python-specific.

Implement the TCK in at least one independent language (preferred: Rust or TypeScript, then Go).

Gate:

- exact contract digest;
- exact plan digest;
- exact manifest digest;
- exact snapshot digest;
- exact protocol-audit digest;
- identical wire behavior on the canonical fixture;
- remote Python client successfully audits the external implementation and vice versa where practical.

**Kill/narrow rule:** if canonicalization/digest semantics cannot be reproduced simply outside Python, fix the protocol before adding providers.

## Phase C — graph / relational algebra

**Goal:** cross another genuinely different retrieval algebra after sparse, dense and late interaction.

Candidate experiment:

- typed graph or knowledge-graph retrieval;
- directional edge/relation scoring;
- top-k traversal/ranking exposed via Protocol v1;
- same application contract where the contract is semantically meaningful.

Use compatibility preflight to reject clauses the graph scorer cannot meaningfully execute rather than forcing false equivalence.

**Gate:** useful portable clauses must survive without pretending that every clause family is universal.

## Phase D — Contract Adequacy under shift

Test multilingual, domain, temporal and rare/high-criticality slices.

Required methodology:

- independent authoring vs adequacy/certification splits;
- explicit object/slice coverage;
- fault-family diversity;
- baseline ordinary IR metrics;
- mutation and real shift evidence;
- `insufficient_evidence` whenever a required slice has inadequate support.

Primary question:

> When does contract conformity remain informative after the deployment distribution changes?

## Phase E — state-bound incremental audits at real scale

Current incremental reuse is software-validated but not yet economically proven on real providers.

Benchmarks must simulate/version:

- unchanged provider state + contract-only edit;
- small index delta;
- model change;
- preprocessing change;
- provider config change;
- nondeterministic provider.

Report:

- operation reuse fraction;
- RPC/API calls avoided;
- latency/cost savings;
- invalidation correctness;
- false cache reuse (target: zero under declared changes).

## Phase F — Progressive Audit vs stronger statistical baselines

Compare current transparent baseline against:

- Adaptive Learn-Then-Test/e-processes;
- relevant conformal/selective-risk baselines;
- stratified/slice-aware sampling;
- heterogeneous clause/backend costs;
- non-iid and clustered failures.

The full contract must remain normative. Any faster method must earn its complexity on untouched scenarios.

## Phase G — release governance

Move `SemanticProtocolAttestation` from tamper-evident digest envelope toward independently verifiable release evidence:

- signature/KMS integration;
- model/index/provider version identity;
- state-digest requirements;
- expiry;
- revocation/quarantine;
- key rotation;
- certificate transparency / append-only release log if justified;
- evidence retention policy.

Do not claim generic attestation novelty; focus on retrieval-specific binding of portable contract + adequacy + provider execution + risk.

## Phase H — repair attribution without hand-tuned blame priors

The fixed-prior incidence planner failed independent validation.

Next research only if economic value remains material:

- learn fault attribution on training fault families;
- validate on untouched fault families;
- structural counterfactual attribution where possible;
- compare directly to simple coverage/high-risk baselines;
- measure downstream recovery per repair dollar rather than localization alone.

No new planner is promoted from the development fault on which it was designed.

## Phase I — human contract-acquisition economics

Semantic Diff is promising but must be measured against baselines with real annotation cost.

Compare:

- random disagreements;
- uncertainty;
- diversity/coverage;
- Semantic Diff priority;
- cost-aware/submodular selection.

Measure:

- expert minutes;
- accepted clauses;
- new fault families killed;
- real regressions caught;
- marginal coverage/adequacy gain.

## Phase J — novelty / publication / IP

Before any strong novelty or patent claim:

- professional patent search;
- systematic paper/product search around retrieval regression contracts, protocol conformance, AI release attestation, vector DB migration and semantic test interfaces;
- explicit claim chart separating known components from the integrated system;
- decide whether the correct output is open standard, research paper, product/control plane, patent filing, or some combination.

## Current strategic sequence

Recommended order:

1. **real provider adapters**;
2. **independent-language TCK implementation**;
3. **graph/relational retrieval gate**;
4. **adequacy under shift**;
5. **incremental audit economics**;
6. **stronger Progressive Audit statistics**;
7. **signed release governance**;
8. **human acquisition economics**;
9. **repair attribution research** only if economic signal justifies it;
10. professional novelty/IP work before public strong claims.

## End-state hypothesis

Not a better vector table and not a better benchmark score, but a control plane with:

**stable identity + portable application invariants + compiled provider-independent execution + explicit adequacy + typed implementation integrity + selective risk/fallback + state-bound incremental audit + attested release evidence + controlled semantic evolution.**

The ColBERT gate makes that hypothesis materially more credible. The next challenge is proving that the protocol remains useful across real infrastructure and operational economics, not merely additional model families.