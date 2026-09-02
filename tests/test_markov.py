from trust_offload import markov
from trust_offload import trust


def test_analytic_quarantine_bound_is_ten():
    assert markov.whitewashing_quarantine_bound() == 10


def test_empirical_quarantine_matches_analytic_bound():
    steps = markov.empirical_quarantine_steps(seed=42)
    assert steps == markov.whitewashing_quarantine_bound()


def test_empirical_quarantine_matches_across_seeds():
    # The bound is deterministic (forced failures, fixed deltas) regardless
    # of RNG seed -- the seed only affects unrelated node fields.
    for seed in (0, 1, 7, 123):
        assert markov.empirical_quarantine_steps(seed=seed) == 10


def test_quarantined_state_is_absorbing_in_practice():
    import random

    from trust_offload.node import EdgeNode

    node = EdgeNode(node_id="n", rng=random.Random(3))
    matrix = markov.estimate_transition_matrix(node, n_steps=500, force_fail_prob=0.9)
    if trust.TrustState.QUARANTINED in matrix:
        q_row = matrix[trust.TrustState.QUARANTINED]
        assert abs(q_row.get(trust.TrustState.QUARANTINED, 0.0) - 1.0) < 1e-9
