"""Multi-dimensional trust scoring and Markov state classification.

Implements Eq. (2) (state vector), the weighted trust formula referenced in
Section III.A / IV.C, and the three-state classification of Section V
(Trusted / Suspicious / Quarantined).

The paper gives two of the four formula weights explicitly: alpha=0.35
(task success rate) in Section IV.C, and beta=0.25 (CPU availability) in the
same section. gamma (latency) and delta (uptime) are not specified, so this
implementation splits the remaining 0.40 evenly between them -- an explicit
design choice documented here and in the README, not a value taken from the
paper.
"""

from __future__ import annotations

ALPHA = 0.35  # task success rate weight (paper, Sec. IV.C)
BETA = 0.25  # CPU availability weight (paper, Sec. IV.C)
GAMMA = 0.20  # latency weight (design choice -- unspecified in paper)
DELTA = 0.20  # historical uptime weight (design choice -- unspecified in paper)

assert abs((ALPHA + BETA + GAMMA + DELTA) - 1.0) < 1e-9, "trust weights must sum to 1.0"

TRUSTED_CUTOFF = 0.75  # Eq. (Trusted state, Sec. V)
QUARANTINE_CUTOFF = 0.55  # tau_threshold (paper, throughout)

# Latency at/above this is treated as "worst case" (0 score). Chosen to match
# the paper's own latency-CDF axis range (Fig. 2), where the baseline's tail
# extends out to ~100ms.
LATENCY_NORMALIZATION_MS = 100.0


class TrustState:
    TRUSTED = "TRUSTED"
    SUSPICIOUS = "SUSPICIOUS"
    QUARANTINED = "QUARANTINED"


def cpu_score(cpu_pct: float) -> float:
    return max(0.0, min(cpu_pct, 100.0)) / 100.0


def latency_score(latency_ms: float) -> float:
    """Lower latency is better; score is 1.0 at 0ms, 0.0 at/above the cap."""
    capped = max(0.0, min(latency_ms, LATENCY_NORMALIZATION_MS))
    return 1.0 - capped / LATENCY_NORMALIZATION_MS


def compute_trust(cpu_pct: float, latency_ms: float, success_rate: float, uptime: float) -> float:
    """Eq. (2) state vector <C, L, SR, A> -> weighted trust score tau.

    Used to seed a node's initial trust score from its advertised hardware
    profile before any task history exists. Ongoing trust is then driven by
    the asymmetric per-task adaptation rule (see node.py), per Section V.
    """
    sr_score = max(0.0, min(success_rate, 1.0))
    uptime_score = max(0.0, min(uptime, 1.0))

    tau = ALPHA * sr_score + BETA * cpu_score(cpu_pct) + GAMMA * latency_score(latency_ms) + DELTA * uptime_score
    return max(0.0, min(tau, 1.0))


def classify_state(tau: float) -> str:
    """Three-state classification from Section V: S_T, S_S, S_Q."""
    if tau >= TRUSTED_CUTOFF:
        return TrustState.TRUSTED
    if tau >= QUARANTINE_CUTOFF:
        return TrustState.SUSPICIOUS
    return TrustState.QUARANTINED
