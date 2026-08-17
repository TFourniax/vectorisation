# Benchmark / evidence protocol

The repository separates **software correctness**, **mechanism evidence**, **real representation evidence**, **contract adequacy**, **statistical certification**, **economics** and **negative/falsification evidence**.

Latest numbers: [`CURRENT_STATUS.md`](CURRENT_STATUS.md).  
Machine-bound provenance: [`evidence-manifest.json`](evidence-manifest.json).

## Evidence classes

### S — software correctness

CI must cover Python 3.10/3.12/3.13, full `pytest`, the fixed hubness regression and evidence freshness. Green unit tests are not retrieval-quality evidence.

### M — mechanism tests

Synthetic/procedural or deliberately corrupted tests answer whether a mechanism reacts to a constructed condition. Examples: hubness, cycle corruption, semantic mutations, Progressive Audit scale and controlled index corruption.

### R — real observed representation tests

Examples: Digits pixels↔HOG, SciFact MiniLM↔BGE, dense BGE↔sparse BM25, and dense/sparse/hybrid multi-dataset comparisons.

### A — contract adequacy

Conformity asks whether an implementation satisfies observed clauses. Adequacy asks whether those clauses/evaluations are sufficient for the **claim** being made.

Possible axes: object coverage, mutation kill/localization, predictive association, lift over an ordinary validation baseline, held-out cases, datasets and fault families.

### C — certification

A deployment certificate must identify selection data, independent certification data, target SLA, `delta`, threshold-selection procedure, multiplicity/optional-stopping treatment, support assumptions and fallback cases.

### E — economics

Repair/migration evidence must measure resources and outcomes: re-embeddings/API/GPU cost, nDCG/Recall gap recovered, certified coverage gained, latency and full-backfill cost avoided.

### N — negative evidence

Negative results are promoted alongside positive evidence. Current examples:

- local BGE→MiniLM mapping loses to global;
- fixed Witness subsets do not robustly dominate random;
- learned fixed Diagnostic Panels overfit;
- current neural repair does not reach 90% downstream recovery;
- three-dataset ABI predictive superiority over ordinary train nDCG is not supported.

## Golden rules

1. **Never use test qrels to author a contract or choose variants.**
2. **Always compare against the simplest relevant baseline.**
3. **Separate portability from predictive validity.**
4. **Separate conformity from adequacy.**
5. **Separate application truth from implementation integrity.**
6. **Report negative results.** Workflow success means the experiment ran, not that the hypothesis passed.
7. **Bind promoted evidence to exact source blobs and artifacts.**

## Core current evidence

### SMA hubness mechanism

Fixed-seed synthetic stress:

- cosine precision@10 **0.6300**;
- SMA **0.8519**;
- cosine injected hubs/query **3.3687**;
- SMA **0.0000**.

Mechanism test only.

### SCF real neural falsification

BGE→MiniLM SciFact:

- global target-neighbor overlap@10 **0.4745**;
- local atlas **0.3680**.

Held-out validation also favors global. Local mapping is optional/evidence-gated.

### Real Digits mechanisms

Application contract: pixels ~0.980, HOG ~0.911, corrupted HOG ~0.813.  
Legacy behavior: pixels 1.000, HOG ~0.711, corrupted HOG ~0.610.

Semantic Diff:

- all disagreements resolvable ~11.7%;
- top 25 **68%**;
- top 50 **60%**.

Fixed Witness stress:

| clauses | held-out TPR | FPR |
|---:|---:|---:|
| 10 | 62.5% | 0% |
| 25 | 100% | 28.6% |
| 100 | 100% | 42.9% |

Learned fixed Diagnostic Panel: perfect training separation → **0% held-out TPR**.

### Progressive Semantic Audit

Policy: hard clauses exhaustive; soft clauses sampled weight-proportional with replacement; cached evaluation; predeclared looks; finite-sample bounds; exact fallback.

Digits 1,500 clauses:

- **15/15** exact decision agreement;
- **12/15** early;
- mean early unique fraction **7.17%**.

Scale 10k/100k/250k:

- **10/10** agreement;
- **9/10** early;
- near-boundary case falls back to full audit.

Representative 250k costs: healthy PASS **0.08%**, 20%-violation FAIL **0.04%**, ~10%-violation FAIL **0.3992%**.

Next statistical baselines: Adaptive Learn-Then-Test/e-processes and realistic non-iid/stratified faults.

## Real neural SciFact gate

SciFact: 1,800 documents, 500 train queries, 200 held-out test queries.

| implementation | ABI | nDCG@10 | Recall@10 |
|---|---:|---:|---:|
| MiniLM dense | ~0.9035 | 0.7387 | 0.8515 |
| BGE dense | **0.9467** | **0.7821** | **0.8840** |
| BM25 sparse | 0.8913 | 0.7335 | 0.8228 |

BGE and BM25 execute the exact same 650-clause contract digest.

Selective rollout at `delta=0.10`:

- 5% SLA: no;
- 10%: no;
- 15%: preregistered exact rule **yes**, upper ~13.16%;
- 20%: yes.

15% rule held-out acceptance: **197/200**; realized accepted risk ~**10.15%**.

## Three-dataset predictive-validity gate — completed

Datasets: SciFact, NFCorpus, FiQA.  
Natural implementations: MiniLM, BGE, BM25, BGE+BM25 RRF.  
Controlled degradations: seven per dataset.

Rules:

- train qrels only compile contracts;
- test qrels only measure held-out quality;
- compare `ABI → test nDCG` with **ordinary `train nDCG → test nDCG`**;
- report natural-only and all-variant results;
- no metric changes after seeing data.

### Canonical result

| metric | ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman | **0.9697** | **0.9757** |
| pooled delta Spearman vs BGE | **0.9573** | **0.9724** |
| pooled delta Pearson | **0.9519** | **0.9850** |
| pooled pairwise concordance | **0.9172** | **0.9400** |

Per-dataset all-variant Spearman:

- SciFact: 0.9364 vs 0.9704;
- NFCorpus: 0.9818 vs 0.9727;
- FiQA: 0.9909 vs 0.9841.

Mean result favors ordinary validation. Natural-only pooled Spearman is ABI 0.8333 vs baseline 0.8167, while Pearson is ABI 0.9513 vs baseline 0.9553; only nine non-BGE natural comparison points exist, so this is near parity rather than superiority evidence.

**Falsification conclusion:** current Semantic ABI is not a generally superior aggregate nDCG predictor. Future ABI claims must focus on normative hard invariants, portability, local support/risk and change control while retaining ordinary IR metrics.

A separate parallel per-dataset run with different NFCorpus/FiQA query seeds reproduces the qualitative narrowing result.

## Contract Adequacy protocol

Future release claims should predeclare required evidence axes through `ContractAdequacyRequirements`. Missing required evidence yields `insufficient_evidence`.

Do not optimize contract adequacy against the same held-out set used to certify it.

A high conformity score is never sufficient evidence of adequacy by itself.

## Neural repair economics

SciFact/BGE: 1,800 docs, 350 train queries, 200 untouched test queries.

Clean ABI ~0.9480; nDCG ~0.7875.  
10% corruption ABI ~0.8429; nDCG ~0.6970.

Budget 25:

- cost-aware coverage precision **88%** corrupted;
- nDCG-gap recovery ~**33.9%**;
- random precision ~**7.3%**;
- random recovery ~**1.5%**.

Budget 180: targeted best ~**50%** recovery vs random ~**9%**.

**Negative gate:** no tested method reaches 90% downstream recovery. Conformity can recover before held-out nDCG.

### Integrity canaries

Without test qrels, document coverage rises from application-only **32.3%** to **67.0%** random-integrity and **72.5%** coverage-oriented integrity.

At budget 100, best lost-nDCG recovery improves from ~62.3% to ~70.2–70.8%; budget 180 coverage-oriented integrity ~71.2%.

Still no 90% recovery. Neighborhood violations can misattribute blame to healthy anchors, motivating the current clause-incidence-aware repair benchmark.

## Real integration requirements

Before production claims, test real Elasticsearch/BM25+dense hybrid, Qdrant, pgvector, Vespa/late interaction and relevant ANN backends.

Report p50/p95/p99 latency, memory/artifact size, API/GPU/token cost, fallback fraction, full-backfill cost avoided, and application/integrity contract roles separately.

## Evidence freshness

Promoted numbers are bound to GitHub Actions run/head identity, artifact SHA-256 and Git blob identity of evidence-sensitive sources. `tools/check_evidence_freshness.py` enforces source freshness in CI.

## Falsification rule

Narrow/kill a mechanism when representative evidence shows it fails to beat a simpler baseline, predictive value is no better than ordinary validation where superiority was claimed, safe coverage is economically useless, gains disappear across datasets/seeds, or conformity is used to imply adequacy without adequate evidence.

A negative benchmark is a successful research result when it removes unjustified complexity.
