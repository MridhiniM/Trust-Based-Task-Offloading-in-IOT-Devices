"""Trust Orchestrator: the four-stage decision pipeline from Section III.A.

    1) Real-Time Data Collection  -> EdgeNode.state_vector()
    2) Trust Computation          -> EdgeNode.trust_score (asymmetrically adapted)
    3) Decision Engine            -> threshold filter + hybrid utility ranking
    4) Dynamic Trust Update       -> EdgeNode.update_trust() (inside execute_task)

The paper names a "hybrid resource-trust utility function" for Stage 3 but
does not give its formula. This implementation uses:

    U_i = UTILITY_TRUST_WEIGHT * trust_i + (1 - UTILITY_TRUST_WEIGHT) * resource_fit_i

where resource_fit_i blends normalized CPU headroom and inverse latency (the
same normalizations trust.py uses for its own C/L terms), without
re-weighting success rate or uptime a second time. This is a documented
design choice, not a value taken from the paper.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import trust as trust_mod
from .node import EdgeNode

UTILITY_TRUST_WEIGHT = 0.6


@dataclass
class DispatchResult:
    node_id: str | None
    success: bool
    latency_ms: float


class TrustOrchestrator:
    def __init__(self, nodes: list[EdgeNode], tau_threshold: float = trust_mod.QUARANTINE_CUTOFF):
        self.nodes = nodes
        self.tau_threshold = tau_threshold

    def _eligible_nodes(self) -> list[EdgeNode]:
        # Stage 3a: filter out quarantined nodes and anything below threshold.
        return [n for n in self.nodes if not n.quarantined and n.trust_score >= self.tau_threshold]

    def _utility(self, node: EdgeNode) -> float:
        cpu_pct, latency_ms, _sr, _a = node.state_vector()
        resource_fit = 0.5 * trust_mod.cpu_score(cpu_pct) + 0.5 * trust_mod.latency_score(latency_ms)
        return UTILITY_TRUST_WEIGHT * node.trust_score + (1 - UTILITY_TRUST_WEIGHT) * resource_fit

    def select_node(self) -> EdgeNode | None:
        candidates = self._eligible_nodes()
        if not candidates:
            return None
        return max(candidates, key=self._utility)

    def dispatch(self) -> DispatchResult:
        """Selects a node for one task and runs it (Stages 1-4 for one task)."""
        node = self.select_node()
        if node is None:
            # No trustworthy node available -- task cannot be safely offloaded.
            return DispatchResult(node_id=None, success=False, latency_ms=0.0)
        success, latency_ms = node.execute_task()
        return DispatchResult(node_id=node.node_id, success=success, latency_ms=latency_ms)
