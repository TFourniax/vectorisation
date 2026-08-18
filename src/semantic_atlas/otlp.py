from __future__ import annotations

"""Raw OTLP/HTTP JSON normalization for Semantic ABI telemetry acquisition.

OTLP JSON follows Protobuf JSON mapping: span attributes are repeated KeyValue messages
and each value is an ``AnyValue`` union (``stringValue``, ``arrayValue``,
``kvlistValue``, ...).  Contract Forge's OpenInference adapter consumes a simpler
attribute mapping, so this module performs only the wire-shape normalization and then
reuses the existing semantic extraction logic.
"""

from dataclasses import dataclass
import base64
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .telemetry import RetrievalObservation, TelemetryImportReport, observation_from_openinference_span


_ANY_VALUE_FIELDS = (
    "stringValue",
    "boolValue",
    "intValue",
    "doubleValue",
    "bytesValue",
    "arrayValue",
    "kvlistValue",
)


def decode_otlp_any_value(value: Any) -> Any:
    """Decode OTLP JSON's AnyValue representation into ordinary Python values."""

    if not isinstance(value, Mapping):
        return value
    present = [field for field in _ANY_VALUE_FIELDS if field in value]
    if not present:
        # Already-normalized maps are accepted to make ingestion composable.
        return {str(key): decode_otlp_any_value(item) for key, item in value.items()}
    if len(present) != 1:
        raise ValueError("OTLP AnyValue must contain exactly one value field")
    field = present[0]
    raw = value[field]
    if field == "stringValue":
        return str(raw)
    if field == "boolValue":
        if not isinstance(raw, bool):
            raise ValueError("OTLP boolValue must be boolean")
        return raw
    if field == "intValue":
        # Protobuf JSON normally encodes int64 as a decimal string.
        return int(raw)
    if field == "doubleValue":
        return float(raw)
    if field == "bytesValue":
        if not isinstance(raw, str):
            raise ValueError("OTLP bytesValue must be base64 text")
        return base64.b64decode(raw, validate=True)
    if field == "arrayValue":
        root = raw if isinstance(raw, Mapping) else {}
        values = root.get("values", ())
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
            raise ValueError("OTLP arrayValue.values must be an array")
        return [decode_otlp_any_value(item) for item in values]
    if field == "kvlistValue":
        root = raw if isinstance(raw, Mapping) else {}
        values = root.get("values", ())
        return decode_otlp_attributes(values)
    raise AssertionError(field)


def decode_otlp_attributes(attributes: Any) -> dict[str, Any]:
    """Decode a repeated OTLP KeyValue collection and reject duplicate keys."""

    if attributes is None:
        return {}
    if isinstance(attributes, Mapping):
        return {str(key): decode_otlp_any_value(value) for key, value in attributes.items()}
    if not isinstance(attributes, Sequence) or isinstance(attributes, (str, bytes, bytearray)):
        raise ValueError("OTLP attributes must be an object or KeyValue array")
    output: dict[str, Any] = {}
    for row in attributes:
        if not isinstance(row, Mapping):
            raise ValueError("OTLP attribute row must be an object")
        key = row.get("key")
        if key is None or not str(key):
            raise ValueError("OTLP attribute key must be non-empty")
        key_text = str(key)
        if key_text in output:
            raise ValueError(f"duplicate OTLP attribute key: {key_text}")
        output[key_text] = decode_otlp_any_value(row.get("value", {}))
    return output


def _iter_otlp_spans(payload: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for item in payload:
            yield from _iter_otlp_spans(item)
        return
    if not isinstance(payload, Mapping):
        return
    resources = payload.get("resourceSpans")
    if resources is None:
        # Also accept one raw span for local/exporter fixtures.
        yield payload
        return
    if not isinstance(resources, Sequence) or isinstance(resources, (str, bytes, bytearray)):
        raise ValueError("OTLP resourceSpans must be an array")
    for resource_span in resources:
        if not isinstance(resource_span, Mapping):
            continue
        scopes = resource_span.get("scopeSpans", ())
        if not isinstance(scopes, Sequence) or isinstance(scopes, (str, bytes, bytearray)):
            raise ValueError("OTLP scopeSpans must be an array")
        for scope_span in scopes:
            if not isinstance(scope_span, Mapping):
                continue
            spans = scope_span.get("spans", ())
            if not isinstance(spans, Sequence) or isinstance(spans, (str, bytes, bytearray)):
                raise ValueError("OTLP spans must be an array")
            for span in spans:
                if isinstance(span, Mapping):
                    yield span


def normalize_otlp_span(span: Mapping[str, Any]) -> dict[str, Any]:
    """Return a span shape accepted by the OpenInference telemetry adapter."""

    normalized = dict(span)
    normalized["attributes"] = decode_otlp_attributes(span.get("attributes", ()))
    # OTLP JSON uses lowerCamelCase; the telemetry adapter accepts these aliases.
    if span.get("traceId") is not None:
        normalized["traceId"] = str(span["traceId"])
    if span.get("spanId") is not None:
        normalized["spanId"] = str(span["spanId"])
    return normalized


@dataclass(slots=True)
class OtlpObservationResult:
    observations: list[RetrievalObservation]
    report: TelemetryImportReport


def observations_from_otlp_payload(
    payload: Any,
    *,
    query_secret: bytes | str | None = None,
    retain_query_text: bool = False,
    allow_reranker: bool = True,
) -> OtlpObservationResult:
    observations: list[RetrievalObservation] = []
    spans_seen = 0
    retrieval_seen = 0
    missing_query = 0
    missing_documents = 0

    for raw_span in _iter_otlp_spans(payload):
        spans_seen += 1
        span = normalize_otlp_span(raw_span)
        attrs = span["attributes"]
        kind = str(attrs.get("openinference.span.kind", "")).upper()
        allowed = {"RETRIEVER"}
        if allow_reranker:
            allowed.add("RERANKER")
        if kind not in allowed:
            continue
        retrieval_seen += 1
        has_query = any(
            attrs.get(key) not in (None, "")
            for key in ("semantic_abi.query_id", "semantic-abi.query-id", "query.id", "input.value", "reranker.query")
        )
        if not has_query:
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

    return OtlpObservationResult(
        observations=observations,
        report=TelemetryImportReport(
            spans_seen=spans_seen,
            retrieval_spans_seen=retrieval_seen,
            observations_emitted=len(observations),
            skipped_missing_query=missing_query,
            skipped_missing_document_ids=missing_documents,
        ),
    )


def load_otlp_jsonl(
    path: str | Path,
    *,
    query_secret: bytes | str | None = None,
    retain_query_text: bool = False,
    allow_reranker: bool = True,
) -> OtlpObservationResult:
    observations: list[RetrievalObservation] = []
    totals = {
        "spans_seen": 0,
        "retrieval_spans_seen": 0,
        "skipped_missing_query": 0,
        "skipped_missing_document_ids": 0,
    }
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid OTLP JSON at line {line_number}: {exc}") from exc
        result = observations_from_otlp_payload(
            payload,
            query_secret=query_secret,
            retain_query_text=retain_query_text,
            allow_reranker=allow_reranker,
        )
        observations.extend(result.observations)
        report = result.report
        totals["spans_seen"] += report.spans_seen
        totals["retrieval_spans_seen"] += report.retrieval_spans_seen
        totals["skipped_missing_query"] += report.skipped_missing_query
        totals["skipped_missing_document_ids"] += report.skipped_missing_document_ids
    return OtlpObservationResult(
        observations=observations,
        report=TelemetryImportReport(
            spans_seen=totals["spans_seen"],
            retrieval_spans_seen=totals["retrieval_spans_seen"],
            observations_emitted=len(observations),
            skipped_missing_query=totals["skipped_missing_query"],
            skipped_missing_document_ids=totals["skipped_missing_document_ids"],
        ),
    )
