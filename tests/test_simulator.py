from trust_offload.simulator import run_trust_based_traced


def test_traced_returns_one_event_per_task():
    _nodes, events = run_trust_based_traced(n_nodes=10, n_tasks=50, malicious_fraction=0.3, seed=1)
    assert len(events) == 50
    assert [e["task_index"] for e in events] == list(range(50))


def test_traced_node_summaries_match_population_size():
    nodes, _events = run_trust_based_traced(n_nodes=12, n_tasks=20, malicious_fraction=0.2, seed=2)
    assert len(nodes) == 12
    assert {n["node_id"] for n in nodes} == {f"EN{i}" for i in range(12)}
    assert all(0.0 <= n["initial_trust"] <= 1.0 for n in nodes)


def test_heavily_malicious_population_produces_a_quarantine_event():
    # High malicious fraction + enough tasks should reliably trigger at
    # least one quarantine within the trace.
    _nodes, events = run_trust_based_traced(n_nodes=10, n_tasks=500, malicious_fraction=0.5, seed=3)
    assert any(e["quarantined"] for e in events)


def test_quarantined_node_never_dispatched_to_again():
    _nodes, events = run_trust_based_traced(n_nodes=10, n_tasks=500, malicious_fraction=0.5, seed=3)
    quarantined_nodes = set()
    for e in events:
        node_id = e["node_id"]
        if node_id is None:
            continue
        assert node_id not in quarantined_nodes, f"{node_id} was dispatched to again after being quarantined"
        if e["quarantined"]:
            quarantined_nodes.add(node_id)
