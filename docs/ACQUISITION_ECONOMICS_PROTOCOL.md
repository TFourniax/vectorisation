# Contract acquisition economics — preregistered product/research gate

**Status:** protocol proposal; results do not exist yet.  
**Purpose:** decide whether Contract Forge creates incremental value over ordinary retrieval-eval curation at an economically meaningful human cost.

This is the highest-value falsification gate for the Semantic ABI product thesis.

The hypothesis is **not**:

> automatically generated contracts are better than nDCG.

That claim would contradict evidence already retained in the repository.

The hypothesis is:

> production evidence + selective expert review can acquire portable application-specific semantic requirements cheaply enough to catch important release regressions that aggregate retrieval metrics and equal-budget conventional eval curation sometimes miss.

## Primary metric

The north-star acquisition metric is:

```text
Important Regression Detection Rate per Expert Minute (IRDR/EM)

= confirmed important candidate regressions detected before release
  ---------------------------------------------------------------
                measured expert review minutes
```

A "confirmed important regression" must satisfy all of the following:

1. the failure is defined by held-out relevance/policy evidence not used to author the candidate clause;
2. the regression is materially worse on a preregistered critical slice or invariant;
3. the detecting contract clause existed before inspecting that candidate's held-out failure;
4. a domain reviewer judges the failure release-relevant under the frozen rubric.

This prevents post-hoc clause authoring from manufacturing success.

## Secondary metrics

Report all of these; do not optimize only one:

- **expert minutes**;
- promoted clauses / expert minute;
- review-queue precision;
- review-queue recall on later confirmed critical clauses;
- false-block rate;
- false-pass rate;
- ordinary nDCG / Recall / MRR;
- contract conformity;
- contract adequacy evidence;
- critical-slice regression recall;
- contract stability across backend changes;
- number of clauses that merely reproduce incumbent mistakes;
- click-evidence bias by query-frequency bucket / position bucket;
- audit execution cost and latency.

## Public data ladder

Use several evidence regimes rather than one benchmark.

### Dataset A — TripClick: acquisition at behavioral scale

TripClick provides large health-search interaction logs and click-derived query-document relevance signals.

Use it to test:

- whether weak behavioral evidence can accumulate into useful soft clauses;
- whether position-aware acquisition beats naive click counting;
- whether uncertainty/review prioritization improves value per review minute;
- long-tail vs frequent-query behavior;
- how often behavioral evidence conflicts with held-out relevance evidence.

Health is useful because incorrect ranking can be consequential, but no claim of clinical safety should be made from this benchmark.

### Dataset B — TREC Deep Learning: independent graded judgments

Use TREC DL test queries and NIST relevance judgments as a stricter held-out validation surface.

The graded judgments allow tests where a candidate keeps aggregate score nearly flat while demoting a highly relevant/perfect result on a declared critical query.

### Dataset C — BEIR multi-domain

Retain SciFact for continuity, then add NFCorpus and at least two non-biomedical datasets.

Purpose:

- verify that Contract Forge is not only exploiting health-search click structure;
- evaluate domain shift;
- preserve comparison with the existing Semantic ABI multi-dataset evidence.

## Experimental split discipline

For each dataset, freeze three disjoint surfaces before running candidate mutations:

```text
ACQUISITION
logs / train judgments / policy examples
        |
        v
candidate clauses
        |
        +---- REVIEW subset (human budget)
        |
        v
frozen Semantic Contract

CERTIFICATION
untouched labels used to tune acquisition thresholds

FINAL TEST
untouched queries / labels / failure families
```

The final test surface must never be used to:

- generate clauses;
- choose clause weights;
- select review items;
- set promotion thresholds;
- choose fault families after observing results.

## Competing acquisition methods

Evaluate equal human-review budgets.

### B0 — Aggregate-metrics only

No application contract. Release uses ordinary train/certification nDCG/Recall gates.

### B1 — Manual golden-set curation

Experts spend the same measured number of minutes writing conventional query -> relevant-document judgments.

### B2 — Incumbent snapshot

Freeze current top-k behavior. This baseline is intentionally dangerous but necessary: it tests whether Contract Forge does more than snapshot testing.

### B3 — LLM-generated eval candidates

Generate candidate expected-source/ranking examples from corpus + traces, then give experts the same review budget.

The LLM may propose; it may not see final-test labels or candidate-failure outcomes.

### B4 — Random review of evidence candidates

Same candidate pool as Contract Forge, but human review items are chosen randomly.

### B5 — Contract Forge

Evidence reliability + contradiction handling + prioritized review.

### B6 — Contract Forge + active information gain

Only after B5 is frozen. Select the next review by expected reduction in critical semantic uncertainty rather than heuristic priority.

## Fault families

Each candidate stack is generated from a frozen fault catalog. Include both realistic and controlled changes.

### Retrieval/model changes

- embedding-model replacement;
- BM25 -> dense;
- dense -> hybrid;
- dense/hybrid -> late interaction;
- reranker replacement/removal;
- hybrid-weight changes;
- ANN recall degradation / search-budget reduction.

### Corpus/index changes

- chunk-size/overlap changes;
- missing-document shard;
- stale document superseding current document;
- document-ID remapping bug;
- partial reindex;
- metadata/filter omission;
- duplicate-document injection.

### High-value application failures

- deprecated content outranks current content;
- generic information outranks required emergency/procedure content;
- wrong jurisdiction/version outranks applicable source;
- exact entity/SKU/account procedure becomes unreachable;
- tenant/permission-scoped material enters an ineligible retrieval surface;
- required multi-document evidence loses one component.

Security/permission faults should only be benchmarked in synthetic or explicitly authorized test data.

## The critical incremental-value experiment

This is the experiment that most directly tests the company thesis.

Generate a candidate retrieval change where:

```text
ordinary aggregate quality >= release threshold
```

Then ask whether a preregistered critical semantic requirement fails.

Count success only if held-out evidence confirms that the failure is real.

Report four quadrants:

| Ordinary metrics | Semantic Contract | Interpretation |
|---|---|---|
| PASS | PASS | candidate appears safe on measured surfaces |
| FAIL | PASS | ordinary broad regression; ABI is not needed to catch it |
| FAIL | FAIL | both mechanisms catch it |
| PASS | FAIL | **incremental Semantic ABI value candidate** |

The fourth quadrant is commercially important but scientifically dangerous: every case must be independently adjudicated so that overly brittle clauses are not counted as victories.

## Human study

Synthetic "review-minute" estimates are acceptable for development only. Promotion requires a measured study.

### Review task

Show the reviewer only:

- query / semantic situation;
- proposed relation;
- minimal source excerpts/IDs needed to decide;
- provenance category;
- conflict summary.

Do **not** show:

- which candidate system will later fail;
- final-test relevance labels;
- whether the clause helps Semantic ABI win the benchmark.

### Timing

Measure wall-clock active review time per item. Exclude setup/training in the primary metric but report it separately as onboarding cost.

### Reviewer agreement

Double-review a preregistered sample. Report agreement and adjudication rate. If agreement is low, the acquisition target may be semantically underspecified rather than merely hard to automate.

## Promotion gates

The feature is not promoted as the default onboarding path unless all gates pass.

### Gate 1 — economics

Contract Forge must improve IRDR/EM over equal-budget manual golden-set curation by a preregistered material margin.

Initial suggested gate for testing, to be frozen before labels are inspected:

```text
>= 1.5x IRDR/EM
```

If 1.5x is not met, report the exact result; do not tune the target post hoc.

### Gate 2 — incremental detection

There must be multiple independently confirmed `ordinary PASS / contract FAIL` regressions across at least two datasets/domains.

A single anecdote is insufficient.

### Gate 3 — false blocks

Contract brittleness must not create an unacceptable release tax. Freeze a maximum false-block rate before the final test.

### Gate 4 — portability

The same acquired contract must execute without semantic translation against at least:

- sparse/BM25;
- dense vector retrieval;
- hybrid retrieval;
- late interaction;
- one production vector/search provider adapter.

### Gate 5 — acquisition leakage

Audit the acquisition pipeline to prove final-test/candidate-failure labels cannot influence clause generation or review priority.

### Gate 6 — bias

Behavioral acquisition must not systematically overfit frequent/head queries while leaving rare, safety-critical or long-tail slices effectively unconstrained.

## Kill criteria

Contract Forge should be materially redesigned if any of the following survive serious testing:

- equal-budget manual eval curation catches the same critical regressions with less expert time;
- most auto-promoted behavioral clauses merely preserve incumbent ranking mistakes;
- contradiction/review volume grows roughly linearly with traffic so human cost does not compress;
- the useful contract is dominated by a tiny hand-written policy set, making automated acquisition unnecessary;
- click bias makes long-tail/safety behavior worse than manual curation;
- the `ordinary PASS / contract FAIL` quadrant is mostly false alarms;
- stable logical IDs are too difficult to maintain across real migrations.

A failed gate is useful evidence. The repository should preserve it.

## Product interpretation if the gates pass

Passing these gates changes the product story materially.

It would support the claim that a team can start from existing production evidence, spend a bounded amount of expert attention, and obtain a portable semantic release contract that catches some important failures ordinary aggregate evaluation does not surface economically.

That is a much stronger foundation for **Semantic Change Control** than either:

- "we have a different eval DSL"; or
- "we can snapshot current retrieval behavior".

It would justify building the hosted control plane, provider adapters, Semantic SLOs and signed release attestations around the protocol.
