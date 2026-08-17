from __future__ import annotations

"""Conformance checks for Semantic ABI Oracle Protocol v1."""

from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .protocol_v1 import BatchSemanticOracleV1, NeighborRequest, OracleManifest, ScorePair


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class ConformanceIssue:
    severity: str
    code: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"severity": self.severity, "code": self.code, "message": self.message, "context": dict(self.context)}


@dataclass(slots=True, frozen=True)
class OracleConformanceReport:
    manifest_digest: str
    implementation_id: str
    passed: bool
    checks: int
    issues: tuple[ConformanceIssue, ...]
    anchors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-oracle-conformance",
            "format_version": 1,
            "manifest_digest": self.manifest_digest,
            "implementation_id": self.implementation_id,
            "passed": self.passed,
            "checks": self.checks,
            "anchors": list(self.anchors),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


def check_oracle_conformance(
    oracle: BatchSemanticOracleV1,
    *,
    anchors: Sequence[str],
    k_values: Sequence[int] = (1, 3, 5),
    score_pairs: Sequence[ScorePair] = (),
    symmetry_tolerance: float = 1e-6,
) -> OracleConformanceReport:
    """Check deterministic ranking/score invariants declared by an oracle.

    The suite intentionally does not require score symmetry unless the manifest
    claims it. This is critical for query->document systems such as ColBERT,
    BM25 and other typed or directional rankers.
    """
    manifest = oracle.manifest
    if not isinstance(manifest, OracleManifest):
        raise TypeError("Protocol-v1 oracle must expose OracleManifest")
    issues: list[ConformanceIssue] = []
    checks = 0
    anchors = tuple(dict.fromkeys(str(x) for x in anchors))
    ks = tuple(sorted({max(1, int(k)) for k in k_values}))

    contains = dict(oracle.contains_many(anchors))
    checks += len(anchors)
    for anchor in anchors:
        if not bool(contains.get(anchor, False)):
            issues.append(ConformanceIssue("error", "missing-anchor", "declared conformance anchor is absent", {"anchor": anchor}))

    requests = [NeighborRequest(anchor, k) for anchor in anchors if contains.get(anchor, False) for k in ks]
    first = dict(oracle.neighbors_many(requests)) if requests else {}
    second = dict(oracle.neighbors_many(requests)) if requests and manifest.deterministic else first

    for anchor in anchors:
        if not contains.get(anchor, False):
            continue
        rows: dict[int, tuple[str, ...]] = {}
        for k in ks:
            req = NeighborRequest(anchor, k)
            values = tuple(str(x) for x in first.get(req, ()))
            rows[k] = values
            checks += 1
            if len(values) > k:
                issues.append(ConformanceIssue("error", "topk-overflow", "neighbors returned more than k items", {"anchor": anchor, "k": k, "returned": len(values)}))
            if len(set(values)) != len(values):
                issues.append(ConformanceIssue("error", "duplicate-neighbor", "neighbors contain duplicate IDs", {"anchor": anchor, "k": k}))
            if anchor in values and not bool(manifest.metadata.get("allow_self_neighbor", False)):
                issues.append(ConformanceIssue("error", "self-neighbor", "anchor appears in its own ranking", {"anchor": anchor, "k": k}))
            known = dict(oracle.contains_many(values)) if values else {}
            checks += len(values)
            unknown = [value for value in values if not known.get(value, False)]
            if unknown:
                issues.append(ConformanceIssue("error", "unknown-neighbor", "ranking returned IDs the oracle says are absent", {"anchor": anchor, "k": k, "ids": unknown[:5]}))
            if manifest.deterministic and values != tuple(second.get(req, ())):
                issues.append(ConformanceIssue("error", "nondeterministic-ranking", "manifest declares deterministic behavior but repeated ranking changed", {"anchor": anchor, "k": k}))

        for small, large in zip(ks, ks[1:]):
            checks += 1
            if rows[large][: len(rows[small])] != rows[small]:
                issues.append(ConformanceIssue("error", "topk-prefix-violation", "top-k rankings are not prefix-consistent", {"anchor": anchor, "small_k": small, "large_k": large}))

        largest = rows[ks[-1]] if ks else ()
        if largest and "score_many" in manifest.capabilities:
            pairs = [ScorePair(anchor, candidate) for candidate in largest]
            scored = dict(oracle.score_many(pairs))
            values = [float(scored[pair]) for pair in pairs]
            checks += len(values)
            if any(not math.isfinite(value) for value in values):
                issues.append(ConformanceIssue("error", "nonfinite-score", "ranking contains a non-finite score", {"anchor": anchor}))
            for left, right in zip(values, values[1:]):
                if left + 1e-8 < right:
                    issues.append(ConformanceIssue("error", "rank-score-incoherence", "neighbors are not ordered by the declared score operation", {"anchor": anchor, "scores": values[:6]}))
                    break

    if score_pairs:
        scored = dict(oracle.score_many(score_pairs))
        checks += len(score_pairs)
        for pair in score_pairs:
            value = float(scored[pair])
            if not math.isfinite(value):
                issues.append(ConformanceIssue("error", "nonfinite-score", "score_many returned a non-finite value", pair.to_dict()))

    if manifest.score_directionality == "symmetric" and score_pairs:
        reverse = [ScorePair(pair.candidate, pair.anchor) for pair in score_pairs]
        forward_scores = dict(oracle.score_many(score_pairs))
        reverse_scores = dict(oracle.score_many(reverse))
        for pair, rev in zip(score_pairs, reverse):
            checks += 1
            if abs(float(forward_scores[pair]) - float(reverse_scores[rev])) > symmetry_tolerance:
                issues.append(ConformanceIssue("error", "symmetry-claim-violation", "manifest claims symmetric scoring but reverse score differs", {"anchor": pair.anchor, "candidate": pair.candidate}))

    passed = not any(issue.severity == "error" for issue in issues)
    return OracleConformanceReport(manifest.digest, manifest.implementation_id, passed, checks, tuple(issues), anchors)
