"""Experiment A: Threshold Sensitivity Analysis (paper Fig. 1).

Sweeps tau_threshold and plots overall task success rate.

Honest-simulation note: under the asymmetric update rule (+0.025 success,
-0.045 fail), a misbehaving node's trust drifts to zero within a handful of
tasks (its "blast radius" is bounded, per the paper's own Eq. 8 argument) --
so in this implementation the exact threshold barely matters across most of
the range: success rate is flat from tau=0.0 up to roughly the trust ceiling
that honest nodes can reach. The real sensitivity shows up as a cliff once
the threshold is pushed above what almost any node -- honest or not -- can
achieve, at which point the eligible pool collapses and tasks have nowhere
to go. This differs from the paper's claimed symmetric bell curve; see
README.md's "Honest results" section for discussion.
"""

from __future__ import annotations

import _common  # noqa: F401  (sets up sys.path / RESULTS_DIR)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trust_offload.simulator import run_trust_based

# Coarse sampling across the plausible range, finer sampling near the
# high-end cliff where the eligible node pool starts collapsing.
THRESHOLDS = [round(0.10 * i, 2) for i in range(10)] + [round(0.90 + 0.01 * i, 2) for i in range(11)]


def main():
    success_rates = []
    for tau in THRESHOLDS:
        result = run_trust_based(
            n_nodes=_common.N_NODES,
            n_tasks=_common.N_TASKS,
            malicious_fraction=_common.MALICIOUS_FRACTION,
            tau_threshold=tau,
            seed=_common.SEED,
        )
        success_rates.append(result.success_rate * 100)
        print(f"tau_threshold={tau:.2f}  success_rate={result.success_rate * 100:.1f}%")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(THRESHOLDS, success_rates, marker="o", markersize=4, label="System Performance")
    ax.axvline(0.55, color="gray", linestyle=":", label=r"Paper's $\tau_{threshold}=0.55$")
    ax.set_xlabel(r"Trust Threshold ($\tau_{threshold}$)")
    ax.set_ylabel("Task Success Rate (%)")
    ax.set_title("Experiment A: Threshold Sensitivity (honest simulation)")
    ax.legend()
    fig.tight_layout()
    out_path = f"{_common.RESULTS_DIR}/exp_a_threshold_sensitivity.png"
    fig.savefig(out_path, dpi=150)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
