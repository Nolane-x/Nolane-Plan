from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .hashing import digest
from .lineage import LineageError
from .lineage_snapshot import LINEAGE_SNAPSHOT_SCHEMA
from .persistence import HashJournal, SnapshotStore
from .schedulability_codec import robust_preparedness_doc
from .types import AuthorizationError, ReplayError


def install_authority_lineage_patch(kernel_cls) -> None:
    """Harden Task-7 lineage closure across legacy restore and v7 suffix replay.

    This patch deliberately keeps pre-v7 snapshots readable. Exact derived
    sidecars are materialized only when a *new* authorization is evaluated;
    historical authority never becomes current merely because a sidecar can be
    reconstructed from current objects.
    """

    if getattr(kernel_cls, "_wave7_authority_lineage_patch_installed", False):
        return

    from . import authority_lineage_runtime as ar
    from . import compaction_runtime as compaction
    from . import lineage_recovery as lineage_recovery
    from . import lineage_snapshot as lineage_snapshot

    authority_open = kernel_cls.open
    original_assert_closure = ar._assert_authority_closure_current

    def has_sidecar(self, family: str, logical_id: str) -> bool:
        try:
            self.lineage.current(family, str(logical_id))
            return True
        except LineageError:
            return False

    def materialize_proof_sidecars(self, artifact_revision: str) -> None:
        manifest = self.proof_manifests.get(artifact_revision)
        support_set = self.support_sets.get(artifact_revision)
        if manifest is None or support_set is None:
            raise AuthorizationError("proof artifact has incomplete exact lineage")

        for source_id, _bound_revision in manifest.positive_revision_dependencies:
            ar._register_proof_source_lineage(self, source_id)

        envelope = self.proof_input_envelopes.get(manifest.input_envelope_revision)
        if envelope is None:
            raise AuthorizationError("proof manifest references missing input envelope")
        ar._register_proof_input_lineage(self, envelope)

        for query in manifest.query_domain_revisions:
            current_query = self.query_domains.latest(query.query_domain_id)
            ar._register_query_lineage(self, current_query)

        ar._register_manifest_lineage(self, manifest)
        for clause in support_set.clauses:
            for support_ref in clause.required_support_refs:
                node = self.support_nodes.get(support_ref)
                if node is None:
                    raise AuthorizationError("proof support set references missing support node")
                ar._register_support_node_lineage(self, node)
        ar._register_support_set_lineage(self, support_set)
        ar._refresh_proof_authority_lineage(self, artifact_revision)

    def proof_binding_fields(self, authorization_id: str) -> dict[str, str]:
        binding = self.proof_authorization_bindings.get(authorization_id)
        if not isinstance(binding, dict):
            return {}
        artifact_raw = binding.get("proof_artifact_revision")
        if not artifact_raw:
            # Wave-6 unit harnesses intentionally substitute a minimal delegate;
            # a noncanonical test-side binding is not promoted into exact v7
            # authority merely because the schedulability layer delegates to it.
            return {}
        artifact = str(artifact_raw)
        if not has_sidecar(self, "ProofAuthority", artifact):
            materialize_proof_sidecars(self, artifact)
        manifest = self.proof_manifests[artifact]
        source_rows = tuple(
            sorted(
                (
                    source_id,
                    ar._current_sidecar(self, "ProofSemanticSource", source_id),
                )
                for source_id, _ in manifest.positive_revision_dependencies
            )
        )
        return {
            "proof_lineage_revision": ar._current_sidecar(self, "ProofAuthority", artifact),
            "proof_manifest_lineage_revision": ar._current_sidecar(self, "ProofManifest", artifact),
            "proof_support_lineage_revision": ar._current_sidecar(self, "ProofSupportSet", artifact),
            "proof_source_lineage_digest": digest(source_rows),
        }

    def materialize_policy_sidecars(self, binding: dict[str, str]) -> None:
        required = (
            "policy_node_revision",
            "selection_record_id",
            "sufficiency_revision",
            "seal_revision",
            "executability_revision",
        )
        if any(not binding.get(key) for key in required):
            raise AuthorizationError("sealed policy binding is not an exact canonical bundle")
        node = self.policy_nodes[str(binding["policy_node_revision"])]
        selection = self.policy_selections[str(binding["selection_record_id"])]
        sufficiency = self.policy_sufficiency[str(binding["sufficiency_revision"])]
        seal = self.policy_seals[str(binding["seal_revision"])]
        executability = self.policy_executability[str(binding["executability_revision"])]
        epoch = self.policy_epochs[node.decision_epoch_ref]
        partition = self.policy_partitions[node.information_partition_revision]
        frontier = self.policy_frontiers[node.observation_frontier_revision]

        ar._register_policy_sidecar(
            self,
            family="PolicyObservationFrontier",
            logical_id=frontier.frontier_id,
            value=frontier,
            provenance="policy:observation-frontier:legacy-materialization",
        )
        ar._register_policy_sidecar(
            self,
            family="PolicyInformationPartition",
            logical_id=partition.logical_id,
            value=partition,
            provenance="policy:information-partition:legacy-materialization",
        )
        ar._register_decision_epoch_lineage(self, epoch)
        ar._register_policy_sidecar(
            self,
            family="PolicyNode",
            logical_id=node.policy_node_id,
            value=node,
            provenance="policy:node:legacy-materialization",
        )
        ar._register_policy_sidecar(
            self,
            family="PolicySelection",
            logical_id=selection.record_id,
            value=selection,
            provenance="policy:selection:legacy-materialization",
        )
        ar._register_policy_sidecar(
            self,
            family="DecisionSufficiency",
            logical_id=sufficiency.certificate_id,
            value=sufficiency,
            provenance="policy:sufficiency:legacy-materialization",
        )
        ar._register_policy_sidecar(
            self,
            family="PlanSeal",
            logical_id=seal.seal_id,
            value=seal,
            provenance="policy:seal:legacy-materialization",
        )
        ar._register_policy_sidecar(
            self,
            family="PolicyExecutability",
            logical_id=executability.assessment_id,
            value=executability,
            provenance="policy:executability:legacy-materialization",
        )

    def policy_binding_fields(self, authorization_id: str) -> dict[str, str]:
        binding = self.policy_authorization_bindings.get(authorization_id)
        if not isinstance(binding, dict):
            return {}
        required = {
            "policy_node_revision",
            "selection_record_id",
            "sufficiency_revision",
            "seal_revision",
            "executability_revision",
        }
        if not required.issubset(binding):
            return {}
        node = self.policy_nodes[str(binding["policy_node_revision"])]
        if not has_sidecar(self, "PolicyNode", node.policy_node_id):
            materialize_policy_sidecars(self, binding)
        return ar._policy_binding_fields_original(self, authorization_id)

    # Preserve the production implementation so the safe wrapper can delegate
    # after legacy/minimal-shape checks.
    ar._policy_binding_fields_original = ar._policy_binding_fields
    ar._proof_binding_fields = proof_binding_fields
    ar._policy_binding_fields = policy_binding_fields

    def assert_closure_current(self, authorization_id: str, base_assert) -> None:
        original_assert_closure(self, authorization_id, base_assert)
        closure = self.authority_lineage_closure_bindings.get(authorization_id)
        proof_binding = self.proof_authorization_bindings.get(authorization_id)
        if not isinstance(closure, dict) or not isinstance(proof_binding, dict):
            return
        artifact_raw = proof_binding.get("proof_artifact_revision")
        expected = closure.get("proof_source_lineage_digest")
        if not artifact_raw or not expected:
            return
        manifest = self.proof_manifests.get(str(artifact_raw))
        if manifest is None:
            raise AuthorizationError("proof authority closure references missing manifest")
        current = digest(
            tuple(
                sorted(
                    (
                        source_id,
                        ar._current_sidecar(self, "ProofSemanticSource", source_id),
                    )
                    for source_id, _ in manifest.positive_revision_dependencies
                )
            )
        )
        if current != expected:
            raise AuthorizationError("proof semantic-source lineage is stale")

    ar._assert_authority_closure_current = assert_closure_current

    # RobustPreparednessAssessment intentionally has no synthetic id/revision;
    # its canonical digest is the registry identity in Wave 6.
    def register_robust_preparedness(self, assessment):
        with self._writer_lock:
            key = assessment.canonical_digest
            if key in self.robust_preparedness_assessments:
                raise ValueError("robust preparedness assessment already exists")
            self.robust_preparedness_assessments[key] = assessment
            self._record(
                "schedulability.robust_preparedness_registered",
                robust_preparedness_doc(assessment),
            )
            ar._register_wave6_sidecar(
                self,
                family="RobustPreparedness",
                logical_id=key,
                value=assessment,
                provenance="schedulability:robust-preparedness",
            )
            return assessment

    kernel_cls.register_robust_preparedness_assessment = register_robust_preparedness

    previous_event_replay = ar._event_sidecar_replay

    def event_sidecar_replay(self, entry) -> None:
        if entry.event_type == "schedulability.robust_preparedness_registered":
            key = str(entry.payload["canonical_digest"])
            assessment = self.robust_preparedness_assessments.get(key)
            if assessment is None:
                raise ReplayError("robust preparedness replay lost canonical assessment")
            ar._register_wave6_sidecar(
                self,
                family="RobustPreparedness",
                logical_id=key,
                value=assessment,
                provenance="schedulability:robust-preparedness",
                created_sequence=entry.sequence,
            )
            return
        previous_event_replay(self, entry)

    ar._event_sidecar_replay = event_sidecar_replay
    kernel_cls._replay_authority_lineage_event = event_sidecar_replay

    def restore_authority_snapshot(kernel, raw_authority: Any) -> None:
        if isinstance(raw_authority, dict):
            ar._restore_state_payload(kernel, raw_authority)
            return
        # A v7 snapshot from before Task 7 is valid history, but it cannot gain
        # exact derived authority retroactively.
        for authorization_id in set(getattr(kernel, "proof_authorization_bindings", {})).union(
            getattr(kernel, "policy_authorization_bindings", {}),
            getattr(kernel, "schedulability_authorization_bindings", {}),
        ):
            kernel.migration_recheck_required_authorizations.add(authorization_id)

    @classmethod
    def open_exact(cls, root: Path):
        root = Path(root)
        state = SnapshotStore(root / "snapshot.json").load()
        if str(state.get("snapshot_schema", "")) != LINEAGE_SNAPSHOT_SCHEMA:
            return authority_open(root)

        journal = HashJournal(root / "journal.jsonl")
        journal.verify(raise_on_error=True)
        entries = journal.entries()
        prefix_length = lineage_snapshot._find_snapshot_prefix(
            entries, str(state.get("journal_head", ""))
        )
        kernel = lineage_snapshot._restore_base_v6_layers(cls, root, state)
        wave7 = state.get("lineage")
        if not isinstance(wave7, dict):
            raise ReplayError("v7 snapshot is missing durable lineage state")

        compaction_raw = copy.deepcopy(wave7.get("compaction") or {})
        sanitized = copy.deepcopy(wave7)
        sanitized["compaction"] = {"manifests": [], "archive": []}
        lineage_snapshot._restore_wave7_state(kernel, sanitized)
        compaction.restore_compaction_snapshot(kernel, compaction_raw)

        # Replay every suffix owner event through the existing correctness
        # reducer, then reconstruct its Task-7 sidecar at the same journal
        # sequence. This is the missing hook in the compaction open closure.
        for entry in entries[prefix_length:]:
            lineage_recovery._replay_entry(kernel, entry)
            kernel._replay_authority_lineage_event(entry)
        lineage_recovery._flush_pending_canonical(kernel)

        suffix_epochs = dict(kernel.decision_epoch_lineage_bindings)
        suffix_authority = dict(kernel.authority_lineage_closure_bindings)
        restore_authority_snapshot(kernel, wave7.get("authority_closure"))
        kernel.decision_epoch_lineage_bindings.update(suffix_epochs)
        kernel.authority_lineage_closure_bindings.update(suffix_authority)
        for authorization_id, closure in kernel.authority_lineage_closure_bindings.items():
            ar._apply_closure_to_layer_bindings(kernel, authorization_id, closure)
        return kernel

    kernel_cls.open = open_exact
    kernel_cls._wave7_authority_lineage_patch_installed = True
