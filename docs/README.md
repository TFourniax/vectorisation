# Documentation index and freshness policy

This repository contains both **current research-control documents** and **historical/supporting design notes**. They do not have equal authority.

## Authoritative current documents

When documents disagree, these win in this order:

1. [`CURRENT_STATUS.md`](CURRENT_STATUS.md) — dated statement of what is implemented, measured, falsified and still experimental.
2. [`evidence-manifest.json`](evidence-manifest.json) — machine-bound promoted evidence, workflow/artifact identities and evidence-sensitive source hashes.
3. [`SEMANTIC_ABI_PROTOCOL_V1.md`](SEMANTIC_ABI_PROTOCOL_V1.md) — current executable Semantic ABI boundary: compiler, directional batch oracle, conformance, remote transport, incremental execution and attestation.
4. [`SEMANTIC_ABI.md`](SEMANTIC_ABI.md) — current Semantic ABI / conformity / adequacy / integrity model.
5. [`BENCHMARKS_V2.md`](BENCHMARKS_V2.md) — current evidence classes and falsification rules.
6. [`ROADMAP.md`](ROADMAP.md) — current evidence-gated next research gates.
7. [`PRIOR_ART.md`](PRIOR_ART.md) — living non-claim / prior-art map. It is not a patent opinion.

The wire shape for Protocol v1 is specified in [`../spec/semantic-abi-oracle-v1.openapi.yaml`](../spec/semantic-abi-oracle-v1.openapi.yaml).

The root [`README.md`](../README.md) is the short public-facing synthesis and should remain consistent with the documents above.

## Supporting / historical documents

The following documents preserve important earlier architecture, mechanisms or threat-model work, but **must not be used as the authoritative statement of current scientific claims**:

- [`SEMANTIC_FABRIC.md`](SEMANTIC_FABRIC.md) — SCF coordinate-migration theory/mechanisms; local translation is now evidence-gated and lost to global on the real BGE→MiniLM SciFact pair.
- [`SEMANTIC_COORDINATE_PROTOCOL.md`](SEMANTIC_COORDINATE_PROTOCOL.md) — coordinate-transition interchange draft; supporting SCF work, **not** the current Semantic ABI Oracle Protocol.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — original SMA architecture.
- [`RESEARCH.md`](RESEARCH.md) — original Phase-0 research basis.
- [`THREAT_MODEL.md`](THREAT_MODEL.md) — security/trust-boundary analysis; still useful but not a benchmark/status document.

Historical mechanism results remain useful when their evidence is still fresh, but any statement such as “next benchmark”, “strongest novelty”, “real neural evidence not yet available” or “local mapping should be preferred” is superseded by `CURRENT_STATUS.md`.

## Evidence freshness

Promoted scientific claims are intentionally stricter than prose freshness:

- `docs/evidence-manifest.json` records the GitHub Actions run/head, artifact SHA-256 and Git blob identities of evidence-sensitive code.
- `tools/check_evidence_freshness.py` recomputes those source hashes in CI.
- If an algorithm or benchmark that produced promoted evidence changes, CI fails until the affected benchmark is regenerated and the manifest is updated.
- Documentation-only edits do not invalidate scientific evidence.

`promoted` means **current and reproducible evidence**, not “positive result.” Negative/falsifying outcomes are promoted too.

Protocol-v1 unit/conformance tests are software evidence. A cross-paradigm implementation claim is promoted only after the corresponding real benchmark artifact is produced and pinned in the evidence manifest.

## Editing rule

A change that materially alters a research claim should update, at minimum:

1. `CURRENT_STATUS.md`;
2. the relevant theory/protocol document (`SEMANTIC_ABI_PROTOCOL_V1.md`, `SEMANTIC_ABI.md`, `BENCHMARKS_V2.md`, `ROADMAP.md`);
3. `PRIOR_ART.md` if the novelty/non-claim boundary changes;
4. `evidence-manifest.json` only after fresh evidence exists;
5. the root README if the public thesis or headline evidence changes.

This hierarchy exists so the repository can preserve research history without allowing an old design note to silently become the source of truth again.
