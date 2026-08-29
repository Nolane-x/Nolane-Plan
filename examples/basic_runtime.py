from pathlib import Path
from nolane_plan.actions import ActionIntent, AuthorityGrant
from nolane_plan.kernel import PlanKernel
from nolane_plan.principals import InformationItem
from nolane_plan.types import RiskClass


class Adapter:
    def execute(self, action, principal_ref):
        return {"ok": True, "postconditions_verified": True, "state_patch": {"done": True}, "executing_principal_ref": principal_ref}


root = Path(".example-plan")
kernel = PlanKernel.create(root, objective="complete verified action", success_conditions=("done",))
kernel.register_principal("agent:executor", {"public"})
kernel.publish_information(InformationItem("ready", True, frozenset({"public"})))
kernel.observe_information("agent:executor", "ready", 0)
kernel.propose_action(ActionIntent("act", "execute", RiskClass.CONSEQUENTIAL))
kernel.add_grant(AuthorityGrant("grant", "agent:executor", frozenset({"execute"}), expires_at=10))
kernel.compile_capsule("agent:executor", 1, ("act",))
auth = kernel.authorize("act", "agent:executor", ("grant",), 1)
print(kernel.dispatch(auth.id, "agent:executor", Adapter(), 2))
