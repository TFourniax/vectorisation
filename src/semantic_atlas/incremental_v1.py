from __future__ import annotations

"""Safe incremental execution for Semantic ABI Protocol v1.

A new contract version often reuses most operations from its parent. Reusing an
old oracle result is only sound when the backend declares a stable state identity
and deterministic behavior. This module therefore refuses incremental reuse
unless the manifest contains ``metadata['state_digest']`` and the complete
manifest digest matches the prior snapshot.
"""

from dataclasses import dataclass
from typing import Any, Mapping
import math

from .protocol_v1 import (
    BatchSemanticOracleV1,
    ContractExecutionPlan,
    NeighborRequest,
    OracleExecutionStats,
    OracleSnapshot,
    ScorePair,
)


@dataclass(slots=True, frozen=True)
class IncrementalExecutionStats:
    reused_object_checks: int
    reused_score_pairs: int
    reused_neighbor_requests: int
    fetched_object_checks: int
    fetched_score_pairs: int
    fetched_neighbor_requests: int
    transport_round_trips: int

    @property
    def reused_operations(self) -> int:
        return self.reused_object_checks + self.reused_score_pairs + self.reused_neighbor_requests

    @property
    def fetched_operations(self) -> int:
        return self.fetched_object_checks + self.fetched_score_pairs + self.fetched_neighbor_requests

    @property
    def reuse_fraction(self) -> float:
        total = self.reused_operations + self.fetched_operations
        return 0.0 if total == 0 else self.reused_operations / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "reused_object_checks": self.reused_object_checks,
            "reused_score_pairs": self.reused_score_pairs,
            "reused_neighbor_requests": self.reused_neighbor_requests,
            "fetched_object_checks": self.fetched_object_checks,
            "fetched_score_pairs": self.fetched_score_pairs,
            "fetched_neighbor_requests": self.fetched_neighbor_requests,
            "reused_operations": self.reused_operations,
            "fetched_operations": self.fetched_operations,
            "reuse_fraction": self.reuse_fraction,
            "transport_round_trips": self.transport_round_trips,
        }


@dataclass(slots=True, frozen=True)
class IncrementalExecutionResult:
    snapshot: OracleSnapshot
    parent_snapshot_digest: str
    stats: IncrementalExecutionStats

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "semantic-abi-incremental-execution",
            "format_version": 1,
            "parent_snapshot_digest": self.parent_snapshot_digest,
            "snapshot_digest": self.snapshot.digest,
            "plan_digest": self.snapshot.plan_digest,
            "oracle_manifest_digest": self.snapshot.manifest.digest,
            "stats": self.stats.to_dict(),
        }


def _covering_neighbor(snapshot: OracleSnapshot, request: NeighborRequest) -> tuple[str, ...] | None:
    exact = snapshot.neighborhoods.get(request)
    if exact is not None:
        return tuple(exact)[: request.k]
    candidates = sorted(
        (item for item in snapshot.neighborhoods if item.anchor == request.anchor and item.k >= request.k),
        key=lambda item: item.k,
    )
    if not candidates:
        return None
    return tuple(snapshot.neighborhoods[candidates[0]])[: request.k]


def execute_contract_plan_incremental(
    new_plan: ContractExecutionPlan,
    oracle: BatchSemanticOracleV1,
    *,
    previous_plan: ContractExecutionPlan,
    previous_snapshot: OracleSnapshot,
) -> IncrementalExecutionResult:
    """Execute only operations not safely reusable from a previous snapshot."""

    state_digest = str(oracle.manifest.metadata.get("state_digest") or "")
    if not state_digest:
        raise ValueError("incremental execution requires oracle manifest metadata['state_digest']")
    if not oracle.manifest.deterministic:
        raise ValueError("incremental execution requires a deterministic oracle")
    if previous_snapshot.manifest.digest != oracle.manifest.digest:
        raise ValueError("oracle manifest/state changed; previous snapshot cannot be reused")
    if previous_snapshot.plan_digest != previous_plan.digest:
        raise ValueError("previous snapshot does not belong to previous plan")

    contains: dict[str, bool] = {}
    missing_objects: list[str] = []
    for object_id in new_plan.object_ids:
        if object_id in previous_snapshot.contains_map:
            contains[object_id] = bool(previous_snapshot.contains_map[object_id])
        else:
            missing_objects.append(object_id)
    contains_calls = int(bool(missing_objects))
    if missing_objects:
        fetched = dict(oracle.contains_many(missing_objects))
        contains.update({object_id: bool(fetched.get(object_id, False)) for object_id in missing_objects})

    scores: dict[ScorePair, float] = {}
    missing_pairs: list[ScorePair] = []
    for pair in new_plan.score_pairs:
        if not (contains.get(pair.anchor, False) and contains.get(pair.candidate, False)):
            continue
        if pair in previous_snapshot.scores:
            scores[pair] = float(previous_snapshot.scores[pair])
        else:
            missing_pairs.append(pair)
    score_calls = int(bool(missing_pairs))
    if missing_pairs:
        fetched = dict(oracle.score_many(missing_pairs))
        for pair in missing_pairs:
            value = float(fetched[pair])
            if not math.isfinite(value):
                raise ValueError(f"non-finite oracle score: {pair}")
            scores[pair] = value

    neighborhoods: dict[NeighborRequest, tuple[str, ...]] = {}
    missing_neighbors: list[NeighborRequest] = []
    reused_neighbors = 0
    for request in new_plan.neighbor_requests:
        if not contains.get(request.anchor, False):
            continue
        cached = _covering_neighbor(previous_snapshot, request)
        if cached is None:
            missing_neighbors.append(request)
        else:
            neighborhoods[request] = cached
            reused_neighbors += 1
    neighbor_calls = int(bool(missing_neighbors))
    if missing_neighbors:
        fetched = dict(oracle.neighbors_many(missing_neighbors))
        neighborhoods.update({request: tuple(str(x) for x in fetched[request])[: request.k] for request in missing_neighbors})

    reused_objects = len(new_plan.object_ids) - len(missing_objects)
    active_pairs = [pair for pair in new_plan.score_pairs if contains.get(pair.anchor, False) and contains.get(pair.candidate, False)]
    reused_pairs = len(active_pairs) - len(missing_pairs)
    active_neighbors = [request for request in new_plan.neighbor_requests if contains.get(request.anchor, False)]

    execution_stats = OracleExecutionStats(
        contains_batch_calls=contains_calls,
        score_batch_calls=score_calls,
        neighbor_batch_calls=neighbor_calls,
        object_checks=len(missing_objects),
        score_pairs=len(missing_pairs),
        neighbor_requests=len(missing_neighbors),
    )
    snapshot = OracleSnapshot(
        manifest=oracle.manifest,
        plan_digest=new_plan.digest,
        contains_map=contains,
        scores=scores,
        neighborhoods=neighborhoods,
        stats=execution_stats,
    )
    stats = IncrementalExecutionStats(
        reused_object_checks=reused_objects,
        reused_score_pairs=reused_pairs,
        reused_neighbor_requests=reused_neighbors,
        fetched_object_checks=len(missing_objects),
        fetched_score_pairs=len(missing_pairs),
        fetched_neighbor_requests=len(missing_neighbors),
        transport_round_trips=contains_calls + score_calls + neighbor_calls,
    )
    # Internal accounting check: every active operation must be either reused or fetched.
    if stats.reused_score_pairs + stats.fetched_score_pairs != len(active_pairs):
        raise AssertionError("incremental score accounting mismatch")
    if stats.reused_neighbor_requests + stats.fetched_neighbor_requests != len(active_neighbors):
        raise AssertionError("incremental neighbor accounting mismatch")
    return IncrementalExecutionResult(snapshot, previous_snapshot.digest, stats)
