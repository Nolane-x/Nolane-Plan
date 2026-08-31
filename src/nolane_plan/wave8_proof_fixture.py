from __future__ import annotations

from pathlib import Path

from .actions import ActionIntent, AuthorityGrant
from .identity import PrincipalAttestation
from .proof_inputs import DependencyCaptureAssurance, ExternalReadPolicy, ProofInputEnvelopeRevision
from .support import SupportAlternativeSetRevision, SupportClause, SupportNode
from .types import RiskClass


def build_proof_authorized_kernel(seed: int, root: Path):
    """Build a deterministic proof-carrying authorization through public runtime APIs."""
    from . import PlanKernel

    seed_value = int(seed)
    principal = f"agent:wave8:{seed_value}"
    action_id = f"action:wave8-proof:{seed_value}"
    grant_id = f"grant:wave8-proof:{seed_value}"
    source_id = f"policy:wave8:{seed_value}"
    source_revision = f"policy:wave8:{seed_value}@1"
    artifact_revision = f"proof:wave8:{seed_value}@1"
    semantic_profile = f"semantic:wave8:{seed_value}@1"
    checker_trust = f"checker-trust:wave8:{seed_value}@1"
    normalizer = f"normalizer:wave8:{seed_value}@1"
    execution_profile = f"python:wave8:{seed_value}@1"

    kernel = PlanKernel.create(
        Path(root),
        f"wave8 proof-carrying mission {seed_value}",
        ("proof-carrying authorization remains exact",),
        ("no authority promotion",),
    )
    attestation = PrincipalAttestation.create(
        attestation_id=f"attestation:wave8:{seed_value}",
        canonical_principal_ref=principal,
        source="host-runtime",
        source_subject=f"subject:wave8:{seed_value}",
        revision=1,
        issued_at=1,
        valid_until=1000,
        assurance=0.95,
        session_ref=f"session:wave8:{seed_value}",
    )
    kernel.bind_principal(attestation, allowed_tags=set(), now=10)
    kernel.propose_action(ActionIntent(action_id, "deploy", RiskClass.CONSEQUENTIAL))
    kernel.add_grant(AuthorityGrant(grant_id, principal, frozenset({"deploy"})))
    kernel.register_semantic_source(
        source_id,
        revision_id=source_revision,
        value={"mode": "safe", "seed": seed_value},
        dependency_domains=(f"source:wave8:{seed_value}", f"proof:wave8:{seed_value}"),
    )
    kernel.register_proof_profile_refs(
        semantic_profile,
        checker_trust,
        normalizer,
        execution_profile,
    )
    query = kernel.create_proof_query_domain(
        query_domain_id=f"grants:wave8:{seed_value}",
        scope_revision=f"scope:wave8:{seed_value}@1",
        index_schema_revision="index:wave8@1",
        completeness_contract="complete-enumeration:wave8@1",
        filter_predicate_revision="conflict:wave8@1",
        alias_equivalence_regime="alias:wave8@1",
        visibility_permission_regime="view:wave8@1",
        mutation_impact_profile_revision="impact:wave8@1",
        query_snapshot_id=f"query-snapshot:wave8:{seed_value}:1",
        snapshot_complete=True,
        opaque=False,
        visibility_assurance=0.95,
    )
    envelope = ProofInputEnvelopeRevision.create(
        input_envelope_id=f"env:wave8:{seed_value}",
        revision_id=f"env:wave8:{seed_value}@1",
        procedure_kind="constraint-check",
        procedure_capability_revision="checker:wave8@1",
        explicit_input_revision_refs=(source_revision,),
        query_domain_revision_refs=(query.revision_id,),
        semantic_profile_refs=(semantic_profile,),
        execution_environment_profile_refs=(execution_profile,),
        external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
        created_from_decision_cut=kernel.current_cut().id,
        capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
        capture_mechanism_ref="runtime:wave8-proof-fence@1",
    )
    kernel.register_proof_input(envelope)
    kernel.capture_proof_manifest(
        manifest_id=f"manifest:wave8:{seed_value}",
        revision_id=f"manifest:wave8:{seed_value}@1",
        artifact_revision=artifact_revision,
        proof_obligation_revision=f"obligation:wave8:{seed_value}@1",
        producer_capability_revision="checker:wave8@1",
        input_envelope_revision=envelope.revision_id,
        positive_revision_dependencies={source_id: source_revision},
        dependency_domains=(f"source:wave8:{seed_value}", f"proof:wave8:{seed_value}"),
        query_domain_ids=(query.query_domain_id,),
        semantic_profile_dependencies=(semantic_profile,),
        trust_checker_normalizer_dependencies=(checker_trust, normalizer),
        execution_semantic_profile_dependencies=(execution_profile,),
        capture_gaps=(),
    )
    support_ref = f"evidence:wave8:{seed_value}@1"
    kernel.register_support_node(
        SupportNode(
            ref=support_ref,
            current=True,
            direct_grounding_roots=frozenset({f"root:host:wave8:{seed_value}"}),
            support_refs=(),
            scope="mission",
            assumption_basis=frozenset({"assumption:wave8@1"}),
            proof_kind="verification",
            validity_regime="runtime@1",
            context_tags=frozenset({"prod"}),
        )
    )
    kernel.register_support_set(
        SupportAlternativeSetRevision.create(
            support_set_id=f"support:wave8:{seed_value}",
            revision_id=f"support:wave8:{seed_value}@1",
            subject_artifact_revision=artifact_revision,
            clauses=(
                SupportClause(
                    f"clause:wave8:{seed_value}@1",
                    (support_ref,),
                    "mission",
                    frozenset({"assumption:wave8@1"}),
                    "verification",
                    frozenset(),
                    "runtime@1",
                    frozenset({"prod"}),
                    1,
                ),
            ),
            scope="mission",
            assumption_context_rules=("prod",),
            proof_kind="verification",
            grounding_policy="accepted-roots-only",
            support_evaluation_profile="bounded-dnf@1",
            created_sequence=kernel.writer_sequence,
        )
    )
    authorization = kernel.authorize_proof_carrying(
        action_id,
        principal,
        (grant_id,),
        now=50,
        proof_artifact_revision=artifact_revision,
        active_context={"prod"},
    )
    return kernel, authorization, principal, artifact_revision
