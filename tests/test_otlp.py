import pytest

from semantic_atlas.otlp import decode_otlp_any_value, decode_otlp_attributes, observations_from_otlp_payload


def test_decode_otlp_any_value_supports_nested_arrays_and_maps():
    value = {
        "kvlistValue": {
            "values": [
                {"key": "name", "value": {"stringValue": "doc"}},
                {
                    "key": "scores",
                    "value": {
                        "arrayValue": {
                            "values": [
                                {"doubleValue": 0.9},
                                {"doubleValue": 0.5},
                            ]
                        }
                    },
                },
            ]
        }
    }

    assert decode_otlp_any_value(value) == {"name": "doc", "scores": [0.9, 0.5]}


def test_decode_otlp_attributes_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate OTLP attribute key"):
        decode_otlp_attributes(
            [
                {"key": "x", "value": {"stringValue": "a"}},
                {"key": "x", "value": {"stringValue": "b"}},
            ]
        )


def test_raw_otlp_openinference_span_becomes_observation_without_retaining_query():
    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "5B8EFFF798038103D269B633813FC60C",
                                "spanId": "EEE19B7EC3C1B174",
                                "name": "retrieve",
                                "attributes": [
                                    {
                                        "key": "openinference.span.kind",
                                        "value": {"stringValue": "RETRIEVER"},
                                    },
                                    {
                                        "key": "input.value",
                                        "value": {"stringValue": "delete my account"},
                                    },
                                    {
                                        "key": "retrieval.documents.0.document.id",
                                        "value": {"stringValue": "doc:newsletter"},
                                    },
                                    {
                                        "key": "retrieval.documents.1.document.id",
                                        "value": {"stringValue": "doc:gdpr-delete"},
                                    },
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }

    result = observations_from_otlp_payload(payload, query_secret="tenant-key")

    assert result.report.spans_seen == 1
    assert result.report.retrieval_spans_seen == 1
    assert result.report.observations_emitted == 1
    observation = result.observations[0]
    assert observation.trace_id == "5B8EFFF798038103D269B633813FC60C"
    assert observation.span_id == "EEE19B7EC3C1B174"
    assert observation.result_ids == ("doc:newsletter", "doc:gdpr-delete")
    assert observation.query_id.startswith("q:hmac-sha256:")
    assert observation.query_text is None


def test_raw_otlp_without_document_ids_is_reported_not_silently_accepted():
    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "abc",
                                "spanId": "def",
                                "attributes": [
                                    {"key": "openinference.span.kind", "value": {"stringValue": "RETRIEVER"}},
                                    {"key": "input.value", "value": {"stringValue": "hello"}},
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }

    result = observations_from_otlp_payload(payload)

    assert result.observations == []
    assert result.report.skipped_missing_document_ids == 1
