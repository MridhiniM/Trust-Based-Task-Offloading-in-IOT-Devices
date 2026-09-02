"""Edge node model: state vector, behavior profiles, and trust adaptation.

Implements the state vector S_i(t) = <C_i, L_i, SR_i, A_i> (Eq. 2) and the
asymmetric trust adaptation rule from Section IV.A / Section V:

    delta_success = +0.025   (Eq. 4)
    delta_fail    = -0.045   (Eq. 5)

Once trust drops below tau_threshold (0.55) the node is permanently
quarantined (the absorbing state S_Q, Eq. 7): it stops being polled/dispatched
by the orchestrator and can no longer accumulate successful executions to
recover, matching the paper's stated defense against whitewashing attacks.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import trust as trust_mod

TRUST_SUCCESS_DELTA = 0.025  # Eq. (4)
TRUST_FAIL_DELTA = -0.045  # Eq. (5)

# Node behavior profiles used to exercise the threat model of Section IV.
HONEST = "honest"
MALICIOUS = "malicious"  # Sec. IV.A -- drops 70-80% of tasks (Table I)
WHITEWASHING = "whitewashing"  # Sec. IV.A -- alternates trustworthy/malicious windows
RESOURCE_EXHAUSTION = "resource_exhaustion"  # Sec. IV.C -- falsely advertises C=100%


@dataclass
class EdgeNode:
    node_id: str
    behavior: str = HONEST
    base_cpu_pct: float = 70.0
    base_latency_ms: float = 8.0
    base_uptime: float = 0.99
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        # Seed trust from the advertised hardware profile with an optimistic
        # prior success rate (no history yet), per Eq. (2)'s weighted formula.
        self.trust_score = trust_mod.compute_trust(
            cpu_pct=self.base_cpu_pct,
            latency_ms=self.base_latency_ms,
            success_rate=1.0,
            uptime=self.base_uptime,
        )
        self.quarantined = False
        self.success_count = 0
        self.fail_count = 0
        self._latency_ema = self.base_latency_ms
        self._drop_rate = self._init_drop_rate()
        self._whitewash_good_phase = True
        self._whitewash_phase_task_count = 0
        self._whitewash_window = self.rng.randint(150, 300)

    def _init_drop_rate(self) -> float:
        if self.behavior in (MALICIOUS, WHITEWASHING):
            return self.rng.uniform(0.70, 0.80)  # Table I: "hardcoded to drop 70%-80% of tasks"
        if self.behavior == RESOURCE_EXHAUSTION:
            return self.rng.uniform(0.20, 0.30)
        return max(0.0, 1.0 - self.base_uptime) * self.rng.uniform(0.5, 1.0)  # honest: rare organic failures

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def reported_cpu_pct(self) -> float:
        if self.behavior == RESOURCE_EXHAUSTION:
            return 100.0  # DoS via falsely-advertised full capacity (Sec. IV.C)
        return max(5.0, min(100.0, self.base_cpu_pct + self.rng.uniform(-5.0, 5.0)))

    def state_vector(self) -> tuple[float, float, float, float]:
        """Current S_i(t) = <C_i, L_i, SR_i, A_i>."""
        return (self.reported_cpu_pct, self._latency_ema, self.success_rate, self.base_uptime)

    def _current_drop_probability(self) -> float:
        if self.behavior != WHITEWASHING:
            return self._drop_rate
        return self._drop_rate if not self._whitewash_good_phase else 0.03

    def execute_task(self) -> tuple[bool, float]:
        """Runs one task on this node. Returns (success, observed_latency_ms).

        Also applies the asymmetric trust update (Eq. 4/5) as a side effect,
        matching Stage 4 (Dynamic Trust Update) of the orchestrator pipeline.
        """
        if self.behavior == WHITEWASHING:
            self._whitewash_phase_task_count += 1
            if self._whitewash_phase_task_count >= self._whitewash_window:
                self._whitewash_good_phase = not self._whitewash_good_phase
                self._whitewash_phase_task_count = 0

        success = self.rng.random() >= self._current_drop_probability()

        observed_latency = self.base_latency_ms * self.rng.uniform(0.8, 1.3)
        if not success:
            observed_latency *= self.rng.uniform(2.0, 4.0)  # failed/retried tasks cost extra latency

        self._latency_ema = 0.9 * self._latency_ema + 0.1 * observed_latency

        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

        self.update_trust(success)
        return success, observed_latency

    def update_trust(self, success: bool) -> None:
        """Eq. (4)/(5) asymmetric adaptation; Eq. (7) absorbing quarantine."""
        if self.quarantined:
            return
        delta = TRUST_SUCCESS_DELTA if success else TRUST_FAIL_DELTA
        self.trust_score = max(0.0, min(1.0, self.trust_score + delta))
        if self.trust_score < trust_mod.QUARANTINE_CUTOFF:
            self.quarantined = True

    @property
    def state(self) -> str:
        if self.quarantined:
            return trust_mod.TrustState.QUARANTINED
        return trust_mod.classify_state(self.trust_score)
