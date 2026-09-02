# Trust-Based Task Offloading Framework (TBTOF)

**[Live interactive demo →](https://trust-based-task-offloading-in-iot-devices-mridhini.vercel.app)** (frontend on Vercel, simulator API on Railway — the demo runs the actual simulator live, nothing is precomputed)

A working implementation of the trust engine, orchestrator, and simulator described in
*"Trust-Based Task Offloading Framework for Edge-Based IoT Systems"* (Anitha H.M., Nalina V.,
Madhusudan, Shakthi, S.P.). It scores edge nodes on task success rate, CPU availability,
response latency, and historical uptime; adapts trust asymmetrically after every task
(small reward, larger penalty); and permanently quarantines nodes that fall below a trust
threshold -- all validated against a discrete-time Markov chain model and benchmarked
against a random-baseline scheduler.

This is an **honest simulation**: it implements the paper's stated rules faithfully and
reports whatever numbers come out, rather than being tuned to reproduce the paper's exact
figures. Several of the paper's numbers (exact RNG seed, some weight values, the "hybrid
utility function" formula) aren't specified precisely enough to reproduce bit-for-bit --
every place this implementation had to make a call is called out below.

## Equation-to-code map

| Paper | Meaning | Code |
|---|---|---|
| Eq. 2, `S_i(t) = <C_i, L_i, SR_i, A_i>` | Node state vector | [`EdgeNode.state_vector()`](trust_offload/node.py) |
| Sec. IV.C weighted trust formula | alpha=0.35 (success rate), beta=0.25 (CPU) | [`trust.compute_trust()`](trust_offload/trust.py) |
| Eq. 4/5, `delta_success=+0.025`, `delta_fail=-0.045` | Asymmetric trust adaptation | [`EdgeNode.update_trust()`](trust_offload/node.py) |
| Sec. V, `S_T / S_S / S_Q` states | Trusted/Suspicious/Quarantined classification | [`trust.classify_state()`](trust_offload/trust.py) |
| Eq. 7, `p_{Q->Q} = 1` | Quarantine is absorbing | [`markov.estimate_transition_matrix()`](trust_offload/markov.py), enforced in [`orchestrator._eligible_nodes()`](trust_offload/orchestrator.py) |
| Eq. 8, `k = ceil((1.0-0.55)/0.045) = 10` | Whitewashing blast-radius bound | [`markov.whitewashing_quarantine_bound()`](trust_offload/markov.py) |
| Sec. III.A four-stage pipeline | Collect -> Score -> Filter/Rank -> Update | [`TrustOrchestrator.dispatch()`](trust_offload/orchestrator.py) |
| Table I | Task/node simulation parameters | [`workload.generate_tasks()`](trust_offload/workload.py), [`simulator.build_node_population()`](trust_offload/simulator.py) |
| Table II | Aggregate comparison | `experiments/run_all.py` |
| Figs. 1-4 | Experiments A-D | `experiments/exp_a..d_*.py` |

## Design choices not specified in the paper

The paper is precise about some things (the two asymmetric deltas, two of the four trust
weights, the 0.55/0.75 cutoffs, Table I's distributions) and silent about others. Rather than
inventing numbers and passing them off as the paper's, here's exactly what was filled in and why:

- **Trust weights gamma (latency) and delta (uptime):** the paper gives alpha=0.35 and
  beta=0.25 but never states the other two. This implementation splits the remaining 0.40
  evenly (gamma=delta=0.20). See `trust_offload/trust.py`.
- **Hybrid resource-trust utility function** (Stage 3 ranking, named but not formularized):
  `U_i = 0.6 * trust_i + 0.4 * resource_fit_i`, where `resource_fit_i` blends normalized CPU
  headroom and inverse latency. See `trust_offload/orchestrator.py`.
- **Node selection policy:** each dispatch is a *utility-weighted random choice* among
  eligible nodes, not a strict argmax. A strict argmax was tried first and made almost the
  entire 10,000-task workload land on a single top-ranked node -- unrealistic, and it made
  the trust threshold irrelevant to the outcome. Weighted-random selection spreads load
  roughly the way a real scheduler would.
- **Malicious/whitewashing/resource-exhaustion behavior parameters** (drop-rate ranges,
  whitewashing phase length): the paper's threat model (Sec. IV) is qualitative; Table I only
  pins down the plain-malicious drop rate (70-80%). The other profiles' specific numbers are
  this implementation's own choices, documented in `trust_offload/node.py`.
- **Energy-Delay Product model:** the paper states the *principle* (failed tasks cost
  retransmission energy) but not a formula. This implementation charges failed/undispatched
  tasks a fixed retry-energy multiplier against payload size. See `RETRY_ENERGY_MULTIPLIER`
  in `trust_offload/simulator.py`.

## Honest results

Running `python experiments/run_all.py` (N=100 nodes, 10,000 tasks, 10% malicious, seed=42):

| Metric | Trust-Based | Random Baseline |
|---|---|---|
| Overall success rate | 98.8% | 89.5% |
| Average latency | 8.2 ms | 11.2 ms |
| Tasks failed | 118 | 1,055 (88.8% more) |
| Normalized EDP | 0.67 | 1.00 |

Directionally this matches the paper: trust-based clearly wins on success rate, latency, and
energy. The exact numbers differ from the paper's (96.2%/74.1%, 15.0ms/43.5ms, EDP 0.38) --
expected, since neither the RNG seed nor several parameters above are specified precisely
enough to reproduce exactly.

**Experiment A came out differently in shape, and that's worth explaining rather than
hiding.** The paper shows a symmetric bell curve peaking near tau=0.55. This simulation
instead shows a wide flat plateau (~99% success) from tau=0.0 up to about tau=0.94, then a
sharp cliff to 0% by tau=0.96. The reason: the asymmetric penalty (-0.045 per failure vs.
+0.025 per success) is aggressive enough that a misbehaving node's trust collapses within
roughly a dozen tasks *regardless* of where the threshold is set in the 0-0.9 range -- so the
exact cutoff barely matters there. The only place the threshold *does* matter is once it's
pushed above the trust ceiling that real hardware can reach, at which point the eligible
node pool collapses and tasks have nowhere to go. That's arguably a more useful finding than
the paper's stylized curve: it says the system is robust to threshold misconfiguration across
a wide practical range, and only becomes fragile if you set the threshold unrealistically
high. See `experiments/exp_a_threshold_sensitivity.py` for the sweep and plot.

## Project layout

```
trust_offload/       core package: trust scoring, node model, orchestrator, baseline, simulator, Markov analysis
experiments/         one script per paper figure (A-D) + run_all.py for the full sweep
tests/                pytest suite covering the trust formula, asymmetric update, quarantine, and the k=10 bound
results/              generated PNGs (git-tracked; regenerate anytime with run_all.py)
backend/              FastAPI wrapper around trust_offload (deployed to Railway) powering the live demo
frontend/             static HTML/JS site (Chart.js, no build step; deployed to Vercel) -- the live demo
```

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest                          # unit tests
python experiments/run_all.py   # aggregate comparison + all 4 experiment plots -> results/
```

To run the web demo locally: `uvicorn backend.main:app --reload --port 8123`, then open
`frontend/index.html` with `API_BASE_URL` pointed at `http://localhost:8123`.

## Scope

This covers the trust engine, orchestrator, Markov-chain validation, simulator, and all four
paper experiments (Sections III-IX), plus a live interactive demo (`backend/` + `frontend/`)
replacing the paper's proposed 1Hz JS dashboard (Section VIII) with an on-demand version:
every chart is computed by a real simulation run on request, not precomputed or 1Hz-streamed.
