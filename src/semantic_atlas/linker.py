"""Proof-carrying semantic dependency resolver for AI systems.

The linker treats AI models, retrievers, tools and other probabilistic components
as replaceable implementations of application-owned semantic slots. A component
is never eligible merely because it advertises capabilities or performs well on
a generic benchmark: it must carry evidence that it is compatible with the exact
baseline and Semantic ABI contract required by the consuming application.

This makes it possible to search for cheaper/faster/sovereign implementations
without turning every provider swap into an ad-hoc migration project.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import itertools
import json
from math import isfinite
from typing import Any, Mapping, Sequence


def _stable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _stable(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (set, frozenset)):
        return sorted(_stable(v) for v in value)
    if isinstance(value, tuple):
        return [_stable(v) for v in value]
    if isinstance(value, list):
        return [_stable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _stable(asdict(value))
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(
        _stable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return sha256(payload.encode()).hexdigest()


class ComponentKind(str, Enum):
    MODEL = "model"
    RETRIEVER = "retriever"
    RERANKER = "reranker"
    TOOL = "tool"
    MEMORY = "memory"
    POLICY = "policy"
    OTHER = "other"


class CertificateVerdict(str, Enum):
    COMPATIBLE = "compatible"
    CONDITIONAL = "conditionally_compatible"


@dataclass(frozen=True)
class ComponentOffer:
    component_id: str
    kind: ComponentKind
    version: str
    provider: str
    unit_cost: float
    p95_latency_ms: float
    capabilities: frozenset[str] = frozenset()
    regions: frozenset[str] = frozenset()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.component_id or not self.version or not self.provider:
            raise ValueError("component identity, version and provider are required")
        if self.unit_cost < 0 or self.p95_latency_ms < 0:
            raise ValueError("cost and latency must be >= 0")
        if not isfinite(self.unit_cost) or not isfinite(self.p95_latency_ms):
            raise ValueError("cost and latency must be finite")


@dataclass(frozen=True)
class CompatibilityCertificate:
    """Proof reference that a candidate can substitute one logical baseline component."""

    baseline_component_id: str
    candidate_component_id: str
    contract_digest: str
    evidence_digest: str
    verdict: CertificateVerdict
    probe_coverage: float
    issuer: str
    issued_at: str
    expires_at: str | None = None
    environment_digest: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all(
            (
                self.baseline_component_id,
                self.candidate_component_id,
                self.contract_digest,
                self.evidence_digest,
                self.issuer,
                self.issued_at,
            )
        ):
            raise ValueError("certificate identity/evidence fields are required")
        if not 0 <= self.probe_coverage <= 1:
            raise ValueError("probe_coverage must be in [0, 1]")
        _parse_time(self.issued_at)
        if self.expires_at:
            _parse_time(self.expires_at)

    @property
    def digest(self) -> str:
        return _digest(self)


@dataclass(frozen=True)
class CompositionCertificate:
    """Evidence that a concrete combination remains compatible when composed."""

    members: frozenset[str]
    contract_digest: str
    evidence_digest: str
    issuer: str
    issued_at: str
    expires_at: str | None = None
    environment_digest: str | None = None

    def __post_init__(self) -> None:
        if len(self.members) < 2:
            raise ValueError("composition certificate needs at least two members")
        _parse_time(self.issued_at)
        if self.expires_at:
            _parse_time(self.expires_at)

    @property
    def digest(self) -> str:
        return _digest(self)


@dataclass(frozen=True)
class SemanticSlot:
    """One logical dependency owned by the application rather than a vendor."""

    slot_id: str
    kind: ComponentKind
    baseline_component_id: str
    contract_digest: str
    required_capabilities: frozenset[str] = frozenset()
    allowed_regions: frozenset[str] = frozenset()
    max_unit_cost: float | None = None
    max_p95_latency_ms: float | None = None
    minimum_probe_coverage: float = 1.0
    allow_conditional: bool = False

    def __post_init__(self) -> None:
        if not self.slot_id or not self.baseline_component_id or not self.contract_digest:
            raise ValueError("slot identity, baseline and contract are required")
        if not 0 <= self.minimum_probe_coverage <= 1:
            raise ValueError("minimum_probe_coverage must be in [0, 1]")


@dataclass(frozen=True)
class CompositionRequirement:
    """Require joint evidence for selected implementations of two or more slots."""

    slot_ids: frozenset[str]
    contract_digest: str

    def __post_init__(self) -> None:
        if len(self.slot_ids) < 2:
            raise ValueError("composition requirement needs at least two slots")


@dataclass(frozen=True)
class LinkPolicy:
    cost_weight: float = 1.0
    latency_weight: float = 0.0
    conditional_penalty: float = 1000.0
    max_total_unit_cost: float | None = None
    max_total_p95_latency_ms: float | None = None
    trusted_issuers: frozenset[str] = frozenset()
    environment_digest: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("cost_weight", self.cost_weight),
            ("latency_weight", self.latency_weight),
            ("conditional_penalty", self.conditional_penalty),
        ):
            if value < 0 or not isfinite(value):
                raise ValueError(f"{name} must be finite and >= 0")


@dataclass(frozen=True)
class LinkChoice:
    slot_id: str
    component_id: str
    certificate_digest: str
    verdict: CertificateVerdict
    unit_cost: float
    p95_latency_ms: float


@dataclass(frozen=True)
class LinkPlan:
    choices: tuple[LinkChoice, ...]
    composition_certificate_digests: tuple[str, ...]
    total_unit_cost: float
    total_p95_latency_ms: float
    objective: float

    @property
    def digest(self) -> str:
        return _digest(self)


@dataclass(frozen=True)
class ResolutionRejection:
    slot_id: str
    component_id: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionResult:
    plan: LinkPlan | None
    rejected: tuple[ResolutionRejection, ...]
    feasible_plan_count: int


class NoCompatiblePlan(RuntimeError):
    pass


def _parse_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _cert_valid(
    cert: CompatibilityCertificate,
    *,
    at: datetime,
    policy: LinkPolicy,
    slot: SemanticSlot,
) -> list[str]:
    reasons: list[str] = []
    if cert.baseline_component_id != slot.baseline_component_id:
        reasons.append("wrong-baseline")
    if cert.contract_digest != slot.contract_digest:
        reasons.append("wrong-contract")
    if cert.probe_coverage < slot.minimum_probe_coverage:
        reasons.append("insufficient-probe-coverage")
    if cert.verdict == CertificateVerdict.CONDITIONAL and not slot.allow_conditional:
        reasons.append("conditional-not-allowed")
    if policy.trusted_issuers and cert.issuer not in policy.trusted_issuers:
        reasons.append("untrusted-issuer")
    if policy.environment_digest and cert.environment_digest != policy.environment_digest:
        reasons.append("wrong-environment")
    if _parse_time(cert.issued_at) > at:
        reasons.append("not-yet-valid")
    if cert.expires_at and _parse_time(cert.expires_at) <= at:
        reasons.append("expired")
    return reasons


def _offer_valid(offer: ComponentOffer, slot: SemanticSlot) -> list[str]:
    reasons: list[str] = []
    if offer.kind != slot.kind:
        reasons.append("wrong-kind")
    if not slot.required_capabilities <= offer.capabilities:
        reasons.append("missing-capability")
    if slot.allowed_regions and not (slot.allowed_regions & offer.regions):
        reasons.append("region-not-allowed")
    if slot.max_unit_cost is not None and offer.unit_cost > slot.max_unit_cost:
        reasons.append("cost-ceiling")
    if slot.max_p95_latency_ms is not None and offer.p95_latency_ms > slot.max_p95_latency_ms:
        reasons.append("latency-ceiling")
    return reasons


def resolve_semantic_dependencies(
    slots: Sequence[SemanticSlot],
    offers: Sequence[ComponentOffer],
    certificates: Sequence[CompatibilityCertificate],
    *,
    composition_requirements: Sequence[CompositionRequirement] = (),
    composition_certificates: Sequence[CompositionCertificate] = (),
    policy: LinkPolicy = LinkPolicy(),
    at: datetime | None = None,
    raise_on_failure: bool = False,
) -> ResolutionResult:
    """Resolve the cheapest/fastest *proven-compatible* AI component graph.

    Unlike a router, an offer is never considered merely because it advertises a
    capability or benchmark. It must carry a compatibility certificate for the
    exact baseline and application contract. Cross-slot requirements additionally
    demand composition evidence for the concrete selected member set.
    """

    now = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if len({s.slot_id for s in slots}) != len(slots):
        raise ValueError("slot_id values must be unique")

    certs_by_candidate: dict[str, list[CompatibilityCertificate]] = {}
    for cert in certificates:
        certs_by_candidate.setdefault(cert.candidate_component_id, []).append(cert)

    candidates_by_slot: dict[str, list[tuple[ComponentOffer, CompatibilityCertificate]]] = {}
    rejected: list[ResolutionRejection] = []

    for slot in slots:
        candidates: list[tuple[ComponentOffer, CompatibilityCertificate]] = []
        for offer in offers:
            reasons = _offer_valid(offer, slot)
            candidate_certs = certs_by_candidate.get(offer.component_id, [])
            matching: list[CompatibilityCertificate] = []
            if not candidate_certs:
                reasons.append("missing-certificate")
            else:
                for cert in candidate_certs:
                    cert_reasons = _cert_valid(cert, at=now, policy=policy, slot=slot)
                    if not cert_reasons:
                        matching.append(cert)
                if not matching:
                    reasons.append("no-valid-certificate")
            if reasons:
                rejected.append(
                    ResolutionRejection(
                        slot.slot_id,
                        offer.component_id,
                        tuple(sorted(set(reasons))),
                    )
                )
                continue
            matching.sort(
                key=lambda c: (
                    c.verdict == CertificateVerdict.CONDITIONAL,
                    -c.probe_coverage,
                    c.digest,
                )
            )
            candidates.append((offer, matching[0]))
        candidates_by_slot[slot.slot_id] = candidates

    if any(not candidates_by_slot[s.slot_id] for s in slots):
        result = ResolutionResult(None, tuple(rejected), 0)
        if raise_on_failure:
            raise NoCompatiblePlan("at least one semantic slot has no proven-compatible candidate")
        return result

    composition_index: dict[tuple[frozenset[str], str], list[CompositionCertificate]] = {}
    for cert in composition_certificates:
        composition_index.setdefault((cert.members, cert.contract_digest), []).append(cert)

    feasible: list[LinkPlan] = []
    ordered_slots = list(slots)
    product = itertools.product(*(candidates_by_slot[s.slot_id] for s in ordered_slots))

    for combo in product:
        chosen = {slot.slot_id: pair for slot, pair in zip(ordered_slots, combo)}
        total_cost = sum(offer.unit_cost for offer, _ in combo)
        total_latency = sum(offer.p95_latency_ms for offer, _ in combo)
        if policy.max_total_unit_cost is not None and total_cost > policy.max_total_unit_cost:
            continue
        if (
            policy.max_total_p95_latency_ms is not None
            and total_latency > policy.max_total_p95_latency_ms
        ):
            continue

        comp_digests: list[str] = []
        composition_ok = True
        for req in composition_requirements:
            try:
                members = frozenset(
                    chosen[slot_id][0].component_id for slot_id in req.slot_ids
                )
            except KeyError as exc:
                raise ValueError(f"unknown slot in composition requirement: {exc}") from exc
            cert_options = composition_index.get((members, req.contract_digest), [])
            valid_options: list[CompositionCertificate] = []
            for cert in cert_options:
                if policy.trusted_issuers and cert.issuer not in policy.trusted_issuers:
                    continue
                if policy.environment_digest and cert.environment_digest != policy.environment_digest:
                    continue
                if _parse_time(cert.issued_at) > now:
                    continue
                if cert.expires_at and _parse_time(cert.expires_at) <= now:
                    continue
                valid_options.append(cert)
            if not valid_options:
                composition_ok = False
                break
            comp_digests.append(sorted(c.digest for c in valid_options)[0])
        if not composition_ok:
            continue

        conditional_count = sum(
            cert.verdict == CertificateVerdict.CONDITIONAL for _, cert in combo
        )
        objective = (
            policy.cost_weight * total_cost
            + policy.latency_weight * total_latency
            + policy.conditional_penalty * conditional_count
        )
        choices = tuple(
            LinkChoice(
                slot_id=slot.slot_id,
                component_id=offer.component_id,
                certificate_digest=cert.digest,
                verdict=cert.verdict,
                unit_cost=offer.unit_cost,
                p95_latency_ms=offer.p95_latency_ms,
            )
            for slot, (offer, cert) in zip(ordered_slots, combo)
        )
        feasible.append(
            LinkPlan(
                choices,
                tuple(sorted(comp_digests)),
                total_cost,
                total_latency,
                objective,
            )
        )

    if not feasible:
        result = ResolutionResult(None, tuple(rejected), 0)
        if raise_on_failure:
            raise NoCompatiblePlan(
                "no composition satisfies semantic evidence and resource constraints"
            )
        return result

    feasible.sort(
        key=lambda p: (
            p.objective,
            p.total_unit_cost,
            p.total_p95_latency_ms,
            p.digest,
        )
    )
    return ResolutionResult(feasible[0], tuple(rejected), len(feasible))
