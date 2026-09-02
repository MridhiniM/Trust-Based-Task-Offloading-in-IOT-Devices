"""Experiment C: Energy-Delay Product (paper Fig. 3).

Compares normalized EDP (total transmission energy x average delay) between
the random baseline and the trust-based scheduler, normalized so the
baseline is 1.0.
"""

from __future__ import annotations

import _common  # noqa: F401
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trust_offload.simulator import run_baseline, run_trust_based


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

    baseline_edp = baseline_result.edp
    trust_edp_normalized = trust_result.edp / baseline_edp
    reduction_pct = (1 - trust_edp_normalized) * 100

    print(f"Baseline EDP (normalized): 1.00")
    print(f"Trust-based EDP (normalized): {trust_edp_normalized:.2f}")
    print(f"Reduction: {reduction_pct:.1f}%")

    fig, ax = plt.subplots(figsize=(5, 5))
    labels = ["Random Baseline", "Trust-Based"]
    values = [1.0, trust_edp_normalized]
    bars = ax.bar(labels, values, color=["tab:red", "tab:blue"])
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.02, f"{val:.2f}", ha="center")
    ax.set_ylabel("Normalized EDP")
    ax.set_title("Experiment C: Energy-Delay Product")
    fig.tight_layout()
    out_path = f"{_common.RESULTS_DIR}/exp_c_edp.png"
    fig.savefig(out_path, dpi=150)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
