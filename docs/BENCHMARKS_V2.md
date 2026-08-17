# Benchmark / evidence protocol

The repository distinguishes **software correctness**, **mechanism evidence**, **real representation evidence**, **deployment-risk evidence** and **negative ablations**. Mixing these categories is not allowed.

For the latest numbers, use [`CURRENT_STATUS.md`](CURRENT_STATUS.md). Machine-readable evidence provenance is moving to `evidence-manifest.json`.

## 1. Evidence classes

### Class S — software correctness

Lightweight CI must run on Python 3.10, 3.12 and 3.13 and include:

- package installation;
- full `pytest` suite;
- fixed-seed hubness regression benchmark.

A green unit test is **not** scientific evidence for model quality.

### Class M — controlled mechanism tests

Synthetic or deliberately corrupted experiments answer questions such as:

- can hubness correction suppress constructed black holes?
- can cycle consistency expose a corrupt transition?
- can a contract kill deliberate semantic mutants?
- can repair planning enrich known corrupt objects?

They prove an implementation can react to a known constructed condition. They do not establish production superiority.

### Class R — real observed representations

Examples:

- Digits raw pixels ↔ HOG;
- SciFact MiniLM ↔ BGE;
- SciFact BGE dense ↔ BM25 sparse.

These require held-out query/data splits and task relevance metrics where available.

### Class C — statistical certification

A certificate must distinguish:

- selection data;
- certification data;
- final held-out evaluation;
- target SLA;
- `delta` / confidence budget;
- threshold-selection procedure;
- multiplicity/optional-stopping treatment;
- abstention cases.

A metric such as AUC is useful for discrimination but is **not itself a risk certificate**.

### Class N — negative/falsification evidence

Failed hypotheses are published alongside positive results. Current examples:

- local BGE→MiniLM mapping loses to global;
- deterministic Witness sparsification does not dominate random held-out;
- discriminative fixed Diagnostic Panels overfit and reach 0% held-out regression recall.

## 2. Historical SMA/SCF mechanism evidence

### Hubness stress test

Fixed-seed synthetic result:

- exact cosine precision@10: **0.6300**;
- SMA precision@10: **0.8519**;
- cosine injected hubs/query: **3.3687**;
- SMA injected hubs/query: **0.0000**.

Interpretation: validates the hub-robust ranking mechanism under a constructed black-hole condition only.

### Coordinate Fabric deterministic mechanisms

`coordinate_fabric_benchmark.py`:

| mechanism | baseline | SCF |
|---|---:|---:|
| region-dependent warp, held-out pair cosine | global 0.7042 | local 0.9414 |
| target index 25% migrated, overlap@10 vs legacy oracle | new-only 0.2080 | fabric 0.8460 |
| transition cycle | good ~1.0000 | corrupted -0.0760 |
| exact-rotation toy, 20% direct vectors | direct coverage 0.20 | virtual coverage 1.00 |

These are mechanism tests. The real neural result later falsifies any claim that local translation is generally superior.

## 3. Real Digits representation evidence

### Pixels ↔ HOG coordinate migration

Dataset: `sklearn.datasets.load_digits`.

- legacy: normalized raw 8×8 pixels, 64-D;
- target: HOG descriptors, 324-D;
- 1,400 indexed images;
- 397 held-out queries.

| anchor coverage | global same-digit p@10 | local same-digit p@10 | global target-neighbor overlap@10 | local overlap@10 |
|---:|---:|---:|---:|---:|
| 20% | 0.4897 | 0.7353 | 0.0788 | 0.1685 |
| 40% | 0.4741 | 0.7776 | 0.0811 | 0.2161 |
| 70% | 0.4280 | 0.8526 | 0.0741 | 0.2809 |

Lesson: downstream relevance and exact target-neighbor imitation are distinct metrics.

### Semantic ABI: application vs legacy behavior

Application contract:

- pixels ~0.980;
- HOG ~0.911;
- corrupted HOG ~0.813.

Legacy-behavior contract:

- pixels 1.000;
- HOG ~0.711;
- corrupted HOG ~0.610.

This is the mechanism evidence for separating application semantics from exact old ranking behavior.

### Active repair

10% deliberate identity corruption:

| review budget | truly corrupt among selected | random expectation |
|---:|---:|---:|
| 25 | 68% | 10% |
| 50 | 54% | 10% |
| 100 | 37% | 10% |
| 140 | 33.6% | 10% |

Next required metric: certified-coverage gained per unit cost, not only corrupt-object precision.

### Semantic Diff

- all disagreement questions label-resolvable: ~11.7%;
- top 25 proposed: 68%;
- top 50: 60%.

Next gate: human/domain judgments rather than digit labels as a proxy oracle.

### Mutation adequacy

Current controlled families:

- identity permutation;
- local collapse;
- hub pull;
- coordinate noise.

The tested contracts kill all four families in the current Digits experiment. Localization remains materially weaker than global detection.

## 4. Real neural SciFact gate

Dataset: `mteb/scifact`.

- 1,800 documents;
- 500 train queries;
- 200 held-out test queries;
- legacy: MiniLM;
- candidate: BGE-small-en-v1.5.

### Direct retrieval

| implementation | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|
| MiniLM | 0.7387 | 0.8515 | 0.8600 |
| BGE | **0.7821** | **0.8840** | **0.8900** |

### Semantic ABI

- contract clauses: **650**;
- exact digest: `59d34bc071273dbaa06ce03df1a3b66a2686b6b8c5f240bb49075054909c7b9f`;
- MiniLM ABI: ~0.9035;
- BGE ABI: **0.9467**;
- logical-object coverage: ~41.6%;
- held-out support-aware failure-risk AUC: **0.7875**.

### Dense↔sparse portability

The exact same contract is audited against BM25 through `CallbackSemanticOracle`.

| implementation | ABI | nDCG@10 | Recall@10 | Hit@10 |
|---|---:|---:|---:|---:|
| BGE dense | **0.9467** | **0.7821** | **0.8840** | **0.8900** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 | 0.8400 |

BM25 evaluates 650/650 clauses with zero missing clauses. The benchmark must fail if the sparse reconstruction produces a different contract digest from the dense evidence.

This is one inter-paradigm gate, not universal representation independence.

### SCF global/local ablation

BGE→MiniLM target-neighbor overlap@10:

- global: **0.4745**;
- local: **0.3680**.

Held-out transition validation also favors global. Any benchmark/report that presents local SCF as the default is stale.

## 5. Rollout-risk certification protocol

Calibration and test queries must remain separated.

### Simultaneous family baseline

`calibrate_semantic_risk()`:

- selection proposes a small threshold family;
- independent certification evaluates the family;
- one-sided Chernoff/KL bounds;
- union correction across candidates.

### Pre-registered exact baseline

`calibrate_semantic_risk_preregistered()`:

- selection chooses one rule under internal slack;
- the rule is frozen before certification labels are observed;
- certification tests exactly that rule using a one-sided exact binomial bound;
- failure means abstention, not post-hoc threshold switching.

### SciFact risk curve

`delta = 0.10`:

| requested failure SLA | simultaneous family | pre-registered exact |
|---:|---|---|
| 5% | no | no |
| 10% | no | no |
| 15% | no; upper ~19.19% | **yes; upper ~13.16%** |
| 20% | yes | yes |

15% pre-registered held-out result:

- accepted 197/200 = **98.5%**;
- realized accepted failure rate ~**10.15%**.

Required future baselines:

- Learn-Then-Test;
- Adaptive LTT;
- conformal/selective risk control;
- confidence sequences / e-processes;
- shift-aware/reweighted calibration.

Required stress axes:

- calibration sample size;
- domain/language/time shift;
- sparse slices;
- score calibration drift;
- support/OOD shift;
- multiple random seeds.

## 6. Contract-cost experiments

### Failed: deterministic Witness sparsification

Stress protocol:

- source contract: 1,500 clauses;
- changed object IDs;
- fault footprints 3%, 5%, 10%;
- changed severities;
- unseen coherent-directional-drift family;
- true negative controls defined as micro-drifts the full contract itself does not detect.

Representative held-out results:

| fixed clauses | TPR | FPR |
|---:|---:|---:|
| 10 | 62.5% | 0% |
| 25 | 100% | 28.6% |
| 100 | 100% | 42.9% |

Conclusion: fixed sparsification is not a promoted mechanism.

### Failed: discriminative Diagnostic Panel

The panel perfectly separates training regressions from approved micro-drifts and then produces **0% held-out TPR** across budgets 5–100 clauses.

Conclusion: item discrimination without broad semantic/topological coverage overfits object-local failure locations.

### Promising: Progressive Semantic Audit

Policy:

- every hard clause exhaustive;
- soft clauses sampled proportional to weight;
- cached evaluation;
- predeclared batch looks;
- exact-binomial bounds with error budget split over tails/looks;
- early PASS/FAIL on weighted soft-clause violation SLA;
- exact fallback if inconclusive.

Digits benchmark:

- contract: 1,500 clauses;
- scenarios: baseline + four corruptions;
- SLAs: 2%, 5%, 10%;
- total decisions: 15;
- agreement with exhaustive decision: **15/15**;
- early/non-full decisions: **12/15**;
- mean unique-clause fraction among early decisions: **7.17%**.

Near-boundary cases fall back to all 1,500 clauses.

Next benchmark axes:

1. 10k/100k/1M clauses;
2. non-uniform weights;
3. expensive remote-oracle clauses;
4. heterogeneous costs;
5. semantic slices/strata;
6. finite-population sampling without replacement;
7. confidence-sequence/e-process stopping;
8. adversarial sparse faults;
9. hard-clause fractions;
10. expected wall-clock/cost savings rather than clause counts alone.

## 7. Real integration requirements

Before any production claim, run candidate generation/audit through mature systems:

- Qdrant;
- pgvector;
- Elasticsearch/BM25 + dense hybrid;
- Vespa or late-interaction equivalent;
- HNSW/DiskANN where useful.

Report:

- p50/p95/p99 retrieval latency;
- p50/p95/p99 audit latency;
- memory/artifact size;
- API/GPU/token cost;
- direct vs virtual representation status;
- fallback fraction;
- full re-embedding cost avoided;
- repair-to-certified-coverage economics.

## 8. Evidence freshness rules

Published numbers must be bound to:

- GitHub Actions workflow run ID;
- workflow head SHA;
- artifact SHA-256 digest;
- Git blob SHA of evidence-sensitive algorithms and benchmark scripts.

`docs/evidence-manifest.json` is the machine-readable source. CI recalculates the Git blob SHA locally and fails when an evidence-sensitive source changes without refreshed evidence.

Changing documentation alone should not invalidate an experiment. Changing an algorithm or its benchmark **must**.

## 9. Falsification rules

Narrow or kill a mechanism when representative data shows:

- it fails to beat a simpler baseline;
- its uncertainty/risk signal is not predictive held-out;
- safe certified coverage is economically useless;
- its apparent gain disappears across model/dataset seeds;
- its audit/maintenance cost approaches exhaustive evaluation;
- it relies on current-model behavior masquerading as application truth.

A negative benchmark is a successful research result when it removes unjustified complexity.
