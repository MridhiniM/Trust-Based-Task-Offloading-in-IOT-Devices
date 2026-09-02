"""Random baseline scheduler.

Represents the "traditional, unauthenticated load balancing system" the
paper compares against (Section IX): it selects a node uniformly at random
from the entire population, with no trust or health filtering whatsoever --
including nodes that a trust-aware orchestrator would already have
quarantined.
"""

from __future__ import annotations

import random

from .node import EdgeNode
from .orchestrator import DispatchResult


class RandomBaselineScheduler:
    def __init__(self, nodes: list[EdgeNode], rng: random.Random | None = None):
        self.nodes = nodes
        self.rng = rng or random.Random()

    def dispatch(self) -> DispatchResult:
        node = self.rng.choice(self.nodes)
        success, latency_ms = node.execute_task()
        return DispatchResult(node_id=node.node_id, success=success, latency_ms=latency_ms)
