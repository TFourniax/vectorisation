"""Semantic ABI linker demo.

The cheapest advertised model is deliberately uncertified and therefore cannot
be selected. The cheapest individually certified model+retriever pair is also
rejected because there is no joint composition proof for that pair.
"""
from datetime import datetime, timezone

from semantic_atlas.linker import (
    CertificateVerdict,
    CompatibilityCertificate,
    ComponentKind,
    ComponentOffer,
    CompositionCertificate,
    CompositionRequirement,
    LinkPolicy,
    SemanticSlot,
    resolve_semantic_dependencies,
)

NOW = datetime(2026, 8, 18, tzinfo=timezone.utc)
ENV = "support-prod-eu-v7"

slots = (
    SemanticSlot(
        slot_id="reasoning-model",
        kind=ComponentKind.MODEL,
        baseline_component_id="model:frontier@stable",
        contract_digest="contract:support-meaning@7",
        required_capabilities=frozenset({"tool-use", "json"}),
        allowed_regions=frozenset({"eu"}),
        minimum_probe_coverage=1.0,
    ),
    SemanticSlot(
        slot_id="knowledge-retriever",
        kind=ComponentKind.RETRIEVER,
        baseline_component_id="retriever:bm25@stable",
        contract_digest="contract:support-retrieval@4",
        allowed_regions=frozenset({"eu"}),
        minimum_probe_coverage=1.0,
    ),
)

offers = (
    # Cheapest model, but it has no Semantic ABI certificate for this app.
    ComponentOffer(
        "model:cheap-uncertified@1",
        ComponentKind.MODEL,
        "1",
        "provider-a",
        0.08,
        180,
        frozenset({"tool-use", "json"}),
        frozenset({"eu"}),
    ),
    ComponentOffer(
        "model:small-proven@3",
        ComponentKind.MODEL,
        "3",
        "provider-b",
        0.15,
        210,
        frozenset({"tool-use", "json"}),
        frozenset({"eu"}),
    ),
    ComponentOffer(
        "model:joint-proven@2",
        ComponentKind.MODEL,
        "2",
        "provider-c",
        0.22,
        160,
        frozenset({"tool-use", "json"}),
        frozenset({"eu"}),
    ),
    ComponentOffer(
        "retriever:dense-cheap@1",
        ComponentKind.RETRIEVER,
        "1",
        "provider-d",
        0.02,
        45,
        regions=frozenset({"eu"}),
    ),
    ComponentOffer(
        "retriever:late-interaction@2",
        ComponentKind.RETRIEVER,
        "2",
        "provider-e",
        0.04,
        62,
        regions=frozenset({"eu"}),
    ),
)


def cert(baseline, candidate, contract):
    return CompatibilityCertificate(
        baseline_component_id=baseline,
        candidate_component_id=candidate,
        contract_digest=contract,
        evidence_digest=f"evidence:{candidate}",
        verdict=CertificateVerdict.COMPATIBLE,
        probe_coverage=1.0,
        issuer="semantic-abi-ci",
        issued_at="2026-08-18T07:00:00+00:00",
        expires_at="2026-09-18T07:00:00+00:00",
        environment_digest=ENV,
    )


certificates = (
    cert(
        "model:frontier@stable",
        "model:small-proven@3",
        "contract:support-meaning@7",
    ),
    cert(
        "model:frontier@stable",
        "model:joint-proven@2",
        "contract:support-meaning@7",
    ),
    cert(
        "retriever:bm25@stable",
        "retriever:dense-cheap@1",
        "contract:support-retrieval@4",
    ),
    cert(
        "retriever:bm25@stable",
        "retriever:late-interaction@2",
        "contract:support-retrieval@4",
    ),
)

# Individual certificates are insufficient here. We require evidence that the
# chosen model and retriever still satisfy the application's end-to-end contract
# when composed together.
composition_requirement = CompositionRequirement(
    frozenset({"reasoning-model", "knowledge-retriever"}),
    "contract:support-end-to-end@9",
)

composition_certificate = CompositionCertificate(
    members=frozenset(
        {"model:joint-proven@2", "retriever:late-interaction@2"}
    ),
    contract_digest="contract:support-end-to-end@9",
    evidence_digest="evidence:end-to-end:joint-proven+late-interaction",
    issuer="semantic-abi-ci",
    issued_at="2026-08-18T07:30:00+00:00",
    expires_at="2026-09-18T07:30:00+00:00",
    environment_digest=ENV,
)

result = resolve_semantic_dependencies(
    slots,
    offers,
    certificates,
    composition_requirements=(composition_requirement,),
    composition_certificates=(composition_certificate,),
    policy=LinkPolicy(
        cost_weight=1.0,
        latency_weight=0.001,
        trusted_issuers=frozenset({"semantic-abi-ci"}),
        environment_digest=ENV,
    ),
    at=NOW,
    raise_on_failure=True,
)

assert result.plan is not None
print("plan", result.plan.digest)
for choice in result.plan.choices:
    print(choice.slot_id, "->", choice.component_id, choice.verdict.value)
print("total unit cost", result.plan.total_unit_cost)
print("composition evidence", result.plan.composition_certificate_digests)
