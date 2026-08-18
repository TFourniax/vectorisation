from semantic_atlas.acquisition import PreferenceEvidence, RelevantSetEvidence
from semantic_atlas.telemetry import (
    RetrievalFeedback,
    evidence_from_observation,
    join_feedback,
    observation_from_openinference_span,
    stable_query_id,
)


def _retriever_span():
    return {
        "trace_id": "trace-1",
        "span_id": "span-1",
        "name": "retrieve",
        "attributes": {
            "openinference.span.kind": "RETRIEVER",
            "input.value": '{"query":"How do I delete my account?"}',
            "retrieval.documents": [
                {"document.id": "doc:newsletter", "document.score": 0.91},
                {"document.id": "doc:gdpr-delete", "document.score": 0.88},
                {"document.id": "doc:identity", "document.score": 0.80},
            ],
        },
    }


def test_openinference_observation_uses_stable_ids_and_does_not_retain_query_by_default():
    observation = observation_from_openinference_span(_retriever_span(), query_secret="tenant-secret")
    assert observation is not None
    assert observation.query_id.startswith("q:hmac-sha256:")
    assert observation.result_ids == ("doc:newsletter", "doc:gdpr-delete", "doc:identity")
    assert observation.query_text is None
    assert observation.trace_id == "trace-1"
    assert observation.span_id == "span-1"


def test_stable_query_id_is_deterministic_and_secret_scoped():
    a = stable_query_id("  delete   my account ", secret="tenant-a")
    b = stable_query_id("delete my account", secret="tenant-a")
    c = stable_query_id("delete my account", secret="tenant-b")
    assert a == b
    assert a != c


def test_retrieval_ranking_alone_emits_no_semantic_evidence():
    observation = observation_from_openinference_span(_retriever_span())
    assert observation is not None
    result = join_feedback([observation], [])
    assert result.evidence == []
    assert result.report.feedback_matched == 0


def test_feedback_only_compares_click_with_skipped_results_above_it():
    observation = observation_from_openinference_span(_retriever_span())
    assert observation is not None
    feedback = RetrievalFeedback(span_id="span-1", clicked=("doc:gdpr-delete",), event_id="click-1")
    evidence = evidence_from_observation(observation, feedback)
    preferences = [item for item in evidence if isinstance(item, PreferenceEvidence)]
    assert {(item.preferred, item.rejected) for item in preferences} == {("doc:gdpr-delete", "doc:newsletter")}


def test_accepted_sources_become_relevant_set_evidence_only_with_feedback():
    observation = observation_from_openinference_span(_retriever_span())
    assert observation is not None
    feedback = RetrievalFeedback(
        span_id="span-1",
        selected=("doc:gdpr-delete",),
        explicit_negative=("doc:newsletter",),
        accepted_sources=("doc:gdpr-delete", "doc:identity"),
        event_id="human-review-1",
    )
    evidence = evidence_from_observation(observation, feedback)
    assert any(
        isinstance(item, PreferenceEvidence)
        and item.preferred == "doc:gdpr-delete"
        and item.rejected == "doc:newsletter"
        for item in evidence
    )
    relevant = [item for item in evidence if isinstance(item, RelevantSetEvidence)]
    assert len(relevant) == 1
    assert relevant[0].relevant == ("doc:gdpr-delete", "doc:identity")


def test_flattened_openinference_document_ids_are_supported():
    span = {
        "context": {"trace_id": "t", "span_id": "s"},
        "attributes": {
            "openinference.span.kind": "RETRIEVER",
            "semantic_abi.query_id": "q:stable-business-id",
            "retrieval.documents.0.document.id": "doc:a",
            "retrieval.documents.0.document.score": 0.9,
            "retrieval.documents.1.document.id": "doc:b",
            "retrieval.documents.1.document.score": 0.8,
        },
    }
    observation = observation_from_openinference_span(span)
    assert observation is not None
    assert observation.query_id == "q:stable-business-id"
    assert observation.result_ids == ("doc:a", "doc:b")
