from __future__ import annotations

from typing import Any


def _mission_doc(mission) -> dict[str, Any]:
    return {
        "version": mission.version,
        "objective": mission.objective,
        "success_conditions": list(mission.success_conditions),
        "hard_constraints": list(mission.hard_constraints),
        "soft_preferences": list(mission.soft_preferences),
        "anti_goals": list(mission.anti_goals),
        "risk_budget": mission.risk_budget,
    }


def _action_doc(action) -> dict[str, Any]:
    return {
        "id": action.id,
        "family": action.family,
        "risk_class": action.risk_class.value,
        "parameters": [list(pair) for pair in action.parameters],
        "preconditions": list(action.preconditions),
        "required_capabilities": list(action.required_capabilities),
        "idempotent": action.idempotent,
        "executor_sensitive": action.executor_sensitive,
    }


def _grant_doc(grant) -> dict[str, Any]:
    return {
        "id": grant.id,
        "principal_ref": grant.principal_ref,
        "scopes": sorted(grant.scopes),
        "expires_at": grant.expires_at,
        "revoked": grant.revoked,
        "risk_classes": sorted(item.value for item in grant.risk_classes),
    }


def _cut_doc(cut) -> dict[str, Any]:
    return {
        "id": cut.id,
        "revision": cut.revision,
        "commit_frontier_sequence": cut.commit_frontier_sequence,
        "mission_revision": cut.mission_revision,
        "canonical_state_revision": cut.canonical_state_revision,
        "strategic_location_revision": cut.strategic_location_revision,
        "source_generations": [list(pair) for pair in cut.source_generations],
    }


def _enrich(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    doc = dict(payload)
    if event_type in {"mission.created", "mission.revised"}:
        doc["mission"] = _mission_doc(self.mission.current)
    elif event_type in {"principal.registered", "principal.access_changed"}:
        profile = self.principals.profile(str(doc["principal_ref"]))
        doc["profile"] = {
            "principal_ref": profile.principal_ref,
            "allowed_tags": sorted(profile.allowed_tags),
            "revision": profile.revision,
        }
    elif event_type == "information.published":
        item = self.information_items[str(doc["item_id"])]
        doc["item"] = {
            "id": item.id,
            "payload": item.payload,
            "tags": sorted(item.tags),
            "visible_at": item.visible_at,
            "valid_until": item.valid_until,
            "provenance": item.provenance,
            "assurance": item.assurance,
        }
    elif event_type == "evidence.added":
        record = self.evidence.records[str(doc["evidence_id"])]
        doc["record"] = {
            "id": record.id,
            "claim": record.claim,
            "polarity": record.polarity.value,
            "source_id": record.source_id,
            "lineage_root": record.lineage_root,
            "observed_at": record.observed_at,
            "valid_until": record.valid_until,
            "assurance": record.assurance,
            "revoked": record.revoked,
            "revocation_reason": record.revocation_reason,
        }
    elif event_type == "future.family_added":
        family = self.future.families[str(doc["family_id"])]
        doc["family"] = {
            "id": family.id,
            "predicate": family.predicate,
            "probability": family.probability,
            "support": family.support,
            "assumptions": list(family.assumptions),
            "impact": family.impact,
            "residual": family.residual,
        }
    elif event_type == "obligation.added":
        obligation = self.obligations.get(str(doc["obligation_id"]))
        doc["obligation"] = {
            "id": obligation.id,
            "condition": obligation.condition,
            "deadline": obligation.deadline,
            "required_capability": obligation.required_capability,
            "hard": obligation.hard,
            "status": obligation.status.value,
            "lineage": list(obligation.lineage),
        }
    elif event_type == "action.proposed":
        doc["action"] = _action_doc(self.actions[str(doc["action_id"])])
    elif event_type == "authority.grant_added":
        doc["grant"] = _grant_doc(self.grants[str(doc["grant_id"])])
    elif event_type == "adapter.registered":
        profile = self.adapters[str(doc["adapter_id"])]
        doc["adapter"] = {
            "adapter_id": profile.adapter_id,
            "revision": profile.revision,
            "principal_attestation": profile.principal_attestation,
            "dispatch_fence": profile.dispatch_fence,
            "postcondition_assurance": profile.postcondition_assurance,
            "capability_digest": profile.capability_digest,
        }
    elif event_type == "region.registered":
        region = next(row for row in self.regions if row.id == str(doc["region_id"]))
        doc["region"] = {
            "id": region.id,
            "required_facts": region.required_facts,
            "decision_signature": region.decision_signature,
        }
    elif event_type == "resource.reserved":
        doc["reservation_count"] = len(self.reservations.commitments)
    elif event_type == "capsule.compiled":
        capsule = self.capsules[str(doc["capsule_id"])]
        doc["capsule"] = {
            "id": capsule.id,
            "recipient_principal_ref": capsule.recipient_principal_ref,
            "information_partition_digest": capsule.information_partition_digest,
            "information_access_profile_revision": capsule.information_access_profile_revision,
            "plan_snapshot_version": capsule.plan_snapshot_version,
            "mission_version": capsule.mission_version,
            "canonical_version": capsule.canonical_version,
            "evidence_watermark": capsule.evidence_watermark,
            "decision_time": capsule.decision_time,
            "item_ids": list(capsule.item_ids),
            "action_ids": list(capsule.action_ids),
            "dependency_digest": capsule.dependency_digest,
            "expires_at": capsule.expires_at,
            "decision_cut_id": capsule.decision_cut_id,
        }
        cut = self.decision_cuts.get(capsule.decision_cut_id)
        doc["decision_cut"] = _cut_doc(cut)
        artifact = self.artifacts.get(capsule.id)
        doc["artifact"] = {
            "id": artifact.id,
            "kind": artifact.kind,
            "produced_sequence": artifact.produced_sequence,
            "dependency_generations": [list(pair) for pair in artifact.dependency_stamp.generations],
            "decision_cut_id": artifact.decision_cut_id,
        }
    elif event_type == "action.authorized":
        authorization = self.authorizations[str(doc["authorization_id"])]
        tx = self.transaction_for_authorization(authorization.id)
        doc["authorization"] = {
            "id": authorization.id,
            "action_id": authorization.action_id,
            "action_family": authorization.action_family,
            "acting_principal_ref": authorization.acting_principal_ref,
            "grant_refs": list(authorization.grant_refs),
            "mission_version": authorization.mission_version,
            "canonical_version": authorization.canonical_version,
            "issued_at": authorization.issued_at,
            "expires_at": authorization.expires_at,
            "decision_cut_id": authorization.decision_cut_id,
            "capsule_id": authorization.capsule_id,
            "adapter_id": authorization.adapter_id,
            "adapter_revision": authorization.adapter_revision,
        }
        if authorization.decision_cut_id:
            doc["decision_cut"] = _cut_doc(self.decision_cuts.get(authorization.decision_cut_id))
        doc["transaction"] = {
            "id": tx.id,
            "action_id": tx.action_id,
            "authorization_id": tx.authorization_id,
            "principal_ref": tx.principal_ref,
            "idempotent": tx.idempotent,
            "state": tx.state.value,
            "adapter_id": tx.adapter_id,
            "adapter_revision": tx.adapter_revision,
            "detail": tx.detail,
        }
    elif event_type == "action.outcome_observed":
        receipt = self.receipts[str(doc["receipt_id"])]
        doc["receipt"] = {
            "id": receipt.id,
            "action_id": receipt.action_id,
            "authorization_id": receipt.authorization_id,
            "executing_principal_ref": receipt.executing_principal_ref,
            "transport_ok": receipt.transport_ok,
            "postconditions_verified": receipt.postconditions_verified,
            "state_patch": receipt.state_patch,
            "observed_at": receipt.observed_at,
        }
    elif event_type == "state.relocated":
        location = self.strategic_location
        doc["location"] = {
            "status": location.status.value,
            "region_ids": list(location.region_ids),
            "decision_signatures": list(location.decision_signatures),
        }
    elif event_type == "recovery.model_class_uncertain":
        state = self.recovery.state
        doc["recovery"] = {
            "mode": state.mode.value,
            "reason": state.reason,
            "residual_weight": state.residual_weight,
            "generation": state.generation,
        }
    elif event_type == "completion.verified":
        report = self.completion_reports[str(doc["artifact_id"])]
        doc["report"] = {
            "complete": report.complete,
            "missing_success_conditions": list(report.missing_success_conditions),
            "open_hard_obligations": list(report.open_hard_obligations),
            "anti_goal_violations": list(report.anti_goal_violations),
            "artifact_id": report.artifact_id,
            "decision_cut_id": report.decision_cut_id,
        }
    elif event_type == "model.proposal_received":
        proposal_id = str(doc["proposal_id"])
        doc["proposal"] = self.model_proposals[proposal_id]

    # A single event must carry enough cross-cut metadata to restore exact current
    # generations even when the originating mutation used the internal `_bump`
    # helper and therefore emitted no separate freshness event.
    doc["_replay"] = {
        "plan_snapshot_version": self.plan_snapshot_version,
        "freshness_generations": dict(self.freshness.generations),
        "location_revision": self._location_revision,
        "evidence_generation": self.evidence.generation,
        "principal_partition_revision": self.principals._partition_revision,
        "decision_cut_revision": self.decision_cuts._revision,
    }
    return doc


def install_replay_payload_runtime(kernel_cls) -> None:
    """Enrich new journal events with exact reducer inputs without a second writer."""
    if getattr(kernel_cls, "_wave7_replay_payload_runtime_installed", False):
        return
    original_record = kernel_cls._record

    def _record(self, event_type: str, payload: dict[str, Any]):
        return original_record(self, event_type, _enrich(self, event_type, payload))

    kernel_cls._record = _record
    kernel_cls._wave7_replay_payload_runtime_installed = True
