# Semantic ABI — meaning as a contract, representations as implementations

## Thesis

A vector is neither the identity nor the meaning of a data object. It is one representation emitted by one implementation at one point in time.

Semantic ABI asks:

> **What must remain semantically true when the representation/retrieval implementation changes?**

```text
stable logical objects + Semantic Contract
                  |
            SemanticOracle
        +---------+---------+
        |         |         |
      dense     sparse     graph / hybrid / remote
        |         |         |
        +---- audit/risk ---+
                  |
       rollout / fallback / repair
                  |
          release evidence
```

The current project is a research hypothesis about **semantic change control**, not a claim that Semantic ABI is already an industry standard or patent-novel abstraction.

For the exact current evidence, use [`CURRENT_STATUS.md`](CURRENT_STATUS.md).

## 1. Contract surface

`SemanticContract` operates on stable logical IDs, not required vector coordinates.

Current clause families:

- **ordinal triplet** — `A must prefer B over C`;
- **critical neighborhood** — a configured fraction of important neighbors must remain retrievable;
- **mutual-neighbor relation** — a reciprocal semantic/topological relation must survive.

Clauses can be hard or soft, weighted and provenance-tagged. Contracts have canonical SHA-256 identities, can be linted for contradictions/impossible constraints and can be recorded in a tamper-evident hash-chained `ContractLedger`.

Ordinal constraints are not new mathematics; Semantic ABI uses them as one portable contract primitive. See [`PRIOR_ART.md`](PRIOR_ART.md).

## 2. Application semantics are not legacy behavior

Two contracts may legitimately coexist:

- **application-semantic contract** — what the product/domain says must remain true;
- **legacy-behavior contract** — selected old retrieval behavior we intentionally want to preserve.

A new retriever can therefore change many old nearest neighbors while improving the actual task. Conversely, a geometrically aligned replacement can still violate a hard domain assertion.

The Digits pixels↔HOG experiment demonstrates this separation:

| representation | application contract | captured legacy behavior |
|---|---:|---:|
| pixels | ~0.980 | 1.000 |
| HOG | ~0.911 | ~0.711 |
| corrupted HOG | ~0.813 | ~0.610 |

Exact old-ranking imitation is therefore not a valid proxy for application meaning by itself.

## 3. `SemanticOracle`: the ABI does not require vectors

`SemanticOracle` is the executable representation boundary. A retriever exposes:

```python
contains(object_id)
similarity(left, right)
neighbors(anchor, k)
```

Current adapters:

- `DenseVectorOracle` — cosine over dense vectors;
- `CallbackSemanticOracle` — arbitrary sparse, graph, hybrid or remote behavior.

`audit_contract()` and `evaluate_contract_clause()` operate against the oracle interface.

### First real inter-paradigm evidence

On SciFact, the exact same 650-clause contract digest

`59d34bc071273dbaa06ce03df1a3b66a2686b6b8c5f240bb49075054909c7b9f`

was evaluated against:

| implementation | ABI score | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|---:|
| BGE-small dense | **0.9467** | **0.7821** | **0.8840** | **0.8900** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 | 0.8400 |

BM25 exposed no dense vectors, evaluated **650/650 clauses** with zero missing clauses, and used the exact same contract identity.

This is meaningful evidence for representation-independent execution on one dataset/contract shape. It is **not** proof of universal portability to graph, multimodal or every hybrid retriever.

## 4. Contract score, support and deployment risk are different things

A high global contract score is not a rollout certificate.

The runtime separates:

1. **contract audit** — which declared invariants hold?
2. **contract coverage** — how much of the logical surface is actually referenced?
3. **local support** — is the current query near audited semantic landmarks?
4. **proxy risk** — does the local risk field rank likely failures?
5. **statistical certification** — does a selective serving rule meet a declared failure SLA with stated evidence?

`estimate_local_semantic_risk()` combines interpolated contract risk with an unsupported-region/OOD penalty. This is a practical diagnostic, not a theorem that detects arbitrary distribution shift.

## 5. Selective rollout certification

### Conservative family-wise baseline

`calibrate_semantic_risk()`:

1. splits calibration cases into selection and independent certification partitions;
2. proposes a family of thresholds using selection data;
3. evaluates the candidate family on certification data;
4. uses one-sided Chernoff/KL Bernoulli bounds;
5. union-corrects the error budget across candidate thresholds;
6. chooses the broadest certified rule or abstains.

### Pre-registered exact-binomial baseline

`calibrate_semantic_risk_preregistered()` addresses sample efficiency differently:

1. the selection split proposes several thresholds;
2. it freezes exactly **one** threshold under a stricter internal selection budget;
3. certification labels are then inspected only for that pre-registered rule;
4. a one-sided exact binomial upper bound certifies or rejects it;
5. if it fails, the method **cannot** post-hoc choose another threshold.

The method saves the multiplicity penalty because it certifies one fixed rule, not because it weakens the final SLA.

Neither approach is claimed as new statistics. Learn-Then-Test, conformal/selective risk control and confidence-sequence methods are stronger prior-art families that must be compared.

### SciFact result

BGE on SciFact:

- 175 calibration events;
- certification split: 87;
- held-out test queries: 200;
- support-aware failure-risk AUC on held-out queries: **0.7875**.

| target failure SLA | simultaneous KL family | pre-registered exact |
|---:|---|---|
| 5% | not certified | not certified |
| 10% | not certified | not certified |
| 15% | not certified; upper ~19.19% | **certified; upper ~13.16%** |
| 20% | certified | certified |

At the 15% pre-registered certificate:

- certification empirical risk: ~**8.05%**;
- exact upper bound: ~**13.16%**;
- held-out coverage: **197/200 = 98.5%**;
- realized held-out risk in the accepted region: ~**10.15%**.

The important result is not only the pass at 15%. **Both methods still refuse 10%**, so the sample-efficient method does not manufacture a strict certificate that the data cannot support.

## 6. Global + slice-aware certification

`calibrate_semantic_risk_by_slice()` constructs a portfolio containing one global certificate plus group-specific certificates for declared slices such as language, tenant, jurisdiction or domain.

A query assigned to a slice should be eligible only when the relevant global and slice rules permit it. Sparse groups remain explicitly uncertified.

This is a baseline; future work must compare conditional/adaptive risk-control methods and shift-aware calibration rather than assuming hand-authored slices are optimal.

## 7. Progressive Semantic Audit: reduce contract cost without deleting the contract

A separate scaling problem is **how much of a very large contract must be evaluated for a release audit**.

Experiments with fixed deterministic clause subsets failed to generalize reliably. The current promoted direction is therefore randomized sequential auditing rather than pretending omitted clauses are semantically redundant.

`progressive_semantic_audit()` defines a specific SLA:

> all hard clauses pass, and weighted soft-clause violation rate is at most `r`.

Policy:

1. evaluate **every hard clause**;
2. sample soft clauses with replacement proportional to their weights;
3. cache oracle evaluations so repeated draws are statistically valid but computationally cheap;
4. inspect results only at predeclared batch looks;
5. split `delta` across both tails and all possible looks;
6. compute exact one-sided binomial bounds;
7. return early PASS if the upper bound is ≤ the SLA;
8. return early FAIL if the lower bound exceeds the SLA;
9. if still ambiguous, evaluate the remaining contract exactly.

This is a separate policy from the historical aggregate ABI score.

### Real Digits result

With a 1,500-clause contract, baseline + four controlled corruptions and three SLAs (2/5/10%):

- **15/15** progressive decisions matched exhaustive decisions;
- **12/15** stopped without full audit;
- mean unique clauses evaluated among early decisions: **7.17%**.

Examples:

- identity permutation, SLA 5%: FAIL after **49/1,500 = 3.27%**;
- coordinate noise, SLA 5%: FAIL after **49/1,500**;
- hub-pull, SLA 5%: FAIL after **140/1,500 = 9.33%**;
- healthy baseline, SLA 10%: PASS after **186/1,500 = 12.4%**.

Three near-boundary cases fell back to the full 1,500 clauses. The healthy baseline itself has ~4.73% exact soft-clause violations, so its 5% SLA is intentionally near the boundary and did not receive a cheap shortcut.

Sequential audit/early stopping is established statistics. The research question here is whether this can make **large Semantic ABI release audits economically useful** across real heterogeneous retrievers.

## 8. Why deterministic contract compression was demoted

### Semantic Witness Set

A 1,500-clause contract was compressed and tested on changed object IDs, 3–10% fault footprints, different severities and an unseen coherent-drift family.

Representative held-out results:

- 10 clauses: TPR **62.5%**, FPR **0%**;
- 25 clauses: TPR **100%**, FPR **28.6%**;
- 100 clauses: TPR **100%**, FPR **42.9%**.

Random same-size subsets remain competitive on the overall trade-off. The module remains a research baseline only.

### Discriminative Diagnostic Panel

A learned panel achieved TPR 1/FPR 0 on its training scenarios, then **0% held-out regression TPR** across budgets 5–100 clauses.

This exposed object-local overfitting: a clause that is highly discriminative for one localized fault may simply point to where that training fault occurred.

The failed panel is not exported by the top-level API.

## 9. Active acquisition and contract adequacy

### Semantic Diff

`semantic_diff()` compares representations and `propose_contract_questions()` turns informative disagreements into ordinal domain questions.

Digits mechanism evidence:

- all disagreement questions label-resolvable: ~**11.7%**;
- top 25 proposed: **68%**;
- top 50: **60%**.

This supports active acquisition as a promising way to reduce human contract-authoring cost, while active preference/query selection itself has substantial prior art.

### Mutation adequacy

Semantic mutation testing deliberately injects identity permutation, local collapse, hub-pull and coordinate noise. The current Digits contract kills the tested mutation families, but fault localization remains much weaker than global detection.

Mutation testing is an adequacy instrument, not a novelty claim.

## 10. Active repair

A failed audit should produce more than red/green output.

Current transparent baselines:

- `plan_repairs()` — risk × violation centrality × diversity;
- `plan_repairs_by_coverage()` — known violation mass covered per unit object cost.

In a Digits/HOG experiment with 10% deliberate identity corruption, the first 25 repair candidates were truly corrupt **68%** of the time versus 10% random expectation.

The intended future metric is **certified semantic coverage gained per dollar/token/GPU-second**, not only corrupted-object precision.

## 11. Closed-loop semantic change management

```text
Contract
   |
   v
Audit / Progressive Audit
   |
   +--> support + rollout-risk calibration --> selective candidate / fallback
   |
   +--> violations --> repair plan --> external correction/re-embed
                                  |
                                  +--> re-audit / re-certify
```

`SemanticChangeManager` never silently mutates semantic truth. External systems perform review/relabeling/re-embedding; the manager produces auditable assessments and comparison deltas.

## 12. Semantic Release Certificate

`SemanticReleaseCertificate` binds:

- implementation/provider/model revision;
- representation dimension and modality;
- preprocessing digest;
- Semantic Contract digest;
- audit score/hard-pass state and logical coverage;
- finite-sample rollout certificate;
- benchmark/evidence hashes;
- release status and metadata.

Hashes make artifacts tamper-evident; they do not authenticate an issuer. Signatures, transparency logs, expiry/revocation and reviewer identity remain future governance work.

The repository is additionally moving to `docs/evidence-manifest.json`, which binds published research claims to the Git blobs of evidence-sensitive code and GitHub Actions artifact digests. CI will fail when those source blobs change without regenerating the evidence.

## 13. Relationship to SCF

The layers solve different questions:

- **SCF:** can observations/queries be transported between coordinate systems during migration?
- **Semantic ABI:** does an implementation satisfy application invariants?
- **rollout certification:** where may a candidate serve traffic under a measured failure SLA?
- **Progressive Audit:** how cheaply can a large contract be audited under a declared clause-violation SLA?

A good coordinate map can fail the ABI. A candidate can satisfy the ABI without resembling old coordinates.

On BGE→MiniLM SciFact, global mapping beats the local atlas, and evidence-gating selects global. Local SCF therefore remains optional rather than architectural dogma.

## 14. Research questions now worth pursuing

1. Does the same contract remain useful across dense, sparse, graph, hybrid and multimodal retrievers?
2. Can Progressive Audit retain large savings at 10k/100k/million-clause scale and heterogeneous clause costs?
3. Can confidence sequences / finite-population sequential methods improve sample efficiency over simple alpha spending?
4. How should query rollout certification behave under domain, language, temporal and configuration shift?
5. Which active-acquisition strategy minimizes human judgments needed per downstream regression caught?
6. What repair policy maximizes certified coverage gained per unit cost?
7. Can contract clauses become richer typed/temporal/provenance assertions without becoming an unmaintainable ontology?
8. Can release certificates become independently verifiable across model providers and databases?

## Kill / narrow criteria

Semantic ABI should collapse toward ordinary regression testing if representative systems show that:

- the ABI predicts no useful failures beyond conventional benchmark suites;
- dense↔sparse portability does not generalize to other representation paradigms;
- useful contracts require near-exhaustive annotation;
- selective rollout certificates have negligible useful coverage;
- Progressive Audit usually falls back to exhaustive evaluation;
- repair does not beat simple backfill economically;
- governance overhead costs as much as simply re-evaluating/re-embedding everything.

The objective is not to preserve the phrase **Semantic ABI**. The objective is to discover whether a portable, auditable semantic interface can make representation changes materially safer and cheaper.
