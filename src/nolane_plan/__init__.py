"""Nolane Plan — proof-carrying strategic future-space runtime."""

from .kernel import PlanKernel
from .mission import MissionContract, MissionLedger
from .policy_recovery import install_policy_recovery
from .policy_runtime import install_policy_runtime
from .proof_recovery import install_proof_recovery
from .proof_runtime import install_proof_runtime
from .resume import install_runtime_extensions
from .seal_lifecycle import install_seal_lifecycle
from .trust_recovery import install_trust_recovery
from .trust_runtime import install_trust_runtime
from .types import RiskClass

install_seal_lifecycle()
install_runtime_extensions(PlanKernel)
install_trust_runtime(PlanKernel)
install_trust_recovery(PlanKernel)
install_proof_runtime(PlanKernel)
install_proof_recovery(PlanKernel)
install_policy_runtime(PlanKernel)
install_policy_recovery(PlanKernel)

__all__ = ["PlanKernel", "MissionContract", "MissionLedger", "RiskClass"]
__version__ = "0.5.0a1"
