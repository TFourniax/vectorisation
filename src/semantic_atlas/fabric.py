from __future__ import annotations
from dataclasses import dataclass, field, replace
from itertools import combinations
from typing import Any, Iterable, Sequence
import numpy as np
from .alignment import TransitionAtlas, TransitionDiagnostics, TransitionGraph
from .core import AtlasIndex, AtlasRecord, SearchPolicy
from .geometry import normalize

@dataclass(slots=True, frozen=True)
class SpaceSpec:
    name: str
    dimensions: int
    modality: str = 'text'
    version: str | None = None

@dataclass(slots=True)
class FabricRecord:
    id: str
    vectors: dict[str, np.ndarray] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None
    confidence: float = 1.0
    timestamp: float | None = None

@dataclass(slots=True, frozen=True)
class SpaceRoute:
    target_space: str
    path: tuple[str, ...]
    coverage: float
    transition_confidence: float
    direct: bool

@dataclass(slots=True)
class SearchPlan:
    query_space: str
    routes: list[SpaceRoute]
    excluded: dict[str, str]

@dataclass(slots=True)
class SpaceEvidence:
    target_space: str
    rank: int
    raw_score: float
    transport_confidence: float
    path: tuple[str, ...]
    transition_chart_ids: tuple[int, ...]

@dataclass(slots=True)
class FabricSearchHit:
    id: str
    score: float
    metadata: dict[str, Any]
    evidence: list[SpaceEvidence]

    @property
    def support_spaces(self) -> tuple[str, ...]:
        return tuple(sorted({e.target_space for e in self.evidence}))

@dataclass(slots=True)
class CellObservation:
    source_space: str
    path: tuple[str, ...]
    transport_confidence: float
    agreement_with_center: float

@dataclass(slots=True)
class SemanticCell:
    id: str
    target_space: str
    center: np.ndarray
    dispersion: float
    confidence: float
    observations: list[CellObservation]

class SemanticFabric:

    def __init__(self, **index_kwargs: Any) -> None:
        self.spaces: dict[str, SpaceSpec] = {}
        self.records: dict[str, FabricRecord] = {}
        self.indexes: dict[str, AtlasIndex] = {}
        self.transitions = TransitionGraph()
        self.index_kwargs = dict(index_kwargs)
        self._dirty = True

    def add_space(self, spec: SpaceSpec | str, dimensions: int | None=None, **kwargs: Any) -> None:
        if isinstance(spec, str):
            if dimensions is None:
                raise ValueError('dimensions are required when adding a space by name')
            spec = SpaceSpec(spec, int(dimensions), **kwargs)
        if spec.dimensions <= 0:
            raise ValueError('space dimensionality must be positive')
        existing = self.spaces.get(spec.name)
        if existing is not None and existing != spec:
            raise ValueError(f'space {spec.name!r} already exists with a different specification')
        self.spaces[spec.name] = spec

    def add(self, record: FabricRecord) -> None:
        if record.id in self.records:
            raise ValueError(f'duplicate record id: {record.id}')
        clean: dict[str, np.ndarray] = {}
        for space, vector in record.vectors.items():
            if space not in self.spaces:
                raise KeyError(f'unknown embedding space: {space}')
            arr = np.asarray(vector, dtype=np.float32).reshape(-1)
            if arr.shape[0] != self.spaces[space].dimensions:
                raise ValueError(f'record {record.id!r} vector in {space!r} has {arr.shape[0]} dimensions; expected {self.spaces[space].dimensions}')
            clean[space] = normalize(arr.reshape(1, -1))[0]
        record.vectors = clean
        record.confidence = float(np.clip(record.confidence, 0.0, 1.0))
        self.records[record.id] = record
        self._dirty = True

    def extend(self, records: Iterable[FabricRecord]) -> None:
        for record in records:
            self.add(record)

    def observe(self, record_id: str, space: str, vector: np.ndarray) -> None:
        if record_id not in self.records:
            raise KeyError(record_id)
        if space not in self.spaces:
            raise KeyError(space)
        arr = np.asarray(vector, dtype=np.float32).reshape(-1)
        if arr.shape[0] != self.spaces[space].dimensions:
            raise ValueError('vector dimensionality does not match space')
        self.records[record_id].vectors[space] = normalize(arr.reshape(1, -1))[0]
        self._dirty = True

    def build(self) -> 'SemanticFabric':
        indexes: dict[str, AtlasIndex] = {}
        for space in self.spaces:
            rows = [r for r in self.records.values() if space in r.vectors]
            if not rows:
                continue
            index = AtlasIndex(**self.index_kwargs)
            index.extend((AtlasRecord(id=r.id, vector=r.vectors[space], metadata={**r.metadata, '_fabric_space': space}, timestamp=r.timestamp, provenance=r.provenance, confidence=r.confidence) for r in rows))
            index.build()
            indexes[space] = index
        self.indexes = indexes
        self._dirty = False
        return self

    def _ensure_built(self) -> None:
        if self._dirty:
            self.build()

    def common_ids(self, source_space: str, target_space: str) -> list[str]:
        return [rid for rid, record in self.records.items() if source_space in record.vectors and target_space in record.vectors]

    def fit_transition(self, source_space: str, target_space: str, *, anchor_ids: Sequence[str] | None=None, **kwargs: Any) -> TransitionAtlas:
        if source_space not in self.spaces or target_space not in self.spaces:
            raise KeyError('both transition spaces must be registered')
        ids = list(anchor_ids) if anchor_ids is not None else self.common_ids(source_space, target_space)
        ids = [rid for rid in ids if rid in self.records and source_space in self.records[rid].vectors and (target_space in self.records[rid].vectors)]
        if len(ids) < 2:
            raise ValueError('at least two records observed in both spaces are required')
        x = np.vstack([self.records[rid].vectors[source_space] for rid in ids])
        y = np.vstack([self.records[rid].vectors[target_space] for rid in ids])
        transition = TransitionAtlas.fit(source_space, target_space, x, y, **kwargs)
        self.transitions.add(transition)
        return transition

    def fit_bidirectional(self, a: str, b: str, *, anchor_ids: Sequence[str] | None=None, **kwargs: Any) -> tuple[TransitionAtlas, TransitionAtlas]:
        forward = self.fit_transition(a, b, anchor_ids=anchor_ids, **kwargs)
        reverse = self.fit_transition(b, a, anchor_ids=anchor_ids, **kwargs)
        return (forward, reverse)

    def plan_search(self, query_space: str, *, min_route_confidence: float=0.0, max_hops: int=4, max_spaces: int | None=None) -> SearchPlan:
        self._ensure_built()
        if query_space not in self.spaces:
            raise KeyError(query_space)
        total = max(1, len(self.records))
        routes: list[SpaceRoute] = []
        excluded: dict[str, str] = {}
        for target in self.spaces:
            if target not in self.indexes:
                excluded[target] = 'no indexed records'
                continue
            coverage = len(self.indexes[target].records) / total
            if target == query_space:
                path = (query_space,)
                confidence = 1.0
            else:
                path = self.transitions.route(query_space, target, max_hops=max_hops)
                if not path:
                    excluded[target] = 'no transition route'
                    continue
                confidence = self.transitions.path_confidence(path)
            if confidence < min_route_confidence:
                excluded[target] = f'route confidence {confidence:.3f} below threshold'
                continue
            routes.append(SpaceRoute(target_space=target, path=tuple(path), coverage=float(coverage), transition_confidence=float(confidence), direct=target == query_space))
        routes.sort(key=lambda r: (r.direct, r.coverage * r.transition_confidence), reverse=True)
        if max_spaces is not None:
            routes = routes[:max(1, int(max_spaces))]
        return SearchPlan(query_space, routes, excluded)

    def search(self, query: np.ndarray, query_space: str, *, top_k: int=10, policy: SearchPolicy | None=None, min_route_confidence: float=0.0, max_spaces: int | None=None, per_space_multiplier: int=3, rrf_k: int=24) -> list[FabricSearchHit]:
        plan = self.plan_search(query_space, min_route_confidence=min_route_confidence, max_spaces=max_spaces)
        if not plan.routes:
            return []
        q = normalize(np.asarray(query, dtype=np.float32).reshape(1, -1))[0]
        if q.shape[0] != self.spaces[query_space].dimensions:
            raise ValueError('query dimensionality does not match query space')
        per_space_k = max(int(top_k), int(top_k) * max(1, int(per_space_multiplier)))
        base_policy = policy or SearchPolicy()
        local_policy = replace(base_policy, top_k=per_space_k)
        accum: dict[str, dict[str, Any]] = {}
        for route in plan.routes:
            if route.direct:
                target_query = q
                transport_conf = 1.0
                chart_ids: tuple[int, ...] = ()
            else:
                moved = self.transitions.transport(q, route.path)
                target_query = moved.vector
                transport_conf = min(route.transition_confidence, moved.confidence)
                chart_ids = moved.chart_ids
            if transport_conf <= 0.0:
                continue
            hits = self.indexes[route.target_space].search(target_query, policy=local_policy)
            for rank, hit in enumerate(hits, start=1):
                corrected_rank = rank / max(route.coverage, 1e-09)
                rank_signal = 1.0 / (max(1, int(rrf_k)) + corrected_rank)
                raw_signal = 0.006 * float(np.clip(hit.score, 0.0, 1.0))
                evidence_weight = transport_conf * float(max(route.coverage, 1e-09))
                contribution = evidence_weight * (rank_signal + raw_signal)
                row = accum.setdefault(hit.id, {'score': 0.0, 'evidence': []})
                row['score'] += contribution
                row['evidence'].append(SpaceEvidence(target_space=route.target_space, rank=rank, raw_score=float(hit.score), transport_confidence=float(transport_conf), path=route.path, transition_chart_ids=chart_ids))
        results: list[FabricSearchHit] = []
        for rid, row in accum.items():
            evidence: list[SpaceEvidence] = row['evidence']
            support = len({e.target_space for e in evidence})
            consensus_boost = 1.0 + 0.03 * max(0, support - 1)
            results.append(FabricSearchHit(id=rid, score=float(row['score'] * consensus_boost), metadata=dict(self.records[rid].metadata), evidence=evidence))
        results.sort(key=lambda hit: (-hit.score, hit.id))
        return results[:max(0, int(top_k))]

    def canonical_cell(self, record_id: str, target_space: str, *, max_hops: int=4, min_transport_confidence: float=0.0) -> SemanticCell | None:
        if record_id not in self.records:
            raise KeyError(record_id)
        if target_space not in self.spaces:
            raise KeyError(target_space)
        record = self.records[record_id]
        vectors: list[np.ndarray] = []
        weights: list[float] = []
        descriptors: list[tuple[str, tuple[str, ...], float]] = []
        for source_space, vector in record.vectors.items():
            if source_space == target_space:
                mapped = vector
                path = (target_space,)
                confidence = 1.0
            else:
                path = self.transitions.route(source_space, target_space, max_hops=max_hops)
                if not path:
                    continue
                moved = self.transitions.transport(vector, path)
                mapped = moved.vector
                confidence = min(self.transitions.path_confidence(path), moved.confidence)
            if confidence < min_transport_confidence:
                continue
            vectors.append(normalize(mapped.reshape(1, -1))[0])
            weights.append(max(confidence, 1e-06) ** 2)
            descriptors.append((source_space, tuple(path), float(confidence)))
        if not vectors:
            return None
        matrix = np.vstack(vectors)
        w = np.asarray(weights, dtype=np.float64)
        w /= max(float(np.sum(w)), 1e-12)
        center = normalize(np.sum(matrix * w[:, None], axis=0, keepdims=True))[0]
        agreement = np.clip(matrix @ center, -1.0, 1.0)
        dispersion = float(np.sum(w * ((1.0 - agreement) / 2.0)))
        transport_quality = float(np.sum(w * np.asarray([d[2] for d in descriptors])))
        confidence = float(np.clip(transport_quality * np.exp(-4.0 * dispersion) * record.confidence, 0.0, 1.0))
        observations = [CellObservation(src, path, conf, float(agr)) for (src, path, conf), agr in zip(descriptors, agreement)]
        return SemanticCell(record_id, target_space, center.astype(np.float32), dispersion, confidence, observations)

    def materialize_virtual_space(self, target_space: str, *, min_cell_confidence: float=0.0, min_transport_confidence: float=0.0) -> AtlasIndex:
        index = AtlasIndex(**self.index_kwargs)
        for rid, record in self.records.items():
            cell = self.canonical_cell(rid, target_space, min_transport_confidence=min_transport_confidence)
            if cell is None or cell.confidence < min_cell_confidence:
                continue
            index.add(AtlasRecord(id=rid, vector=cell.center, metadata={**record.metadata, '_fabric_space': target_space, '_virtual': target_space not in record.vectors, '_cell_dispersion': cell.dispersion, '_cell_observations': len(cell.observations)}, timestamp=record.timestamp, provenance=record.provenance, confidence=cell.confidence))
        return index.build()

    def virtual_coverage(self, target_space: str, *, min_cell_confidence: float=0.0) -> dict[str, float | int]:
        cells = [self.canonical_cell(rid, target_space) for rid in self.records]
        valid = [c for c in cells if c is not None and c.confidence >= min_cell_confidence]
        direct = sum((1 for r in self.records.values() if target_space in r.vectors))
        return {'total_records': len(self.records), 'direct_records': direct, 'virtual_or_direct_records': len(valid), 'direct_coverage': 0.0 if not self.records else direct / len(self.records), 'virtual_coverage': 0.0 if not self.records else len(valid) / len(self.records), 'mean_cell_confidence': 0.0 if not valid else float(np.mean([c.confidence for c in valid])), 'mean_cell_dispersion': 0.0 if not valid else float(np.mean([c.dispersion for c in valid]))}

    def migration_status(self, legacy_space: str, new_space: str) -> dict[str, Any]:
        if legacy_space not in self.spaces or new_space not in self.spaces:
            raise KeyError('unknown migration space')
        old = {rid for rid, r in self.records.items() if legacy_space in r.vectors}
        new = {rid for rid, r in self.records.items() if new_space in r.vectors}
        total = len(self.records)
        route = self.transitions.route(new_space, legacy_space)
        return {'total_records': total, 'legacy_records': len(old), 'new_records': len(new), 'both': len(old & new), 'legacy_only': len(old - new), 'new_only': len(new - old), 'neither': total - len(old | new), 'new_coverage': 0.0 if total == 0 else len(new) / total, 'legacy_searchable_from_new': bool(route), 'transport_path': list(route), 'transport_confidence': self.transitions.path_confidence(route) if route else 0.0}

    def transition_audit(self, source_space: str, target_space: str, *, ids: Sequence[str] | None=None, k: int=10) -> TransitionDiagnostics:
        transition = self.transitions.transitions[source_space, target_space]
        eval_ids = list(ids) if ids is not None else self.common_ids(source_space, target_space)
        if not eval_ids:
            return TransitionDiagnostics(0, 0.0, 0.0, 0.0, 0.0)
        x = np.vstack([self.records[rid].vectors[source_space] for rid in eval_ids])
        y = np.vstack([self.records[rid].vectors[target_space] for rid in eval_ids])
        return transition.evaluate(x, y, k=k)

    def neighborhood_disagreement(self, record_id: str, *, k: int=10) -> dict[str, Any]:
        self._ensure_built()
        if record_id not in self.records:
            raise KeyError(record_id)
        record = self.records[record_id]
        neighborhoods: dict[str, set[str]] = {}
        p = replace(SearchPolicy(), top_k=max(2, int(k) + 1), diversify=0.0)
        for space, vector in record.vectors.items():
            index = self.indexes.get(space)
            if index is None:
                continue
            ids = [hit.id for hit in index.search(vector, policy=p) if hit.id != record_id][:k]
            neighborhoods[space] = set(ids)
        pairwise: dict[str, float] = {}
        agreements: list[float] = []
        for a, b in combinations(sorted(neighborhoods), 2):
            left, right = (neighborhoods[a], neighborhoods[b])
            union = left | right
            agreement = 1.0 if not union else len(left & right) / len(union)
            pairwise[f'{a}::{b}'] = float(agreement)
            agreements.append(float(agreement))
        mean = float(np.mean(agreements)) if agreements else 1.0
        return {'id': record_id, 'spaces': sorted(neighborhoods), 'mean_neighbor_agreement': mean, 'representation_sensitivity': 1.0 - mean, 'pairwise_agreement': pairwise}

    def fault_lines(self, *, limit: int=20, k: int=10) -> list[dict[str, Any]]:
        reports = [self.neighborhood_disagreement(rid, k=k) for rid, record in self.records.items() if len(record.vectors) >= 2]
        reports.sort(key=lambda x: (-x['representation_sensitivity'], x['id']))
        return reports[:max(0, int(limit))]

    def cycle_audit(self, cycle: Sequence[str], *, ids: Sequence[str] | None=None) -> dict[str, float]:
        if not cycle or cycle[0] != cycle[-1]:
            raise ValueError('cycle must be closed')
        start = cycle[0]
        selected = list(ids) if ids is not None else [rid for rid, r in self.records.items() if start in r.vectors]
        vectors = np.vstack([self.records[rid].vectors[start] for rid in selected])
        return self.transitions.cycle_consistency(cycle, vectors)
