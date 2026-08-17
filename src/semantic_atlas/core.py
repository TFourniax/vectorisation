from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np

from .geometry import (
    RobustScale,
    cosine_matrix,
    csls_scores,
    local_intrinsic_dimension,
    normalize,
    pca_basis,
    project_local,
)
from .topology import NeighborGraph, build_mutual_knn


@dataclass(slots=True)
class AtlasRecord:
    id: str
    vector: np.ndarray
    facets: list[np.ndarray] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float | None = None
    provenance: str | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.vector = normalize(np.asarray(self.vector, dtype=np.float32).reshape(1, -1))[0]
        self.facets = [normalize(np.asarray(v, dtype=np.float32).reshape(1, -1))[0] for v in self.facets]
        self.confidence = float(np.clip(self.confidence, 0.0, 1.0))
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).timestamp()


@dataclass(slots=True)
class SearchPolicy:
    top_k: int = 10
    candidate_multiplier: int = 8
    chart_probe: int = 3
    coarse_dims: int | None = None
    semantic_weight: float = 0.62
    hub_robust_weight: float = 0.23
    facet_weight: float = 0.10
    trust_weight: float = 0.05
    diversify: float = 0.08


@dataclass(slots=True)
class SearchHit:
    id: str
    score: float
    semantic_score: float
    hub_robust_score: float
    facet_score: float
    trust_score: float
    chart_ids: tuple[int, ...]
    local_coordinates: tuple[float, ...]
    metadata: dict[str, Any]


@dataclass(slots=True)
class Chart:
    id: int
    members: np.ndarray
    centroid: np.ndarray
    mean: np.ndarray
    basis: np.ndarray
    explained_variance: np.ndarray
    radius: float
    intrinsic_dimension: float


class AtlasIndex:
    """Research implementation of a Semantic Manifold Atlas.

    The reference kernel keeps the source vector intact, creates overlapping
    local charts, uses reciprocal topology/hub diagnostics, supports optional
    multi-vector facets, and exposes navigational primitives beyond top-k ANN.
    Production candidate generation can be swapped for HNSW/DiskANN/IVF.
    """

    def __init__(self, chart_size: int = 64, chart_overlap: float = 1.25, graph_k: int = 8):
        self.chart_size = max(4, int(chart_size))
        self.chart_overlap = max(1.0, float(chart_overlap))
        self.graph_k = max(2, int(graph_k))
        self.records: list[AtlasRecord] = []
        self._id_to_idx: dict[str, int] = {}
        self.vectors = np.empty((0, 0), dtype=np.float32)
        self.graph = NeighborGraph([], np.empty((0, 0)), np.empty(0), np.empty(0))
        self.charts: list[Chart] = []
        self.memberships: list[tuple[int, ...]] = []
        self.chart_edges: dict[tuple[int, int], int] = {}
        self._hub_scale = RobustScale(0.0, 1.0)

    def add(self, record: AtlasRecord) -> None:
        if record.id in self._id_to_idx:
            raise ValueError(f"duplicate record id: {record.id}")
        if self.records and record.vector.shape != self.records[0].vector.shape:
            raise ValueError("all primary vectors must have the same dimensionality")
        self._id_to_idx[record.id] = len(self.records)
        self.records.append(record)

    def extend(self, records: Iterable[AtlasRecord]) -> None:
        for record in records:
            self.add(record)

    def extend_and_build(self, records: Iterable[AtlasRecord]) -> "AtlasIndex":
        self.extend(records)
        return self.build()

    def build(self) -> "AtlasIndex":
        if not self.records:
            self.vectors = np.empty((0, 0), dtype=np.float32)
            return self
        self.vectors = np.vstack([r.vector for r in self.records]).astype(np.float32)
        self.graph = build_mutual_knn(self.vectors, self.graph_k)
        self._hub_scale = RobustScale.fit(self.graph.hubness)
        self._build_charts()
        return self

    def _build_charts(self) -> None:
        n = len(self.records)
        if n == 0:
            self.charts = []
            self.memberships = []
            return
        target_charts = max(1, int(np.ceil(n / self.chart_size)))
        centroids = [self.vectors[0]]
        if target_charts > 1:
            min_dist = 1.0 - cosine_matrix(self.vectors, np.vstack(centroids))[:, 0]
            for _ in range(1, target_charts):
                idx = int(np.argmax(min_dist))
                centroids.append(self.vectors[idx])
                d = 1.0 - cosine_matrix(self.vectors, self.vectors[idx : idx + 1])[:, 0]
                min_dist = np.minimum(min_dist, d)
        centroid_matrix = np.vstack(centroids)
        distances = 1.0 - cosine_matrix(self.vectors, centroid_matrix)
        nearest = np.argmin(distances, axis=1)

        raw_radii: list[float] = []
        for cid in range(target_charts):
            base_members = np.where(nearest == cid)[0]
            if len(base_members) == 0:
                base_members = np.array([int(np.argmin(distances[:, cid]))])
            radius = float(np.quantile(distances[base_members, cid], 0.90)) if len(base_members) > 1 else float(distances[base_members[0], cid] + 1e-6)
            raw_radii.append(max(radius, 1e-6))

        charts: list[Chart] = []
        memberships: list[list[int]] = [[] for _ in range(n)]
        for cid in range(target_charts):
            threshold = raw_radii[cid] * self.chart_overlap
            members = np.where(distances[:, cid] <= threshold)[0]
            if len(members) < 2:
                members = np.argsort(distances[:, cid])[: min(n, max(2, self.chart_size // 4))]
            chart_vectors = self.vectors[members]
            mean, basis, variance = pca_basis(chart_vectors, max_dims=3)
            local_dists = 1.0 - cosine_matrix(chart_vectors, np.mean(chart_vectors, axis=0, keepdims=True))[:, 0]
            lid = local_intrinsic_dimension(np.sort(np.maximum(local_dists, 1e-8))[: min(len(local_dists), self.graph_k + 2)])
            lid = min(float(self.vectors.shape[1]), float(lid))
            charts.append(
                Chart(
                    id=cid,
                    members=members.astype(int),
                    centroid=normalize(np.mean(chart_vectors, axis=0, keepdims=True))[0],
                    mean=mean,
                    basis=basis,
                    explained_variance=variance,
                    radius=float(raw_radii[cid]),
                    intrinsic_dimension=float(lid),
                )
            )
            for idx in members:
                memberships[int(idx)].append(cid)

        self.charts = charts
        self.memberships = [tuple(ids) for ids in memberships]
        overlap: dict[tuple[int, int], int] = {}
        for ids in self.memberships:
            for i, a in enumerate(ids):
                for b in ids[i + 1 :]:
                    key = (min(a, b), max(a, b))
                    overlap[key] = overlap.get(key, 0) + 1
        self.chart_edges = overlap

    def search(self, query: np.ndarray, facets: list[np.ndarray] | None = None, policy: SearchPolicy | None = None) -> list[SearchHit]:
        if len(self.records) == 0:
            return []
        if not self.charts:
            self.build()
        policy = policy or SearchPolicy()
        q = normalize(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        if q.shape[0] != self.vectors.shape[1]:
            raise ValueError("query dimensionality differs from index dimensionality")

        coarse_q = q
        coarse_centroids = np.vstack([c.centroid for c in self.charts])
        if policy.coarse_dims is not None and 0 < policy.coarse_dims < q.shape[0]:
            coarse_q = normalize(q[: policy.coarse_dims].reshape(1, -1))[0]
            coarse_centroids = normalize(coarse_centroids[:, : policy.coarse_dims])
        chart_scores = cosine_matrix(coarse_q.reshape(1, -1), coarse_centroids)[0]
        probe = np.argsort(-chart_scores)[: max(1, min(policy.chart_probe, len(self.charts)))]
        candidate_set: set[int] = set()
        for cid in probe:
            candidate_set.update(map(int, self.charts[int(cid)].members))

        semantic_all = cosine_matrix(q.reshape(1, -1), self.vectors)[0]
        target_candidates = min(len(self.records), max(policy.top_k, policy.top_k * policy.candidate_multiplier))
        if len(candidate_set) < target_candidates:
            candidate_set.update(map(int, np.argsort(-semantic_all)[:target_candidates]))
        candidates = np.array(sorted(candidate_set), dtype=int)

        semantic = semantic_all[candidates]
        hub_robust_raw = csls_scores(q, self.vectors[candidates], self.graph.density[candidates], k=self.graph_k)
        hub_robust = RobustScale.fit(hub_robust_raw).transform(hub_robust_raw)
        semantic01 = np.clip((semantic + 1.0) / 2.0, 0.0, 1.0)

        q_facets = [normalize(np.asarray(v, dtype=np.float32).reshape(1, -1))[0] for v in (facets or [])]
        facet_scores = np.zeros(len(candidates), dtype=np.float32)
        if q_facets:
            for pos, idx in enumerate(candidates):
                doc_facets = self.records[int(idx)].facets
                if not doc_facets:
                    continue
                interactions = cosine_matrix(np.vstack(q_facets), np.vstack(doc_facets))
                facet_scores[pos] = float(np.mean(np.max(interactions, axis=1)))
            facet_scores = np.clip((facet_scores + 1.0) / 2.0, 0.0, 1.0)

        trust = np.array([self.records[int(i)].confidence for i in candidates], dtype=np.float32)
        hub_penalty = self._hub_scale.transform(self.graph.hubness[candidates])
        total = (
            policy.semantic_weight * semantic01
            + policy.hub_robust_weight * hub_robust
            + policy.facet_weight * facet_scores
            + policy.trust_weight * trust
            - 0.10 * hub_penalty
        )

        order = list(np.argsort(-total))
        selected: list[int] = []
        while order and len(selected) < policy.top_k:
            best_pos = order.pop(0)
            if selected and policy.diversify > 0:
                redundancy = max(float(self.graph.similarities[candidates[best_pos], candidates[p]]) for p in selected)
                adjusted = total[best_pos] - policy.diversify * max(0.0, redundancy)
                alternatives = [
                    (
                        total[p] - policy.diversify * max(0.0, max(float(self.graph.similarities[candidates[p], candidates[s]]) for s in selected)),
                        p,
                    )
                    for p in order[: min(12, len(order))]
                ]
                if alternatives:
                    alt_score, alt_pos = max(alternatives)
                    if alt_score > adjusted:
                        order.remove(alt_pos)
                        order.insert(0, best_pos)
                        best_pos = alt_pos
            selected.append(best_pos)

        hits: list[SearchHit] = []
        for pos in selected:
            idx = int(candidates[pos])
            memberships = self.memberships[idx]
            cid = memberships[0] if memberships else int(probe[0])
            coord = project_local(self.vectors[idx], self.charts[cid].mean, self.charts[cid].basis)
            hits.append(
                SearchHit(
                    id=self.records[idx].id,
                    score=float(total[pos]),
                    semantic_score=float(semantic01[pos]),
                    hub_robust_score=float(hub_robust[pos]),
                    facet_score=float(facet_scores[pos]),
                    trust_score=float(trust[pos]),
                    chart_ids=memberships,
                    local_coordinates=tuple(float(x) for x in coord),
                    metadata=dict(self.records[idx].metadata),
                )
            )
        return hits

    def bridge(self, source_id: str, target_id: str) -> list[str]:
        self._require_built()
        start = self._id_to_idx[source_id]
        end = self._id_to_idx[target_id]
        path = self.graph.shortest_path(start, end)
        return [self.records[i].id for i in path]

    def boundary(self, source_id: str, target_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find records in the semantic transition region between two anchors."""
        self._require_built()
        a = self._id_to_idx[source_id]
        b = self._id_to_idx[target_id]
        sa = cosine_matrix(self.vectors, self.vectors[a : a + 1])[:, 0]
        sb = cosine_matrix(self.vectors, self.vectors[b : b + 1])[:, 0]
        closeness = (sa + sb) / 2.0
        balance = 1.0 - np.minimum(1.0, np.abs(sa - sb) / 2.0)
        score = 0.65 * ((closeness + 1.0) / 2.0) + 0.35 * balance
        score[[a, b]] = -np.inf
        order = np.argsort(-score)[: max(0, int(limit))]
        return [
            {
                "id": self.records[int(i)].id,
                "boundary_score": float(score[int(i)]),
                "source_similarity": float(sa[int(i)]),
                "target_similarity": float(sb[int(i)]),
                "chart_ids": list(self.memberships[int(i)]),
            }
            for i in order
            if np.isfinite(score[int(i)])
        ]

    def inspect(self, record_id: str) -> dict[str, Any]:
        self._require_built()
        idx = self._id_to_idx[record_id]
        neighbors = sorted(self.graph.adjacency[idx], key=lambda j: -self.graph.similarities[idx, j])
        return {
            "id": record_id,
            "chart_ids": list(self.memberships[idx]),
            "hubness": float(self.graph.hubness[idx]),
            "density": float(self.graph.density[idx]),
            "mutual_neighbors": [self.records[j].id for j in neighbors],
            "confidence": self.records[idx].confidence,
            "provenance": self.records[idx].provenance,
        }

    def map(self) -> dict[str, Any]:
        self._require_built()
        return {
            "charts": [
                {
                    "id": c.id,
                    "size": int(len(c.members)),
                    "radius": c.radius,
                    "intrinsic_dimension": c.intrinsic_dimension,
                    "explained_variance_3d": [float(v) for v in c.explained_variance],
                }
                for c in self.charts
            ],
            "edges": [
                {"source": a, "target": b, "overlap": overlap}
                for (a, b), overlap in sorted(self.chart_edges.items())
            ],
        }

    def _require_built(self) -> None:
        if not self.charts and self.records:
            self.build()
