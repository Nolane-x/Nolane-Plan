import unittest

from nolane_plan.principals import AccessProfile, InformationItem, PrincipalRegistry


class PrincipalInformationTests(unittest.TestCase):
    def setUp(self):
        self.registry = PrincipalRegistry()
        self.a = self.registry.register("agent:a", {"public", "secret:a"})
        self.b = self.registry.register("agent:b", {"public"})
        self.public = InformationItem("i-public", {"x": 1}, frozenset({"public"}), visible_at=1)
        self.secret = InformationItem("i-secret", {"token": "x"}, frozenset({"secret:a"}), visible_at=1)

    def test_kernel_visibility_does_not_imply_principal_availability(self):
        self.registry.observe("agent:a", self.secret.id, observed_at=2)
        self.assertTrue(self.registry.info_available(self.secret, "agent:a", decision_time=3))
        self.assertFalse(self.registry.info_available(self.secret, "agent:b", decision_time=3))

    def test_delivery_must_happen_before_decision(self):
        self.registry.observe("agent:b", self.public.id, observed_at=10)
        self.assertFalse(self.registry.info_available(self.public, "agent:b", decision_time=9))
        self.assertTrue(self.registry.info_available(self.public, "agent:b", decision_time=10))

    def test_access_profile_revision_changes_partition_digest(self):
        self.registry.observe("agent:b", self.public.id, observed_at=1)
        p1 = self.registry.build_partition("agent:b", [self.public], decision_time=2)
        self.registry.update_access("agent:b", {"public", "secret:a"})
        p2 = self.registry.build_partition("agent:b", [self.public], decision_time=2)
        self.assertNotEqual(p1.access_profile_revision, p2.access_profile_revision)
        self.assertNotEqual(p1.digest, p2.digest)

    def test_partition_is_principal_bound_even_with_same_items(self):
        self.registry.observe("agent:a", self.public.id, observed_at=1)
        self.registry.observe("agent:b", self.public.id, observed_at=1)
        pa = self.registry.build_partition("agent:a", [self.public], decision_time=2)
        pb = self.registry.build_partition("agent:b", [self.public], decision_time=2)
        self.assertNotEqual(pa.digest, pb.digest)
        self.assertEqual(pa.item_ids, pb.item_ids)

    def test_expired_information_is_unavailable(self):
        item = InformationItem("short", "x", frozenset({"public"}), visible_at=1, valid_until=5)
        self.registry.observe("agent:b", item.id, observed_at=2)
        self.assertTrue(self.registry.info_available(item, "agent:b", 5))
        self.assertFalse(self.registry.info_available(item, "agent:b", 6))


if __name__ == "__main__":
    unittest.main()
