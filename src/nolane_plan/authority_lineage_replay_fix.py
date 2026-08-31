from __future__ import annotations


def install_authority_lineage_replay_fix(kernel_cls) -> None:
    """Use exact revision registries and closure fields while rebuilding Wave-7 authority on replay."""
    if getattr(kernel_cls, "_wave7_authority_lineage_replay_fix_installed", False):
        return

    from . import authority_lineage_runtime as ar

    previous = kernel_cls._replay_authority_lineage_event

    def replay(self, entry) -> None:
        payload = dict(entry.payload)
        if entry.event_type == "schedulability.resource_registered":
            value = self.control_plane_resource_revisions[str(payload["revision_id"])]
            ar._register_wave6_sidecar(
                self,
                family="ControlPlaneResource",
                logical_id=value.resource_id,
                value=value,
                provenance="schedulability:resource",
                created_sequence=entry.sequence,
            )
            return
        if entry.event_type == "schedulability.job_registered":
            value = self.reaction_job_revisions[str(payload["revision_id"])]
            ar._register_wave6_sidecar(
                self,
                family="ReactionJob",
                logical_id=value.reaction_job_id,
                value=value,
                provenance="schedulability:reaction-job",
                created_sequence=entry.sequence,
            )
            return
        previous(self, entry)

    ar._event_sidecar_replay = replay
    kernel_cls._replay_authority_lineage_event = replay

    previous_apply = ar._apply_closure_to_layer_bindings

    def apply_closure_to_layer_bindings(self, authorization_id: str, closure: dict[str, str]) -> None:
        previous_apply(self, authorization_id, closure)
        proof_binding = getattr(self, "proof_authorization_bindings", {}).get(authorization_id)
        if isinstance(proof_binding, dict):
            proof_source_digest = closure.get("proof_source_lineage_digest")
            if proof_source_digest:
                proof_binding["proof_source_lineage_digest"] = proof_source_digest

    ar._apply_closure_to_layer_bindings = apply_closure_to_layer_bindings
    kernel_cls._wave7_authority_lineage_replay_fix_installed = True
