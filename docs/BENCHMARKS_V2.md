# Benchmark / evidence protocol

The repository separates **software correctness**, **protocol interoperability**, **mechanism evidence**, **real representation evidence**, **contract adequacy**, **statistical certification**, **economics** and **negative/falsification evidence**.

Latest numbers: [`CURRENT_STATUS.md`](CURRENT_STATUS.md). Machine-bound promoted evidence: [`evidence-manifest.json`](evidence-manifest.json).

## Research rules

1. Never use test qrels to author a contract or choose a variant.
2. Compare against the simplest relevant baseline.
3. Separate portability from predictive validity.
4. Separate conformity from adequacy.
5. Separate portable application truth from implementation integrity.
6. Workflow success means the experiment executed; a hypothesis may still fail its preregistered gate.
7. Negative results are promoted when reproducible.
8. Bind major evidence to exact artifacts and evidence-sensitive source blobs.
9. For Protocol-v1 claims, distinguish **software/TCK conformance** from **real cross-paradigm evidence**.

## Evidence classes

- **S — software:** unit/integration tests, Python matrix, TCK, evidence freshness.
- **P — protocol interoperability:** unchanged contract digest, provider manifest/conformance, zero missing clauses, batch-plan execution and wire compatibility across genuinely different retriever algebras.
- **M — mechanisms:** synthetic/procedural or deliberately corrupted tests.
- **R — real representation:** real datasets/models/retrievers with untouched task evaluation.
- **A — adequacy:** coverage, mutation/localization, predictive validity, baseline comparison, held-out volume/diversity.
- **C — certification:** selection/certification split, SLA, confidence/error budget, optional-stopping treatment and fallback.
- **E — economics:** re-embeddings/API/GPU/backend cost, downstream gap recovered, latency/backfill avoided.
- **N — negative evidence:** failed/narrowed hypotheses retained explicitly.

## Protocol v1 gate

A Protocol-v1 interoperability result is promoted only when all of the following are explicit:

- exact application-contract digest;
- backend/oracle manifest identity and directionality;
- contract compiled without backend-specific clause rewriting;
- zero required missing clauses;
- conformance result;
- execution-plan operation counts / batch calls;
- untouched downstream retrieval metrics when available;
- guardrail distinguishing portability from quality superiority and novelty claims.

### Real ColBERTv2 / SciFact result — promoted

The v0.5 gate compares lexical BM25 and real ColBERTv2 MaxSim under the **same 600-clause contract**:

- 1,800 docs;
- 300 train queries for contract construction;
- 200 untouched test queries;
- contract digest `d3dd26211a7a18c8ae8ec07be4e0bcd8e1805024fb8dcd4a67d71506627e1843`.

| implementation | ABI | nDCG@10 | Recall@10 | missing |
|---|---:|---:|---:|---:|
| BM25 | 0.9067 | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | 0.9047 | 0.7337 | 0.8395 | 0 |

ColBERT passes **660 conformance checks with zero issues**, all hard clauses and zero missing clauses. The compiled audit represents 805 object checks, 600 unique directional score pairs and 300 top-k requests in **3 batch operation families**.

**Promotion meaning:** evidence that a single contract executes across sparse lexical and asymmetric multi-vector late-interaction retrieval without shared coordinates or clause translation. It is not a general quality-superiority result.

## Predictive-validity gate

SciFact, NFCorpus and FiQA; MiniLM, BGE, BM25, BGE+BM25 hybrid and seven controlled degradations per dataset. Train qrels author contracts; test qrels evaluate downstream quality only.

| metric | ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman | 0.9697 | **0.9757** |
| pooled delta Spearman | 0.9573 | **0.9724** |
| pooled delta Pearson | 0.9519 | **0.9850** |
| pooled pairwise concordance | 0.9172 | **0.9400** |

**Falsification:** current ABI is not a generally superior aggregate nDCG predictor. Keep ordinary IR validation.

## Progressive Semantic Audit

Policy: hard clauses exhaustive; soft clauses weight-proportional; cached observations; predeclared looks; explicit error budget; exact fallback.

Evidence:

- Digits 1,500 clauses: **15/15** exact decision agreement, **12/15** early, mean early unique fraction **7.17%**;
- procedural 10k/100k/250k: **10/10** exact decisions, **9/10** early;
- representative 250k away-from-boundary decisions inspect **0.04–0.3992%** of clauses.

Next baseline: Adaptive Learn-Then-Test/e-processes under non-iid/sliced faults and heterogeneous oracle costs.

## Selective rollout

SciFact/BGE at `delta=0.10`:

- 10% failure SLA not certified;
- preregistered exact rule certifies 15% with upper bound ~13.16%;
- held-out acceptance 197/200;
- realized accepted failure ~10.15%.

## Repair economics

SciFact/BGE 10% document corruption:

- clean nDCG 0.7875 → corrupted ~0.6970;
- budget25 coverage planner: 88% corrupted docs, ~33.9% lost-gap recovery;
- random: ~7.3% corrupted, ~1.5% recovery;
- no method reaches the preregistered 90% recovery target.

Implementation-integrity canaries increase coverage and larger-budget recovery, but still do not reach 90%.

### Fixed clause-incidence planner — failed independent gate

Weights were frozen before four unseen fault scenarios. Budget50 preregistered gate required +0.05 mean recovery over best baseline and ≥3/4 wins/ties.

Observed:

- incidence ~0.215;
- best baseline ~0.237;
- lift ~-0.022;
- wins/ties 2/4.

**Not promoted as a repair improvement.**

## Protocol TCK vs scientific evidence

`spec/semantic-abi-oracle-v1-tck.json` fixes canonical contract, plan, manifest, snapshot and protocol-audit digests. The Python implementation must reproduce them across supported Python versions.

Passing the TCK proves implementation compatibility with the protocol fixture. It does **not** by itself prove that a new retrieval paradigm preserves useful semantics; that requires a real benchmark such as the ColBERTv2 gate.

## State-bound incremental evidence

Incremental execution is software/mechanism evidence until tested under real provider state changes. Reuse is allowed only with deterministic behavior, non-empty `state_digest`, unchanged full manifest identity and parent snapshot/plan binding.

Future economic benchmarks should report:

- operation reuse fraction;
- network/API calls avoided;
- latency/cost reduction;
- false-reuse rate (must remain zero under declared state changes).

## Contract Adequacy protocol

Strong release claims should preregister required adequacy axes with `ContractAdequacyRequirements`. Missing required evidence must remain `insufficient_evidence`.

Do not optimize adequacy against the same held-out set used to certify it.

## Real integration requirements

Before production claims, implement and measure real Elasticsearch, Qdrant, pgvector and Vespa/provider adapters. Report:

- protocol conformance / missing clauses;
- p50/p95/p99 control-plane latency;
- batch payload sizes;
- provider/API/GPU cost;
- incremental reuse savings;
- fallback fraction;
- backfill/reindex cost avoided;
- application vs integrity roles;
- state-digest invalidation behavior.

## Evidence freshness

Major promoted numbers are tied to Actions run/head identity, artifact SHA-256 and Git blob identity of evidence-sensitive sources. `tools/check_evidence_freshness.py` enforces those hashes in CI.

A negative benchmark is a successful research result when it removes unjustified complexity.