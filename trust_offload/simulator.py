"""Simulation loop: wires a node population + scheduler + workload together
and collects the metrics used by the aggregate comparison (Table II) and
the four experiments.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import trust as trust_mod
from .baseline import RandomBaselineScheduler
from .node import EdgeNode, HONEST, MALICIOUS, WHITEWASHING, RESOURCE_EXHAUSTION
from .orchestrator import TrustOrchestrator
from .workload import generate_tasks

# Cost charged when no eligible (non-quarantined, above-threshold) node exists
# for a task under the trust-based scheduler -- the task simply cannot be
# safely offloaded and is counted as failed.
NO_NODE_AVAILABLE_LATENCY_MS = 150.0

# Failed tasks are assumed to cost one retransmission's worth of extra
# energy (Section VII.B's "retransmitting a failed task consumes costly
# wireless transmission energy"). This is a documented simplification: the
# paper does not give a joint energy/latency/payload formula.
RETRY_ENERGY_MULTIPLIER = 2.0


@dataclass
class SimulationResult:
    total_tasks: int
    successes: int
    failures: int
    latencies: list[float] = field(default_factory=list)
    energy_units: list[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_tasks if self.total_tasks else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def total_energy(self) -> float:
        return sum(self.energy_units)

    @property
    def edp(self) -> float:
        """Energy-Delay Product: total energy x average delay."""
        return self.total_energy * self.avg_latency_ms


def build_node_population(
    n_nodes: int,
    malicious_fraction: float = 0.10,
    whitewashing_fraction: float = 0.0,
    resource_exhaustion_fraction: float = 0.0,
    seed: int | None = None,
) -> list[EdgeNode]:
    """Builds N nodes with a mix of behavior profiles.

    Remaining nodes after the given fractions are honest. Each node gets its
    own RNG stream (deterministically derived from `seed`) so populations are
    reproducible across scheduler comparisons.
    """
    master_rng = random.Random(seed)
    n_malicious = round(n_nodes * malicious_fraction)
    n_whitewashing = round(n_nodes * whitewashing_fraction)
    n_resource_exhaustion = round(n_nodes * resource_exhaustion_fraction)
    n_honest = max(0, n_nodes - n_malicious - n_whitewashing - n_resource_exhaustion)

    behaviors = (
        [HONEST] * n_honest
        + [MALICIOUS] * n_malicious
        + [WHITEWASHING] * n_whitewashing
        + [RESOURCE_EXHAUSTION] * n_resource_exhaustion
    )
    # Pad/truncate for rounding safety.
    while len(behaviors) < n_nodes:
        behaviors.append(HONEST)
    behaviors = behaviors[:n_nodes]
    master_rng.shuffle(behaviors)

    nodes = []
    for i, behavior in enumerate(behaviors):
        node_seed = master_rng.randrange(2**32)
        node_rng = random.Random(node_seed)
        nodes.append(
            EdgeNode(
                node_id=f"EN{i}",
                behavior=behavior,
                base_cpu_pct=node_rng.uniform(40.0, 95.0),
                base_latency_ms=node_rng.uniform(5.0, 12.0),
                base_uptime=node_rng.uniform(0.90, 0.999),
                rng=node_rng,
            )
        )
    return nodes


def run_simulation(
    scheduler: TrustOrchestrator | RandomBaselineScheduler,
    n_tasks: int,
    workload_seed: int | None = None,
) -> SimulationResult:
    tasks = generate_tasks(n_tasks, random.Random(workload_seed))

    result = SimulationResult(total_tasks=n_tasks, successes=0, failures=0)
    for task in tasks:
        payload_mb = task.payload_mb
        dispatch = scheduler.dispatch()

        if dispatch.node_id is None:
            result.failures += 1
            result.latencies.append(NO_NODE_AVAILABLE_LATENCY_MS)
            result.energy_units.append(payload_mb * RETRY_ENERGY_MULTIPLIER)
            continue

        if dispatch.success:
            result.successes += 1
            result.energy_units.append(payload_mb)
        else:
            result.failures += 1
            result.energy_units.append(payload_mb * RETRY_ENERGY_MULTIPLIER)
        result.latencies.append(dispatch.latency_ms)

    return result


def run_trust_based(
    n_nodes: int,
    n_tasks: int,
    malicious_fraction: float = 0.10,
    tau_threshold: float = trust_mod.QUARANTINE_CUTOFF,
    whitewashing_fraction: float = 0.0,
    resource_exhaustion_fraction: float = 0.0,
    seed: int | None = None,
) -> SimulationResult:
    nodes = build_node_population(
        n_nodes, malicious_fraction, whitewashing_fraction, resource_exhaustion_fraction, seed=seed
    )
    orchestrator = TrustOrchestrator(nodes, tau_threshold=tau_threshold)
    return run_simulation(orchestrator, n_tasks, workload_seed=seed)


def run_baseline(
    n_nodes: int,
    n_tasks: int,
    malicious_fraction: float = 0.10,
    whitewashing_fraction: float = 0.0,
    resource_exhaustion_fraction: float = 0.0,
    seed: int | None = None,
) -> SimulationResult:
    nodes = build_node_population(
        n_nodes, malicious_fraction, whitewashing_fraction, resource_exhaustion_fraction, seed=seed
    )
    scheduler = RandomBaselineScheduler(nodes, rng=random.Random(seed))
    return run_simulation(scheduler, n_tasks, workload_seed=seed)
