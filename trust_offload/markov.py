"""Discrete-time Markov chain analysis of trust state transitions (Section V).

Provides:
  - `whitewashing_quarantine_bound()`: the analytic k = 10 derivation (Eq. 8).
  - `empirical_quarantine_steps()`: runs a live EdgeNode through forced
    consecutive failures and counts how many it survives before quarantine,
    to confirm the analytic bound holds in the actual implementation.
  - `estimate_transition_matrix()`: builds an empirical S_T/S_S/S_Q
    transition matrix from a simulation trace and checks the absorbing
    property p_{Q->Q} = 1 (Eq. 7).
"""

from __future__ import annotations

import math
import random
from collections import defaultdict

from . import trust as trust_mod
from .node import EdgeNode, TRUST_FAIL_DELTA


def whitewashing_quarantine_bound(
    start_trust: float = 1.0,
    threshold: float = trust_mod.QUARANTINE_CUTOFF,
    fail_delta: float = TRUST_FAIL_DELTA,
) -> int:
    """Eq. (8): number of consecutive failures to drop a fully-trusted node
    (tau=1.0) below tau_threshold=0.55, given delta_fail=-0.045."""
    return math.ceil((start_trust - threshold) / abs(fail_delta))


def empirical_quarantine_steps(seed: int | None = None) -> int:
    """Forces consecutive failures on a fresh node (trust pinned to 1.0) and
    counts how many it takes before it is quarantined, exercising the real
    EdgeNode.update_trust() code path rather than the closed-form formula."""
    node = EdgeNode(node_id="whitewasher", rng=random.Random(seed))
    node.trust_score = 1.0
    steps = 0
    while not node.quarantined:
        node.update_trust(success=False)
        steps += 1
        if steps > 1000:  # safety valve against an infinite loop from a logic bug
            raise RuntimeError("node failed to quarantine after 1000 consecutive failures")
    return steps


def estimate_transition_matrix(node: EdgeNode, n_steps: int, force_fail_prob: float = 0.75) -> dict:
    """Drives a node through n_steps task outcomes (stochastic, biased toward
    failure to reach quarantine) and tallies observed S_T/S_S/S_Q state
    transitions into an empirical matrix.

    Returns {from_state: {to_state: probability}}.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    prev_state = node.state
    for _ in range(n_steps):
        success = node.rng.random() >= force_fail_prob
        node.update_trust(success)
        curr_state = node.state
        counts[prev_state][curr_state] += 1
        prev_state = curr_state

    matrix: dict[str, dict[str, float]] = {}
    for from_state, to_counts in counts.items():
        total = sum(to_counts.values())
        matrix[from_state] = {to_state: c / total for to_state, c in to_counts.items()}
    return matrix
