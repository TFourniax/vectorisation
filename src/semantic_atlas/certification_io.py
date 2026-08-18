from __future__ import annotations

"""Portable I/O for adequacy and risk evidence used by production attestations."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .adequacy import (
    ContractAdequacyEvidence,
    ContractAdequacyReport,
    ContractAdequacyRequirements,
    assess_contract_adequacy,
)
from .risk_control import CalibrationEvent, RiskCertificate, calibrate_semantic_risk


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def risk_certificate_to_dict(certificate: RiskCertificate) -> dict[str, Any]:
    return {
        "format": "semantic-abi-risk-certificate",
        "format_version": 1,
        **asdict(certificate),
    }


def risk_certificate_digest(certificate: RiskCertificate) -> str:
    return _digest(risk_certificate_to_dict(certificate))


def save_risk_certificate(certificate: RiskCertificate, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = risk_certificate_to_dict(certificate)
    envelope = {"certificate": payload, "certificate_digest": _digest(payload)}
    target.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_risk_certificate(path: str | Path) -> RiskCertificate:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(envelope, Mapping):
        raise ValueError("risk certificate file must be a JSON object")
    raw = envelope.get("certificate", envelope)
    if not isinstance(raw, Mapping):
        raise ValueError("risk certificate payload must be a JSON object")
    if raw.get("format") != "semantic-abi-risk-certificate" or int(raw.get("format_version", 0)) != 1:
        raise ValueError("unsupported Semantic ABI risk certificate")
    payload = dict(raw)
    payload.pop("format", None)
    payload.pop("format_version", None)
    certificate = RiskCertificate(**payload)
    expected = envelope.get("certificate_digest")
    if expected is not None and str(expected) != risk_certificate_digest(certificate):
        raise ValueError("risk certificate digest mismatch")
    return certificate


def load_calibration_events_jsonl(path: str | Path) -> list[CalibrationEvent]:
    events: list[CalibrationEvent] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, Mapping):
                raise ValueError("row must be a JSON object")
            events.append(
                CalibrationEvent(
                    proxy_risk=float(row["proxy_risk"]),
                    observed_loss=float(row["observed_loss"]),
                    object_id=None if row.get("object_id") is None else str(row["object_id"]),
                    group=None if row.get("group") is None else str(row["group"]),
                )
            )
        except Exception as exc:
            raise ValueError(f"invalid risk calibration event at line {line_number}: {exc}") from exc
    return events


def calibrate_risk_from_jsonl(
    path: str | Path,
    *,
    target_risk: float = 0.10,
    delta: float = 0.05,
    selection_fraction: float = 0.5,
    threshold_candidates: int = 12,
    min_selection: int = 20,
    min_certification: int = 30,
    seed: int = 17,
) -> RiskCertificate:
    return calibrate_semantic_risk(
        load_calibration_events_jsonl(path),
        target_risk=target_risk,
        delta=delta,
        selection_fraction=selection_fraction,
        threshold_candidates=threshold_candidates,
        min_selection=min_selection,
        min_certification=min_certification,
        seed=seed,
    )


def adequacy_report_to_dict(report: ContractAdequacyReport) -> dict[str, Any]:
    payload = report.to_dict()
    return {"report": payload, "report_digest": report.digest}


def save_adequacy_report(report: ContractAdequacyReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(adequacy_report_to_dict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _evidence_from_dict(payload: Mapping[str, Any], *, contract_digest: str | None = None) -> ContractAdequacyEvidence:
    raw_digest = str(payload.get("contract_digest") or contract_digest or "")
    if contract_digest is not None and raw_digest != str(contract_digest):
        raise ValueError("adequacy evidence belongs to a different Semantic Contract")
    return ContractAdequacyEvidence(
        contract_digest=raw_digest,
        object_coverage=None if payload.get("object_coverage") is None else float(payload["object_coverage"]),
        mutation_kill_rate=None if payload.get("mutation_kill_rate") is None else float(payload["mutation_kill_rate"]),
        mutation_localization=None if payload.get("mutation_localization") is None else float(payload["mutation_localization"]),
        predictive_correlation=None if payload.get("predictive_correlation") is None else float(payload["predictive_correlation"]),
        baseline_predictive_correlation=None if payload.get("baseline_predictive_correlation") is None else float(payload["baseline_predictive_correlation"]),
        heldout_cases=None if payload.get("heldout_cases") is None else int(payload["heldout_cases"]),
        datasets=None if payload.get("datasets") is None else int(payload["datasets"]),
        fault_families=None if payload.get("fault_families") is None else int(payload["fault_families"]),
        metadata=dict(payload.get("metadata", {})),
    )


def _requirements_from_dict(payload: Mapping[str, Any]) -> ContractAdequacyRequirements:
    fields = (
        "min_object_coverage",
        "min_mutation_kill_rate",
        "min_mutation_localization",
        "min_predictive_correlation",
        "min_predictive_lift_over_baseline",
        "min_heldout_cases",
        "min_datasets",
        "min_fault_families",
    )
    values: dict[str, Any] = {}
    for field in fields:
        value = payload.get(field)
        if value is None:
            values[field] = None
        elif field in {"min_heldout_cases", "min_datasets", "min_fault_families"}:
            values[field] = int(value)
        else:
            values[field] = float(value)
    return ContractAdequacyRequirements(**values)


def assess_adequacy_spec(path: str | Path, *, contract_digest: str) -> ContractAdequacyReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("adequacy specification must be a JSON object")
    evidence_raw = payload.get("evidence", {})
    requirements_raw = payload.get("requirements", {})
    if not isinstance(evidence_raw, Mapping) or not isinstance(requirements_raw, Mapping):
        raise ValueError("adequacy specification requires evidence and requirements objects")
    evidence = _evidence_from_dict(evidence_raw, contract_digest=contract_digest)
    requirements = _requirements_from_dict(requirements_raw)
    return assess_contract_adequacy(evidence, requirements)


def load_adequacy_report(path: str | Path, *, contract_digest: str | None = None) -> ContractAdequacyReport:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(envelope, Mapping):
        raise ValueError("adequacy report file must be a JSON object")
    raw = envelope.get("report", envelope)
    if not isinstance(raw, Mapping):
        raise ValueError("adequacy report payload must be a JSON object")
    if raw.get("format") != "semantic-contract-adequacy" or int(raw.get("format_version", 0)) != 1:
        raise ValueError("unsupported Semantic Contract adequacy report")
    evidence_raw = raw.get("evidence", {})
    requirements_raw = raw.get("requirements", {})
    if not isinstance(evidence_raw, Mapping) or not isinstance(requirements_raw, Mapping):
        raise ValueError("adequacy report omitted evidence or requirements")
    evidence = _evidence_from_dict(evidence_raw, contract_digest=contract_digest)
    report = assess_contract_adequacy(evidence, _requirements_from_dict(requirements_raw))
    if str(raw.get("status")) != report.status:
        raise ValueError("adequacy report status does not match recomputed evidence")
    expected = envelope.get("report_digest")
    if expected is not None and str(expected) != report.digest:
        raise ValueError("adequacy report digest mismatch")
    return report
