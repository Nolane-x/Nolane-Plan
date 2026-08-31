from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .destructive_compaction_runtime import (
    DestructiveCompactionObservation,
    _accept_observation,
)
from .execution_contract import (
    CompensationRecord,
    ExecutionContract,
    RemoteCancellationAcknowledgement,
    validate_remote_cancellation_acknowledgement,
)
from .hashing import digest
from .multiwriter_runtime import (
    AuthorizationAuthorityEpochBinding,
    MultiWriterCommitObservation,
    _accept_commit_observation,
    _accept_epoch_observation,
    _lease_from_payload,
    _lease_payload,
)
from .persistence import HashJournal, SnapshotStore
from .types import ReplayError


WAVE9_SNAPSHOT_SCHEMA = "nolane-plan-runtime-snapshot-v9"


def _execution_state(kernel) -> dict[str, object]:
    return {
        "contracts": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.execution_contracts.items())
        },
        "authorization_bindings": dict(
            sorted(kernel.authorization_execution_contract_bindings.items())
        ),
        "remote_cancellation_acknowledgements": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.remote_cancellation_acknowledgements.items())
        },
        "compensation_records": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.compensation_records.items())
        },
    }


def _destructive_compaction_state(kernel) -> dict[str, object]:
    return {
        "observations": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.destructive_compaction_observations.items())
        }
    }


def _multiwriter_state(kernel) -> dict[str, object]:
    latest = kernel.latest_observed_authority_epoch
    return {
        "observed_authority_epochs": {
            key: _lease_payload(value)
            for key, value in sorted(kernel.observed_authority_epochs.items())
        },
        "latest_epoch_digest": None if latest is None else latest.epoch.canonical_digest,
        "commit_observations": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.multiwriter_commit_observations.items())
        },
        "authorization_epoch_bindings": {
            key: value.canonical_payload()
            for key, value in sorted(kernel.authorization_authority_epoch_bindings.items())
        },
    }


def _wave9_state(kernel) -> dict[str, object]:
    body = {
        "execution": _execution_state(kernel),
        "destructive_compaction": _destructive_compaction_state(kernel),
        "multiwriter": _multiwriter_state(kernel),
    }
    return {**body, "canonical_digest": digest(body)}


def _validate_wave9_envelope(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ReplayError("v9 snapshot is missing Wave-9 correctness state")
    body = {key: value for key, value in raw.items() if key != "canonical_digest"}
    recorded = str(raw.get("canonical_digest", ""))
    if not recorded or digest(body) != recorded:
        raise ReplayError("Wave-9 snapshot internal canonical digest mismatch")
    for key in ("execution", "destructive_compaction", "multiwriter"):
        if not isinstance(body.get(key), dict):
            raise ReplayError(f"Wave-9 snapshot is missing {key} state")
    return body


def _restore_execution_state(kernel, raw: dict[str, Any]) -> None:
    contracts: dict[str, ExecutionContract] = {}
    for key, doc in sorted(dict(raw.get("contracts", {})).items()):
        try:
            contract = ExecutionContract.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 execution contract snapshot: {exc}") from exc
        expected_key = f"{contract.adapter_id}@{contract.adapter_revision}"
        if str(key) != expected_key:
            raise ReplayError("Wave-9 execution contract key/revision mismatch")
        profile = kernel.adapters.get(contract.adapter_id)
        if profile is None or profile.revision < contract.adapter_revision:
            raise ReplayError("Wave-9 execution contract lacks matching adapter history")
        contracts[expected_key] = contract
    kernel.execution_contracts = contracts

    bindings: dict[str, str] = {}
    for authorization_id, contract_digest in sorted(
        dict(raw.get("authorization_bindings", {})).items()
    ):
        auth_id = str(authorization_id)
        authorization = kernel.authorizations.get(auth_id)
        if authorization is None or authorization.adapter_id is None or authorization.adapter_revision is None:
            raise ReplayError("Wave-9 execution binding references invalid authorization")
        key = f"{authorization.adapter_id}@{authorization.adapter_revision}"
        contract = contracts.get(key)
        if contract is None or contract.canonical_digest != str(contract_digest):
            raise ReplayError("Wave-9 execution binding contract digest mismatch")
        bindings[auth_id] = contract.canonical_digest
    kernel.authorization_execution_contract_bindings = bindings

    acknowledgements: dict[str, RemoteCancellationAcknowledgement] = {}
    for key, doc in sorted(
        dict(raw.get("remote_cancellation_acknowledgements", {})).items()
    ):
        try:
            acknowledgement = RemoteCancellationAcknowledgement.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 cancellation acknowledgement snapshot: {exc}") from exc
        if acknowledgement.acknowledgement_id != str(key):
            raise ReplayError("Wave-9 cancellation acknowledgement key/id mismatch")
        authorization = kernel.authorizations.get(acknowledgement.authorization_id)
        if authorization is None:
            raise ReplayError("Wave-9 cancellation acknowledgement references unknown authorization")
        contract_key = f"{acknowledgement.adapter_id}@{acknowledgement.adapter_revision}"
        contract = contracts.get(contract_key)
        if contract is None:
            raise ReplayError("Wave-9 cancellation acknowledgement references unknown execution contract")
        try:
            tx = kernel.transaction_for_authorization(acknowledgement.authorization_id)
            validate_remote_cancellation_acknowledgement(
                acknowledgement,
                contract,
                transaction_id=tx.id,
                action_id=tx.action_id,
                authorization_id=acknowledgement.authorization_id,
                principal_ref=tx.principal_ref,
                authority_epoch=acknowledgement.authority_epoch,
            )
        except Exception as exc:
            raise ReplayError(f"Wave-9 cancellation acknowledgement is not self-consistent: {exc}") from exc
        acknowledgements[acknowledgement.acknowledgement_id] = acknowledgement
    kernel.remote_cancellation_acknowledgements = acknowledgements

    transaction_ids = {tx.id for tx in kernel.transactions.all()}
    compensations: dict[str, CompensationRecord] = {}
    for key, doc in sorted(dict(raw.get("compensation_records", {})).items()):
        try:
            record = CompensationRecord.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 compensation snapshot: {exc}") from exc
        if record.record_id != str(key):
            raise ReplayError("Wave-9 compensation key/id mismatch")
        if (
            record.original_transaction_id not in transaction_ids
            or record.compensation_transaction_id not in transaction_ids
            or record.compensation_authorization_id not in kernel.authorizations
        ):
            raise ReplayError("Wave-9 compensation references missing transaction or authorization")
        compensations[record.record_id] = record
    kernel.compensation_records = compensations


def _restore_destructive_compaction_state(kernel, raw: dict[str, Any]) -> None:
    kernel.destructive_compaction_observations = {}
    for key, doc in sorted(dict(raw.get("observations", {})).items()):
        try:
            observation = DestructiveCompactionObservation.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 destructive-compaction snapshot: {exc}") from exc
        if observation.compaction_id != str(key):
            raise ReplayError("Wave-9 destructive-compaction observation key/id mismatch")
        _accept_observation(kernel, observation, replay=True)


def _restore_multiwriter_state(kernel, raw: dict[str, Any]) -> None:
    kernel.observed_authority_epochs = {}
    kernel.latest_observed_authority_epoch = None
    kernel.multiwriter_commit_observations = {}
    kernel.authorization_authority_epoch_bindings = {}

    leases = []
    for key, doc in sorted(dict(raw.get("observed_authority_epochs", {})).items()):
        try:
            lease = _lease_from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 authority epoch snapshot: {exc}") from exc
        if lease.epoch.canonical_digest != str(key):
            raise ReplayError("Wave-9 observed authority epoch key/digest mismatch")
        leases.append(lease)
    for lease in sorted(leases, key=lambda value: value.epoch.epoch):
        _accept_epoch_observation(kernel, lease, replay=True)

    latest_digest = raw.get("latest_epoch_digest")
    latest = kernel.latest_observed_authority_epoch
    expected_latest = None if latest is None else latest.epoch.canonical_digest
    if latest_digest != expected_latest:
        raise ReplayError("Wave-9 latest authority epoch pointer mismatch")

    for key, doc in sorted(dict(raw.get("commit_observations", {})).items()):
        try:
            observation = MultiWriterCommitObservation.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 multi-writer commit snapshot: {exc}") from exc
        if observation.canonical_digest != str(key):
            raise ReplayError("Wave-9 multi-writer observation key/digest mismatch")
        _accept_commit_observation(kernel, observation, replay=True)

    for authorization_id, doc in sorted(
        dict(raw.get("authorization_epoch_bindings", {})).items()
    ):
        try:
            binding = AuthorizationAuthorityEpochBinding.from_payload(dict(doc))
        except Exception as exc:
            raise ReplayError(f"invalid Wave-9 authorization epoch snapshot: {exc}") from exc
        if binding.authorization_id != str(authorization_id):
            raise ReplayError("Wave-9 authorization epoch binding key/id mismatch")
        authorization = kernel.authorizations.get(binding.authorization_id)
        if authorization is None or authorization.acting_principal_ref != binding.acting_principal_ref:
            raise ReplayError("Wave-9 authorization epoch binding crosses authorization identity")
        if binding.authorization_id not in kernel.authorization_execution_contract_bindings:
            raise ReplayError("Wave-9 authorization epoch binding lacks execution-contract binding")
        lease = kernel.observed_authority_epochs.get(binding.epoch_digest)
        if lease is None:
            raise ReplayError("Wave-9 authorization epoch binding references unobserved epoch")
        if (
            lease.writer.canonical_digest != binding.writer_identity_digest
            or lease.writer.writer_id != binding.writer_id
            or lease.writer.principal_ref != binding.acting_principal_ref
            or lease.epoch.backend_id != binding.storage_backend_id
            or lease.epoch.backend_revision != binding.storage_backend_revision
            or lease.epoch.epoch != binding.epoch
        ):
            raise ReplayError("Wave-9 authorization epoch binding/lease mismatch")
        kernel.authorization_authority_epoch_bindings[binding.authorization_id] = binding


def _restore_wave9_state(kernel, raw: Any) -> None:
    body = _validate_wave9_envelope(raw)
    _restore_execution_state(kernel, dict(body["execution"]))
    _restore_destructive_compaction_state(kernel, dict(body["destructive_compaction"]))
    _restore_multiwriter_state(kernel, dict(body["multiwriter"]))


def install_wave9_snapshot(kernel_cls) -> None:
    """Persist Wave-9 correctness sidecars without serializing external stores."""
    if getattr(kernel_cls, "_wave9_snapshot_installed", False):
        return

    from . import authority_lineage_runtime as ar
    from . import compaction_runtime as compaction
    from . import lineage_recovery
    from . import lineage_snapshot

    base_snapshot_state = kernel_cls.snapshot_state
    base_open = kernel_cls.open

    def snapshot_state(self):
        state = dict(base_snapshot_state(self))
        state["snapshot_schema"] = WAVE9_SNAPSHOT_SCHEMA
        state["wave9"] = _wave9_state(self)
        return state

    def save_snapshot(self):
        with self._writer_lock:
            state = snapshot_state(self)
            self.snapshots.save(state)
            self._record(
                "snapshot.saved",
                {
                    "snapshot_schema": WAVE9_SNAPSHOT_SCHEMA,
                    "snapshot_digest": digest(state),
                    "bound_journal_head": state["journal_head"],
                },
            )
            return state

    @classmethod
    def open_wave9(cls, root: Path):
        root = Path(root)
        state = SnapshotStore(root / "snapshot.json").load()
        if str(state.get("snapshot_schema", "")) != WAVE9_SNAPSHOT_SCHEMA:
            return base_open(root)

        wave9_raw = state.get("wave9")
        _validate_wave9_envelope(wave9_raw)

        journal = HashJournal(root / "journal.jsonl")
        journal.verify(raise_on_error=True)
        entries = journal.entries()
        prefix_length = lineage_snapshot._find_snapshot_prefix(
            entries, str(state.get("journal_head", ""))
        )

        base_state = copy.deepcopy(state)
        base_state["snapshot_schema"] = lineage_snapshot.LINEAGE_SNAPSHOT_SCHEMA
        base_state.pop("wave9", None)
        kernel = lineage_snapshot._restore_base_v6_layers(cls, root, base_state)
        wave7 = base_state.get("lineage")
        if not isinstance(wave7, dict):
            raise ReplayError("v9 snapshot is missing durable Wave-7 lineage state")

        compaction_raw = copy.deepcopy(wave7.get("compaction") or {})
        sanitized = copy.deepcopy(wave7)
        sanitized["compaction"] = {"manifests": [], "archive": []}
        lineage_snapshot._restore_wave7_state(kernel, sanitized)
        compaction.restore_compaction_snapshot(kernel, compaction_raw)

        # Wave-9 pre-snapshot state must exist before suffix replay. In
        # particular an epoch-N+1 authorization binding may depend on an
        # execution-contract binding that was durable before the snapshot.
        _restore_wave9_state(kernel, wave9_raw)

        for entry in entries[prefix_length:]:
            lineage_recovery._replay_entry(kernel, entry)
            kernel._replay_authority_lineage_event(entry)
        lineage_recovery._flush_pending_canonical(kernel)

        # Preserve the exact Wave-7 authority-closure ordering used by the
        # hardened v7 open path: suffix authority is retained while the
        # pre-snapshot closure is restored and re-applied to layer bindings.
        suffix_epochs = dict(kernel.decision_epoch_lineage_bindings)
        suffix_authority = dict(kernel.authority_lineage_closure_bindings)
        raw_authority = wave7.get("authority_closure")
        if isinstance(raw_authority, dict):
            ar._restore_state_payload(kernel, raw_authority)
        else:
            for authorization_id in set(getattr(kernel, "proof_authorization_bindings", {})).union(
                getattr(kernel, "policy_authorization_bindings", {}),
                getattr(kernel, "schedulability_authorization_bindings", {}),
            ):
                kernel.migration_recheck_required_authorizations.add(authorization_id)
        kernel.decision_epoch_lineage_bindings.update(suffix_epochs)
        kernel.authority_lineage_closure_bindings.update(suffix_authority)
        for authorization_id, closure in kernel.authority_lineage_closure_bindings.items():
            ar._apply_closure_to_layer_bindings(kernel, authorization_id, closure)
        return kernel

    kernel_cls.snapshot_state = snapshot_state
    kernel_cls.save_snapshot = save_snapshot
    kernel_cls.open = open_wave9
    kernel_cls._wave9_snapshot_installed = True
