# Semantic ABI — meaning as a contract, embeddings as implementations

## Problem statement

Embedding interoperability is becoming an active research area. Translation, vector linking and embedding-independent database representations can reduce coupling between one stored index and one encoder.

That still leaves a different production question unanswered:

> **What must remain semantically true when a representation implementation changes?**

A migration can be geometrically well aligned and still break the application's important cases. Conversely, a new representation can reorder many nearest neighbors while preserving or improving the semantic behavior the application actually cares about.

Semantic ABI treats this as a schema/compatibility problem rather than only a coordinate-translation problem.

## Analogy

A software ABI does not require two implementations to have identical machine code. It defines externally observable contracts they must respect.

Semantic ABI applies the same separation:

```text
semantic contract (stable logical layer)
        |
        +-- embedding model A + vector store A
        +-- embedding model B + vector store B
        +-- sparse / graph / symbolic implementation
        +-- future representation not known when contract was authored
```

The contract is expressed over stable logical object IDs and relations, not vector coordinates.

## Contract clauses in the V0 implementation

### Ordinal triplet

`closer(anchor, positive) < closer(anchor, negative)`

Operationally, candidate coordinates must satisfy:

`sim(anchor, positive) - sim(anchor, negative) >= margin`

The assertion is coordinate-independent: it identifies logical objects and an ordering relation, not a required vector value.

Triplets have a strong mathematical basis in ordinal-embedding literature, where configurations can be studied or reconstructed from relative distance comparisons alone.

### Neighborhood clause

A critical object may require that at least a configured fraction of a reference semantic neighborhood survives.

This is useful for **behavior compatibility**, which is intentionally separate from application semantics.

### Mutual-neighbor clause

A reciprocal edge can be frozen as a stronger local-topology invariant.

Future clauses should include typed graph relationships, group separation, monotonic attributes, contradiction constraints, temporal ordering and provenance/trust requirements.

## Two independent compatibility dimensions

Semantic ABI deliberately separates two questions.

### 1. Application semantic compatibility

Examples:

- a fraud pattern must remain nearer to known fraud cases than to a hard benign negative;
- two parts with the same engineering function must remain semantically related;
- a safety-policy exception must never become the nearest match for a prohibited request;
- a digit should prefer hard examples of the same digit over a confusable different digit.

These clauses may come from labels, domain rules, human judgments, click/relevance data, ontologies or curated safety cases.

### 2. Legacy behavior compatibility

The system can independently capture selected nearest-neighbor sets, reciprocal edges and ordinal relations from a current implementation.

A new representation may therefore receive two scores:

```text
application semantic compatibility = 0.95
legacy behavior compatibility      = 0.72
```

That result is meaningful: the new implementation changed retrieval behavior substantially while mostly preserving the application's declared semantics.

A single "embedding similarity" number cannot express this distinction.

## Local certification field

A global compatibility score is insufficient. Representation changes often fail in localized semantic regions.

Every violated clause contributes risk to the logical objects it touches. The audit therefore produces a sparse **semantic risk field** over stable object IDs.

At query time, `ContractReport.local_risk()` interpolates risk from nearby audited landmarks in the candidate implementation's coordinate system. `SemanticABIGate` can:

1. prefer a new implementation in certified regions;
2. fall back to a legacy implementation where the new model violates the contract;
3. reject all implementations when hard clauses fail or no region is sufficiently certified.

This turns model rollout from an all-or-nothing deployment into a potentially **region-wise semantic rollout**.

## Hash-chained semantic schema history

A contract has a canonical SHA-256 digest over its meaning-bearing content. `ContractLedger` records contract versions in an append-only hash chain.

The ledger is intentionally small; it is not a blockchain claim. Its purpose is to make semantic schema evolution explicit and tamper-evident:

```text
contract v1 -> contract v2 -> contract v3
      |             |             |
   model A       model B        model C
   audit         audit          audit
```

In a production design, contract versions, provenance, reviewers, test evidence and deployment decisions should be signed and stored in the governance/control plane.

## Relationship to Semantic Coordinate Fabric

These layers solve different problems:

- **SCF** asks: *can coordinates be translated/routed between representation spaces?*
- **Semantic ABI** asks: *does a representation preserve the semantic invariants required by the application?*

A transition can be mathematically high-confidence but still fail an ABI clause. An implementation can satisfy the ABI without being a faithful coordinate translation of the previous model.

Therefore ABI certification should eventually become an independent gate in SCF routing.

## First real-data mechanism result

The included `semantic_abi_digits_benchmark.py` uses 1,400 real handwritten-digit observations represented as either 64-D normalized pixels or 324-D HOG descriptors.

A task-oriented contract containing 1,400 hard-negative ordinal assertions scores approximately:

- pixels: **0.980**;
- HOG: **0.911**;
- HOG with 10% of object identities deliberately corrupted: **0.813**.

At a local-risk threshold of 0.15, certified coverage falls from about **76.9%** for HOG to **57.0%** after corruption.

A separate captured legacy-behavior contract scores:

- pixels: **1.000**;
- HOG: **0.711**;
- corrupted HOG: **0.610**.

The useful observation is not that HOG is "better". It is that application compatibility and legacy-ranking compatibility are measurably different properties.

This is still a small classical dataset, not evidence that the abstraction works for production text embedding upgrades.

## Research questions

1. Which clause families are sufficient to predict downstream retrieval regressions?
2. How many semantic assertions are needed for a useful contract on million/billion-object corpora?
3. Can active selection choose the next contract examples/re-embeddings to reduce uncertainty optimally?
4. How should local certification be calibrated so that a stated 1% risk corresponds to observed failure probability?
5. Can semantic contracts be shared across dense, sparse, graph and multimodal implementations?
6. Which invariants are stable across language and domain shifts without preserving obsolete model quirks?
7. Can topology or persistent ordinal structures provide compact high-order clauses?

## Kill criterion

Semantic ABI should be reduced to ordinary regression testing if its local risk field does not predict downstream failures better than simple held-out relevance evaluation, or if useful contracts require so many assertions that maintaining them costs as much as re-evaluating the entire corpus.

The objective is not a new name for tests. The objective is a **portable semantic interface** whose clauses, provenance, local risk and deployment semantics survive representation changes.
