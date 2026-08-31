from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nolane_plan import PlanKernel
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.relocation import CandidateRegion, LocationStatus, StateRelocator
from nolane_plan.types import AuthorizationError

from wave7_authority_fixture import AuthorityFixture, CountingAdapter


class PatchAdapter:
    def __init__(self, patch):
        self.patch = dict(patch)
        self.calls = 0

    def execute(self, action, principal_ref):
        self.calls += 1
        return {
            "executing_principal_ref": principal_ref,
            "ok": True,
            "postconditions_verified": True,
            "state_patch": dict(self.patch),
            "outcome_known": True,
        }


class Wave8RelocationTests(unittest.TestCase):
    def test_exhaustive_region_sets_one_through_five_are_order_independent(self):
        cases = 0
        for count in range(1, 6):
            for compatibility_mask in range(1 << count):
                canonical_state = {
                    f"fact:{index}": bool(compatibility_mask & (1 << index))
                    for index in range(count)
                }
                for signature_mask in range(1 << count):
                    regions = [
                        CandidateRegion(
                            id=f"region:{index}",
                            required_facts={f"fact:{index}": True},
                            decision_signature=(
                                "decision:a" if not (signature_mask & (1 << index)) else "decision:b"
                            ),
                        )
                        for index in range(count)
                    ]
                    expected_ids = tuple(
                        sorted(
                            region.id
                            for index, region in enumerate(regions)
                            if compatibility_mask & (1 << index)
                        )
                    )
                    expected_signatures = tuple(
                        sorted(
                            {
                                region.decision_signature
                                for index, region in enumerate(regions)
                                if compatibility_mask & (1 << index)
                            }
                        )
                    )
                    if not expected_ids:
                        expected_status = LocationStatus.UNLOCATED
                    elif len(expected_signatures) == 1:
                        expected_status = LocationStatus.LOCATED
                    else:
                        expected_status = LocationStatus.AMBIGUOUS

                    forward = StateRelocator(regions).locate(canonical_state)
                    reverse = StateRelocator(list(reversed(regions))).locate(canonical_state)
                    rotated = StateRelocator(regions[1:] + regions[:1]).locate(canonical_state)

                    self.assertEqual(expected_status, forward.status)
                    self.assertEqual(expected_ids, forward.region_ids)
                    self.assertEqual(expected_signatures, forward.decision_signatures)
                    self.assertEqual(forward, reverse)
                    self.assertEqual(forward, rotated)
                    cases += 1

        self.assertEqual(1364, cases)

    def test_canonical_commit_recomputes_location_and_advances_revision(self):
        root = Path(tempfile.mkdtemp())
        kernel = PlanKernel.create(root, "relocate")
        kernel.register_region(CandidateRegion("region:ready", {"ready": True}, "deploy"))
        kernel.propose_action(ActionIntent("action:set-ready", "set-ready"))
        kernel.add_grant(AuthorityGrant("grant:set-ready", "agent:a", frozenset({"set-ready"})))
        authorization = kernel.authorize(
            "action:set-ready",
            "agent:a",
            ("grant:set-ready",),
            1,
        )
        adapter = PatchAdapter({"ready": True})
        before_revision = kernel._location_revision

        kernel.dispatch(authorization.id, "agent:a", adapter, 2)

        self.assertEqual(1, adapter.calls)
        self.assertGreater(kernel._location_revision, before_revision)
        self.assertEqual(LocationStatus.LOCATED, kernel.strategic_location.status)
        self.assertEqual(("region:ready",), kernel.strategic_location.region_ids)
        self.assertEqual(("deploy",), kernel.strategic_location.decision_signatures)

    def test_decision_relevant_relocation_stales_old_epoch_and_authorization(self):
        fixture = AuthorityFixture(Path(tempfile.mkdtemp()))
        kernel = fixture.kernel
        authorization = fixture.authorize()
        epoch = fixture.policy["epoch"]
        adapter = CountingAdapter()

        kernel._assert_decision_epoch_current(epoch.epoch_id)
        old_location_revision = kernel._location_revision
        kernel.register_region(CandidateRegion("region:new", {}, "new-decision"))
        kernel._relocate_after_commit()

        self.assertGreater(kernel._location_revision, old_location_revision)
        self.assertEqual(LocationStatus.LOCATED, kernel.strategic_location.status)
        self.assertEqual(("new-decision",), kernel.strategic_location.decision_signatures)
        with self.assertRaises(AuthorizationError):
            kernel._assert_decision_epoch_current(epoch.epoch_id)
        with self.assertRaises(AuthorizationError):
            kernel.dispatch(authorization.id, "agent:a", adapter, 60)
        self.assertEqual(0, adapter.calls)


if __name__ == "__main__":
    unittest.main()
