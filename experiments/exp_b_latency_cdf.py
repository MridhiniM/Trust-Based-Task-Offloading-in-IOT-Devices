"""Experiment B: Latency CDF Analysis (paper Fig. 2).

Compares the empirical cumulative distribution of task completion latency
between the trust-based scheduler and the random baseline, over the same
node population and workload.
"""

from __future__ import annotations

import numpy as np
import _common  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trust_offload.simulator import run_baseline, run_trust_based


def ecdf(values):
    xs = np.sort(np.array(values))
    ys = np.arange(1, len(xs) + 1) / len(xs)
    return xs, ys


def main():
    trust_result = run_trust_based(
        n_nodes=_common.N_NODES,
        n_tasks=_common.N_TASKS,
        malicious_fraction=_common.MALICIOUS_FRACTION,
        seed=_common.SEED,
    )
    baseline_result = run_baseline(
        n_nodes=_common.N_NODES,
        n_tasks=_common.N_TASKS,
        malicious_fraction=_common.MALICIOUS_FRACTION,
        seed=_common.SEED,
    )

    trust_x, trust_y = ecdf(trust_result.latencies)
    base_x, base_y = ecdf(baseline_result.latencies)

    p95_trust = np.percentile(trust_result.latencies, 95)
    p95_base = np.percentile(baseline_result.latencies, 95)
    print(f"Trust-based: avg={trust_result.avg_latency_ms:.1f}ms  p95={p95_trust:.1f}ms")
    print(f"Baseline:    avg={baseline_result.avg_latency_ms:.1f}ms  p95={p95_base:.1f}ms")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(trust_x, trust_y, label="Trust-Based", color="tab:blue")
    ax.plot(base_x, base_y, label="Random Baseline", color="tab:red", linestyle="--")
    ax.set_xlabel("Completion Latency (ms)")
    ax.set_ylabel("Cumulative Probability")
    ax.set_title("Experiment B: Latency CDF")
    ax.legend()
    fig.tight_layout()
    out_path = f"{_common.RESULTS_DIR}/exp_b_latency_cdf.png"
    fig.savefig(out_path, dpi=150)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
