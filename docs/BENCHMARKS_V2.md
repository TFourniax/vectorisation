# Benchmark / evidence protocol

The repository distinguishes **software correctness**, **mechanism evidence**, **real representation evidence**, **contract adequacy**, **deployment-risk evidence**, **economics** and **negative/falsification evidence**. Mixing these categories is not allowed.

For the latest numbers, use [`CURRENT_STATUS.md`](CURRENT_STATUS.md). Machine-readable promoted evidence is bound in [`evidence-manifest.json`](evidence-manifest.json).

## 1. Evidence classes

### Class S — software correctness

CI must cover Python 3.10, 3.12 and 3.13 plus:

- package install;
- full `pytest`;
- fixed-seed hubness regression;
- evidence-freshness validation.

A green unit test is not scientific evidence for retrieval quality.

### Class M — controlled mechanism tests

Synthetic/procedural or deliberately corrupted tests answer whether a mechanism can react to a constructed condition. Examples: hubness, cycle corruption, semantic mutants, Progressive Audit scale, controlled index corruption.

Mechanism evidence must never be reported as universal production superiority.

### Class R — real observed representation evidence

Examples:

- Digits pixels ↔ HOG;
- SciFact MiniLM ↔ BGE;
- dense BGE ↔ sparse BM25;
- dense/sparse/hybrid multi-dataset comparisons.

Task relevance and untouched held-out evaluation are required where labels/qrels exist.

### Class A — contract adequacy evidence

A conformity score asks whether an implementation satisfies observed clauses. Adequacy asks whether the contract/test surface is sufficient for the **claim** being made.

Potential axes:

- logical-object coverage;
- mutation kill rate;
- mutation localization;
- predictive association with independent held-out outcomes;
- predictive lift over an ordinary validation baseline;
- held-out sample count;
- dataset/fault-family diversity.

Adequacy requirements are application-declared. A favorable conformity score cannot substitute for missing adequacy evidence.

### Class C — statistical certification

A certificate must report:

- selection data;
- independent certification data;
- final held-out evaluation;
- target SLA;
- `delta` / error budget;
- threshold-selection procedure;
- multiplicity / optional-stopping treatment;
- support/OOD assumptions;
- abstention/fallback cases.

AUC is discrimination, not a risk certificate.

### Class E — economic evidence

Repair/migration claims must measure the actual resource objective, for example:

- documents re-embedded;
- API/GPU/token cost;
- nDCG/Recall gap recovered;
- certified coverage gained;
- latency overhead;
- full-backfill cost avoided.

Corrupted-object precision alone is not sufficient.

### Class N — negative/falsification evidence

Negative results are promoted alongside positive evidence. Current examples include:

- local BGE→MiniLM mapping loses to global;
- deterministic Witness sparsification does not dominate random held-out;
- learned Diagnostic Panels overfit to localized faults;
- current neural repair does not achieve 90% downstream recovery;
- FiQA ABI predictive correlation is strong but not materially superior to ordinary train nDCG.

## 2. Golden rules

1. **Never use test qrels to author a contract or choose model variants.**
2. **Always compare against the simplest relevant baseline.**
3. **Separate portability from predictive validity.** A contract can execute everywhere and still add no useful predictive information.
4. **Separate conformity from adequacy.** A high score can coexist with unobserved downstream damage.
5. **Separate application truth from implementation integrity.** Integrity canaries must not freeze implementation quirks into portable semantics.
6. **Report negative results.** A workflow success means the experiment ran, not that the hypothesis passed.
7. **Bind promoted evidence to exact source blobs and artifacts.**

## 3. Historical SMA/SCF evidence

### Hubness mechanism

Fixed-seed synthetic result:

- exact cosine precision@10 **0.6300**;
- SMA **0.8519**;
- cosine injected hubs/query **3.3687**;
- SMA **0.0000**.

Interpretation: constructed mechanism test only.

### SCF mechanism vs real falsification

Synthetic/local-coordinate mechanisms remain useful, but on real BGE→MiniLM SciFact:

- global target-neighbor overlap@10 **0.4745**;
- local atlas **0.3680**;
- held-out validation also favors global.

`EvidenceGatedTransition` therefore selects global. Any report claiming local mapping is generally superior is stale.

## 4. Real Digits evidence

### Application vs legacy behavior

Application contract:

- pixels ~0.980;
- HOG ~0.911;
- corrupted HOG ~0.813.

Legacy behavior:

- pixels 1.000;
- HOG ~0.711;
- corrupted HOG ~0.610.

### Semantic Diff

- all disagreement questions label-resolvable ~11.7%;
- top 25 **68%**;
- top 50 **60%**.

### Mutation adequacy

Current controlled families are identity permutation, local collapse, hub pull and coordinate noise. Current Digits contracts kill the tested families globally; localization remains weaker.

### Fixed-subset failures

Witness stress test on 1,500 clauses:

| fixed clauses | held-out TPR | FPR |
|---:|---:|---:|
| 10 | 62.5% | 0% |
| 25 | 100% | 28.6% |
| 100 | 100% | 42.9% |

A learned fixed Diagnostic Panel reaches perfect training separation then **0% held-out TPR** across tested budgets. Neither mechanism is promoted.

## 5. Progressive Semantic Audit

Policy:

- every hard clause exhaustive;
- soft clauses sampled with replacement proportional to weight;
- cached oracle evaluation;
- predeclared batch looks;
- exact-binomial bounds with error budget across tails/looks;
- early PASS/FAIL on weighted soft-clause violation SLA;
- exact fallback when inconclusive.

### Digits 1,500-clause result

- decisions: 15;
- exact agreement: **15/15**;
- early decisions: **12/15**;
- mean unique-clause fraction among early decisions: **7.17%**.

### Scale result

Procedural weighted contracts at 10k/100k/250k:

- exact agreement: **10/10**;
- early decisions: **9/10**;
- deliberately near-boundary case falls back to full audit.

Representative costs:

| clauses | case | unique evaluated |
|---:|---|---:|
| 100k | healthy PASS | 200 = 0.20% |
| 100k | 20% violation FAIL | 100 = 0.10% |
| 250k | healthy PASS | 200 = 0.08% |
| 250k | 20% violation FAIL | 100 = 0.04% |
| 250k | ~10% violation FAIL | 998 = 0.3992% |

Next baselines must include adaptive LTT/e-processes and realistic non-iid/stratified fault distributions.

## 6. Real neural SciFact gate

Dataset: `mteb/scifact`, 1,800 documents, 500 train queries, 200 held-out test queries.

### Direct retrieval / ABI

| implementation | ABI | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|---:|
| MiniLM dense | ~0.9035 | 0.7387 | 0.8515 | 0.8600 |
| BGE dense | **0.9467** | **0.7821** | **0.8840** | **0.8900** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 | 0.8400 |

BGE and BM25 execute the exact same 650-clause contract digest, with BM25 evaluating 650/650 clauses and no dense-vector exposure.

### Rollout risk

At `delta=0.10`:

| failure SLA | simultaneous KL family | preregistered exact |
|---:|---|---|
| 5% | no | no |
| 10% | no | no |
| 15% | no | **yes, upper ~13.16%** |
| 20% | yes | yes |

The 15% preregistered rule accepts 197/200 held-out queries and observes ~10.15% failure within the accepted region.

## 7. Multi-dataset predictive-validity protocol

This is the key adequacy gate introduced in August 2026.

Datasets:

- SciFact;
- NFCorpus;
- FiQA.

Natural implementations:

- MiniLM dense;
- BGE dense;
- BM25 sparse;
- BGE + BM25 reciprocal-rank hybrid.

Controlled degradations broaden the quality range but are reported separately from natural systems.

Rules:

- official **train qrels only** compile the application contract;
- official **test qrels only** measure held-out downstream quality;
- each dataset uses one exact contract digest across all implementations;
- report Pearson, Spearman and pairwise concordance;
- compare `Semantic ABI → held-out nDCG` against **ordinary train nDCG → held-out nDCG**;
- report natural-only and all-variant results separately;
- a weak/no ABI lift is a narrowing result, not a reason to change the metric after seeing data.

### FiQA first completed result

11 natural/degraded systems:

- ABI→test nDCG Spearman **0.9636**;
- train nDCG→test nDCG Spearman **0.9522**;
- ABI lift only **+0.0115**;
- ABI Pearson **0.9823**;
- train-nDCG Pearson **0.9945**.

Natural-only (4 systems): both signals Spearman **0.80**.

Interpretation: ABI tracks broad quality strongly but is **not clearly a superior aggregate-quality predictor** on FiQA. Its differentiated value must therefore be established in hard invariants, portability, local risk/support and controlled rollout—not assumed from correlation alone.

SciFact/NFCorpus replicas remain required before a cross-dataset conclusion.

## 8. Real neural repair economics

SciFact/BGE: 1,800 documents, 350 train queries, 200 untouched test queries. Controlled identity permutations corrupt 5%/10% of document embeddings; repair restores selected documents only.

Clean:

- ABI ~0.9480;
- nDCG ~0.7875.

10% corruption:

- ABI ~0.8429;
- nDCG ~0.6970.

At budget 25:

- coverage planner corruption precision **88%**;
- lost-nDCG recovery ~**33.9%**;
- random corruption precision ~**7.3%**;
- random recovery ~**1.5%**.

At budget 180, targeted recovery reaches roughly **50%** versus ~**9%** random.

**Negative gate:** no tested method reaches 90% downstream recovery. Application ABI conformity can recover before held-out nDCG does, proving that conformity alone cannot stand in for contract adequacy.

## 9. Implementation-integrity canary experiment

Follow-up on the 10% SciFact/BGE corruption; canaries are derived from the clean document graph without test qrels.

Document coverage:

- application-only **32.3%**;
- + random integrity anchors **67.0%**;
- + coverage-oriented integrity anchors **72.5%**.

At budget 100, best lost-nDCG recovery improves from about **62.3%** application-only to **70.2–70.8%** with integrity canaries. At budget 180, coverage-oriented integrity reaches ~**71.2%**.

Still no 90% recovery.

Naive highest-risk can fail badly at small budgets because a neighborhood violation can implicate a healthy anchor while the damaged neighbor is causal. Future baselines must include clause-role/incidence-aware repair, not only scalar object risk.

## 10. Contract Adequacy protocol

A future release claim should specify its adequacy policy before observing final evidence. Candidate axes can include:

- `min_object_coverage`;
- `min_mutation_kill_rate`;
- `min_mutation_localization`;
- `min_predictive_correlation`;
- `min_predictive_lift_over_baseline`;
- `min_heldout_cases`;
- `min_datasets`;
- `min_fault_families`.

Missing required evidence yields `insufficient_evidence`. There is no library-wide universal threshold.

Do not optimize contract adequacy against the same held-out set used to certify it.

## 11. Real integration requirements

Before production claims, run through mature systems such as Qdrant, pgvector, Elasticsearch/BM25+dense hybrid, Vespa/late interaction and relevant ANN engines.

Report:

- retrieval and audit p50/p95/p99 latency;
- memory/artifact size;
- API/GPU/token cost;
- fallback fraction;
- full-backfill cost avoided;
- repair-to-quality/certified-coverage economics;
- integrity and application-contract roles separately.

## 12. Evidence freshness

Promoted numbers are bound to:

- GitHub Actions run ID;
- workflow head SHA;
- artifact SHA-256;
- Git blob SHA of evidence-sensitive code/benchmark scripts.

`tools/check_evidence_freshness.py` recomputes source identities in CI. Algorithm/benchmark changes make promoted evidence stale until regenerated; documentation-only edits do not.

## 13. Falsification rules

Narrow/kill a mechanism when representative evidence shows:

- it fails to beat a simpler baseline;
- apparent predictive value is no better than ordinary validation where predictive superiority is claimed;
- safe certified coverage is economically useless;
- gains disappear across models/datasets/seeds;
- audit/maintenance cost approaches exhaustive evaluation;
- implementation-specific behavior is masquerading as application truth;
- conformity is being used to imply adequacy without adequacy evidence.

A negative benchmark is a successful research result when it removes unjustified complexity.
