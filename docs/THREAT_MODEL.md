# Threat model

Semantic-coordinate transitions create a new trust boundary. A transition can influence many queries and therefore deserves the same scrutiny as an index build or model artifact.

## Assets

- logical record identity and metadata;
- raw embeddings and facets;
- paired transition anchors;
- fitted transition artifacts;
- transition diagnostics and routing graph;
- virtual semantic cells;
- ranking integrity.

## Threats

### Poisoned anchors

An attacker who controls paired anchors can bend a local transition so selected queries are transported toward attacker-controlled regions.

Mitigations:

- anchor provenance;
- deterministic held-out evaluation;
- robust sampling / outlier detection;
- minimum support per local chart;
- cycle consistency against independent routes;
- signed immutable anchor manifests in production.

### Hub / black-hole injection

High-dimensional indexes can contain vectors that appear in a disproportionate number of neighborhoods. A cross-model transport layer could amplify the effect if it routes many queries into such a region.

Mitigations already in the research kernel:

- mutual-kNN topology;
- hubness diagnostics;
- local-density / CSLS-inspired ranking;
- cross-space consensus rather than trusting one coordinate system.

Future work should benchmark targeted adversarial hub injection across transitions.

### Model or preprocessing identity confusion

Two artifacts called by the same model name can differ by tokenizer, pooling, normalization, prompt prefix or model revision. A transition trained for one pipeline may silently fail on another.

Mitigations:

- immutable space fingerprints rather than human labels alone;
- dimension checks;
- canary anchors at load time;
- transition expiry / revalidation.

### Stale transition under model/domain drift

A valid transition can become invalid when the data distribution changes.

Mitigations:

- rolling held-out canaries;
- neighborhood-disagreement monitoring;
- coordinate-aware drift reports;
- time-bounded transition validity;
- automatic quarantine below confidence thresholds.

### Corrupted transition artifact

A modified matrix can redirect every transported query.

Mitigations planned for protocol v1:

- cryptographic checksums;
- signed manifests;
- explicit source/target fingerprints;
- append-only audit history;
- cycle audit after deployment.

### Overconfident virtual materialization

A transported coordinate is an approximation, not a fresh embedding. Treating it as direct evidence may create hidden retrieval errors.

Mitigations:

- `_virtual` flag;
- cell dispersion;
- minimum cell/route confidence;
- direct observation replaces virtual coordinate as soon as available;
- surface direct/virtual coverage in migration status.

### Privacy / inversion

Embedding vectors can leak properties of their source data, and paired anchors expose correspondence across representation systems. Transition matrices may themselves reveal structural information.

Mitigations depend on deployment:

- least-privilege access to vectors and anchors;
- encryption at rest/in transit;
- avoid exporting transition artifacts across trust domains without review;
- empirical membership/inversion testing for sensitive corpora;
- consider privacy-preserving anchor schemes as separate research work.

## Safety posture

A failed transition should degrade to **unreachable**, not to silent approximate transport. The most important production feature is not another mapping family; it is reliable refusal when evidence no longer supports a route.
