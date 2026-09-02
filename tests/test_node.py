import random

from trust_offload.node import EdgeNode
from trust_offload import trust


def _fresh_node(**kwargs) -> EdgeNode:
    return EdgeNode(node_id="n0", rng=random.Random(0), **kwargs)


def test_success_increments_trust_by_delta():
    node = _fresh_node()
    node.trust_score = 0.5
    node.update_trust(success=True)
    assert abs(node.trust_score - (0.5 + 0.025)) < 1e-9


def test_failure_decrements_trust_by_delta():
    node = _fresh_node()
    node.trust_score = 0.5
    node.update_trust(success=False)
    assert abs(node.trust_score - (0.5 - 0.045)) < 1e-9


def test_trust_is_clamped_to_unit_interval():
    node = _fresh_node()
    node.trust_score = 0.99
    node.quarantined = False
    node.update_trust(success=True)
    assert node.trust_score <= 1.0

    node2 = _fresh_node()
    node2.trust_score = 0.02
    node2.update_trust(success=False)
    assert node2.trust_score >= 0.0


def test_node_quarantines_once_below_threshold():
    node = _fresh_node()
    node.trust_score = trust.QUARANTINE_CUTOFF + 0.01
    assert not node.quarantined
    node.update_trust(success=False)
    assert node.trust_score < trust.QUARANTINE_CUTOFF
    assert node.quarantined


def test_quarantine_is_absorbing_further_successes_ignored():
    node = _fresh_node()
    node.trust_score = trust.QUARANTINE_CUTOFF - 0.1
    node.update_trust(success=False)  # trigger quarantine
    assert node.quarantined
    trust_at_quarantine = node.trust_score

    node.update_trust(success=True)  # should have no effect once quarantined
    assert node.trust_score == trust_at_quarantine
    assert node.quarantined
