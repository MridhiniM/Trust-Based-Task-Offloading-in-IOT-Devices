"""Runs the Table II aggregate comparison plus all four experiments,
saving figures to results/."""

from __future__ import annotations

import _common  # noqa: F401

from trust_offload.simulator import run_baseline, run_trust_based

import exp_a_threshold_sensitivity
import exp_b_latency_cdf
import exp_c_edp
import exp_d_saturation


def print_aggregate_comparison():
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

    print("=" * 72)
    print("Table II: System Performance -- Trust-Based vs. Random Baseline")
    print("=" * 72)
    print(f"{'Metric':<24}{'Trust-Based':<18}{'Random Baseline':<18}{'Delta'}")
    print(
        f"{'Overall Success Rate':<24}"
        f"{trust_result.success_rate * 100:<18.1f}"
        f"{baseline_result.success_rate * 100:<18.1f}"
        f"{(trust_result.success_rate - baseline_result.success_rate) * 100:+.1f} pp"
    )
    print(
        f"{'Average Latency (ms)':<24}"
        f"{trust_result.avg_latency_ms:<18.1f}"
        f"{baseline_result.avg_latency_ms:<18.1f}"
        f"{trust_result.avg_latency_ms - baseline_result.avg_latency_ms:+.1f} ms"
    )
    print(
        f"{'Total Tasks Failed':<24}"
        f"{trust_result.failures:<18}"
        f"{baseline_result.failures:<18}"
        f"{(1 - trust_result.failures / baseline_result.failures) * 100:.1f}% reduction"
    )
    print("=" * 72)
    print()


def main():
    print_aggregate_comparison()
    exp_a_threshold_sensitivity.main()
    print()
    exp_b_latency_cdf.main()
    print()
    exp_c_edp.main()
    print()
    exp_d_saturation.main()


if __name__ == "__main__":
    main()
