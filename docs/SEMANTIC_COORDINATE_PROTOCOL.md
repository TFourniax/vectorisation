# Semantic Coordinate Protocol — draft 0

This document sketches a database-neutral contract for interoperable embedding coordinate systems. It is deliberately small. The objective is to define invariants that can sit above any ANN engine, not to invent another database wire protocol.

## 1. Space

A `Space` identifies a representation coordinate system. At minimum it has:

- stable name / identifier;
- dimensionality;
- modality;
- model/version identifier when known;
- preprocessing identity in production deployments.

**Invariant S1:** vectors from different spaces have no implicit metric relationship. A system must never compute cross-space cosine or L2 merely because dimensions happen to match.

## 2. Logical object

A logical object has one stable ID and zero or more observations:

`object_id -> {space_id: vector}`

Model migrations add observations; they do not create a new logical object.

**Invariant O1:** logical identity is independent of embedding identity.

## 3. Transition

A transition maps a source coordinate into a target coordinate:

`Transition(source, target, maps, diagnostics)`

Required metadata should include:

- source/target space IDs;
- transition family/version;
- support/anchor count;
- held-out diagnostics;
- creation timestamp and training-data fingerprint;
- optional validity domain / chart centroids;
- integrity checksum/signature.

The current executable format is `semantic-coordinate-transition` version 1 stored as compressed NumPy arrays plus JSON metadata. It is an implementation seed, not a frozen standard.

**Invariant T1:** a transition without an audit is untrusted.

**Invariant T2:** confidence must be based on held-out observations when enough anchors exist.

**Invariant T3:** every transported vector retains the transition path and confidence that produced it.

## 4. Route

A route is an ordered list of transitions. Route confidence decreases with uncertain or long paths.

**Invariant R1:** routing optimizes reliability, not hop count alone.

**Invariant R2:** callers may set a minimum confidence; unreachable is preferable to fabricated certainty.

## 5. Cycle audit

For a closed route `A -> ... -> A`, transported anchors should approximately recover their starting coordinates.

**Invariant C1:** large cycle error invalidates or quarantines the affected route until investigated.

Cycle consistency does not prove correctness; it is a necessary cross-check when redundant transitions exist.

## 6. Semantic cell

A semantic cell represents one logical object in a target space from one or more direct/transported observations.

Required fields:

- target space;
- center;
- dispersion;
- confidence;
- observation provenance;
- direct vs virtual status.

**Invariant CELL1:** transported coordinates are explicitly labelled; they must never masquerade as direct embeddings.

**Invariant CELL2:** disagreement is information. It is stored as uncertainty, not averaged away silently.

## 7. Virtual materialization

A virtual index may materialize high-confidence semantic-cell centers into a target coordinate system before every object has a direct target embedding.

**Invariant V1:** every virtual point is replaceable by a direct observation without changing logical identity.

**Invariant V2:** virtual admission is confidence-gated.

**Invariant V3:** coverage and direct/virtual proportions are observable.

## 8. Search fusion

When several spaces are searched concurrently, raw similarity scores are not assumed to be calibrated across spaces. Rank-based fusion is the safe default.

A partially populated index must declare coverage.

**Invariant F1:** evidence from a partial index cannot be treated as if it came from full-corpus rank statistics.

The reference engine applies coverage-corrected reciprocal-rank fusion and transition-confidence weighting.

## 9. Security and governance

A production protocol should add:

- signed transition manifests;
- immutable model/preprocessing fingerprints;
- anchor provenance and access controls;
- calibration windows and expiry;
- revocation / quarantine;
- privacy policy for transition artifacts.

See `THREAT_MODEL.md`.

## 10. Portability goal

The protocol should eventually allow this topology:

```text
                 transition
Open model A  ---------------->  proprietary model B
     |                                  |
     |                                  |
  Qdrant                              DiskANN
     |                                  |
     +------------ logical IDs ---------+
```

The ANN stores remain independent. The Semantic Coordinate Fabric makes their representation spaces explicitly interoperable when—and only when—the measured evidence justifies it.
