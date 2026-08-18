# Semantic ABI — Product Entry Point

The root `README.md` intentionally remains the evidence-oriented research history of Semantic ABI v0.5. The v0.6 productization work is documented separately so product packaging does not erase or rewrite the research record.

## Start here

- **End-to-end usage:** [`docs/PRODUCT_QUICKSTART.md`](docs/PRODUCT_QUICKSTART.md)
- **What is actually proven/tested:** [`docs/PRODUCT_READINESS.md`](docs/PRODUCT_READINESS.md)
- **Security/trust boundary:** [`docs/PRODUCT_SECURITY.md`](docs/PRODUCT_SECURITY.md)
- **GitHub release gate:** [`docs/GITHUB_ACTION.md`](docs/GITHUB_ACTION.md)
- **Acquisition economics experiment:** [`docs/ACQUISITION_ECONOMICS_PROTOCOL.md`](docs/ACQUISITION_ECONOMICS_PROTOCOL.md)
- **Protocol v1:** [`docs/SEMANTIC_ABI_PROTOCOL_V1.md`](docs/SEMANTIC_ABI_PROTOCOL_V1.md)

## Product surface

Install the release-candidate engine and inspect the CLI:

```bash
pip install -e .
semantic-abi --help
```

Production integrations should prefer the curated Python API:

```python
from semantic_atlas.product import SemanticContract, ReleasePolicy
```

The current package version on the productization branch is `0.6.0rc1`. It is deliberately not labeled 1.0 while acquisition-economics, external signing, independent non-Python interoperability and external security review remain open gates.

## Intended lifecycle

```text
policy / judgments / telemetry + feedback
                  |
                  v
          Contract Forge
                  |
          review + versioning
                  |
                  v
          Semantic Contract
                  |
       +----------+-----------+
       |                      |
    baseline               candidate
       |                      |
       +----- Protocol v1 ----+
                  |
             semantic diff
                  |
        adequacy + risk evidence
                  |
              attestation
                  |
          strict release gate
```

`semantic-abi check` is a preflight semantic diff. `semantic-abi release` is deliberately stricter: it revalidates the candidate and certification evidence and refuses production certification without an immutable provider `state_digest`.

## Rollback / research preservation

This productization is developed on its own branch. The R&D branch and the Contract Forge checkpoint remain separate so unsuccessful product decisions can be discarded without destroying the underlying experiments or evidence history.
