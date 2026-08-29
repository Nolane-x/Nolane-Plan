"""Nolane Plan — proof-carrying strategic future-space runtime."""

from .kernel import PlanKernel
from .mission import MissionContract, MissionLedger
from .resume import install_runtime_extensions
from .trust_recovery import install_trust_recovery
from .trust_runtime import install_trust_runtime
from .types import RiskClass

install_runtime_extensions(PlanKernel)
install_trust_runtime(PlanKernel)
install_trust_recovery(PlanKernel)

__all__ = ["PlanKernel", "MissionContract", "MissionLedger", "RiskClass"]
__version__ = "0.2.0a1"
