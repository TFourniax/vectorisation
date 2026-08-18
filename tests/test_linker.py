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


def offer(
    component_id,
    kind=ComponentKind.MODEL,
    *,
    cost=1.0,
    latency=100.0,
    capabilities=("chat",),
    regions=("eu",),
):
    return ComponentOffer(
        component_id=component_id,
        kind=kind,
        version="1",
        provider="provider",
        unit_cost=cost,
        p95_latency_ms=latency,
        capabilities=frozenset(capabilities),
        regions=frozenset(regions),
    )


def certificate(
    baseline,
    candidate,
    contract="contract",
    *,
    verdict=CertificateVerdict.COMPATIBLE,
    coverage=1.0,
    issuer="trusted",
    expires_at=None,
):
    return CompatibilityCertificate(
        baseline_component_id=baseline,
        candidate_component_id=candidate,
        contract_digest=contract,
        evidence_digest=f"evidence:{candidate}:{contract}",
        verdict=verdict,
        probe_coverage=coverage,
        issuer=issuer,
        issued_at="2026-08-01T00:00:00+00:00",
        expires_at=expires_at,
        environment_digest="prod-eu",
    )


def policy(**kwargs):
    return LinkPolicy(environment_digest="prod-eu", **kwargs)


def test_cheapest_uncertified_component_is_never_selected():
    slot = SemanticSlot(
        "model",
        ComponentKind.MODEL,
        "baseline-model",
        "contract",
        required_capabilities=frozenset({"chat"}),
    )

    result = resolve_semantic_dependencies(
        [slot],
        [offer("cheap", cost=0.10), offer("proven", cost=0.50)],
        [certificate("baseline-model", "proven")],
        policy=policy(trusted_issuers=frozenset({"trusted"})),
        at=NOW,
    )

    assert result.plan is not None
    assert result.plan.choices[0].component_id == "proven"
    assert any(
        item.component_id == "cheap" and "missing-certificate" in item.reasons
        for item in result.rejected
    )


def test_expired_certificate_fails_closed():
    slot = SemanticSlot("model", ComponentKind.MODEL, "baseline-model", "contract")

    result = resolve_semantic_dependencies(
        [slot],
        [offer("candidate")],
        [
            certificate(
                "baseline-model",
                "candidate",
                expires_at="2026-08-10T00:00:00+00:00",
            )
        ],
        policy=policy(),
        at=NOW,
    )

    assert result.plan is None
    assert result.feasible_plan_count == 0


def test_slot_resource_constraints_are_enforced_before_optimization():
    slot = SemanticSlot(
        "model",
        ComponentKind.MODEL,
        "baseline-model",
        "contract",
        max_unit_cost=0.30,
    )

    result = resolve_semantic_dependencies(
        [slot],
        [offer("expensive", cost=0.40), offer("within-budget", cost=0.20)],
        [
            certificate("baseline-model", "expensive"),
            certificate("baseline-model", "within-budget"),
        ],
        policy=policy(),
        at=NOW,
    )

    assert result.plan is not None
    assert result.plan.choices[0].component_id == "within-budget"


def test_full_compatibility_beats_cheaper_conditional_candidate_by_policy():
    slot = SemanticSlot(
        "model",
        ComponentKind.MODEL,
        "baseline-model",
        "contract",
        allow_conditional=True,
    )

    result = resolve_semantic_dependencies(
        [slot],
        [offer("cheap-conditional", cost=0.10), offer("fully-proven", cost=0.50)],
        [
            certificate(
                "baseline-model",
                "cheap-conditional",
                verdict=CertificateVerdict.CONDITIONAL,
            ),
            certificate("baseline-model", "fully-proven"),
        ],
        policy=policy(conditional_penalty=10.0),
        at=NOW,
    )

    assert result.plan is not None
    assert result.plan.choices[0].component_id == "fully-proven"


def test_individually_compatible_components_still_require_joint_composition_evidence():
    slots = [
        SemanticSlot("model", ComponentKind.MODEL, "old-model", "model-contract"),
        SemanticSlot(
            "retriever",
            ComponentKind.RETRIEVER,
            "old-retriever",
            "retriever-contract",
        ),
    ]
    offers = [
        offer("model-cheap", cost=0.10),
        offer("model-joint", cost=0.30),
        offer("retriever-joint", ComponentKind.RETRIEVER, cost=0.10),
        offer("retriever-other", ComponentKind.RETRIEVER, cost=0.20),
    ]
    certificates = [
        certificate("old-model", "model-cheap", "model-contract"),
        certificate("old-model", "model-joint", "model-contract"),
        certificate("old-retriever", "retriever-joint", "retriever-contract"),
        certificate("old-retriever", "retriever-other", "retriever-contract"),
    ]
    requirement = CompositionRequirement(
        frozenset({"model", "retriever"}),
        "application-composition-contract",
    )
    joint_certificate = CompositionCertificate(
        members=frozenset({"model-joint", "retriever-joint"}),
        contract_digest="application-composition-contract",
        evidence_digest="joint-evidence",
        issuer="trusted",
        issued_at="2026-08-01T00:00:00+00:00",
        environment_digest="prod-eu",
    )

    result = resolve_semantic_dependencies(
        slots,
        offers,
        certificates,
        composition_requirements=[requirement],
        composition_certificates=[joint_certificate],
        policy=policy(),
        at=NOW,
    )

    assert result.plan is not None
    assert {choice.component_id for choice in result.plan.choices} == {
        "model-joint",
        "retriever-joint",
    }
    assert len(result.plan.composition_certificate_digests) == 1
