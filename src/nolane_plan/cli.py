from __future__ import annotations

import argparse
import json
from pathlib import Path

from .actions import ActionIntent, AuthorityGrant
from .conformance import verify_acceptance_surface
from .future import FutureFamily
from .kernel import PlanKernel
from .obligations import StrategicObligation
from .principals import InformationItem
from .types import RiskClass


class _DemoAdapter:
    def execute(self, action, principal_ref):
        return {
            "ok": True,
            "postconditions_verified": True,
            "state_patch": {"deployed": True, "last_action": action.id},
            "executing_principal_ref": principal_ref,
        }


def _demo(root: Path) -> dict:
    k = PlanKernel.create(root, objective="deploy verified artifact", success_conditions=("deployed",), hard_constraints=("preserve rollback",))
    k.register_principal("agent:planner", {"public", "build"})
    info = InformationItem("build-proof", {"status": "verified"}, frozenset({"public", "build"}), visible_at=0, provenance="demo-verifier")
    k.publish_information(info)
    k.observe_information("agent:planner", info.id, 0)
    k.add_future_family(FutureFamily("primary", "deployment endpoint healthy", probability=0.8))
    k.add_future_family(FutureFamily("degraded", "deployment endpoint degraded", probability=0.15))
    k.add_obligation(StrategicObligation("rollback", "rollback path preserved"))
    action = ActionIntent("deploy", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
    k.propose_action(action)
    grant = AuthorityGrant("deploy-grant", "agent:planner", frozenset({"deploy"}), expires_at=100)
    k.add_grant(grant)
    capsule = k.compile_capsule("agent:planner", decision_time=1, action_ids=("deploy",))
    auth = k.authorize("deploy", "agent:planner", ("deploy-grant",), now=1)
    receipt = k.dispatch(auth.id, "agent:planner", _DemoAdapter(), now=2)
    snapshot = k.save_snapshot()
    return {
        "capsule_id": capsule.id,
        "authorization_id": auth.id,
        "receipt_id": receipt.id,
        "canonical_state": k.canonical_state,
        "canonical_version": k.canonical_version,
        "future_families": sorted(k.future.families),
        "recovery_mode": k.recovery.state.mode.value,
        "journal_valid": k.journal.verify(),
        "snapshot": snapshot,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nolane-plan", description="Nolane Plan strategic future-space runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("conformance", help="run v0.15 deterministic conformance surface")
    demo = sub.add_parser("demo", help="run an end-to-end model-free reference lifecycle")
    demo.add_argument("--root", type=Path, default=Path(".nolane-plan-demo"))
    init = sub.add_parser("init", help="initialize a session journal/snapshot directory")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--objective", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "conformance":
        report = verify_acceptance_surface()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 1
    if args.command == "demo":
        print(json.dumps(_demo(args.root), indent=2, sort_keys=True))
        return 0
    if args.command == "init":
        k = PlanKernel.create(args.root, objective=args.objective)
        print(json.dumps(k.snapshot_state(), indent=2, sort_keys=True))
        return 0
    return 2
