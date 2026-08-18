"""JSON-compatible I/O helpers for the Semantic ABI linker."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from .linker import (
    CertificateVerdict,
    CompatibilityCertificate,
    ComponentKind,
    ComponentOffer,
    CompositionCertificate,
    CompositionRequirement,
    LinkPolicy,
    ResolutionResult,
    SemanticSlot,
    resolve_semantic_dependencies,
)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset, tuple, list)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _jsonable(asdict(value))
    return value


def resolve_link_payload(payload: Mapping[str, Any], *, at: datetime | None = None) -> ResolutionResult:
    slots = tuple(
        SemanticSlot(
            slot_id=str(item["slot_id"]),
            kind=ComponentKind(item["kind"]),
            baseline_component_id=str(item["baseline_component_id"]),
            contract_digest=str(item["contract_digest"]),
            required_capabilities=frozenset(item.get("required_capabilities", ())),
            allowed_regions=frozenset(item.get("allowed_regions", ())),
            max_unit_cost=item.get("max_unit_cost"),
            max_p95_latency_ms=item.get("max_p95_latency_ms"),
            minimum_probe_coverage=float(item.get("minimum_probe_coverage", 1.0)),
            allow_conditional=bool(item.get("allow_conditional", False)),
        )
        for item in payload.get("slots", ())
    )
    offers = tuple(
        ComponentOffer(
            component_id=str(item["component_id"]),
            kind=ComponentKind(item["kind"]),
            version=str(item["version"]),
            provider=str(item["provider"]),
            unit_cost=float(item["unit_cost"]),
            p95_latency_ms=float(item["p95_latency_ms"]),
            capabilities=frozenset(item.get("capabilities", ())),
            regions=frozenset(item.get("regions", ())),
            metadata=dict(item.get("metadata", {})),
        )
        for item in payload.get("offers", ())
    )
    certificates = tuple(
        CompatibilityCertificate(
            baseline_component_id=str(item["baseline_component_id"]),
            candidate_component_id=str(item["candidate_component_id"]),
            contract_digest=str(item["contract_digest"]),
            evidence_digest=str(item["evidence_digest"]),
            verdict=CertificateVerdict(item["verdict"]),
            probe_coverage=float(item["probe_coverage"]),
            issuer=str(item["issuer"]),
            issued_at=str(item["issued_at"]),
            expires_at=item.get("expires_at"),
            environment_digest=item.get("environment_digest"),
            metadata=dict(item.get("metadata", {})),
        )
        for item in payload.get("certificates", ())
    )
    requirements = tuple(
        CompositionRequirement(
            slot_ids=frozenset(item["slot_ids"]),
            contract_digest=str(item["contract_digest"]),
        )
        for item in payload.get("composition_requirements", ())
    )
    composition_certificates = tuple(
        CompositionCertificate(
            members=frozenset(item["members"]),
            contract_digest=str(item["contract_digest"]),
            evidence_digest=str(item["evidence_digest"]),
            issuer=str(item["issuer"]),
            issued_at=str(item["issued_at"]),
            expires_at=item.get("expires_at"),
            environment_digest=item.get("environment_digest"),
        )
        for item in payload.get("composition_certificates", ())
    )
    raw_policy = payload.get("policy", {})
    policy = LinkPolicy(
        cost_weight=float(raw_policy.get("cost_weight", 1.0)),
        latency_weight=float(raw_policy.get("latency_weight", 0.0)),
        conditional_penalty=float(raw_policy.get("conditional_penalty", 1000.0)),
        max_total_unit_cost=raw_policy.get("max_total_unit_cost"),
        max_total_p95_latency_ms=raw_policy.get("max_total_p95_latency_ms"),
        trusted_issuers=frozenset(raw_policy.get("trusted_issuers", ())),
        environment_digest=raw_policy.get("environment_digest"),
    )
    return resolve_semantic_dependencies(
        slots,
        offers,
        certificates,
        composition_requirements=requirements,
        composition_certificates=composition_certificates,
        policy=policy,
        at=at,
    )


def link_result_to_dict(result: ResolutionResult) -> dict[str, Any]:
    payload = _jsonable(result)
    assert isinstance(payload, dict)
    if result.plan is not None:
        payload["plan"]["digest"] = result.plan.digest
    return payload
