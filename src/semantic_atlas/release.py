from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .contracts import ContractReport
from .risk_control import RiskCertificate
from .support import ContractCoverage


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(slots=True, frozen=True)
class ImplementationFingerprint:
    """Stable identity of one semantic implementation candidate.

    A human model alias is not enough for reproducibility. Callers should pin a
    provider/model revision and a preprocessing digest (tokenization, prompts,
    normalization, chunking, pooling or any transform that changes coordinates).
    """

    implementation_id: str
    model_id: str
    revision: str
    dimensions: int
    modality: str = "text"
    preprocessing_digest: str = "unspecified"
    runtime: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if not self.implementation_id or not self.model_id or not self.revision:
            raise ValueError("implementation_id, model_id and revision are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "implementation_id": self.implementation_id,
            "model_id": self.model_id,
            "revision": self.revision,
            "dimensions": self.dimensions,
            "modality": self.modality,
            "preprocessing_digest": self.preprocessing_digest,
            "runtime": self.runtime,
            "metadata": dict(self.metadata),
        }

    @property
    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(slots=True, frozen=True)
class EvidenceReference:
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


@dataclass(slots=True)
class SemanticReleaseCertificate:
    """Tamper-evident manifest for a semantically certified rollout candidate."""

    implementation: ImplementationFingerprint
    contract_digest: str
    audit_score: float
    hard_pass: bool
    evaluated_clauses: int
    missing_clauses: int
    contract_object_coverage: float
    risk_certificate: RiskCertificate
    evidence: tuple[EvidenceReference, ...] = ()
    status: str = "candidate"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def payload(self, *, include_created_at: bool = True) -> dict[str, Any]:
        payload = {
            "format": "semantic-release-certificate",
            "format_version": 1,
            "implementation": self.implementation.to_dict(),
            "implementation_digest": self.implementation.digest,
            "contract_digest": self.contract_digest,
            "audit_score": float(self.audit_score),
            "hard_pass": bool(self.hard_pass),
            "evaluated_clauses": int(self.evaluated_clauses),
            "missing_clauses": int(self.missing_clauses),
            "contract_object_coverage": float(self.contract_object_coverage),
            "risk_certificate": asdict(self.risk_certificate),
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
            "metadata": self.metadata,
        }
        if include_created_at:
            payload["created_at"] = self.created_at
        return payload

    @property
    def digest(self) -> str:
        return _digest(self.payload(include_created_at=False))

    @property
    def rollout_eligible(self) -> bool:
        return bool(
            self.hard_pass
            and self.risk_certificate.certified
            and self.audit_score > 0.0
            and self.contract_object_coverage > 0.0
        )

    def verify_evidence(self, files: Mapping[str, bytes]) -> dict[str, bool]:
        """Verify supplied evidence bytes against hashes named in the manifest."""
        return {
            ref.name: bool(ref.name in files and hashlib.sha256(files[ref.name]).hexdigest() == ref.sha256)
            for ref in self.evidence
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        envelope = {"certificate": self.payload(), "certificate_digest": self.digest}
        path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, envelope: Mapping[str, Any]) -> "SemanticReleaseCertificate":
        payload = dict(envelope.get("certificate", envelope))
        if payload.get("format") != "semantic-release-certificate":
            raise ValueError("not a semantic release certificate")
        impl = payload["implementation"]
        fingerprint = ImplementationFingerprint(
            implementation_id=str(impl["implementation_id"]),
            model_id=str(impl["model_id"]),
            revision=str(impl["revision"]),
            dimensions=int(impl["dimensions"]),
            modality=str(impl.get("modality", "text")),
            preprocessing_digest=str(impl.get("preprocessing_digest", "unspecified")),
            runtime=impl.get("runtime"),
            metadata=dict(impl.get("metadata", {})),
        )
        risk = RiskCertificate(**payload["risk_certificate"])
        evidence = tuple(
            EvidenceReference(
                name=str(item["name"]),
                sha256=str(item["sha256"]),
                kind=str(item.get("kind", "benchmark")),
                uri=item.get("uri"),
                metadata=dict(item.get("metadata", {})),
            )
            for item in payload.get("evidence", [])
        )
        certificate = cls(
            implementation=fingerprint,
            contract_digest=str(payload["contract_digest"]),
            audit_score=float(payload["audit_score"]),
            hard_pass=bool(payload["hard_pass"]),
            evaluated_clauses=int(payload["evaluated_clauses"]),
            missing_clauses=int(payload["missing_clauses"]),
            contract_object_coverage=float(payload["contract_object_coverage"]),
            risk_certificate=risk,
            evidence=evidence,
            status=str(payload.get("status", "candidate")),
            created_at=str(payload.get("created_at") or datetime.now(timezone.utc).isoformat()),
            metadata=dict(payload.get("metadata", {})),
        )
        expected = envelope.get("certificate_digest")
        if expected is not None and str(expected) != certificate.digest:
            raise ValueError("semantic release certificate digest mismatch")
        return certificate

    @classmethod
    def load(cls, path: str | Path) -> "SemanticReleaseCertificate":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def make_release_certificate(
    implementation: ImplementationFingerprint,
    report: ContractReport,
    coverage: ContractCoverage,
    risk_certificate: RiskCertificate,
    *,
    evidence: Sequence[EvidenceReference] = (),
    status: str = "candidate",
    metadata: Mapping[str, Any] | None = None,
) -> SemanticReleaseCertificate:
    return SemanticReleaseCertificate(
        implementation=implementation,
        contract_digest=report.contract_digest,
        audit_score=report.score,
        hard_pass=report.hard_pass,
        evaluated_clauses=report.evaluated_clauses,
        missing_clauses=report.missing_clauses,
        contract_object_coverage=coverage.object_coverage,
        risk_certificate=risk_certificate,
        evidence=tuple(evidence),
        status=status,
        metadata=dict(metadata or {}),
    )
