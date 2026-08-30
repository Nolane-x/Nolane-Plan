from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hashing import digest


class MigrationError(ValueError):
    """Raised when a semantic migration would guess, erase, or promote meaning."""


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise MigrationError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


class MigrationDisposition(str, Enum):
    PRESERVED_EXACTLY = "PRESERVED_EXACTLY"
    RECOMPUTED_FROM_CANONICAL_INPUTS = "RECOMPUTED_FROM_CANONICAL_INPUTS"
    INVALIDATED_REQUIRES_RECHECK = "INVALIDATED_REQUIRES_RECHECK"
    ESCALATED_TO_DEBT = "ESCALATED_TO_DEBT"
    ARCHIVED_READ_ONLY = "ARCHIVED_READ_ONLY"
    UNSUPPORTED_FAIL_CLOSED = "UNSUPPORTED_FAIL_CLOSED"

    @classmethod
    def parse(cls, value: str | "MigrationDisposition") -> "MigrationDisposition":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().upper())
        except ValueError as exc:
            raise MigrationError(f"unsupported migration disposition: {value}") from exc


@dataclass(frozen=True, slots=True)
class FieldMigrationDisposition:
    object_family: str
    field_path: str
    disposition: MigrationDisposition
    source_ref: str | None = None
    target_ref: str | None = None
    debt_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "object_family", _required("object_family", self.object_family))
        object.__setattr__(self, "field_path", _required("field_path", self.field_path))
        object.__setattr__(self, "disposition", MigrationDisposition.parse(self.disposition))
        if self.source_ref is not None:
            object.__setattr__(self, "source_ref", _required("source_ref", self.source_ref))
        if self.target_ref is not None:
            object.__setattr__(self, "target_ref", _required("target_ref", self.target_ref))
        if self.debt_ref is not None:
            object.__setattr__(self, "debt_ref", _required("debt_ref", self.debt_ref))

    @property
    def key(self) -> tuple[str, str]:
        return (self.object_family, self.field_path)

    def canonical_payload(self) -> dict[str, object]:
        return {
            "object_family": self.object_family,
            "field_path": self.field_path,
            "disposition": self.disposition.value,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "debt_ref": self.debt_ref,
        }


@dataclass(frozen=True, slots=True)
class IdentityMapping:
    object_family: str
    source_logical_id: str
    target_logical_id: str
    source_revision_id: str
    target_revision_id: str

    def __post_init__(self) -> None:
        for name in (
            "object_family",
            "source_logical_id",
            "target_logical_id",
            "source_revision_id",
            "target_revision_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))

    def canonical_payload(self) -> dict[str, str]:
        return {
            "object_family": self.object_family,
            "source_logical_id": self.source_logical_id,
            "target_logical_id": self.target_logical_id,
            "source_revision_id": self.source_revision_id,
            "target_revision_id": self.target_revision_id,
        }


@dataclass(frozen=True, slots=True)
class MigrationBridgeEvidence:
    evidence_ref: str
    source_schema_revision: str
    target_schema_revision: str
    transaction_ids: tuple[str, ...]
    verified: bool
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        evidence_ref: str,
        source_schema_revision: str,
        target_schema_revision: str,
        transaction_ids: Iterable[str],
        verified: bool,
    ) -> "MigrationBridgeEvidence":
        transactions = _canon(transaction_ids)
        if not transactions:
            raise MigrationError("migration bridge must bind at least one transaction")
        body = {
            "evidence_ref": _required("evidence_ref", evidence_ref),
            "source_schema_revision": _required("source_schema_revision", source_schema_revision),
            "target_schema_revision": _required("target_schema_revision", target_schema_revision),
            "transaction_ids": transactions,
            "verified": bool(verified),
        }
        return cls(
            evidence_ref=body["evidence_ref"],
            source_schema_revision=body["source_schema_revision"],
            target_schema_revision=body["target_schema_revision"],
            transaction_ids=transactions,
            verified=bool(verified),
            canonical_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class MigrationManifest:
    manifest_id: str
    source_schema_revision: str
    target_schema_revision: str
    target_schema_semantic_digest: str
    changed_correctness_fields: tuple[tuple[str, str], ...]
    field_dispositions: tuple[FieldMigrationDisposition, ...]
    identity_mappings: tuple[IdentityMapping, ...]
    checked_invariants: tuple[str, ...]
    revoked_certificate_refs: tuple[str, ...]
    revoked_authorization_refs: tuple[str, ...]
    new_debt_refs: tuple[str, ...]
    replay_fixture_digests: tuple[str, ...]
    rollback_procedure_ref: str
    backup_ref: str
    unsupported_legacy_cases: tuple[str, ...]
    external_effect_history_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        source_schema_revision: str,
        target_schema_revision: str,
        target_schema_semantic_digest: str,
        changed_correctness_fields: Iterable[tuple[str, str]],
        field_dispositions: Iterable[FieldMigrationDisposition],
        identity_mappings: Iterable[IdentityMapping],
        checked_invariants: Iterable[str],
        revoked_certificate_refs: Iterable[str],
        revoked_authorization_refs: Iterable[str],
        new_debt_refs: Iterable[str],
        replay_fixture_digests: Iterable[str],
        rollback_procedure_ref: str,
        backup_ref: str,
        unsupported_legacy_cases: Iterable[str],
        external_effect_history_refs: Iterable[str],
        provenance_refs: Iterable[str],
    ) -> "MigrationManifest":
        source = _required("source_schema_revision", source_schema_revision)
        target = _required("target_schema_revision", target_schema_revision)
        if source == target:
            raise MigrationError("source and target schema revisions must differ")

        changed: set[tuple[str, str]] = set()
        for family, field_path in changed_correctness_fields:
            changed.add((_required("changed object_family", family), _required("changed field_path", field_path)))
        changed_fields = tuple(sorted(changed))

        dispositions = tuple(sorted(tuple(field_dispositions), key=lambda row: row.key))
        disposition_by_key: dict[tuple[str, str], FieldMigrationDisposition] = {}
        for row in dispositions:
            if row.key in disposition_by_key:
                raise MigrationError(f"duplicate migration disposition for {row.key!r}")
            disposition_by_key[row.key] = row
        if set(disposition_by_key) != set(changed_fields):
            missing = sorted(set(changed_fields) - set(disposition_by_key))
            extra = sorted(set(disposition_by_key) - set(changed_fields))
            raise MigrationError(
                f"every changed correctness field needs exactly one disposition; missing={missing!r}, extra={extra!r}"
            )

        mappings = tuple(
            sorted(
                tuple(identity_mappings),
                key=lambda row: (
                    row.object_family,
                    row.source_logical_id,
                    row.target_logical_id,
                    row.source_revision_id,
                    row.target_revision_id,
                ),
            )
        )
        mapped_families = {mapping.object_family for mapping in mappings}
        for family, field_path in changed_fields:
            leaf = field_path.rsplit(".", 1)[-1]
            if leaf in {"logical_id", "revision_id"} and family not in mapped_families:
                raise MigrationError(
                    f"identity-changing field {family}.{field_path} requires explicit IdentityMapping"
                )

        debts = _canon(new_debt_refs)
        for row in dispositions:
            if row.disposition is MigrationDisposition.ESCALATED_TO_DEBT:
                if row.debt_ref is None:
                    raise MigrationError(f"{row.key!r} escalates to debt but has no debt_ref")
                if row.debt_ref not in debts:
                    raise MigrationError(f"migration debt {row.debt_ref!r} is not declared in new_debt_refs")

        checked = _canon(checked_invariants)
        revoked_certificates = _canon(revoked_certificate_refs)
        revoked_authorizations = _canon(revoked_authorization_refs)
        fixtures = _canon(replay_fixture_digests)
        unsupported = _canon(unsupported_legacy_cases)
        effect_history = _canon(external_effect_history_refs)
        provenance = _canon(provenance_refs)
        rollback = _required("rollback_procedure_ref", rollback_procedure_ref)
        backup = _required("backup_ref", backup_ref)
        target_semantic = _required("target_schema_semantic_digest", target_schema_semantic_digest)
        manifest = _required("manifest_id", manifest_id)

        body = {
            "manifest_id": manifest,
            "source_schema_revision": source,
            "target_schema_revision": target,
            "target_schema_semantic_digest": target_semantic,
            "changed_correctness_fields": changed_fields,
            "field_dispositions": tuple(row.canonical_payload() for row in dispositions),
            "identity_mappings": tuple(row.canonical_payload() for row in mappings),
            "checked_invariants": checked,
            "revoked_certificate_refs": revoked_certificates,
            "revoked_authorization_refs": revoked_authorizations,
            "new_debt_refs": debts,
            "replay_fixture_digests": fixtures,
            "rollback_procedure_ref": rollback,
            "backup_ref": backup,
            "unsupported_legacy_cases": unsupported,
            "external_effect_history_refs": effect_history,
            "provenance_refs": provenance,
        }
        return cls(
            manifest_id=manifest,
            source_schema_revision=source,
            target_schema_revision=target,
            target_schema_semantic_digest=target_semantic,
            changed_correctness_fields=changed_fields,
            field_dispositions=dispositions,
            identity_mappings=mappings,
            checked_invariants=checked,
            revoked_certificate_refs=revoked_certificates,
            revoked_authorization_refs=revoked_authorizations,
            new_debt_refs=debts,
            replay_fixture_digests=fixtures,
            rollback_procedure_ref=rollback,
            backup_ref=backup,
            unsupported_legacy_cases=unsupported,
            external_effect_history_refs=effect_history,
            provenance_refs=provenance,
            canonical_digest=digest(body),
        )

    def supports_legacy_case(self, case_ref: str) -> bool:
        return _required("legacy case", case_ref) not in self.unsupported_legacy_cases

    def canonical_payload(self) -> dict[str, object]:
        return {
            "manifest_id": self.manifest_id,
            "source_schema_revision": self.source_schema_revision,
            "target_schema_revision": self.target_schema_revision,
            "target_schema_semantic_digest": self.target_schema_semantic_digest,
            "changed_correctness_fields": self.changed_correctness_fields,
            "field_dispositions": tuple(row.canonical_payload() for row in self.field_dispositions),
            "identity_mappings": tuple(row.canonical_payload() for row in self.identity_mappings),
            "checked_invariants": self.checked_invariants,
            "revoked_certificate_refs": self.revoked_certificate_refs,
            "revoked_authorization_refs": self.revoked_authorization_refs,
            "new_debt_refs": self.new_debt_refs,
            "replay_fixture_digests": self.replay_fixture_digests,
            "rollback_procedure_ref": self.rollback_procedure_ref,
            "backup_ref": self.backup_ref,
            "unsupported_legacy_cases": self.unsupported_legacy_cases,
            "external_effect_history_refs": self.external_effect_history_refs,
            "provenance_refs": self.provenance_refs,
            "canonical_digest": self.canonical_digest,
        }


@dataclass(frozen=True, slots=True)
class MigrationResult:
    manifest_id: str
    source_schema_revision: str
    target_schema_revision: str
    invalidated_authorization_ids: tuple[str, ...]
    new_debt_refs: tuple[str, ...]
    bridge_evidence_ref: str | None
    root_switched_sequence: int
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        manifest_id: str,
        source_schema_revision: str,
        target_schema_revision: str,
        invalidated_authorization_ids: Iterable[str],
        new_debt_refs: Iterable[str],
        bridge_evidence_ref: str | None,
        root_switched_sequence: int,
    ) -> "MigrationResult":
        invalidated = _canon(invalidated_authorization_ids)
        debts = _canon(new_debt_refs)
        bridge = None if bridge_evidence_ref is None else _required("bridge_evidence_ref", bridge_evidence_ref)
        body = {
            "manifest_id": _required("manifest_id", manifest_id),
            "source_schema_revision": _required("source_schema_revision", source_schema_revision),
            "target_schema_revision": _required("target_schema_revision", target_schema_revision),
            "invalidated_authorization_ids": invalidated,
            "new_debt_refs": debts,
            "bridge_evidence_ref": bridge,
            "root_switched_sequence": int(root_switched_sequence),
        }
        return cls(
            manifest_id=body["manifest_id"],
            source_schema_revision=body["source_schema_revision"],
            target_schema_revision=body["target_schema_revision"],
            invalidated_authorization_ids=invalidated,
            new_debt_refs=debts,
            bridge_evidence_ref=bridge,
            root_switched_sequence=int(root_switched_sequence),
            canonical_digest=digest(body),
        )
