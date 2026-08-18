# Semantic ABI GitHub Action

The repository exposes a composite action that runs the **strict** production release gate. It does not implement a second policy engine; it installs the same Python package and executes `semantic-abi release`.

## Caller workflow

The caller repository should check out its own contract/configuration artifacts first, then invoke Semantic ABI from a pinned commit or release tag:

```yaml
name: semantic-release

on:
  pull_request:

jobs:
  semantic-abi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: TFourniax/vectorisation@<PINNED-COMMIT-OR-TAG>
        with:
          contract: semantic/contract.json
          baseline: semantic/prod.json
          candidate: semantic/candidate.json
          attestation: semantic/candidate-attestation.json
          adequacy: semantic/adequacy.json
          risk-certificate: semantic/risk-certificate.json
          check-score-pairs: "true"
```

For a pgvector provider add:

```yaml
          install-extras: postgres
```

The provider configuration itself references secrets by environment-variable name. Supply those environment variables through GitHub Actions secrets or an OIDC-backed secret manager; do not put secret values in the action inputs.

## Failure behavior

The action fails the step when `semantic-abi release` returns non-zero. A passing action therefore means that, for the exact artifacts and provider states observed in that run:

- the baseline→candidate semantic diff satisfies the declared release policy;
- the candidate has a non-empty `state_digest`;
- its attestation matches the exact re-executed candidate audit;
- conformance is re-executed and matches the attestation;
- adequacy is recomputed and matches the attestation;
- the risk artifact is bound to the same contract and candidate manifest and matches the attestation.

The Markdown report is appended to the GitHub job summary when available.

## Pinning

Do not use a floating branch such as `@main` for a production gate. Pin the action to an immutable release tag whose commit is protected, or preferably to the exact commit SHA used by your organization after review.

## What the Action does not provide

The composite action does not add:

- tenant authentication to remote Protocol-v1 services;
- KMS/PKI signatures for attestations;
- provider credentials;
- generation of adequacy or risk evidence;
- a hosted contract registry.

Those remain separate lifecycle/control-plane concerns rather than being hidden inside a CI wrapper.
