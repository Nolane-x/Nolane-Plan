import unittest

from nolane_plan.actions import ActionIntent, AuthorityEngine, AuthorityGrant
from nolane_plan.capsule import CapsuleCompiler
from nolane_plan.mission import MissionLedger
from nolane_plan.principals import InformationItem, PrincipalRegistry
from nolane_plan.types import AuthorizationError, CapsuleError, RiskClass


class CapsuleActionTests(unittest.TestCase):
    def setUp(self):
        self.registry = PrincipalRegistry()
        self.registry.register("agent:a", {"public", "secret:a"})
        self.registry.register("agent:b", {"public"})
        self.public = InformationItem("pub", "ok", frozenset({"public"}), 0)
        self.secret = InformationItem("sec", "secret", frozenset({"secret:a"}), 0)
        for p in ("agent:a", "agent:b"):
            self.registry.observe(p, "pub", 0)
        self.registry.observe("agent:a", "sec", 0)
        self.mission = MissionLedger.create("deploy safely")
        self.compiler = CapsuleCompiler(self.registry)

    def test_capsule_cannot_be_reused_by_another_principal(self):
        partition = self.registry.build_partition("agent:a", [self.public, self.secret], 1)
        capsule = self.compiler.compile("agent:a", partition, self.mission.current, canonical_version=1, action_ids=("act",), evidence_watermark=0)
        with self.assertRaises(CapsuleError):
            self.compiler.validate(capsule, "agent:b", partition, self.mission.current, canonical_version=1)

    def test_hydration_cannot_escalate_information_scope(self):
        partition = self.registry.build_partition("agent:b", [self.public, self.secret], 1)
        capsule = self.compiler.compile("agent:b", partition, self.mission.current, 1, ("act",), 0)
        with self.assertRaises(CapsuleError):
            self.compiler.hydrate(capsule, "agent:b", self.secret, decision_time=1)

    def test_authorization_is_acting_principal_bound(self):
        engine = AuthorityEngine()
        grant = AuthorityGrant("g-a", "agent:a", frozenset({"deploy"}), expires_at=100)
        action = ActionIntent("act", "deploy", risk_class=RiskClass.CONSEQUENTIAL)
        auth = engine.authorize(action, "agent:a", [grant], mission_version=1, canonical_version=1, now=1)
        self.assertTrue(engine.dispatch_eligible(auth, "agent:a", [grant], 1, 1, now=2))
        self.assertFalse(engine.dispatch_eligible(auth, "agent:b", [grant], 1, 1, now=2))

    def test_grant_for_other_principal_cannot_authorize(self):
        engine = AuthorityEngine()
        action = ActionIntent("act", "deploy")
        grant = AuthorityGrant("g-b", "agent:b", frozenset({"deploy"}), expires_at=100)
        with self.assertRaises(AuthorizationError):
            engine.authorize(action, "agent:a", [grant], 1, 1, now=1)

    def test_revoked_grant_blocks_dispatch(self):
        engine = AuthorityEngine()
        grant = AuthorityGrant("g-a", "agent:a", frozenset({"deploy"}), expires_at=100)
        action = ActionIntent("act", "deploy")
        auth = engine.authorize(action, "agent:a", [grant], 1, 1, now=1)
        revoked = grant.with_revoked(True)
        self.assertFalse(engine.dispatch_eligible(auth, "agent:a", [revoked], 1, 1, now=2))


if __name__ == "__main__": unittest.main()
