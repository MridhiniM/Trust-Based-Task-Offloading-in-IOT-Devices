import random

from trust_offload.node import EdgeNode
from trust_offload.orchestrator import TrustOrchestrator
from trust_offload import trust


def _node(node_id, trust_score, quarantined=False, cpu=80.0, latency=5.0):
    n = EdgeNode(node_id=node_id, rng=random.Random(hash(node_id) % (2**32)))
    n.trust_score = trust_score
    n.quarantined = quarantined
    n.base_cpu_pct = cpu
    n._latency_ema = latency
    return n


def test_filters_out_quarantined_and_below_threshold_nodes():
    nodes = [
        _node("quarantined", 0.9, quarantined=True),
        _node("below", 0.40),
        _node("eligible", 0.80),
    ]
    orch = TrustOrchestrator(nodes, tau_threshold=0.55)
    eligible = orch._eligible_nodes()
    assert [n.node_id for n in eligible] == ["eligible"]


def test_returns_none_when_no_eligible_nodes():
    nodes = [_node("a", 0.1), _node("b", 0.2, quarantined=True)]
    orch = TrustOrchestrator(nodes, tau_threshold=0.55)
    assert orch.select_node() is None
    result = orch.dispatch()
    assert result.node_id is None
    assert result.success is False


def test_never_dispatches_to_a_quarantined_node_even_if_high_trust_recorded():
    nodes = [_node("q", 0.9, quarantined=True), _node("ok", 0.60)]
    orch = TrustOrchestrator(nodes, tau_threshold=0.55)
    for _ in range(20):
        result = orch.dispatch()
        assert result.node_id != "q"


def test_ranks_higher_trust_node_above_lower_trust_when_resources_similar():
    nodes = [_node("low_trust", 0.56, cpu=80.0, latency=5.0), _node("high_trust", 0.95, cpu=80.0, latency=5.0)]
    orch = TrustOrchestrator(nodes, tau_threshold=0.55)
    assert orch.select_node().node_id == "high_trust"
