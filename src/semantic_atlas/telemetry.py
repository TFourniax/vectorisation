from __future__ import annotations

"""Telemetry adapters for evidence-gated Semantic Contract acquisition.

This module intentionally separates *observing retrieval* from *declaring semantic
truth*. OpenInference/OpenTelemetry retrieval spans provide query/result identities and
provenance. They do not become contract clauses unless joined with an explicit feedback
signal (selection, click, correction, accepted source, etc.).

The parser is dependency-free and accepts the common JSON/JSONL shapes emitted by
OpenInference-compatible systems while preserving a stable logical-ID boundary.
"""

from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .acquisition import Evidence, evidence_from_trace


_OPENINFERENCE_RETRIEVER = "RETRIEVER"
_OPENINFERENCE_RERANKER = "RERANKER"


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{\"":
        return value
    try:
        return json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_tuple(value: Any) -> tuple[str, ...]:
    value = _json_value(value)
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return tuple(str(item) for item in value if item is not None and str(item))
    return (str(value),)


def _first_nonempty(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None and str(value):
            return str(value)
    return None


def _canonical_query_text(value: Any) -> str | None:
    value = _json_value(value)
    if isinstance(value, Mapping):
        for key in ("query", "question", "input", "text", "prompt"):
            if key in value and value[key] is not None:
                return str(value[key]).strip() or None
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) == 1:
            return _canonical_query_text(value[0])
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def stable_query_id(query_text: str, *, secret: bytes | str | None = None, namespace: str = "q") -> str:
    """Create a deterministic logical query ID without retaining raw query text.

    Supplying ``secret`` uses HMAC-SHA256 and is recommended when query text can contain
    personal or commercially sensitive data. Plain SHA-256 is deterministic but must
    not be described as anonymization because low-entropy text can be dictionary-guessed.
    """

    normalized = " ".join(str(query_text).split())
    payload = normalized.encode("utf-8")
    if secret is None:
        digest = hashlib.sha256(payload).hexdigest()
        return f"{namespace}:sha256:{digest}"
    key = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return f"{namespace}:hmac-sha256:{digest}"


def _document_ids(attributes: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract stable document IDs from structured or flattened OpenInference attrs."""

    documents = _json_value(attributes.get("retrieval.documents"))
    output: list[str] = []
    if isinstance(documents, Sequence) and not isinstance(documents, (str, bytes, bytearray)):
        for document in documents:
            document = _json_value(document)
            if not isinstance(document, Mapping):
                continue
            document_id = document.get("document.id", document.get("id"))
            if document_id is not None and str(document_id):
                output.append(str(document_id))

    # OpenInference structured lists may be flattened for OTEL transports:
    # retrieval.documents.0.document.id, retrieval.documents.1.document.id, ...
    flattened: list[tuple[int, str]] = []
    prefix = "retrieval.documents."
    suffix = ".document.id"
    for key, value in attributes.items():
        if not key.startswith(prefix) or not key.endswith(suffix):
            continue
        index_text = key[len(prefix) : -len(suffix)]
        try:
            index = int(index_text)
        except ValueError:
            continue
        if value is not None and str(value):
            flattened.append((index, str(value)))
    flattened.sort()
    output.extend(value for _, value in flattened)

    # Preserve order but remove duplicates.
    return tuple(dict.fromkeys(output))


def _span_attributes(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    attributes = payload.get("attributes")
    if isinstance(attributes, Mapping):
        return attributes
    # Some dataframe/JSON exporters flatten span attributes at the top level.
    return payload


def _span_kind(attributes: Mapping[str, Any]) -> str | None:
    value = attributes.get("openinference.span.kind")
    return None if value is None else str(value).upper()


def _iter_spans(payload: Any) -> Iterable[Mapping[str, Any]]:
    """Yield spans from direct JSON, list exports, or OTLP JSON envelopes."""

    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for item in payload:
            yield from _iter_spans(item)
        return
    if not isinstance(payload, Mapping):
        return
    if "resourceSpans" in payload:
        for resource in payload.get("resourceSpans", []):
            for scope in _as_mapping(resource).get("scopeSpans", []):
                for span in _as_mapping(scope).get("spans", []):
                    if isinstance(span, Mapping):
                        yield span
        return
    if "spans" in payload and isinstance(payload.get("spans"), Sequence):
        for span in payload.get("spans", []):
            if isinstance(span, Mapping):
                yield span
        return
    yield payload


@dataclass(slots=True, frozen=True)
class RetrievalObservation:
    query_id: str
    result_ids: tuple[str, ...]
    trace_id: str | None = None
    span_id: str | None = None
    kind: str = _OPENINFERENCE_RETRIEVER
    query_text: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "result_ids": list(self.result_ids),
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "kind": self.kind,
            "query_text": self.query_text,
            "provenance": dict(self.provenance),
        }


@dataclass(slots=True, frozen=True)
class RetrievalFeedback:
    """Feedback joined to an observed retrieval span by span or trace identity."""

    span_id: str | None = None
    trace_id: str | None = None
    clicked: tuple[str, ...] = ()
    selected: tuple[str, ...] = ()
    explicit_negative: tuple[str, ...] = ()
    accepted_sources: tuple[str, ...] = ()
    criticality: float = 0.0
    event_id: str | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.span_id and not self.trace_id:
            raise ValueError("feedback requires span_id and/or trace_id")
        if not 0.0 <= float(self.criticality) <= 1.0:
            raise ValueError("criticality must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "clicked": list(self.clicked),
            "selected": list(self.selected),
            "explicit_negative": list(self.explicit_negative),
            "accepted_sources": list(self.accepted_sources),
            "criticality": self.criticality,
            "event_id": self.event_id,
            "provenance": dict(self.provenance),
        }


@dataclass(slots=True, frozen=True)
class TelemetryImportReport:
    spans_seen: int
    retrieval_spans_seen: int
    observations_emitted: int
    skipped_missing_query: int
    skipped_missing_document_ids: int
    feedback_records: int = 0
    feedback_matched: int = 0
    evidence_emitted: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "spans_seen": self.spans_seen,
            "retrieval_spans_seen": self.retrieval_spans_seen,
            "observations_emitted": self.observations_emitted,
            "skipped_missing_query": self.skipped_missing_query,
            "skipped_missing_document_ids": self.skipped_missing_document_ids,
            "feedback_records": self.feedback_records,
            "feedback_matched": self.feedback_matched,
            "evidence_emitted": self.evidence_emitted,
        }


@dataclass(slots=True)
class TelemetryEvidenceResult:
    observations: list[RetrievalObservation]
    evidence: list[Evidence]
    report: TelemetryImportReport


def observation_from_openinference_span(
    span: Mapping[str, Any],
    *,
    query_secret: bytes | str | None = None,
    retain_query_text: bool = False,
    allow_reranker: bool = True,
) -> RetrievalObservation | None:
    attributes = _span_attributes(span)
    kind = _span_kind(attributes)
    allowed = {_OPENINFERENCE_RETRIEVER}
    if allow_reranker:
        allowed.add(_OPENINFERENCE_RERANKER)
    if kind not in allowed:
        return None

    explicit_query_id = _first_nonempty(
        attributes,
        ("semantic_abi.query_id", "semantic-abi.query-id", "query.id"),
    )
    query_text = _canonical_query_text(
        attributes.get("reranker.query") if kind == _OPENINFERENCE_RERANKER else attributes.get("input.value")
    )
    if explicit_query_id:
        query_id = explicit_query_id
    elif query_text:
        query_id = stable_query_id(query_text, secret=query_secret)
    else:
        return None

    if kind == _OPENINFERENCE_RERANKER:
        output_documents = _json_value(attributes.get("reranker.output_documents"))
        reranker_attrs = dict(attributes)
        if output_documents is not None:
            reranker_attrs["retrieval.documents"] = output_documents
        result_ids = _document_ids(reranker_attrs)
    else:
        result_ids = _document_ids(attributes)
    if not result_ids:
        return None

    trace_id = _first_nonempty(span, ("trace_id", "traceId", "context.trace_id", "context.traceId"))
    span_id = _first_nonempty(span, ("span_id", "spanId", "context.span_id", "context.spanId"))
    context = _as_mapping(span.get("context"))
    if trace_id is None:
        trace_id = _first_nonempty(context, ("trace_id", "traceId"))
    if span_id is None:
        span_id = _first_nonempty(context, ("span_id", "spanId"))

    return RetrievalObservation(
        query_id=query_id,
        result_ids=result_ids,
        trace_id=trace_id,
        span_id=span_id,
        kind=kind or _OPENINFERENCE_RETRIEVER,
        query_text=query_text if retain_query_text else None,
        provenance={
            "telemetry": "openinference",
            "span_name": span.get("name"),
        },
    )


def feedback_from_payload(payload: Mapping[str, Any]) -> RetrievalFeedback:
    return RetrievalFeedback(
        span_id=None if payload.get("span_id") is None else str(payload.get("span_id")),
        trace_id=None if payload.get("trace_id") is None else str(payload.get("trace_id")),
        clicked=_string_tuple(payload.get("clicked")),
        selected=_string_tuple(payload.get("selected")),
        explicit_negative=_string_tuple(payload.get("explicit_negative")),
        accepted_sources=_string_tuple(payload.get("accepted_sources")),
        criticality=float(payload.get("criticality", 0.0)),
        event_id=None if payload.get("event_id") is None else str(payload.get("event_id")),
        provenance=dict(_as_mapping(payload.get("provenance"))),
    )


def load_feedback_jsonl(path: str | Path) -> list[RetrievalFeedback]:
    output: list[RetrievalFeedback] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, Mapping):
                raise ValueError("row must be a JSON object")
            output.append(feedback_from_payload(payload))
        except Exception as exc:
            raise ValueError(f"invalid telemetry feedback at line {line_number}: {exc}") from exc
    return output


def load_openinference_jsonl(
    path: str | Path,
    *,
    query_secret: bytes | str | None = None,
    retain_query_text: bool = False,
    allow_reranker: bool = True,
) -> tuple[list[RetrievalObservation], TelemetryImportReport]:
    observations: list[RetrievalObservation] = []
    spans_seen = 0
    retrieval_spans_seen = 0
    missing_query = 0
    missing_documents = 0

    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid telemetry JSON at line {line_number}: {exc}") from exc
        for span in _iter_spans(payload):
            spans_seen += 1
            attributes = _span_attributes(span)
            kind = _span_kind(attributes)
            if kind not in ({_OPENINFERENCE_RETRIEVER, _OPENINFERENCE_RERANKER} if allow_reranker else {_OPENINFERENCE_RETRIEVER}):
                continue
            retrieval_spans_seen += 1
            explicit_query = _first_nonempty(attributes, ("semantic_abi.query_id", "semantic-abi.query-id", "query.id"))
            query_value = attributes.get("reranker.query") if kind == _OPENINFERENCE_RERANKER else attributes.get("input.value")
            if not explicit_query and not _canonical_query_text(query_value):
                missing_query += 1
                continue
            observation = observation_from_openinference_span(
                span,
                query_secret=query_secret,
                retain_query_text=retain_query_text,
                allow_reranker=allow_reranker,
            )
            if observation is None:
                missing_documents += 1
                continue
            observations.append(observation)

    report = TelemetryImportReport(
        spans_seen=spans_seen,
        retrieval_spans_seen=retrieval_spans_seen,
        observations_emitted=len(observations),
        skipped_missing_query=missing_query,
        skipped_missing_document_ids=missing_documents,
    )
    return observations, report


def evidence_from_observation(observation: RetrievalObservation, feedback: RetrievalFeedback) -> list[Evidence]:
    provenance = {**dict(observation.provenance), **dict(feedback.provenance)}
    if observation.trace_id:
        provenance["trace_id"] = observation.trace_id
    if observation.span_id:
        provenance["span_id"] = observation.span_id
    return list(
        evidence_from_trace(
            {
                "anchor": observation.query_id,
                "results": list(observation.result_ids),
                "clicked": list(feedback.clicked),
                "selected": list(feedback.selected),
                "explicit_negative": list(feedback.explicit_negative),
                "accepted_sources": list(feedback.accepted_sources),
                "criticality": feedback.criticality,
                "event_id": feedback.event_id or observation.span_id or observation.trace_id,
                "provenance": provenance,
            }
        )
    )


def join_feedback(
    observations: Sequence[RetrievalObservation],
    feedback: Sequence[RetrievalFeedback],
) -> TelemetryEvidenceResult:
    """Join feedback to retrieval observations and emit acquisition evidence.

    Span identity wins over trace identity. A retrieval observation without matching
    feedback remains an observation and emits zero semantic clauses.
    """

    by_span = {item.span_id: item for item in feedback if item.span_id}
    by_trace = {item.trace_id: item for item in feedback if item.trace_id and not item.span_id}
    evidence: list[Evidence] = []
    matched = 0
    for observation in observations:
        record = by_span.get(observation.span_id) if observation.span_id else None
        if record is None and observation.trace_id:
            record = by_trace.get(observation.trace_id)
        if record is None:
            continue
        matched += 1
        evidence.extend(evidence_from_observation(observation, record))

    return TelemetryEvidenceResult(
        observations=list(observations),
        evidence=evidence,
        report=TelemetryImportReport(
            spans_seen=len(observations),
            retrieval_spans_seen=len(observations),
            observations_emitted=len(observations),
            skipped_missing_query=0,
            skipped_missing_document_ids=0,
            feedback_records=len(feedback),
            feedback_matched=matched,
            evidence_emitted=len(evidence),
        ),
    )
