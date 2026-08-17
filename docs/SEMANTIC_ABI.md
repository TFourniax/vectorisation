# Semantic ABI — meaning as a contract, representations as implementations

## Thesis

A vector is not the data and it is not the meaning of the data. It is one coordinate emitted by one representation implementation at one point in time.

Semantic ABI asks a different production question from embedding alignment:

> **What must remain semantically true when the representation implementation changes?**

A migration can align coordinates well and still break important application behavior. Conversely, a new model can reorder many neighbors while preserving or improving the semantics the application actually needs.

The proposed abstraction is therefore:

```text
stable logical objects + semantic contract
                  |
        +---------+----------+
        |         |          |
      dense     sparse      graph       ... future representation
      model A   model B    symbolic
```

Representation systems become implementations of a stable semantic interface rather than the definition of the data itself.

This is a research hypothesis, not a claim that an embedding-independent semantic ABI has already been established as a standard.

## Contract clauses in the reference implementation

The V0.3 contract operates on stable logical IDs, never on required vector coordinates.

### Ordinal triplet

`A must prefer B over C`.

For a candidate implementation this becomes:

`sim(A, B) - sim(A, C) >= margin`

The assertion remains meaningful after rotations, dimension changes or replacement of the representation engine. Ordinal-embedding theory motivates the broader principle that relative distance information can encode structure without fixing absolute coordinates.

### Critical neighborhood

A logical object can require that a configured portion of an important semantic neighborhood remains retrievable.

This is useful both for application semantics and for explicit legacy-behavior regression contracts.

### Mutual-neighbor relation

A reciprocal semantic edge can be frozen as a stronger local-topology invariant.

Future clause families should be evidence-driven and may include typed relations, contradictions, monotonic attributes, group separation, temporal ordering, provenance/trust requirements and multimodal constraints.

## Application semantics and legacy behavior are different contracts

Semantic ABI deliberately does not collapse these questions.

**Application semantic compatibility** asks whether business/domain meaning still holds. Sources may include labels, relevance judgments, domain rules, ontologies, human review, safety cases or observed outcomes.

**Legacy behavior compatibility** asks whether selected behavior of the previous implementation survives: neighborhoods, reciprocal edges or ordinal decisions.

A representation may therefore legitimately score:

```text
application semantic compatibility = 0.95
legacy behavior compatibility      = 0.72
```

That says the implementation changed the old retriever substantially while preserving most declared application semantics. Requiring identical rankings would incorrectly reject this potentially desirable change.

## A score is not a certificate

The first prototype used a manually chosen local-risk threshold. That is no longer the intended deployment mechanism.

The current pipeline separates four concepts:

1. **contract audit** — which declared invariants hold?
2. **contract support** — is the current query in a region actually covered by audited landmarks?
3. **risk calibration** — among deployment-like held-out cases, how does proxy risk relate to observed semantic failure?
4. **statistical certificate** — what is the broadest selective region that meets a stated failure budget at a stated confidence level?

These distinctions are essential. A 0.98 contract score over 2% of a corpus is not broad coverage; a low interpolated risk far from all contract landmarks is not trustworthy; and a calibration statement from one distribution must not be silently extrapolated under shift.

## Contract support and OOD abstention

`contract_coverage()` reports how much of the logical corpus is actually referenced by the semantic schema.

`estimate_local_semantic_risk()` augments the sparse contract risk field with a support diagnostic. It estimates a reference radius from landmark-to-landmark distances. A query outside this empirical support receives an increasing risk penalty even if its nearest audited landmarks happen to have low violation risk.

Conceptually:

```text
local risk = max(interpolated contract risk, unsupported-region penalty)
```

This is a geometric diagnostic, not a theorem that detects every distribution shift. It exists to prevent a particularly dangerous failure mode: projecting confidence into regions the contract never observed.

## Finite-sample selective risk certification

`calibrate_semantic_risk()` uses held-out binary semantic outcomes to replace an arbitrary rollout threshold with an evidence-gated one.

The current reference procedure is deliberately conservative:

1. randomly split calibration events into **selection** and **certification** partitions;
2. propose a small family of proxy-risk thresholds using only the selection partition;
3. evaluate the fixed candidate family on the independent certification partition;
4. compute one-sided Bernoulli Chernoff/KL upper risk bounds;
5. allocate error probability across candidate thresholds with a union correction;
6. choose the broadest threshold whose upper bound remains below the requested semantic-risk budget;
7. **abstain** if none can be certified.

The resulting `RiskCertificate` records:

- requested risk budget;
- confidence parameter `delta`;
- certified proxy-risk threshold;
- empirical and upper-bounded failure risk;
- calibration sample counts;
- estimated selective coverage;
- method and reason.

This is not advertised as conformal prediction. It is a simple finite-sample high-probability risk-control baseline. Its validity assumes deployment resembles the independent calibration population. Covariate/configuration shift requires reweighting, recalibration or refusal; the implementation explicitly does not claim arbitrary-shift guarantees.

## Fine-grained / slice certification

Average safety can hide a broken minority region. `calibrate_semantic_risk_by_slice()` therefore constructs a `SliceRiskPortfolio` containing:

- one global certificate;
- one certificate for each declared group/slice;
- a union allocation of the overall confidence budget;
- explicit uncertified status for sparse groups.

Slices can represent language, tenant, jurisdiction, domain, product family, modality or another application-defined partition.

A query assigned to a slice is eligible only if both the global rule and that slice rule accept its risk. A rare slice with too little calibration data is not silently merged into the majority; it remains uncertified.

This is intentionally a first baseline. Future work should compare it against richer conditional/adaptive risk-control methods rather than assuming hand-written slices are optimal.

## Certified region-wise rollout

`CertifiedSemanticABIGate` combines:

- global hard-clause status;
- global contract score;
- support-aware local risk;
- the finite-sample rollout certificate.

A candidate implementation can therefore be used only where the evidence supports it, with fallback elsewhere:

```text
query
  |
  +-- supported + risk-certified region ---> candidate model
  |
  +-- uncertified / shifted region --------> legacy model or review
  |
  +-- hard semantic failure ---------------> block
```

This changes model rollout from one global switch into a potentially **selective semantic rollout**.

## Active semantic repair

Certification should not end with a red/green result. A failed audit produces a sparse map of broken contract clauses and implicated logical objects.

Two repair planners exist as transparent baselines.

### Risk/diversity planner

`plan_repairs()` prioritizes high-risk and high-centrality objects while avoiding spending the whole budget in one dense failure region.

### Cost-aware violation-coverage planner

`plan_repairs_by_coverage()` models each violated clause as violation mass:

`clause weight * (1 - clause score)`

with an optional multiplier for hard clauses.

Given a cost per logical object (human review, relabeling, re-embedding, API call, GPU work), it greedily selects the next object that covers the most previously uncovered known violation mass per unit cost, with an optional object-risk bonus.

This does **not** claim that touching one object automatically repairs every incident clause. It is a diagnostic-budget planner: maximize how much known breakage the limited investigation budget exposes.

The next scientific baselines are random selection, pure highest-risk selection, uncertainty sampling, submodular/cost-aware selection and learned active policies.

## Closed-loop semantic change management

`SemanticChangeManager` implements the control loop while deliberately keeping mutation outside the library:

```text
Contract
   |
   v
 Audit ---> Support ---> Risk calibration
   |                         |
   |                         v
   |                   Certified gate
   |                         |
 violations                  +---- candidate region
   |                         |
   v                         +---- fallback / abstain
Repair plan
   |
external review / re-embed / correct
   |
   v
Re-audit + Re-certify
```

The manager produces immutable-ish assessment data; it never silently rewrites embeddings or semantic truth. `compare_assessments()` reports whether a repair actually improved contract score, violation count and peak object risk.

## Semantic Release Certificate

A deployment decision is only useful if it can be reproduced later.

`SemanticReleaseCertificate` binds in one canonical, SHA-256-addressed manifest:

- exact implementation identity;
- provider/model revision;
- vector dimension and modality;
- preprocessing digest;
- Semantic Contract digest;
- contract audit score and hard-pass state;
- logical-object coverage;
- finite-sample risk certificate;
- hashes of benchmark/evidence artifacts;
- release status and metadata.

`ImplementationFingerprint` intentionally requires more than a human model alias. Tokenization, query prefixes, chunking, pooling and normalization can change coordinates and therefore belong in the implementation identity.

The JSON certificate is tamper-evident through a canonical digest, and referenced evidence can be verified against SHA-256 hashes. Cryptographic signatures/transparency logs are a future governance layer; the current implementation does not pretend a hash alone authenticates an issuer.

## Hash-chained semantic schema history

Contracts themselves have canonical SHA-256 identities. `ContractLedger` records their evolution in a small append-only hash chain.

This is not a blockchain claim. It makes the evolution of the semantic schema explicit:

```text
contract v1 -> contract v2 -> contract v3
     |              |              |
 release A      release B       release C
```

Production governance should ultimately bind reviewers, provenance, evidence, signatures, expiry/revocation and deployment decisions.

## Relationship to Semantic Coordinate Fabric

The layers are deliberately separable:

- **SCF:** can observations/queries move between representation coordinate systems?
- **Semantic ABI:** does an implementation preserve the application invariants that matter?
- **release control:** where, and with what measured risk, may that implementation actually serve traffic?

A mathematically good coordinate translation can still violate the ABI. A candidate can satisfy the ABI without faithfully imitating old coordinates. This is why the ABI sits above migration adapters rather than being another adapter.

## Existing evidence

### Real classical representation stress test

On 1,400 handwritten digits represented either as 64-D pixels or 324-D HOG:

- task-oriented contract: pixels ~**0.980**, HOG ~**0.911**;
- HOG after deliberate 10% identity corruption: ~**0.813**;
- captured legacy behavior: pixels **1.000**, HOG ~**0.711**, corrupted HOG ~**0.610**.

This established an important mechanism result: application compatibility and old-ranking compatibility can differ sharply.

The earlier fixed threshold coverage values are retained as historical mechanism evidence, but the production direction is now the statistically calibrated support-aware gate described above.

### Real neural encoder gate

`benchmarks/real_encoder_scifact_benchmark.py` is the next critical falsification test. It evaluates MiniLM and BGE on public SciFact relevance judgments, measures direct retrieval and cross-model transport separately, calibrates a support-aware selective risk rule, evaluates it on held-out test queries, emits an NPZ for adapter comparisons, and produces a Semantic Release Certificate tied to exact model revisions.

The benchmark is intentionally isolated in `.github/workflows/real-encoder.yml` so model downloads do not run on every code commit.

## Research questions

1. Which clause families best predict real downstream regressions rather than merely old-neighbor drift?
2. How many assertions are required to cover million/billion-object corpora economically?
3. Can contracts be learned/curated actively without encoding current-model quirks as permanent truth?
4. How should calibration adapt under domain, language, temporal and configuration shift?
5. Can semantic slices be discovered rather than manually declared?
6. What repair objective maximizes **certified coverage gained per unit cost**?
7. Can the same contract certify dense, sparse, graph and multimodal implementations?
8. Which high-order topological/ordinal invariants compress many individual clauses safely?
9. Can release certificates become interoperable across independent databases and model providers?

## Kill / narrow criteria

Semantic ABI should collapse toward ordinary regression testing if one or more of these persist on representative real systems:

- local/support-aware risk does not predict failures beyond ordinary validation metrics;
- statistically safe selective regions have negligible useful coverage;
- useful contracts require near-exhaustive annotation;
- slice certification is too data-hungry to be operationally meaningful;
- repair planning does not beat simple/random backfill on certified-coverage-per-cost;
- maintaining the semantic contract costs as much as simply re-evaluating/re-embedding everything;
- abstraction across representation families proves illusory.

A negative result is acceptable. The objective is not to preserve the name **Semantic ABI**. The objective is to discover whether a portable, auditable semantic interface can make representation changes materially safer and cheaper.