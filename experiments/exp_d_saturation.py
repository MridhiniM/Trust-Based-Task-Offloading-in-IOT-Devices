"""Experiment D: Resilience to Saturation (paper Fig. 4).

Fixes a large node population (500) and sweeps the fraction of malicious
nodes from 0% to 50%, comparing overall success rate for the trust-based
scheduler vs. the random baseline.
"""

from __future__ import annotations

import _common  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trust_offload.simulator import run_baseline, run_trust_based

N_NODES = 500
MALICIOUS_PCTS = [0, 10, 20, 30, 40, 50]


def main():
    trust_rates = []
    baseline_rates = []
    for pct in MALICIOUS_PCTS:
        fraction = pct / 100.0
        trust_result = run_trust_based(
            n_nodes=N_NODES,
            n_tasks=_common.N_TASKS,
            malicious_fraction=fraction,
            seed=_common.SEED,
        )
        baseline_result = run_baseline(
            n_nodes=N_NODES,
            n_tasks=_common.N_TASKS,
            malicious_fraction=fraction,
            seed=_common.SEED,
        )
        trust_rates.append(trust_result.success_rate * 100)
        baseline_rates.append(baseline_result.success_rate * 100)
        print(
            f"malicious={pct}%  trust-based={trust_result.success_rate * 100:.1f}%  "
            f"baseline={baseline_result.success_rate * 100:.1f}%"
        )

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(MALICIOUS_PCTS, trust_rates, marker="s", color="tab:blue", label="Trust-Based")
    ax.plot(MALICIOUS_PCTS, baseline_rates, marker="^", color="tab:red", linestyle="--", label="Baseline")
    ax.set_xlabel("Percentage of Malicious Nodes in Network (%)")
    ax.set_ylabel("Overall Success Rate (%)")
    ax.set_title("Experiment D: Resilience to Saturation")
    ax.legend()
    fig.tight_layout()
    out_path = f"{_common.RESULTS_DIR}/exp_d_saturation.png"
    fig.savefig(out_path, dpi=150)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
