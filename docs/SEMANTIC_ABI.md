# Semantic ABI — portable meaning contracts with explicit adequacy

## Thesis

A vector is neither the identity nor the meaning of a data object. It is one representation emitted by one implementation at one point in time.

Semantic ABI asks:

> **What must remain semantically true when the representation/retrieval implementation changes, and what evidence is required before that statement is trusted?**

The latest experiments force an important three-way separation:

```text
                    stable logical objects
                            |
                 Application Semantic Contract
                  portable normative invariants
                            |
                      SemanticOracle
           dense / sparse / graph / hybrid / remote
                            |
                  Contract Conformity Audit
                            |
             +--------------+---------------+
             |                              |
      Contract Adequacy              Implementation Integrity
  is the observation surface       canaries for one concrete
   sufficient for this claim?       implementation/index
             |                              |
             +--------------+---------------+
                            |
                     support + risk
                            |
                   rollout / fallback
                            |
                    repair / re-audit
                            |
                     release evidence
```

This is a research program about **semantic change control**, not a claim that Semantic ABI is already a standard or patent-novel abstraction.

For exact dated evidence, see [`CURRENT_STATUS.md`](CURRENT_STATUS.md) and [`evidence-manifest.json`](evidence-manifest.json).

## 1. Application Semantic Contract

`SemanticContract` operates on stable logical IDs, not required vector coordinates.

Current clause families:

- **ordinal triplet** — `A must prefer B over C`;
- **critical neighborhood** — a configured fraction of important neighbors must remain retrievable;
- **mutual-neighbor relation** — a reciprocal semantic/topological relation must survive.

Clauses can be hard or soft, weighted and provenance-tagged. Contracts have canonical SHA-256 identities, static consistency linting and an append-only hash-chained `ContractLedger`.

Ordinal constraints themselves are established mathematics. Semantic ABI uses them as one portable contract primitive; it does not claim to invent ordinal embedding.

## 2. Application semantics, legacy behavior and integrity are different roles

Three behaviors must not be conflated.

### Application semantics

What the product/domain says must remain true. Sources can include relevance judgments, domain rules, ontologies, expert decisions, safety constraints or observed outcomes.

### Legacy behavior

Selected old retrieval behavior we consciously want to preserve during a transition. This may be useful for regression compatibility but must not automatically become permanent application truth.

### Implementation integrity

Canaries that describe the expected internal behavior of **one concrete implementation** so silent corruption can be detected. These are intentionally implementation-specific and should not be used to reject a legitimate migration to a different representation family.

The distinction matters experimentally. On Digits pixels↔HOG:

| representation | application contract | captured legacy behavior |
|---|---:|---:|
| pixels | ~0.980 | 1.000 |
| HOG | ~0.911 | ~0.711 |
| corrupted HOG | ~0.813 | ~0.610 |

The real SciFact repair experiment later showed the complementary failure mode: application conformity can recover before a corrupted implementation's full downstream retrieval quality is restored. Implementation-integrity canaries help observe more of that corruption without redefining it as portable application truth.

## 3. `SemanticOracle`: the ABI does not require vectors

`SemanticOracle` is the executable representation boundary:

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

BM25 exposed no dense vectors, evaluated **650/650 clauses** with zero missing clauses and used the exact same contract identity.

This is meaningful evidence for representation-independent execution on one dataset/contract shape. It is not proof of universal portability.

## 4. Conformity is not adequacy

A `ContractReport` answers:

> Does this implementation satisfy the clauses that exist?

It does **not** answer:

> Are the clauses that exist sufficient to justify the deployment claim we want to make?

The neural repair benchmark made that distinction unavoidable. In several repaired states the application ABI score returned to approximately its clean value (~0.948) while held-out nDCG remained below the clean index. The contract was conforming but not exhaustive enough to observe all downstream damage.

### `ContractAdequacyEvidence`

Adequacy is now a separate evidence object. Supported axes include:

- logical-object coverage;
- mutation kill rate;
- mutation localization;
- predictive correlation with independent held-out outcomes;
- predictive lift over an ordinary validation baseline;
- number of held-out cases;
- number of datasets;
- number of fault families.

### No universal adequacy threshold

`ContractAdequacyRequirements` deliberately has no hidden defaults. A deployment policy explicitly declares which evidence floors it requires. `assess_contract_adequacy()` returns:

- `adequate` only if every declared requirement is observed and passes;
- `failed` if any observed requirement fails;
- `insufficient_evidence` if a required evidence axis is missing.

This avoids turning a strong conformity score, one favorable benchmark or one mutation suite into an unjustified universal certificate.

## 5. Contract score, support and deployment risk are different

The runtime separates:

1. **conformity audit** — which declared invariants hold?
2. **contract adequacy** — is the declared observation surface enough for the claim?
3. **contract/object coverage** — how much logical surface is directly referenced?
4. **local support** — is the query near audited semantic landmarks?
5. **proxy risk** — does the local risk field rank likely failures?
6. **statistical certification** — does a selective serving rule meet a failure SLA with stated evidence?

`estimate_local_semantic_risk()` combines interpolated contract risk with an unsupported-region penalty. It is a diagnostic, not a theorem for arbitrary distribution shift.

## 6. Selective rollout certification

### Conservative family-wise baseline

`calibrate_semantic_risk()` splits data, proposes a family of thresholds on selection data, evaluates them independently and union-corrects one-sided Bernoulli Chernoff/KL bounds.

### Pre-registered exact-binomial baseline

`calibrate_semantic_risk_preregistered()` freezes one threshold before certification labels are inspected and certifies that single rule with a one-sided exact binomial bound. If it fails, it cannot post-hoc choose a different threshold on the same holdout.

Neither method is claimed as new statistics. Learn-Then-Test, adaptive LTT/e-processes, conformal/selective risk control and localized risk methods are explicit prior art/baselines.

### SciFact result

BGE on SciFact:

- 175 calibration events;
- certification split: 87;
- held-out test queries: 200;
- support-aware failure-risk AUC: **0.7875**.

| target failure SLA | simultaneous KL family | pre-registered exact |
|---:|---|---|
| 5% | not certified | not certified |
| 10% | not certified | not certified |
| 15% | not certified | **certified; upper ~13.16%** |
| 20% | certified | certified |

At the 15% pre-registered certificate:

- certification empirical risk: ~**8.05%**;
- exact upper bound: ~**13.16%**;
- held-out coverage: **197/200 = 98.5%**;
- realized held-out risk in the accepted region: ~**10.15%**.

Both methods still refuse 10%; the sample-efficient method does not manufacture a stricter guarantee than the data support.

## 7. Progressive Semantic Audit: reduce evaluation cost without deleting truth

Fixed deterministic clause subsets failed to generalize reliably. The full contract therefore remains normative.

`progressive_semantic_audit()` defines a separate release SLA:

> all hard clauses pass, and weighted soft-clause violation rate is at most `r`.

Policy:

1. evaluate **every hard clause**;
2. sample positive-weight soft clauses with replacement proportional to weight;
3. cache oracle evaluations so repeated draws do not repay execution cost;
4. inspect only at predeclared batch looks;
5. split the global error budget across both tails and all looks;
6. use exact-binomial bounds;
7. early PASS when the upper bound is below the SLA;
8. early FAIL when the lower bound is above it;
9. otherwise fall back to exact full audit.

This is separate from the historical aggregate ABI score.

### Real Digits result

With a 1,500-clause contract, four controlled corruptions and three SLAs:

- **15/15** progressive decisions match exhaustive decisions;
- **12/15** stop early;
- early decisions evaluate on average **7.17%** of unique clauses.

### 10k / 100k / 250k scaling result

A procedural weighted-contract mechanism test produces:

- **10/10** decision agreement with exact audit;
- **9/10** early decisions;
- the deliberately boundary-adjacent case falls back to full audit.

Representative far-from-boundary costs:

| contract | case | unique clauses evaluated |
|---:|---|---:|
| 100k | healthy PASS | 200 = **0.20%** |
| 100k | 20% violations FAIL | 100 = **0.10%** |
| 250k | healthy PASS | 200 = **0.08%** |
| 250k | 20% violations FAIL | 100 = **0.04%** |
| 250k | ~10% violations FAIL | 998 = **0.3992%** |

This supports a useful scaling property: away from the SLA boundary, decision cost can depend much more on statistical margin than total clause count. It remains a procedural mechanism test, not evidence that production semantic violations are iid.

Sequential testing itself has strong prior art; future baselines should include adaptive LTT/e-processes rather than inventing new ad-hoc confidence bounds.

## 8. Why deterministic contract compression was demoted

### Semantic Witness Set

On a 1,500-clause contract with changed IDs, 3–10% fault footprints, changed severities and an unseen drift family:

- 10 clauses: TPR **62.5%**, FPR **0%**;
- 25 clauses: TPR **100%**, FPR **28.6%**;
- 100 clauses: TPR **100%**, FPR **42.9%**.

Random same-size subsets remain competitive. Fixed witness sparsification is not a production mechanism.

### Discriminative Diagnostic Panel

A learned panel achieved TPR 1/FPR 0 on its training scenarios then **0% held-out regression TPR** across budgets 5–100. It overfit object-local fault identity and is not promoted as a public API.

These negative results motivated Progressive Audit rather than pretending omitted clauses are universally redundant.

## 9. Active acquisition and adequacy testing

### Semantic Diff

`semantic_diff()` compares implementations and `propose_contract_questions()` prioritizes disagreements for domain review.

Digits evidence:

- all disagreement questions label-resolvable: ~**11.7%**;
- top 25 proposed: **68%**;
- top 50: **60%**.

Active preference/query selection itself has substantial prior art. The open question is whether this acquisition loop can build a useful portable contract at much lower human cost.

### Mutation adequacy

Mutation testing deliberately injects identity permutation, local collapse, hub-pull and coordinate noise. Current Digits contracts kill the tested mutation families globally, while localization is materially weaker.

Mutation results should feed **Contract Adequacy Evidence**, not be confused with conformity of one candidate.

## 10. Neural active repair economics

A SciFact/BGE experiment uses 1,800 documents, 350 train queries and 200 untouched test queries. Five or ten percent of document embeddings are deliberately permuted; repair restores only selected documents to their clean BGE vector.

Clean:

- application ABI ~**0.9480**;
- nDCG@10 ~**0.7875**.

At 10% corruption:

- ABI ~**0.8429**;
- nDCG ~**0.6970**.

At repair budget 25:

- cost-aware coverage selection is **88% actually corrupted**;
- it restores ~**33.9%** of the lost nDCG gap;
- random finds ~**7.3%** corruption and restores ~**1.5%**.

At budget 180, the best targeted method restores roughly **50%** of the nDCG gap versus ~**9%** random.

### Critical negative result

No tested planner reaches 90% nDCG recovery. More importantly, application ABI conformity can saturate near its clean score while downstream nDCG remains damaged.

This is direct evidence that **repair success cannot be defined only as “contract score returned to normal.”** Adequacy and downstream validation remain necessary.

## 11. Implementation-integrity canaries

A follow-up experiment adds 250 document-graph canary anchors without using test qrels.

Document coverage rises from:

- application-only: **32.3%**;
- application + random integrity anchors: **67.0%**;
- application + coverage-oriented anchors: **72.5%**.

With 10% corruption:

- clean nDCG: **0.7875**;
- corrupted nDCG: **0.7338**.

At repair budget 100, best lost-gap recovery rises from about **62.3%** under application-only diagnosis to **70.2–70.8%** with integrity canaries. At budget 180, coverage-oriented integrity reaches about **71.2%**.

This is useful but incomplete: 90% recovery remains unreached.

A second important finding is causal ambiguity. Naive highest-object-risk ranking can fail badly at small budgets because a broken neighborhood clause may place risk on a healthy anchor while one of its expected neighbors is actually corrupted. Future repair needs clause-role and incidence/causal reasoning rather than one merged scalar risk field.

## 12. Multi-dataset predictive-validity gate

The current falsification campaign compares Semantic ABI against ordinary train-query nDCG for predicting untouched test nDCG across SciFact, NFCorpus and FiQA, using natural dense/sparse/hybrid implementations plus controlled degradations.

Contracts use **train qrels only**; test qrels are never used to author clauses or choose variants.

### First completed dataset: FiQA

On 11 natural/degraded implementations:

- Spearman `ABI → test nDCG`: **0.9636**;
- Spearman `train nDCG → test nDCG`: **0.9522**;
- ABI minus baseline Spearman: only **+0.0115**;
- Pearson ABI: **0.9823**;
- Pearson train-nDCG baseline: **0.9945**.

Across the four natural implementations only, both signals have Spearman **0.80**.

So FiQA is a **narrowing result**: ABI is a strong quality-correlated signal, but it is not clearly a better global quality predictor than ordinary IR validation. Its differentiated value must be tested in the properties ordinary aggregate nDCG does not encode well: hard invariants, portability, local support/risk, provenance and controlled deployment.

SciFact/NFCorpus replication remains in progress; no cross-dataset predictive-superiority claim is made before their artifacts exist.

## 13. Closed-loop semantic change management

```text
Application Contract + explicit Adequacy Policy
                 |
                 v
       Conformity / Progressive Audit
                 |
        +--------+---------+
        |                  |
 support + rollout risk   violations
        |                  |
 candidate/fallback       repair planner
                           |
                 external fix/re-embed
                           |
                     re-audit/re-test
```

`SemanticChangeManager` does not silently mutate semantic truth. External systems perform review/relabel/re-embedding; the manager produces auditable assessments.

## 14. Release evidence

`SemanticReleaseCertificate` currently binds:

- exact implementation/provider/model revision;
- representation dimension/modality;
- preprocessing digest;
- Semantic Contract digest;
- audit and hard-pass state;
- logical coverage;
- statistical rollout certificate;
- evidence hashes;
- status and metadata.

Generic AI attestation/release certificates have substantial prior art and are not claimed as novel. The repository-specific open question is whether **retrieval-specific attestations bound to portable semantic contracts, adequacy evidence, selective risk/fallback and repair history** are operationally useful.

`docs/evidence-manifest.json` additionally binds promoted research claims to GitHub Actions run/artifact identities and the Git blobs of evidence-sensitive code. CI fails when those sources change without regenerated evidence.

## 15. Relationship to SCF

The layers solve different questions:

- **SCF:** can queries/observations be transported between coordinate systems during migration?
- **Semantic ABI conformity:** does an implementation satisfy declared application invariants?
- **Contract Adequacy:** is the contract/test surface sufficient for the claim?
- **Implementation Integrity:** is one concrete implementation silently damaged?
- **rollout certification:** where may the candidate serve traffic under measured risk?
- **Progressive Audit:** how cheaply can a large hard/soft contract be audited?

On BGE→MiniLM SciFact, global translation beats local. `EvidenceGatedTransition` correctly chooses global, so local SCF remains optional rather than architectural dogma.

## 16. Research questions now worth pursuing

1. Does the same application contract remain useful across graph, late-interaction and multimodal retrievers after dense/sparse/hybrid?
2. Does ABI add predictive value beyond ordinary validation on SciFact/NFCorpus, or is its value primarily normative/local rather than aggregate-predictive?
3. Which adequacy axes predict when conformity scores are trustworthy downstream?
4. Can integrity contracts be typed and audited without contaminating portable application semantics?
5. Can clause-incidence/causal repair outperform highest-risk and generic coverage heuristics?
6. Can aLTT/e-processes improve Progressive Audit efficiency on realistic fault distributions?
7. How should selective rollout adapt under domain/language/temporal shift?
8. Which active-acquisition policy minimizes expert judgments per real regression caught?
9. Can release evidence become independently verifiable across model providers and databases?

## Kill / narrow criteria

Semantic ABI should collapse toward ordinary regression testing if representative systems show that:

- portable contracts add no operational information beyond conventional benchmark suites;
- adequacy requires near-exhaustive annotation/evaluation;
- representation independence does not generalize beyond current paradigms;
- selective rollout has negligible useful coverage;
- Progressive Audit usually falls back to full evaluation;
- repair/integrity does not beat simple baselines economically;
- governance overhead costs as much as re-evaluating/re-indexing everything.

The objective is not to preserve the phrase **Semantic ABI**. The objective is to discover whether a portable, auditable semantic interface can make retrieval changes materially safer and cheaper.
