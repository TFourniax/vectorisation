from __future__ import annotations

"""Tamper-evident attestation envelope for Semantic ABI Protocol v1."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .adequacy import ContractAdequacyReport
from .conformance import OracleConformanceReport
from .protocol_v1 import ProtocolAuditResult


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class AttestedEvidence:
    name: str
    sha256: str
    kind: str = "benchmark"
    uri: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sha256": self.sha256,
            "kind": self.kind,
            "uri": self.uri,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True, frozen=True)
class SemanticProtocolAttestation:
    """Bind one contract execution to its backend identity and governance evidence.

    This is a digest envelope, not a digital signature. A deployment system can
    sign the resulting attestation digest with its own KMS/signature mechanism.
    """

    contract_digest: str
    oracle_manifest_digest: str
    plan_digest: str
    snapshot_digest: str
    protocol_audit_digest: str
    audit_score: float
    hard_pass: bool
    evaluated_clauses: int
    missing_clauses: int
    conformance_digest: str
    conformance_passed: bool
    adequacy_digest: str | None = None
    adequacy_status: str | None = None
    risk_certificate_digest: str | None = None
    risk_certified: bool | None = None
    evidence: tuple[AttestedEvidence, ...] = ()
    status: str = "observed"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in {"observed", "conformant", "certified", "blocked"}:
            raise ValueError("invalid attestation status")
        if self.adequacy_status not in {None, "adequate", "failed", "insufficient_evidence"}:
            raise ValueError("invalid adequacy status")

    def payload(self, *, include_created_at: bool = True) -> dict[str, Any]:
        payload = {
            "format": "semantic-abi-protocol-attestation",
            "format_version": 1,
            "contract_digest": self.contract_digest,
            "oracle_manifest_digest": self.oracle_manifest_digest,
            "plan_digest": self.plan_digest,
            "snapshot_digest": self.snapshot_digest,
            "protocol_audit_digest": self.protocol_audit_digest,
            "audit_score": float(self.audit_score),
            "hard_pass": bool(self.hard_pass),
            "evaluated_clauses": int(self.evaluated_clauses),
            "missing_clauses": int(self.missing_clauses),
            "conformance_digest": self.conformance_digest,
            "conformance_passed": bool(self.conformance_passed),
            "adequacy_digest": self.adequacy_digest,
            "adequacy_status": self.adequacy_status,
            "risk_certificate_digest": self.risk_certificate_digest,
            "risk_certified": self.risk_certified,
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
            "metadata": dict(self.metadata),
        }
        if include_created_at:
            payload["created_at"] = self.created_at
        return payload

    @property
    def digest(self) -> str:
        return _digest(self.payload(include_created_at=False))

    @property
    def deployment_eligible(self) -> bool:
        """Strict explicit gate; no good-looking metric can imply certification."""
        return bool(
            self.status == "certified"
            and self.conformance_passed
            and self.hard_pass
            and self.missing_clauses == 0
            and self.adequacy_status == "adequate"
            and self.risk_certified is True
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"attestation": self.payload(), "attestation_digest": self.digest}
        path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, envelope: Mapping[str, Any]) -> "SemanticProtocolAttestation":
        raw = dict(envelope.get("attestation", envelope))
        if raw.get("format") != "semantic-abi-protocol-attestation" or int(raw.get("format_version", 0)) != 1:
            raise ValueError("not a Semantic ABI protocol attestation v1")
        evidence = tuple(
            AttestedEvidence(
                name=str(item["name"]),
                sha256=str(item["sha256"]),
                kind=str(item.get("kind", "benchmark")),
                uri=item.get("uri"),
                metadata=dict(item.get("metadata", {})),
            )
            for item in raw.get("evidence", ())
        )
        attestation = cls(
            contract_digest=str(raw["contract_digest"]),
            oracle_manifest_digest=str(raw["oracle_manifest_digest"]),
            plan_digest=str(raw["plan_digest"]),
            snapshot_digest=str(raw["snapshot_digest"]),
            protocol_audit_digest=str(raw["protocol_audit_digest"]),
            audit_score=float(raw["audit_score"]),
            hard_pass=bool(raw["hard_pass"]),
            evaluated_clauses=int(raw["evaluated_clauses"]),
            missing_clauses=int(raw["missing_clauses"]),
            conformance_digest=str(raw["conformance_digest"]),
            conformance_passed=bool(raw["conformance_passed"]),
            adequacy_digest=raw.get("adequacy_digest"),
            adequacy_status=raw.get("adequacy_status"),
            risk_certificate_digest=raw.get("risk_certificate_digest"),
            risk_certified=raw.get("risk_certified"),
            evidence=evidence,
            status=str(raw.get("status", "observed")),
            created_at=str(raw.get("created_at") or datetime.now(timezone.utc).isoformat()),
            metadata=dict(raw.get("metadata", {})),
        )
        expected = envelope.get("attestation_digest")
        if expected is not None and str(expected) != attestation.digest:
            raise ValueError("Semantic ABI protocol attestation digest mismatch")
        return attestation

    @classmethod
    def load(cls, path: str | Path) -> "SemanticProtocolAttestation":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def make_protocol_attestation(
    audit: ProtocolAuditResult,
    conformance: OracleConformanceReport,
    *,
    adequacy: ContractAdequacyReport | None = None,
    risk_certificate_digest: str | None = None,
    risk_certified: bool | None = None,
    evidence: Sequence[AttestedEvidence] = (),
    status: str = "observed",
    metadata: Mapping[str, Any] | None = None,
) -> SemanticProtocolAttestation:
    if conformance.manifest_digest != audit.snapshot.manifest.digest:
        raise ValueError("conformance report belongs to a different oracle manifest")
    if adequacy is not None and adequacy.contract_digest != audit.report.contract_digest:
        raise ValueError("adequacy report belongs to a different Semantic Contract")
    if audit.plan.contract_digest != audit.report.contract_digest:
        raise ValueError("execution plan and audit contract digests differ")
    if audit.snapshot.plan_digest != audit.plan.digest:
        raise ValueError("snapshot does not belong to the supplied execution plan")

    return SemanticProtocolAttestation(
        contract_digest=audit.report.contract_digest,
        oracle_manifest_digest=audit.snapshot.manifest.digest,
        plan_digest=audit.plan.digest,
        snapshot_digest=audit.snapshot.digest,
        protocol_audit_digest=audit.digest,
        audit_score=audit.report.score,
        hard_pass=audit.report.hard_pass,
        evaluated_clauses=audit.report.evaluated_clauses,
        missing_clauses=audit.report.missing_clauses,
        conformance_digest=conformance.digest,
        conformance_passed=conformance.passed,
        adequacy_digest=None if adequacy is None else adequacy.digest,
        adequacy_status=None if adequacy is None else adequacy.status,
        risk_certificate_digest=risk_certificate_digest,
        risk_certified=risk_certified,
        evidence=tuple(evidence),
        status=status,
        metadata=dict(metadata or {}),
    )
