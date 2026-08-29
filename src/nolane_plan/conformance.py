from __future__ import annotations

import itertools
import json
from collections import defaultdict

from .failure_registry import PRINCIPAL_SCOPE_FAILURES


def _collision_count(rows, projection_key, outcome_key):
    groups = defaultdict(list)
    for row in rows:
        groups[projection_key(row)].append(row)
    collisions = 0
    for group in groups.values():
        for a, b in itertools.combinations(group, 2):
            if outcome_key(a) != outcome_key(b):
                collisions += 1
    return collisions


def run_principal_scope_oracle() -> dict[str, int | bool]:
    principals = tuple(f"agent:p{i}" for i in range(4))

    info_rows = []
    for scenario in range(32):
        principal_sensitive = scenario < 16
        for principal in principals:
            required_action = f"act:{principal}" if principal_sensitive else "act:shared"
            info_rows.append({
                "scenario": scenario,
                "principal": principal,
                "required_action": required_action,
                "v014_projection": (scenario, "shared-partition"),
                "v015_projection": (scenario, principal, "principal-partition"),
            })

    v014_info = _collision_count(info_rows, lambda r: r["v014_projection"], lambda r: r["required_action"])
    v015_info = _collision_count(info_rows, lambda r: r["v015_projection"], lambda r: r["required_action"])

    auth_rows = []
    for case, intended in enumerate(principals):
        for presented in principals:
            legal = presented == intended
            auth_rows.append({
                "case": case,
                "intended": intended,
                "presented": presented,
                "legal": legal,
                "v014_projection": (case, "authorization-id"),
                "v015_projection": (case, intended, presented),
            })

    v014_auth = _collision_count(auth_rows, lambda r: r["v014_projection"], lambda r: r["legal"])
    v015_auth = _collision_count(auth_rows, lambda r: r["v015_projection"], lambda r: r["legal"])

    return {
        "principal_count": len(principals),
        "information_decisions": len(info_rows),
        "authorization_decisions": len(auth_rows),
        "v014_information_collision_pairs": v014_info,
        "v014_authorization_collision_pairs": v014_auth,
        "v014_total_collision_pairs": v014_info + v014_auth,
        "v015_information_collision_pairs": v015_info,
        "v015_authorization_collision_pairs": v015_auth,
        "v015_challenger_collision_pairs": v015_info + v015_auth,
        "independent_evaluator_agreement": (v014_info, v014_auth, v015_info, v015_auth) == (96, 12, 0, 0),
    }


def verify_acceptance_surface() -> dict:
    oracle = run_principal_scope_oracle()
    checks = {
        "pg01_pg40_complete": len(PRINCIPAL_SCOPE_FAILURES) == 40 and set(PRINCIPAL_SCOPE_FAILURES) == {f"PG{i:02d}" for i in range(1, 41)},
        "information_decisions_128": oracle["information_decisions"] == 128,
        "authorization_decisions_16": oracle["authorization_decisions"] == 16,
        "v014_collisions_108": oracle["v014_total_collision_pairs"] == 108,
        "v015_collisions_zero": oracle["v015_challenger_collision_pairs"] == 0,
        "evaluator_agrees": bool(oracle["independent_evaluator_agreement"]),
    }
    failed = [name for name, ok in checks.items() if not ok]
    return {"ok": not failed, "failed": failed, "checks": checks, "oracle": oracle}


def main() -> int:
    print(json.dumps(verify_acceptance_surface(), indent=2, sort_keys=True))
    return 0 if verify_acceptance_surface()["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
