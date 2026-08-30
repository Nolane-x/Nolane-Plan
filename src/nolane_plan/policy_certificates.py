from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .hashing import digest


def _required(name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    return text


def _canon(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


class RecallLevel(str, Enum):
    RECALL_SUFFICIENT = "recall_sufficient"
    RECALL_INSUFFICIENT = "recall_insufficient"
    RECALL_UNKNOWN = "recall_unknown"


@dataclass(frozen=True, slots=True)
class DecisionHistorySignature:
    history_ref: str
    current_information_class: str
    current_action_semantics: str
    transition_signature: str
    observation_capability_signature: str
    obligation_signature: str
    resource_authority_signature: str
    risk_signature: str
    action_space_signature: str
    continuation_signature: str
    canonical_digest: str

    @classmethod
    def create(
        cls,
        *,
        history_ref: str,
        current_information_class: str,
        current_action_semantics: str,
        transition_signature: str,
        observation_capability_signature: str,
        obligation_signature: str,
        resource_authority_signature: str,
        risk_signature: str,
        action_space_signature: str,
        continuation_signature: str,
    ) -> "DecisionHistorySignature":
        body = {
            "history_ref": _required("history_ref", history_ref),
            "current_information_class": _required("current_information_class", current_information_class),
            "current_action_semantics": _required("current_action_semantics", current_action_semantics),
            "transition_signature": _required("transition_signature", transition_signature),
            "observation_capability_signature": _required("observation_capability_signature", observation_capability_signature),
            "obligation_signature": _required("obligation_signature", obligation_signature),
            "resource_authority_signature": _required("resource_authority_signature", resource_authority_signature),
            "risk_signature": _required("risk_signature", risk_signature),
            "action_space_signature": _required("action_space_signature", action_space_signature),
            "continuation_signature": _required("continuation_signature", continuation_signature),
        }
        return cls(**body, canonical_digest=digest(body))

    @property
    def recursive_decision_signature(self) -> tuple[str, ...]:
        return (
            self.current_information_class,
            self.current_action_semantics,
            self.transition_signature,
            self.observation_capability_signature,
            self.obligation_signature,
            self.resource_authority_signature,
            self.risk_signature,
            self.action_space_signature,
            self.continuation_signature,
        )


@dataclass(frozen=True, slots=True)
class RecallCounterexample:
    code: str
    alias_class_ref: str
    history_refs: tuple[str, ...]
    differing_dimensions: tuple[str, ...]
    detail: str


@dataclass(frozen=True, slots=True)
class DecisionRecallCertificate:
    certificate_id: str
    revision_id: str
    policy_revision: str
    horizon_ref: str
    history_signature_digests: tuple[tuple[str, str], ...]
    alias_classes: tuple[tuple[str, tuple[str, ...]], ...]
    level: RecallLevel
    counterexamples: tuple[RecallCounterexample, ...]
    created_sequence: int
    validity_regime: str
    canonical_digest: str

    _DIMENSIONS = (
        "current_information_class",
        "current_action_semantics",
        "transition_signature",
        "observation_capability_signature",
        "obligation_signature",
        "resource_authority_signature",
        "risk_signature",
        "action_space_signature",
        "continuation_signature",
    )

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        policy_revision: str,
        horizon_ref: str,
        histories: Iterable[DecisionHistorySignature],
        alias_classes: Mapping[str, Iterable[str]],
        created_sequence: int,
        validity_regime: str,
    ) -> "DecisionRecallCertificate":
        if int(created_sequence) < 0:
            raise ValueError("created_sequence cannot be negative")
        history_rows = tuple(histories)
        history_map: dict[str, DecisionHistorySignature] = {}
        for row in history_rows:
            if row.history_ref in history_map:
                raise ValueError(f"duplicate history ref: {row.history_ref}")
            history_map[row.history_ref] = row

        aliases: list[tuple[str, tuple[str, ...]]] = []
        counterexamples: list[RecallCounterexample] = []
        unknown = False
        for alias_ref, members in alias_classes.items():
            alias = _required("alias class", alias_ref)
            refs = _canon(members)
            if not refs:
                raise ValueError("recall alias class must contain at least one history")
            aliases.append((alias, refs))
            missing = tuple(ref for ref in refs if ref not in history_map)
            if missing:
                unknown = True
                counterexamples.append(
                    RecallCounterexample(
                        "RECALL_HISTORY_MISSING",
                        alias,
                        missing,
                        (),
                        "one or more aliased histories have no bounded recursive decision signature",
                    )
                )
                continue
            rows = tuple(history_map[ref] for ref in refs)
            baseline = rows[0]
            differing: set[str] = set()
            for row in rows[1:]:
                for field in cls._DIMENSIONS:
                    if getattr(row, field) != getattr(baseline, field):
                        differing.add(field)
            if differing:
                counterexamples.append(
                    RecallCounterexample(
                        "RECALL_DOWNSTREAM_MISMATCH",
                        alias,
                        refs,
                        tuple(sorted(differing)),
                        "aliased histories are not recursively decision-equivalent over the certified horizon",
                    )
                )

        if any(item.code == "RECALL_DOWNSTREAM_MISMATCH" for item in counterexamples):
            level = RecallLevel.RECALL_INSUFFICIENT
        elif unknown:
            level = RecallLevel.RECALL_UNKNOWN
        else:
            level = RecallLevel.RECALL_SUFFICIENT
        digest_rows = tuple(sorted((row.history_ref, row.canonical_digest) for row in history_rows))
        alias_tuple = tuple(sorted(aliases))
        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_revision": _required("policy_revision", policy_revision),
            "horizon_ref": _required("horizon_ref", horizon_ref),
            "history_signature_digests": digest_rows,
            "alias_classes": alias_tuple,
            "level": level.value,
            "counterexamples": tuple(
                (item.code, item.alias_class_ref, item.history_refs, item.differing_dimensions, item.detail)
                for item in counterexamples
            ),
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            policy_revision=body["policy_revision"],
            horizon_ref=body["horizon_ref"],
            history_signature_digests=digest_rows,
            alias_classes=alias_tuple,
            level=level,
            counterexamples=tuple(counterexamples),
            created_sequence=body["created_sequence"],
            validity_regime=body["validity_regime"],
            canonical_digest=digest(body),
        )


class TotalityMode(str, Enum):
    TOTAL = "total"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class OutcomeSupport:
    outcome_ref: str
    support_kind: str
    supported: bool
    residual: bool

    def __post_init__(self) -> None:
        _required("outcome_ref", self.outcome_ref)
        _required("support_kind", self.support_kind)


@dataclass(frozen=True, slots=True)
class SuccessorHandler:
    outcome_ref: str
    handler_ref: str
    handler_kind: str
    legitimate_residual: bool

    def __post_init__(self) -> None:
        _required("outcome_ref", self.outcome_ref)
        _required("handler_ref", self.handler_ref)
        _required("handler_kind", self.handler_kind)


@dataclass(frozen=True, slots=True)
class MissingSuccessorCounterexample:
    code: str
    outcome_ref: str
    detail: str


@dataclass(frozen=True, slots=True)
class PolicyTotalityCertificate:
    certificate_id: str
    revision_id: str
    policy_revision: str
    action_node_revision: str
    outcome_digest: str
    handler_digest: str
    solver_status: str
    mode: TotalityMode
    counterexamples: tuple[MissingSuccessorCounterexample, ...]
    created_sequence: int
    validity_regime: str
    canonical_digest: str

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        policy_revision: str,
        action_node_revision: str,
        outcomes: Iterable[OutcomeSupport],
        handlers: Iterable[SuccessorHandler],
        solver_status: str,
        created_sequence: int,
        validity_regime: str,
    ) -> "PolicyTotalityCertificate":
        if int(created_sequence) < 0:
            raise ValueError("created_sequence cannot be negative")
        outcome_rows = tuple(outcomes)
        handler_rows = tuple(handlers)
        solver = _required("solver_status", solver_status).upper()
        counterexamples: list[MissingSuccessorCounterexample] = []

        if solver == "UNKNOWN":
            mode = TotalityMode.UNKNOWN
        elif solver == "UNSUPPORTED":
            mode = TotalityMode.UNSUPPORTED
        elif solver != "PROVED":
            mode = TotalityMode.UNKNOWN
        else:
            exact_handlers: dict[str, list[SuccessorHandler]] = {}
            generic_handlers: list[SuccessorHandler] = []
            for handler in handler_rows:
                if handler.outcome_ref == "*":
                    generic_handlers.append(handler)
                    continue
                exact_handlers.setdefault(handler.outcome_ref, []).append(handler)

            if generic_handlers:
                counterexamples.append(
                    MissingSuccessorCounterexample(
                        "GENERIC_CATCHALL_NOT_TOTALITY_PROOF",
                        "*",
                        "generic continuation/catch-all does not prove that every supported outcome has a valid successor",
                    )
                )

            for outcome in outcome_rows:
                if not outcome.supported:
                    continue
                candidates = exact_handlers.get(outcome.outcome_ref, ())
                valid = False
                for handler in candidates:
                    if outcome.residual:
                        if handler.legitimate_residual and handler.handler_kind in {
                            "residual_handler",
                            "reconciliation",
                            "recovery",
                        }:
                            valid = True
                            break
                    elif handler.handler_kind in {"successor", "reconciliation", "recovery"}:
                        valid = True
                        break
                if not valid:
                    counterexamples.append(
                        MissingSuccessorCounterexample(
                            "MISSING_SUCCESSOR",
                            outcome.outcome_ref,
                            "supported outcome has no exact valid successor/reconciliation/residual handler",
                        )
                    )
            mode = TotalityMode.TOTAL if not counterexamples else TotalityMode.INCOMPLETE

        outcome_doc = tuple(
            sorted((item.outcome_ref, item.support_kind, item.supported, item.residual) for item in outcome_rows)
        )
        handler_doc = tuple(
            sorted((item.outcome_ref, item.handler_ref, item.handler_kind, item.legitimate_residual) for item in handler_rows)
        )
        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "policy_revision": _required("policy_revision", policy_revision),
            "action_node_revision": _required("action_node_revision", action_node_revision),
            "outcome_digest": digest(outcome_doc),
            "handler_digest": digest(handler_doc),
            "solver_status": solver,
            "mode": mode.value,
            "counterexamples": tuple((item.code, item.outcome_ref, item.detail) for item in counterexamples),
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            policy_revision=body["policy_revision"],
            action_node_revision=body["action_node_revision"],
            outcome_digest=body["outcome_digest"],
            handler_digest=body["handler_digest"],
            solver_status=solver,
            mode=mode,
            counterexamples=tuple(counterexamples),
            created_sequence=body["created_sequence"],
            validity_regime=body["validity_regime"],
            canonical_digest=digest(body),
        )


@dataclass(frozen=True, slots=True)
class PolicyStitchCounterexample:
    mismatched_fields: tuple[str, ...]
    parent_values: tuple[tuple[str, str], ...]
    child_requirements: tuple[tuple[str, str], ...]
    detail: str


@dataclass(frozen=True, slots=True)
class PolicyEdgeCertificate:
    certificate_id: str
    revision_id: str
    parent_policy_node_revision: str
    child_policy_node_revision: str
    edge_guard_ref: str
    parent_post_contract: tuple[tuple[str, str], ...]
    child_entry_contract: tuple[tuple[str, str], ...]
    valid: bool
    counterexample: PolicyStitchCounterexample | None
    created_sequence: int
    validity_regime: str
    canonical_digest: str

    @classmethod
    def evaluate(
        cls,
        *,
        certificate_id: str,
        revision_id: str,
        parent_policy_node_revision: str,
        child_policy_node_revision: str,
        edge_guard_ref: str,
        parent_post_contract: Mapping[str, object],
        child_entry_contract: Mapping[str, object],
        created_sequence: int,
        validity_regime: str,
    ) -> "PolicyEdgeCertificate":
        if int(created_sequence) < 0:
            raise ValueError("created_sequence cannot be negative")
        parent = tuple(sorted((str(key), str(value)) for key, value in parent_post_contract.items()))
        child = tuple(sorted((str(key), str(value)) for key, value in child_entry_contract.items()))
        parent_map = dict(parent)
        child_map = dict(child)
        mismatched = tuple(
            sorted(
                key
                for key, required in child_map.items()
                if key not in parent_map or parent_map[key] != required
            )
        )
        counterexample = None
        if mismatched:
            counterexample = PolicyStitchCounterexample(
                mismatched_fields=mismatched,
                parent_values=tuple((key, parent_map.get(key, "<missing>")) for key in mismatched),
                child_requirements=tuple((key, child_map[key]) for key in mismatched),
                detail="parent post-support does not refine the child entry contract on every required dimension",
            )
        body = {
            "certificate_id": _required("certificate_id", certificate_id),
            "revision_id": _required("revision_id", revision_id),
            "parent_policy_node_revision": _required("parent_policy_node_revision", parent_policy_node_revision),
            "child_policy_node_revision": _required("child_policy_node_revision", child_policy_node_revision),
            "edge_guard_ref": _required("edge_guard_ref", edge_guard_ref),
            "parent_post_contract": parent,
            "child_entry_contract": child,
            "valid": not mismatched,
            "counterexample": None
            if counterexample is None
            else (
                counterexample.mismatched_fields,
                counterexample.parent_values,
                counterexample.child_requirements,
                counterexample.detail,
            ),
            "created_sequence": int(created_sequence),
            "validity_regime": _required("validity_regime", validity_regime),
        }
        return cls(
            certificate_id=body["certificate_id"],
            revision_id=body["revision_id"],
            parent_policy_node_revision=body["parent_policy_node_revision"],
            child_policy_node_revision=body["child_policy_node_revision"],
            edge_guard_ref=body["edge_guard_ref"],
            parent_post_contract=parent,
            child_entry_contract=child,
            valid=not mismatched,
            counterexample=counterexample,
            created_sequence=body["created_sequence"],
            validity_regime=body["validity_regime"],
            canonical_digest=digest(body),
        )
