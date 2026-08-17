# Semantic ABI / Semantic Manifold Atlas

**An evidence-gated semantic change-control layer above replaceable retrieval implementations.**

> A vector is not meaning. A ranking engine is not the contract. Semantic requirements should survive implementation changes when the evidence says they do.

The project began as topology-aware vector research. The strongest surviving direction is now **Semantic ABI v0.5**: a portable, versioned semantic contract that can be **compiled, executed remotely, audited, tested for adequacy and attested** across retrieval systems with unrelated internal representations.

```text
SemanticContract
     |
     v
Protocol-v1 compiler
     |
ContractExecutionPlan
     |
     +--> dense vector retriever
     +--> sparse BM25
     +--> hybrid
     +--> ColBERT / MaxSim late interaction
     +--> graph / provider adapter
     +--> remote HTTP service
     |
     v
Conformity + Adequacy + Risk + Integrity
     |
     v
Protocol Attestation / rollout / fallback / repair
```

The intended role is **above** Qdrant, pgvector, Elasticsearch, Vespa, HNSW/DiskANN/PLAID/Voyager and similar engines—not to replace their indexing algorithms. SQL remains appropriate for transactions, constraints, metadata and logical identity.

**Authoritative status:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)  
**Protocol:** [`docs/SEMANTIC_ABI_PROTOCOL_V1.md`](docs/SEMANTIC_ABI_PROTOCOL_V1.md)  
**OpenAPI:** [`spec/semantic-abi-oracle-v1.openapi.yaml`](spec/semantic-abi-oracle-v1.openapi.yaml)  
**Machine-bound evidence:** [`docs/evidence-manifest.json`](docs/evidence-manifest.json)

## v0.5 — compiled Semantic ABI Oracle Protocol

The old research API proved that an audit did not require vectors. v0.5 turns that into an executable interoperability boundary.

Protocol v1 uses three batch primitives:

```text
contains_many(ids)
score_many((anchor, candidate) ...)
neighbors_many((anchor, k) ...)
```

`score(anchor, candidate)` is explicitly **directional**. The protocol therefore does not assume cosine, Euclidean geometry or score symmetry.

### Contract compiler

`compile_contract()` deduplicates the full contract into a canonical plan containing only unique:

- logical-object membership checks;
- directional pair scores;
- top-k requests.

Repeated clauses reuse backend work. A large contract does **not** imply one RPC per clause. This is execution deduplication, not semantic compression: the full contract remains normative.

### Remote and cross-language surface

v0.5 includes:

- canonical `OracleManifest` with implementation/scoring identity and digest;
- OpenAPI 3.1 wire specification;
- framework-neutral server dispatcher;
- stdlib JSON/HTTP client;
- `semantic-abi` CLI;
- provider/capability compatibility preflight;
- conformance suite;
- state-bound incremental execution;
- tamper-evident protocol attestation;
- language-neutral TCK with canonical contract/plan/manifest/snapshot/audit digests.

## Major real-world gate: BM25 → ColBERTv2 without changing the contract

The central v0.5 benchmark uses public SciFact with **real `lightonai/colbertv2.0` multi-vector representations**, PyLate/Voyager retrieval and MaxSim scoring.

- 1,800 documents;
- 300 train queries to author the contract;
- 200 untouched test queries;
- 600 application clauses;
- contract digest `d3dd26211a7a18c8ae8ec07be4e0bcd8e1805024fb8dcd4a67d71506627e1843`.

The **same contract digest** executes unchanged against lexical BM25 and asymmetric ColBERT late interaction:

| implementation | Semantic ABI | nDCG@10 | Recall@10 | missing clauses |
|---|---:|---:|---:|---:|
| BM25 sparse | **0.9067** | 0.7167 | 0.8086 | 0 |
| ColBERTv2 MaxSim | **0.9047** | **0.7337** | **0.8395** | **0** |

ColBERT:

- passes all hard clauses;
- passes **660/660 Protocol-v1 conformance checks with zero issues**;
- explicitly declares asymmetric `maxsim-sum` scoring;
- audits **805 logical IDs + 600 unique directional score pairs + 300 top-k requests** through only **3 batch operation families**.

This is the strongest interoperability result in the repository so far. It does **not** claim ColBERT is universally better than BM25 or that MaxSim/OpenAPI/RPC/batching are novel. It demonstrates something narrower and more useful to the thesis: **portable semantic requirements can survive a change of retrieval algebra without shared coordinates or contract translation.**

## Safe contract evolution

`execute_contract_plan_incremental()` can reuse observations from a previous contract version only when the backend is deterministic and exposes a stable `state_digest`, and when the entire manifest identity is unchanged.

It can reuse unchanged membership, pair scores and top-k prefixes, then query only the delta. If the model/index/backend state changes, reuse is rejected.

That makes versioned contract growth cheaper without quietly trusting stale observations.

## Attested change control

`SemanticProtocolAttestation` binds:

- contract digest;
- backend manifest digest;
- execution-plan digest;
- observed snapshot digest;
- audit/conformance result;
- optional adequacy and risk certificates;
- external evidence hashes.

Good metrics alone never auto-authorize deployment. Current `deployment_eligible` logic requires explicit certified status, conformance, hard-clause pass, zero missing clauses, adequate contract evidence and positive risk certification.

The envelope is tamper-evident; a production system can sign its digest with KMS/PKI.

## Conformity is not adequacy

A candidate can satisfy every clause that exists while the contract still misses downstream damage outside its observed surface.

`ContractAdequacyEvidence` therefore separately tracks policy-defined axes such as:

- object coverage;
- mutation kill/localization;
- independent predictive validity;
- comparison with ordinary validation;
- held-out cases;
- datasets;
- fault families.

There is no hidden universal threshold. Missing required evidence remains `insufficient_evidence`.

## Semantic ABI does **not** replace nDCG

A preregistered SciFact/NFCorpus/FiQA campaign compared ABI with ordinary train-query nDCG as a predictor of untouched test nDCG across dense, sparse, hybrid and controlled-degradation variants.

| metric | Semantic ABI | train nDCG baseline |
|---|---:|---:|
| mean per-dataset Spearman | **0.9697** | **0.9757** |
| pooled delta Spearman | **0.9573** | **0.9724** |
| pooled delta Pearson | **0.9519** | **0.9850** |

**No general predictive superiority.** Conventional IR evaluation remains mandatory. Semantic ABI is a normative/operational layer, not a replacement benchmark.

## Progressive Semantic Audit

Fixed deterministic “tiny witness” compression failed on held-out faults. The scalable approach keeps the full contract normative and uses controlled early stopping:

- all hard clauses exhaustive;
- weighted soft sampling;
- predeclared looks/error budget;
- cached oracle evaluations;
- exact fallback when uncertain.

Evidence:

- 1,500 clauses: **15/15** exact decisions, **12/15** early;
- 10k/100k/250k: **10/10** exact decisions, **9/10** early;
- representative 250k cases away from the SLA boundary inspect about **0.04–0.3992%** of clauses.

Sequential testing itself has substantial prior art; the research contribution being tested is its operational role around a portable semantic contract.

## Repair / integrity: useful, incomplete

On SciFact/BGE with 10% document-embedding corruption, targeted repair strongly beats random at equal budget, but no tested planner reaches the preregistered 90% downstream-recovery target.

Implementation-specific canaries improve coverage and repair but remain separate from portable application truth.

A fixed role-weighted clause-incidence planner was then independently falsified: mean recovery ~**0.215** vs ~**0.237** best baseline at budget 50, lift ~**-0.022**, wins/ties **2/4**. It is **not promoted**.

## Important negative results

The repository deliberately preserves results that killed attractive ideas:

- local BGE→MiniLM SCF mapping loses to global;
- fixed Semantic Witness does not robustly dominate random subsets;
- learned fixed Diagnostic Panel overfits and produces 0% held-out regression recall;
- ABI is not a generally better aggregate nDCG predictor than ordinary validation;
- current repair does not reach 90% downstream recovery;
- fixed-prior repair attribution does not generalize.

Negative evidence removes unjustified complexity.

## Minimal Protocol-v1 usage

```python
from semantic_atlas import audit_contract_v1, compile_contract

plan = compile_contract(contract)
result = audit_contract_v1(contract, protocol_v1_oracle)

print(result.report.score)
print(result.snapshot.stats.transport_round_trips)
```

Remote tooling:

```bash
semantic-abi plan contract.json
semantic-abi remote-audit https://oracle.example contract.json
semantic-abi remote-conformance https://oracle.example --anchors q:1,q:2
```

## Validation

```bash
pip install -e '.[dev]'
pytest
python benchmarks/hubness_benchmark.py
python tools/check_evidence_freshness.py
```

CI covers Python 3.10/3.12/3.13. Promoted scientific results are bound to exact GitHub Actions artifacts and source Git blobs; changing evidence-sensitive code makes the corresponding proof stale until regeneration.

## Next gates

1. real Elasticsearch/Qdrant/pgvector/Vespa adapters behind Protocol v1;
2. independent Rust/Go/TypeScript implementation of the TCK;
3. typed graph/relation retrieval under the same contract;
4. multilingual/domain/temporal adequacy shift;
5. Progressive Audit vs Adaptive Learn-Then-Test/e-process baselines;
6. signed/expiring/revocable protocol attestations;
7. human contract-acquisition economics;
8. professional novelty/IP review.

## Scientific posture

This remains a falsifiable research program, not a claim that Semantic ABI is already a standard or legally patent-novel.

The v0.5 hypothesis is now concrete:

> **Can one stable, versioned Semantic Contract serve as an executable control plane above replaceable retrieval implementations, with explicit adequacy, conformance, risk and release evidence?**

The BM25→ColBERTv2 gate says this is technically plausible across a materially different retrieval algebra. The next question is whether the same boundary delivers enough operational value across real providers, languages and distribution shift to justify becoming infrastructure.