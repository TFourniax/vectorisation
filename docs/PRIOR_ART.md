# Prior art and differentiation notes

This is a living research map, **not** a novelty or patent opinion. The literature is moving quickly; claims must narrow whenever stronger prior art appears.

## Current position

The original V0.2 thesis—embedding models as interoperable coordinate systems—overlaps materially with active academic work and older representation-compatibility literature. **SMA/SCF must not claim that cross-model translation, local alignment, composable translation, confidence-aware routing or embedding-independent vector-database representations are broadly new.**

The strongest current systems hypothesis is instead the **Semantic ABI / semantic change-management layer**:

> versioned, coordinate-free application invariants evaluated through a representation-agnostic behavior interface, combined with support-aware risk, evidence-gated rollout/fallback, active contract acquisition/repair and reproducible release evidence.

Even that complete formulation remains a hypothesis. Individual ingredients have substantial prior art, documented below.

## Cross-model embedding interoperability

### Integrating Vector Databases across Embedding Models — SIGMOD 2026

Beining Yang, Yang Cao and Yang Ren, *Integrating Vector Databases across Embedding Models*, ACM SIGMOD 2026 (Best Paper Honorable Mention).

This work directly studies integration of vector databases produced by different embedding models, using local cross-model geometric consistency and real model evaluations. It is direct prior art against broad SCF interoperability claims.

### Generalizable and Composable Multi-Model Embedding Translation — ICML 2026

Beining Yang and Yang Cao, *Generalizable and Composable Multi-Model Embedding Translation*, ICML 2026 Spotlight.

This work covers multi-model translation, OOD behavior, composed/chained translations, geometry-aware confidence and localized adaptation through hierarchical mixture-of-experts designs.

SCF therefore does **not** claim novelty for:

- local embedding translation by itself;
- query/model-specific translation confidence by itself;
- chaining translations across representation models;
- localized experts for cross-model interoperability.

### Vector Linking via Cross-Model Local Isometric Consistency — ICML 2026

Ziying Chen, Yang Cao, He Sun, Beining Yang and Tianjian Yang, *Vector Linking via Cross-Model Local Isometric Consistency*, ICML 2026.

This provides theoretical/empirical support for local geometric consistency between independently trained contrastive encoders and anchor-based vector linking. It supports local methods while constraining novelty claims around the atlas metaphor.

### Metric Algebra: Embedding-Independence in Vector Databases — accepted SIGMOD 2027

Tianjian Yang, Yang Cao, Beining Yang, Ziying Chen and Tiejun Ma, *Metric Algebra: Embedding-Independence in Vector Databases*, accepted for SIGMOD 2027.

The authors position it as an intermediate representation for embedding independence in vector-database systems. Until the full work can be reviewed, broad claims around representation-independent vector-database IRs should be assumed to overlap materially.

### Drift-Adapter — EMNLP 2025

Harshil Vejendla, *Drift-Adapter: A Practical Approach to Near Zero-Downtime Embedding Model Upgrades in Vector Databases*, EMNLP 2025.

It maps new queries into a legacy space using paired anchors and evaluates orthogonal Procrustes, low-rank affine and residual-MLP adapters. This is strong prior art for migration-time query transformation and deferred re-embedding.

### Older compatibility literature

Backward/forward-compatible representation learning substantially predates this repository: Forward Compatible Training, bidirectional compatibility, learning compatible embeddings, neighborhood-consensus approaches, Darwinian/selective model upgrades and heterogeneous visual-search compatibility all establish representation compatibility as a long-standing problem.

*Query Drift Compensation* (CoLLAs 2026) further studies continual text-retrieval model updates by projecting new queries into old embedding spaces.

## Coordinate-free semantic primitives

### Ordinal embedding

Ordinal-embedding literature studies constraints such as “A is closer to B than C” without fixing absolute coordinates. Semantic ABI uses that mathematical primitive as a contract clause; it does **not** claim to invent ordinal constraints.

The systems hypothesis is to use stable-ID ordinal/topological assertions as a compatibility interface across changing retrieval implementations and to combine them with provenance, versioning, support, risk and deployment control.

### Vector Annotation Databases

A 2026 SSRN paper, *Vector Annotation Databases: An Architecture for Auditable Semantic Retrieval*, argues for explicit data objects and deterministic semantic metadata with vectors as replaceable annotations. It is relevant conceptual prior art for treating embeddings as derived rather than canonical.

### Uncertainty-aware and adaptive retrieval

Work such as *DINOSAUR: Distributional Approximate Nearest Neighbour Search for Uncertainty-Aware Retrieval* rejects the assumption that uncertain representations must collapse to a single point. SCF SemanticCells encode disagreement differently; uncertainty-aware retrieval itself is not novel.

Moskvoretskii et al., *Adaptive Retrieval Without Self-Knowledge? Bringing Uncertainty Back Home* (ACL 2025), compare 35 adaptive-retrieval/uncertainty approaches across six datasets and show that relatively simple uncertainty techniques can outperform more elaborate adaptive pipelines on efficiency/self-knowledge while retaining comparable QA quality. This reinforces the repository rule that complex runtime routing must beat simple uncertainty baselines before it is promoted.

### Hubness

Hubness diagnostics and local-scaling/CSLS-like remedies predate SMA. They are mechanisms, not novelty claims.

## Property testing, deployment gates and statistical risk control

Semantic ABI must avoid a broad claim that it invented “testing model properties and using statistics to gate deployment.”

Relevant prior art includes:

- **Learn-Then-Test (LTT)** — converts risk control over a family of candidate rules into a multiple-hypothesis testing problem;
- **Adaptive Learn-Then-Test (aLTT)** — Zecchin, Park and Simeone, ICML 2025, uses sequential data-dependent multiple-hypothesis testing with e-processes and early termination while retaining finite-sample population-risk guarantees;
- **Conformal Risk Control / distribution-free risk-controlling prediction sets** — controls general losses rather than only marginal coverage;
- **Aligning Model Properties via Conformal Risk Control** (NeurIPS 2024) — explicitly combines property-testing ideas with conformal risk control;
- **Localized Adaptive Risk Control** (NeurIPS 2024) — addresses locally varying risk rather than one global threshold;
- **Selective Conformal Risk Control** (2025) — combines abstention/selective prediction with risk control.

The current `split-chernoff-kl`, `split-preregistered-exact-binomial` and progressive-audit alpha-spending procedures in this repository are transparent statistical baselines, **not new statistical theory**. In particular, the fact that `progressive_semantic_audit()` can stop early is not itself a novelty claim: sequential testing and adaptive early stopping with stronger e-process machinery already exist.

Potential differentiation must be tested at the systems level: whether sequential risk control applied to a **portable hard/soft Semantic Contract** materially reduces the cost of auditing heterogeneous retrieval implementations while remaining composable with fallback, repair and release evidence.

The exact-binomial rollout baseline is intentionally restricted to **one rule frozen before certification labels are inspected**. Traditional binomial-proportion confidence intervals are appropriate for such fixed Bernoulli safety statements; they must not be misused to justify post-hoc threshold selection on the same holdout.

## Retrieval test adequacy and coverage

Kim, Pasini and Tonella, *Testing Retrieval-Augmented Generation Systems with Chunk Coverage* (2026), introduce **Chunk Coverage** as an oracle-independent adequacy criterion for retrieval testing and use coverage-guided query selection/generation to exercise previously uncovered retrieval regions. Their experiments report faster coverage growth and earlier fault discovery than random/redundancy-biased baselines.

This is close prior art for any broad claim that this repository invented:

- retrieval test coverage as an adequacy signal;
- coverage-guided test selection;
- using structural coverage to discover retrieval faults earlier.

Semantic ABI's `contract_coverage()` is different in object: it measures how much of the logical corpus is referenced by a normative semantic contract rather than how much of a corpus has been retrieved by a query test suite. But the conceptual neighborhood is now explicit, and future contract-acquisition experiments must compare against chunk/retrieval-coverage-guided baselines instead of treating coverage as an unexplored idea.

## Active contract acquisition

`Semantic Diff` prioritizes disagreements between implementations and turns them into ordinal questions for human/domain review. The broad principle of querying informative comparisons is not new.

Relevant prior art includes active learning with label comparisons, active preference learning, active query synthesis and recent preference-data acquisition systems such as ActiveUltraFeedback. These works support the possibility that informative comparisons can reduce annotation cost while constraining novelty claims around “ask only useful pairwise questions.”

Potential differentiation must therefore come from the role those questions play in a **versioned representation-independent semantic contract and deployment lifecycle**, not from active preference querying alone.

## Contract sparsification / diagnostic subsets

The repository experimentally asked whether a much smaller fixed subset of a Semantic Contract could retain the full contract’s regression-detection behavior.

Test-suite minimization, requirements-coverage-guided selection, mutation-based adequacy and fault-detection-preserving test reduction are established software-testing research areas. The repository therefore does **not** claim novelty for test-suite reduction itself.

More importantly, current evidence **falsified the naive fixed-subset approach**: greedy witness sets lost sensitivity/specificity on held-out localized faults, and a discriminative diagnostic panel overfit affected object identities. The current architecture therefore keeps the full contract normative and investigates randomized/progressive evaluation instead of claiming that a tiny deterministic witness is equivalent to the contract.

This negative result matters for novelty discipline: future work should not rename ordinary test minimization as a semantic invention. Any compact/cheap audit mechanism must establish a statistically explicit relationship to the full contract on unseen faults.

## Semantic mutation testing

Mutation/metamorphic testing also predates this project in software and ML systems. Semantic mutation testing is used here as an **adequacy instrument**: deliberately corrupt a representation and ask whether the contract detects and localizes the damage. The contribution, if any, must be in how mutation adequacy informs contract acquisition and release control—not the existence of mutation testing.

## AI attestation and pre-deployment certificates

The generic idea of binding evidence to an AI release is also **not** new.

Relevant 2026 work includes:

- Tan, Singer and Anagnostopoulos, *Attesting LLM Pipelines: Enforcing Verifiable Training and Release Claims* — proposes an attestation-aware promotion gate that cryptographically binds lineage/security claims to LLM pipeline artifacts and verifies evidence before promotion into trusted environments;
- Tuan and Sanyal, *Toward Pre-Deployment Assurance for Enterprise AI Agents: Ontology-Grounded Simulation and Trust Certification* — proposes an operational envelope, generated verification scenarios and a machine-verifiable Trust Certificate with graduated deployment verdicts.

These works are adjacent enough that `SemanticReleaseCertificate` must **not** claim novelty for AI release manifests, cryptographic evidence binding, promotion gates or machine-verifiable certificates in general.

The narrower open systems question here is different: can a release attestation bind an implementation to a **portable retrieval-behavior contract**, with exact contract identity, adequacy evidence, support-aware/selective semantic risk, fallback semantics and repair/re-certification history? That integrated retrieval-specific role remains a hypothesis, not a novelty conclusion.

## What remains potentially differentiated

The strongest current integrated systems hypothesis is:

> **A retrieval/data system should expose a stable Semantic ABI above representation implementations: versioned application invariants evaluated through a common semantic-oracle interface, with contract adequacy tests, support-aware/local risk, statistically controlled progressive/full audit, rollout certificates, selective fallback, cost-aware repair and tamper-evident release evidence.**

This is meaningfully different from embedding translation alone because a candidate can:

- satisfy application semantics without reproducing legacy rankings;
- reproduce geometry yet fail a hard semantic clause;
- be dense, sparse, graph-based or otherwise non-isomorphic to the old representation;
- be accepted in one supported region and rejected/abstained elsewhere;
- trigger targeted review/re-embedding rather than full backfill;
- carry a release certificate bound to exact implementation/preprocessing/evidence identity.

**This is still not a novelty conclusion.** A professional patent search and broader systems-literature search remain necessary before any IP claim.

## Highest-priority prior-art searches remaining

Before strong publication/IP claims, continue targeted searches for:

- semantic regression contracts specifically for retrieval/ranking systems;
- specification-driven information-retrieval deployment gates;
- region-wise/selective rollout driven by semantic invariants;
- coordinate-free retrieval intermediate representations beyond vector systems;
- semantic test adequacy across heterogeneous retrievers;
- retrieval-specific semantic release attestations and behavior certificates;
- patents on embedding compatibility certification, semantic regression testing and selective semantic deployment.

## Kill criterion

Semantic ABI should collapse toward ordinary regression testing if representative experiments show that portability, local risk calibration, active acquisition/repair or rollout economics add little beyond conventional benchmark suites.

The project should preserve evidence, not its terminology: if a simpler abstraction wins, keep the simpler abstraction.
