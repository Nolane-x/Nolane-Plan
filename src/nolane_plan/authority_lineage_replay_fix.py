from __future__ import annotations


def install_authority_lineage_replay_fix(kernel_cls) -> None:
    """Use revision-index registries while rebuilding Wave-7 sidecars on replay."""
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
    kernel_cls._wave7_authority_lineage_replay_fix_installed = True
