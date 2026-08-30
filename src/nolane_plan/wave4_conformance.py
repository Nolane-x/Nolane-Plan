from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from .actions import ActionIntent, AuthorityGrant
from .freshness import FreshnessDomainLedger
from .identity import PrincipalAttestation
from .kernel import PlanKernel
from .proof_dependencies import ProofDependencyManifestRevision
from .proof_inputs import (
    DependencyCaptureAssurance,
    ExternalReadPolicy,
    ProofInputEnvelopeRevision,
    ProofInputError,
)
from .query_domain import QueryDomainLedger
from .semantic_barrier import MutationImpactProfileRevision
from .support import (
    ArtifactAuthorityAssessment,
    InvalidityCause,
    SupportAlternativeSetRevision,
    SupportClause,
    SupportEvaluator,
    SupportNode,
    SupportStatus,
)
from .types import AuthorizationError, RiskClass


def _raises(exc_type, fn: Callable[[], object]) -> bool:
    try:
        fn()
    except exc_type:
        return True
    return False


def _strong_envelope(*, cut: str = "cut@1") -> ProofInputEnvelopeRevision:
    return ProofInputEnvelopeRevision.create(
        input_envelope_id="env",
        revision_id="env@1",
        procedure_kind="verification",
        procedure_capability_revision="checker@1",
        explicit_input_revision_refs=("policy@1",),
        semantic_profile_refs=("semantic@1",),
        execution_environment_profile_refs=("python@3.13",),
        external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
        created_from_decision_cut=cut,
        capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
    )


def _query_ledger() -> tuple[QueryDomainLedger, object]:
    ledger = QueryDomainLedger()
    revision = ledger.create(
        query_domain_id="domain",
        scope_revision="scope@1",
        index_schema_revision="index@1",
        completeness_contract="complete@1",
        filter_predicate_revision="predicate@1",
        alias_equivalence_regime="alias@1",
        visibility_permission_regime="visibility@1",
        mutation_impact_profile_revision="impact@1",
        query_snapshot_id="snapshot@1",
        snapshot_complete=True,
        opaque=False,
        visibility_assurance=0.95,
        created_sequence=1,
    )
    return ledger, revision


def _manifest(freshness: FreshnessDomainLedger, query_revision) -> ProofDependencyManifestRevision:
    freshness.ensure("source:policy")
    return ProofDependencyManifestRevision.capture(
        freshness,
        manifest_id="manifest",
        revision_id="manifest@1",
        artifact_revision="proof@1",
        proof_obligation_revision="obligation@1",
        producer_capability_revision="checker@1",
        input_envelope=_strong_envelope(),
        positive_revision_dependencies={"policy": "policy@1"},
        dependency_domains=("source:policy",),
        query_domain_revisions=(query_revision,),
        semantic_profile_dependencies=("semantic@1",),
        execution_semantic_profile_dependencies=("python@3.13",),
        created_sequence=1,
        evaluated_at_cut="cut@1",
    )


def _support_set(*clauses: SupportClause) -> SupportAlternativeSetRevision:
    return SupportAlternativeSetRevision.create(
        support_set_id="support",
        revision_id="support@1",
        subject_artifact_revision="proof@1",
        clauses=clauses,
        scope="mission",
        assumption_context_rules=("prod",),
        proof_kind="verification",
        grounding_policy="accepted-roots-only",
        support_evaluation_profile="bounded-dnf@1",
        created_sequence=1,
    )


def _node(ref: str, *, current: bool = True, roots=frozenset({"root:a"}), support_refs=()) -> SupportNode:
    return SupportNode(
        ref=ref,
        current=current,
        direct_grounding_roots=frozenset(roots),
        support_refs=tuple(support_refs),
        scope="mission",
        assumption_basis=frozenset({"assumption@1"}),
        proof_kind="verification",
        validity_regime="runtime@1",
        context_tags=frozenset({"prod"}),
    )


def _clause(clause_id: str, refs: tuple[str, ...], *, minimum_roots: int = 1) -> SupportClause:
    return SupportClause(
        clause_id,
        refs,
        "mission",
        frozenset({"assumption@1"}),
        "verification",
        frozenset(),
        "runtime@1",
        frozenset({"prod"}),
        minimum_roots,
    )


def _self_report_is_not_strong() -> bool:
    env = ProofInputEnvelopeRevision.create(
        input_envelope_id="env",
        revision_id="env@self",
        procedure_kind="verification",
        procedure_capability_revision="checker@1",
        external_read_policy=ExternalReadPolicy.ALLOW_OPAQUE,
        created_from_decision_cut="cut@1",
        capture_assurance=DependencyCaptureAssurance.SELF_REPORTED_DECLARED,
    )
    return not env.strong_dependency_complete and _raises(ProofInputError, env.require_strong_capture)


def _hidden_read_is_rejected() -> bool:
    env = _strong_envelope()
    return _raises(ProofInputError, lambda: env.assert_observed_reads_captured(("policy@1", "hidden@9")))


def _incomplete_query_cannot_prove_absence() -> bool:
    ledger, revision = _query_ledger()
    incomplete = ledger.revise("domain", snapshot_complete=False, query_snapshot_id="snapshot@2", created_sequence=2)
    return not ledger.can_prove_absence(incomplete, returned_match_count=0, minimum_assurance=0.8)


def _new_member_stales_absence() -> bool:
    ledger, revision = _query_ledger()
    ledger.advance_membership("domain", query_snapshot_id="snapshot@2", created_sequence=2)
    return not ledger.current(revision) and not ledger.can_prove_absence(revision, returned_match_count=0, minimum_assurance=0.8)


def _member_predicate_mutation_stales_absence() -> bool:
    ledger, revision = _query_ledger()
    changed = ledger.record_member_mutation(
        "domain", predicate_result_may_change=True, query_snapshot_id="snapshot@2", created_sequence=2
    )
    return (
        changed.membership_generation == revision.membership_generation
        and changed.result_sensitivity_generation == revision.result_sensitivity_generation + 1
        and not ledger.current(revision)
    )


def _generation_drift_stales_manifest() -> bool:
    freshness = FreshnessDomainLedger()
    queries, query = _query_ledger()
    manifest = _manifest(freshness, query)
    freshness.bump("source:policy")
    return not manifest.strong_reuse_eligible(
        freshness=freshness,
        exact_current_revisions={"policy": "policy@1"},
        query_domains=queries,
        current_trust_profile_refs={"semantic@1", "python@3.13"},
        minimum_query_assurance=0.8,
    )


def _one_surviving_alternative_supports() -> bool:
    support = _support_set(_clause("a", ("e1",)), _clause("b", ("e2",)))
    assessment = SupportEvaluator.evaluate(
        support,
        {"e1": _node("e1", current=False), "e2": _node("e2", roots=frozenset({"root:b"}))},
        active_context={"prod"},
        evaluated_at_cut="cut@1",
        generation=1,
    )
    return assessment.status == SupportStatus.SUPPORTED and assessment.surviving_clause_refs == ("b",)


def _conjunctive_support_requires_every_leaf() -> bool:
    support = _support_set(_clause("all", ("e1", "e2")))
    assessment = SupportEvaluator.evaluate(
        support,
        {"e1": _node("e1"), "e2": _node("e2", current=False)},
        active_context={"prod"},
        evaluated_at_cut="cut@1",
        generation=1,
    )
    return assessment.status == SupportStatus.UNSUPPORTED


def _empty_clause_has_no_authority() -> bool:
    assessment = SupportEvaluator.evaluate(
        _support_set(_clause("empty", ())),
        {},
        active_context={"prod"},
        evaluated_at_cut="cut@1",
        generation=1,
    )
    return assessment.status == SupportStatus.UNSUPPORTED


def _circular_support_is_not_grounding() -> bool:
    assessment = SupportEvaluator.evaluate(
        _support_set(_clause("cycle", ("a",))),
        {
            "a": _node("a", roots=frozenset(), support_refs=("b",)),
            "b": _node("b", roots=frozenset(), support_refs=("a",)),
        },
        active_context={"prod"},
        evaluated_at_cut="cut@1",
        generation=1,
    )
    return assessment.status == SupportStatus.UNSUPPORTED


def _blocking_invalidity_beats_positive_support() -> bool:
    support = SupportEvaluator.evaluate(
        _support_set(_clause("ok", ("e",))),
        {"e": _node("e")},
        active_context={"prod"},
        evaluated_at_cut="cut@1",
        generation=1,
    )
    authority = ArtifactAuthorityAssessment(
        support,
        (InvalidityCause("revoked", "VERIFIER_REVOKED", True, True),),
    )
    return support.status == SupportStatus.SUPPORTED and not authority.current_usable


def _attestation() -> PrincipalAttestation:
    return PrincipalAttestation.create(
        attestation_id="identity-a",
        canonical_principal_ref="agent:a",
        source="host-runtime",
        source_subject="subject-a",
        revision=1,
        issued_at=1,
        valid_until=1000,
        assurance=0.95,
        session_ref="session-a",
    )


def _install_kernel_proof(k: PlanKernel) -> None:
    k.bind_principal(_attestation(), allowed_tags=set(), now=10)
    k.propose_action(ActionIntent("act", "deploy", RiskClass.CONSEQUENTIAL))
    k.add_grant(AuthorityGrant("grant", "agent:a", frozenset({"deploy"})))
    k.register_semantic_source(
        "policy", revision_id="policy@1", value={"mode": "safe"}, dependency_domains=("source:policy",)
    )
    k.register_proof_profile_refs("semantic@1", "python@3.13")
    query = k.create_proof_query_domain(
        query_domain_id="domain",
        scope_revision="scope@1",
        index_schema_revision="index@1",
        completeness_contract="complete@1",
        filter_predicate_revision="predicate@1",
        alias_equivalence_regime="alias@1",
        visibility_permission_regime="visibility@1",
        mutation_impact_profile_revision="impact@1",
        query_snapshot_id="snapshot@1",
        snapshot_complete=True,
        opaque=False,
        visibility_assurance=0.95,
    )
    env = ProofInputEnvelopeRevision.create(
        input_envelope_id="env",
        revision_id="env@kernel",
        procedure_kind="verification",
        procedure_capability_revision="checker@1",
        explicit_input_revision_refs=("policy@1",),
        query_domain_revision_refs=(query.revision_id,),
        semantic_profile_refs=("semantic@1",),
        execution_environment_profile_refs=("python@3.13",),
        external_read_policy=ExternalReadPolicy.DENY_UNDECLARED,
        created_from_decision_cut=k.current_cut().id,
        capture_assurance=DependencyCaptureAssurance.FULL_ENVELOPE_ENFORCED,
    )
    k.register_proof_input(env)
    k.capture_proof_manifest(
        manifest_id="manifest",
        revision_id="manifest@1",
        artifact_revision="proof@1",
        proof_obligation_revision="obligation@1",
        producer_capability_revision="checker@1",
        input_envelope_revision=env.revision_id,
        positive_revision_dependencies={"policy": "policy@1"},
        dependency_domains=("source:policy",),
        query_domain_ids=("domain",),
        semantic_profile_dependencies=("semantic@1",),
        execution_semantic_profile_dependencies=("python@3.13",),
    )
    k.register_support_node(_node("evidence@1"))
    k.register_support_set(_support_set(_clause("supported", ("evidence@1",))))


def _semantic_mutation_blocks_kernel_authority() -> bool:
    with tempfile.TemporaryDirectory() as td:
        k = PlanKernel.create(Path(td), "wave4 semantic mutation")
        _install_kernel_proof(k)
        k.mutate_semantic_source(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "changed"},
            impact_profile=MutationImpactProfileRevision("impact@2", "policy", ("source:policy",), True, ()),
        )
        return _raises(
            AuthorizationError,
            lambda: k.authorize_proof_carrying(
                "act", "agent:a", ("grant",), now=50,
                proof_artifact_revision="proof@1", active_context={"prod"}
            ),
        )


def _query_drift_blocks_kernel_authority() -> bool:
    with tempfile.TemporaryDirectory() as td:
        k = PlanKernel.create(Path(td), "wave4 query drift")
        _install_kernel_proof(k)
        k.advance_proof_query_membership("domain", query_snapshot_id="snapshot@2")
        return _raises(
            AuthorizationError,
            lambda: k.authorize_proof_carrying(
                "act", "agent:a", ("grant",), now=50,
                proof_artifact_revision="proof@1", active_context={"prod"}
            ),
        )


def _stale_proof_stays_stale_after_restart() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        k = PlanKernel.create(root, "wave4 replay stale")
        _install_kernel_proof(k)
        k.mutate_semantic_source(
            "policy",
            new_revision_id="policy@2",
            new_value={"mode": "changed"},
            impact_profile=MutationImpactProfileRevision("impact@2", "policy", ("source:policy",), True, ()),
        )
        k.save_snapshot()
        reopened = PlanKernel.open(root)
        return (
            reopened.semantic_barrier.read_source("policy").revision_id == "policy@2"
            and _raises(
                AuthorizationError,
                lambda: reopened.evaluate_proof_authority("proof@1", active_context={"prod"}),
            )
        )


_CASES: tuple[tuple[str, Callable[[], bool]], ...] = (
    ("self_report_not_strong_capture", _self_report_is_not_strong),
    ("hidden_read_rejected", _hidden_read_is_rejected),
    ("incomplete_query_no_absence", _incomplete_query_cannot_prove_absence),
    ("new_member_stales_absence", _new_member_stales_absence),
    ("predicate_mutation_stales_absence", _member_predicate_mutation_stales_absence),
    ("generation_drift_stales_manifest", _generation_drift_stales_manifest),
    ("or_alternative_survival", _one_surviving_alternative_supports),
    ("and_clause_requires_all_leaves", _conjunctive_support_requires_every_leaf),
    ("empty_clause_no_authority", _empty_clause_has_no_authority),
    ("circular_support_not_grounded", _circular_support_is_not_grounding),
    ("blocking_invalidity_beats_support", _blocking_invalidity_beats_positive_support),
    ("semantic_mutation_blocks_authority", _semantic_mutation_blocks_kernel_authority),
    ("query_drift_blocks_authority", _query_drift_blocks_kernel_authority),
    ("stale_authority_not_resurrected", _stale_proof_stays_stale_after_restart),
)


def run_wave4_conformance() -> dict:
    rows: list[dict[str, object]] = []
    for name, fn in _CASES:
        try:
            passed = bool(fn())
            detail = "defense held" if passed else "unsafe shortcut was not rejected"
        except Exception as exc:
            passed = False
            detail = f"unexpected {type(exc).__name__}: {exc}"
        rows.append({"name": name, "passed": passed, "detail": detail})
    failed = [row["name"] for row in rows if not row["passed"]]
    return {
        "ok": not failed,
        "total": len(rows),
        "passed": len(rows) - len(failed),
        "failed": failed,
        "cases": rows,
    }


def main() -> int:
    import json

    report = run_wave4_conformance()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
