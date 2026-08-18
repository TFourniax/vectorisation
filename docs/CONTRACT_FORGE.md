# Contract Forge — acquiring Semantic Contracts without freezing today's bugs

**Status:** experimental v0.6 candidate  
**Goal:** make `semantic-abi init` economically plausible for a real production system.

Semantic ABI only becomes infrastructure if teams do **not** have to hand-author thousands of clauses. Contract Forge is the first acquisition layer: it turns existing evidence from a running system into a small auto-promoted contract plus a prioritized review queue.

The design constraint is stronger than "generate evals from logs":

> Current retrieval behavior is evidence, not truth.

Blindly snapshotting today's top-k results would make migrations reproducible while also preserving existing mistakes. Contract Forge therefore separates sources by epistemic strength, accumulates support, detects opposite evidence and refuses to silently turn ambiguity into application truth.

## Inputs

The zero-dependency JSONL format currently accepts four event families.

### 1. Explicit preference

```json
{"type":"preference","anchor":"q:delete-account","preferred":"doc:gdpr-delete","rejected":"doc:newsletter-unsubscribe","source":"human_correction","confidence":1.0,"criticality":0.9,"event_id":"ticket-1842"}
```

Meaning: for this semantic situation, the preferred object should outrank the rejected object.

### 2. Relevant set

```json
{"type":"relevant_set","anchor":"q:delete-account","relevant":["doc:gdpr-delete","doc:identity-check"],"candidate_k":5,"min_recall":1.0,"source":"human_judgment","event_id":"review-51"}
```

Meaning: these objects should remain reachable within a declared retrieval budget.

### 3. Policy invariant

```json
{"type":"policy","anchor":"q:overdose","preferred":"doc:emergency-protocol","rejected":"doc:marketing-faq","criticality":1.0,"hard_eligible":true,"event_id":"med-policy-7"}
```

Policy evidence is marked as eligible to become a hard invariant. Automatic hard promotion still depends on the declared acquisition thresholds; it is never inferred from clicks.

### 4. Production trace

```json
{"type":"trace","anchor":"q:refund","results":["doc:a","doc:b","doc:c"],"clicked":["doc:b"],"selected":["doc:b"],"explicit_negative":["doc:a"],"accepted_sources":["doc:b"],"event_id":"trace-991"}
```

For click evidence, Contract Forge only infers `clicked > skipped-above-click`. It does **not** treat every non-clicked result as negative. Baseline ranking alone creates no clause.

## Promotion model

Each event contributes effective support:

```text
effective support = event confidence × source reliability
```

Default source reliabilities deliberately distinguish normative and behavioral evidence:

| Source | Default reliability |
|---|---:|
| policy | 1.00 |
| human correction | 1.00 |
| human judgment | 0.95 |
| explicit feedback | 0.90 |
| accepted answer source | 0.85 |
| user selection | 0.75 |
| production click | 0.45 |
| implicit behavior | 0.35 |
| synthetic | 0.30 |
| captured baseline behavior | 0.15 |

Repeated weak evidence may eventually become a **soft** clause. It cannot become hard unless every supporting event is explicitly `hard_eligible`, criticality is high, confidence clears the hard threshold and there is no opposing evidence.

For a directional preference, evidence in the reverse direction is aggregated as opposition. Sufficient opposition forces review even if one direction has more support.

## Outputs

`forge_contract()` returns four artifacts:

1. **Auto-promoted Semantic Contract** — only candidates that clear policy.
2. **Acquisition report** — evidence digest, source mix, promoted/review/rejected counts, conflict count and review economics.
3. **Candidate ledger** — why every candidate was promoted, reviewed or rejected.
4. **Prioritized review queue** — conflicts and high-criticality uncertainty first.

The contract metadata binds the order-independent evidence digest and acquisition policy. The same raw evidence therefore has an auditable lineage into the resulting Semantic Contract.

## CLI

```bash
semantic-abi forge evidence.jsonl \
  --name customer-support \
  --version 17 \
  --output contract-v17.json \
  --report forge-report.json \
  --review review-queue.jsonl
```

Then audit any Protocol-v1 implementation with the resulting contract:

```bash
semantic-abi remote-audit https://candidate-oracle.example contract-v17.json
```

A versioned evolution can link a parent contract:

```bash
semantic-abi forge new-evidence.jsonl \
  --parent contract-v17.json \
  --version 18 \
  --output contract-v18.json
```

## Why this is different from an ordinary eval dataset

An eval dataset usually binds an input to an expected output or a score. Contract Forge targets a different artifact: **portable semantic relations over stable logical IDs** that can execute unchanged against dense, sparse, late-interaction, graph or proprietary retrieval implementations.

The intended workflow is complementary to nDCG/Recall and LLM-as-judge evaluation:

```text
production traces / feedback / policy / judgments
                    |
                    v
              Contract Forge
                    |
       +------------+-------------+
       |                          |
 auto-promoted contract      review queue
       |                          |
       +------------+-------------+
                    |
             Semantic ABI
                    |
        +-----------+-----------+
        |           |           |
      Qdrant     OpenSearch    ColBERT ...
        |           |           |
        +-----------+-----------+
                    |
       conformity + adequacy + risk
```

Conventional IR evaluation still asks whether a candidate is good on aggregate. Semantic ABI asks whether the candidate still satisfies the specific relations the application considers non-negotiable.

## The anti-self-reference rule

The acquisition layer follows one architectural rule that should remain invariant as the product evolves:

> A system may propose changes to its semantic implementation, but the same untrusted mechanism must not be allowed to invent, approve and evaluate its own definition of success.

Therefore:

- agent/LLM-generated candidate clauses are allowed;
- synthetic evidence has low default reliability;
- production behavior can accumulate into soft requirements;
- explicit policy and human corrections are privileged evidence;
- contradiction triggers review;
- adequacy remains separate from conformity;
- hard clauses cannot emerge from ordinary click evidence.

## Next acquisition gates

The current implementation intentionally starts with a small, inspectable kernel. The highest-value next gates are:

1. **OpenTelemetry/OpenInference ingestion** so existing retrieval spans can feed the forge without a proprietary tracing SDK.
2. **LangSmith / Phoenix / OpenSearch UBI importers** implemented as adapters over the same evidence model.
3. **Source-sensitive promotion thresholds** so a signed policy artifact can be handled differently from weak behavioral evidence without globally lowering thresholds.
4. **De-biasing for implicit feedback** using position/examination-aware estimators rather than raw click counts.
5. **Active review** that chooses the next human question by expected reduction in critical semantic uncertainty, not merely confidence proximity.
6. **Contract mutation adequacy**: generated clauses must demonstrate that they catch realistic faults before they can support release claims.
7. **Temporal semantics**: expiry, supersession and stale-document invariants.
8. **PII minimization**: hash/stable-ID acquisition paths that do not require storing raw user queries when the customer cannot retain them.

## Economic research target

The important adoption metric is not raw clause count. It is:

```text
important regressions caught / expert-minute
```

Contract Forge already reports estimated review minutes and promoted clauses per review minute as crude instrumentation. Future benchmark campaigns should measure the stronger outcome above against ordinary manual eval curation.

A successful gate would look like:

- ingest a real production trace/history export;
- infer thousands of candidate requirements;
- automatically promote the high-confidence majority;
- surface a small, high-value review queue;
- use the resulting contract to catch regressions missed by aggregate metrics;
- preserve the contract unchanged across materially different retrieval implementations.

That is the path from a research protocol to a low-friction semantic control plane.
