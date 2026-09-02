"""FastAPI wrapper around the trust_offload simulator.

Thin HTTP layer only -- all simulation logic lives in trust_offload/. This
just validates/clamps request parameters, calls the existing simulator
functions, and shapes the results as JSON for the frontend's charts.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from trust_offload.simulator import run_baseline, run_trust_based, run_trust_based_traced

app = FastAPI(title="TBTOF Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server-side safety caps -- this is a public, unauthenticated endpoint doing
# real compute, so requests are clamped regardless of what's asked for.
MAX_NODES = 500
MAX_TASKS = 20_000
MAX_SWEEP_TASKS = 8_000


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def downsample_sorted(values: list[float], max_points: int = 300) -> list[float]:
    values = sorted(values)
    if len(values) <= max_points:
        return values
    step = len(values) / max_points
    return [values[int(i * step)] for i in range(max_points)]


def shape_result(result) -> dict:
    return {
        "success_rate": result.success_rate,
        "avg_latency_ms": result.avg_latency_ms,
        "failures": result.failures,
        "total_tasks": result.total_tasks,
        "edp": result.edp,
        "latencies": downsample_sorted(result.latencies),
    }


class SimulateRequest(BaseModel):
    n_nodes: int = Field(default=100, ge=1)
    n_tasks: int = Field(default=10_000, ge=1)
    malicious_fraction: float = Field(default=0.10, ge=0.0, le=1.0)
    tau_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    seed: int = Field(default=42)


class LiveSimulateRequest(BaseModel):
    n_nodes: int = Field(default=20, ge=6, le=36)
    n_tasks: int = Field(default=300, ge=10, le=1500)
    malicious_fraction: float = Field(default=0.20, ge=0.0, le=1.0)
    tau_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    seed: int = Field(default=42)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/simulate")
def simulate(req: SimulateRequest):
    n_nodes = clamp(req.n_nodes, 1, MAX_NODES)
    n_tasks = clamp(req.n_tasks, 1, MAX_TASKS)

    trust_result = run_trust_based(
        n_nodes=n_nodes,
        n_tasks=n_tasks,
        malicious_fraction=req.malicious_fraction,
        tau_threshold=req.tau_threshold,
        seed=req.seed,
    )
    baseline_result = run_baseline(
        n_nodes=n_nodes,
        n_tasks=n_tasks,
        malicious_fraction=req.malicious_fraction,
        seed=req.seed,
    )

    baseline_edp = baseline_result.edp or 1.0
    return {
        "params": {
            "n_nodes": n_nodes,
            "n_tasks": n_tasks,
            "malicious_fraction": req.malicious_fraction,
            "tau_threshold": req.tau_threshold,
        },
        "trust_based": {**shape_result(trust_result), "edp_normalized": trust_result.edp / baseline_edp},
        "baseline": {**shape_result(baseline_result), "edp_normalized": 1.0},
    }


@app.post("/simulate/live")
def simulate_live(req: LiveSimulateRequest):
    n_nodes = clamp(req.n_nodes, 6, 36)
    n_tasks = clamp(req.n_tasks, 10, 1500)

    nodes, events = run_trust_based_traced(
        n_nodes=n_nodes,
        n_tasks=n_tasks,
        malicious_fraction=req.malicious_fraction,
        tau_threshold=req.tau_threshold,
        seed=req.seed,
    )
    return {"nodes": nodes, "events": events}


@app.get("/experiments/threshold-sensitivity")
def threshold_sensitivity(
    n_nodes: int = 100,
    n_tasks: int = 10_000,
    malicious_fraction: float = 0.10,
    seed: int = 42,
):
    n_nodes = clamp(n_nodes, 1, MAX_NODES)
    n_tasks = clamp(n_tasks, 1, MAX_SWEEP_TASKS)
    malicious_fraction = max(0.0, min(malicious_fraction, 1.0))

    thresholds = [round(0.10 * i, 2) for i in range(10)] + [round(0.90 + 0.01 * i, 2) for i in range(11)]
    success_rates = []
    for tau in thresholds:
        result = run_trust_based(
            n_nodes=n_nodes,
            n_tasks=n_tasks,
            malicious_fraction=malicious_fraction,
            tau_threshold=tau,
            seed=seed,
        )
        success_rates.append(result.success_rate)

    return {"thresholds": thresholds, "success_rates": success_rates}


@app.get("/experiments/saturation")
def saturation(n_nodes: int = 500, n_tasks: int = 10_000, seed: int = 42):
    n_nodes = clamp(n_nodes, 1, MAX_NODES)
    n_tasks = clamp(n_tasks, 1, MAX_SWEEP_TASKS)

    malicious_pcts = [0, 10, 20, 30, 40, 50]
    trust_rates = []
    baseline_rates = []
    for pct in malicious_pcts:
        fraction = pct / 100.0
        trust_result = run_trust_based(n_nodes=n_nodes, n_tasks=n_tasks, malicious_fraction=fraction, seed=seed)
        baseline_result = run_baseline(n_nodes=n_nodes, n_tasks=n_tasks, malicious_fraction=fraction, seed=seed)
        trust_rates.append(trust_result.success_rate)
        baseline_rates.append(baseline_result.success_rate)

    return {"malicious_pcts": malicious_pcts, "trust_rates": trust_rates, "baseline_rates": baseline_rates}
