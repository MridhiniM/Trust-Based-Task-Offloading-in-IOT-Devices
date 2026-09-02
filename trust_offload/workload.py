"""Task stream generation per Table I (Simulation Environment Parameters)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Task:
    task_id: int
    payload_mb: float
    cpu_cycles_mc: float
    baseline_latency_ms: float


def generate_tasks(n_tasks: int, rng: random.Random | None = None) -> list[Task]:
    """Table I: payload Uniform[1,15]MB, CPU cycles ~N(500,50)Mc,
    baseline network latency 5-12ms."""
    rng = rng or random.Random()
    tasks = []
    for i in range(n_tasks):
        payload_mb = rng.uniform(1.0, 15.0)
        cpu_cycles_mc = max(1.0, rng.gauss(500.0, 50.0))
        baseline_latency_ms = rng.uniform(5.0, 12.0)
        tasks.append(Task(i, payload_mb, cpu_cycles_mc, baseline_latency_ms))
    return tasks
