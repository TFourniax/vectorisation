from __future__ import annotations

"""Late-interaction / MaxSim adapter for Semantic ABI Protocol v1."""

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .protocol_v1 import NeighborRequest, OracleManifest, ScorePair

_EPS = 1e-12


def _tokens(value: np.ndarray) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError("late-interaction representations must be non-empty 2-D token matrices")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norms, _EPS)


def maxsim_score(query_tokens: np.ndarray, document_tokens: np.ndarray, *, aggregation: str = "sum") -> float:
    """ColBERT-style directional MaxSim score.

    For each query token, take the maximum dot product over all document tokens,
    then aggregate over query tokens. ``sum`` matches the classic ColBERT
    operator. ``mean`` is available for diagnostics when query lengths differ.
    """
    q = _tokens(query_tokens)
    d = _tokens(document_tokens)
    token_scores = np.max(q @ d.T, axis=1)
    if aggregation == "sum":
        return float(np.sum(token_scores))
    if aggregation == "mean":
        return float(np.mean(token_scores))
    raise ValueError("aggregation must be 'sum' or 'mean'")


@dataclass(slots=True, frozen=True)
class MaxSimExplanation:
    anchor: str
    candidate: str
    query_token_best_document_token: tuple[int, ...]
    query_token_scores: tuple[float, ...]
    total_score: float


class LateInteractionOracleV1:
    """Protocol-v1 oracle over multi-vector query/document representations.

    ``rankings`` is optional. When supplied, it can come from PLAID, Voyager,
    Vespa, WARP, or another candidate engine and is used for ``neighbors_many``.
    Pair scores are always evaluated from the supplied token matrices, so triplet
    clauses do not depend on whether a positive/negative happened to be retrieved
    in the top-k candidate list.

    Without precomputed rankings the adapter performs exhaustive MaxSim ranking;
    that mode is intended for tests and small corpora, not large-scale serving.
    """

    def __init__(
        self,
        query_representations: Mapping[str, np.ndarray],
        document_representations: Mapping[str, np.ndarray],
        *,
        rankings: Mapping[str, Sequence[str]] | None = None,
        implementation_id: str = "late-interaction",
        model_id: str | None = None,
        aggregation: str = "sum",
    ) -> None:
        if aggregation not in {"sum", "mean"}:
            raise ValueError("aggregation must be 'sum' or 'mean'")
        self.queries = {str(k): _tokens(v) for k, v in query_representations.items()}
        self.documents = {str(k): _tokens(v) for k, v in document_representations.items()}
        overlap = set(self.queries) & set(self.documents)
        if overlap:
            raise ValueError(f"query/document namespaces overlap: {sorted(overlap)[:3]}")
        self.rankings = {str(k): tuple(str(x) for x in v) for k, v in (rankings or {}).items()}
        self.aggregation = aggregation
        self.manifest = OracleManifest(
            implementation_id=implementation_id,
            implementation_kind="late_interaction",
            score_semantics=f"maxsim-{aggregation}",
            score_directionality="asymmetric",
            deterministic=True,
            metadata={
                "model_id": model_id,
                "query_objects": len(self.queries),
                "document_objects": len(self.documents),
                "precomputed_rankings": bool(rankings),
            },
        )

    def contains_many(self, object_ids: Sequence[str]) -> Mapping[str, bool]:
        universe = set(self.queries) | set(self.documents)
        return {str(x): str(x) in universe for x in object_ids}

    def score_many(self, pairs: Sequence[ScorePair]) -> Mapping[ScorePair, float]:
        out: dict[ScorePair, float] = {}
        for pair in pairs:
            if pair.anchor not in self.queries:
                raise KeyError(f"late-interaction anchor is not a query object: {pair.anchor!r}")
            if pair.candidate not in self.documents:
                raise KeyError(f"late-interaction candidate is not a document object: {pair.candidate!r}")
            out[pair] = maxsim_score(self.queries[pair.anchor], self.documents[pair.candidate], aggregation=self.aggregation)
        return out

    def neighbors_many(self, requests: Sequence[NeighborRequest]) -> Mapping[NeighborRequest, Sequence[str]]:
        out: dict[NeighborRequest, tuple[str, ...]] = {}
        doc_ids = tuple(self.documents)
        for req in requests:
            if req.anchor not in self.queries:
                raise KeyError(f"late-interaction anchor is not a query object: {req.anchor!r}")
            if req.anchor in self.rankings:
                out[req] = tuple(x for x in self.rankings[req.anchor] if x in self.documents)[: req.k]
                continue
            scores = np.asarray([
                maxsim_score(self.queries[req.anchor], self.documents[doc_id], aggregation=self.aggregation)
                for doc_id in doc_ids
            ])
            order = np.argsort(-scores)[: min(req.k, len(doc_ids))]
            out[req] = tuple(doc_ids[int(i)] for i in order)
        return out

    def explain(self, anchor: str, candidate: str) -> MaxSimExplanation:
        q = self.queries[anchor]
        d = self.documents[candidate]
        matrix = q @ d.T
        best = np.argmax(matrix, axis=1)
        values = matrix[np.arange(len(q)), best]
        total = float(np.sum(values) if self.aggregation == "sum" else np.mean(values))
        return MaxSimExplanation(
            anchor=anchor,
            candidate=candidate,
            query_token_best_document_token=tuple(int(x) for x in best),
            query_token_scores=tuple(float(x) for x in values),
            total_score=total,
        )
