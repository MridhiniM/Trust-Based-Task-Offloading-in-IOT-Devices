from trust_offload import trust


def test_weights_sum_to_one():
    assert abs((trust.ALPHA + trust.BETA + trust.GAMMA + trust.DELTA) - 1.0) < 1e-9


def test_perfect_state_yields_full_trust():
    tau = trust.compute_trust(cpu_pct=100.0, latency_ms=0.0, success_rate=1.0, uptime=1.0)
    assert tau == 1.0


def test_worst_state_yields_zero_trust():
    tau = trust.compute_trust(cpu_pct=0.0, latency_ms=trust.LATENCY_NORMALIZATION_MS, success_rate=0.0, uptime=0.0)
    assert tau == 0.0


def test_success_rate_has_largest_single_factor_swing():
    # Moving success_rate from 0 to 1 should move tau by exactly ALPHA,
    # holding everything else fixed -- confirms the weight is applied as documented.
    low = trust.compute_trust(cpu_pct=50.0, latency_ms=50.0, success_rate=0.0, uptime=0.5)
    high = trust.compute_trust(cpu_pct=50.0, latency_ms=50.0, success_rate=1.0, uptime=0.5)
    assert abs((high - low) - trust.ALPHA) < 1e-9


def test_classify_state_boundaries():
    assert trust.classify_state(0.75) == trust.TrustState.TRUSTED
    assert trust.classify_state(0.749) == trust.TrustState.SUSPICIOUS
    assert trust.classify_state(0.55) == trust.TrustState.SUSPICIOUS
    assert trust.classify_state(0.549) == trust.TrustState.QUARANTINED
