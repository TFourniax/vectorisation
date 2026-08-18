from datetime import datetime, timezone

from semantic_atlas.link_io import link_result_to_dict, resolve_link_payload


def test_json_payload_resolves_only_evidence_bound_candidate():
    payload = {
        "slots": [
            {
                "slot_id": "model",
                "kind": "model",
                "baseline_component_id": "old",
                "contract_digest": "contract",
                "required_capabilities": ["json"],
                "minimum_probe_coverage": 1.0,
            }
        ],
        "offers": [
            {
                "component_id": "cheap",
                "kind": "model",
                "version": "1",
                "provider": "a",
                "unit_cost": 0.1,
                "p95_latency_ms": 100,
                "capabilities": ["json"],
            },
            {
                "component_id": "proven",
                "kind": "model",
                "version": "1",
                "provider": "b",
                "unit_cost": 0.2,
                "p95_latency_ms": 100,
                "capabilities": ["json"],
            },
        ],
        "certificates": [
            {
                "baseline_component_id": "old",
                "candidate_component_id": "proven",
                "contract_digest": "contract",
                "evidence_digest": "evidence",
                "verdict": "compatible",
                "probe_coverage": 1.0,
                "issuer": "ci",
                "issued_at": "2026-08-01T00:00:00+00:00",
            }
        ],
    }

    result = resolve_link_payload(
        payload,
        at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )
    data = link_result_to_dict(result)

    assert data["plan"]["choices"][0]["component_id"] == "proven"
    assert data["plan"]["digest"] == result.plan.digest
    assert any(item["component_id"] == "cheap" for item in data["rejected"])
