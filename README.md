# Trust-Based Task Offloading Framework (TBTOF)

**[Live interactive demo →](https://trust-based-task-offloading-in-iot-devices-mridhini.vercel.app)** (frontend on Vercel, simulator API on Railway — the demo runs the actual simulator live, nothing is precomputed)
**[Read the paper (PDF) →](paper/Trust-Based-Task-Offloading-Framework.pdf)**

A working implementation of the trust engine, orchestrator, and simulator described in
*"Trust-Based Task Offloading Framework for Edge-Based IoT Systems"* (Anitha H.M., Nalina V.,
Madhusudan, Shakthi, S.P.) — included in this repo at
[`paper/Trust-Based-Task-Offloading-Framework.pdf`](paper/Trust-Based-Task-Offloading-Framework.pdf).
It scores edge nodes on task success rate, CPU availability,
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
  eligible nodes (`TrustOrchestrator.dispatch()` in `trust_offload/orchestrator.py`), not a
  strict argmax. A strict argmax was tried first and made almost the entire 10,000-task
  workload land on a single top-ranked node regardless of how many other nodes were
  eligible -- unrealistic, and it made the trust threshold nearly irrelevant to the outcome
  (see the correction note under "Honest results" below; this was caught late, after it had
  already produced misleadingly clean-looking results). Weighted-random selection spreads
  load roughly the way a real scheduler would. `select_node()` (strict argmax) is kept as a
  separate method for tests that need a deterministic "best node" check.
- **Malicious/whitewashing/resource-exhaustion behavior parameters** (drop-rate ranges,
  whitewashing phase length): the paper's threat model (Sec. IV) is qualitative; Table I only
  pins down the plain-malicious drop rate (70-80%). The other profiles' specific numbers are
  this implementation's own choices, documented in `trust_offload/node.py`.
- **Energy-Delay Product model:** the paper states the *principle* (failed tasks cost
  retransmission energy) but not a formula. This implementation charges failed/undispatched
  tasks a fixed retry-energy multiplier against payload size. See `RETRY_ENERGY_MULTIPLIER`
  in `trust_offload/simulator.py`.

## Honest results

**Correction (2026-09-03):** an earlier version of this README reported results produced under
a node-selection bug: `dispatch()` called a strict-argmax `select_node()` instead of the
weighted-random policy described above and below. In practice this meant one or two
top-ranked nodes absorbed nearly all traffic for the entire run, so misbehaving nodes rarely
got dispatched to at all -- the framework looked *more* robust than it actually is, and the
trust threshold barely mattered (Experiment A came out as a flat line). The bug was caught
while building an animated visualization of per-task dispatches, where the same 2-3 node IDs
lighting up on every single task made the problem obvious. It's fixed now (`dispatch()`
actually uses weighted-random selection), and every number below reflects the corrected code.
This is left in rather than quietly edited away because catching your own bugs is part of
"honest simulation," not a footnote.

Running `python experiments/run_all.py` (N=100 nodes, 10,000 tasks, 10% malicious, seed=42):

| Metric | Trust-Based | Random Baseline |
|---|---|---|
| Overall success rate | 95.3% | 89.5% |
| Average latency | 9.9 ms | 11.2 ms |
| Tasks failed | 471 | 1,055 (55.4% fewer) |
| Normalized EDP | 0.83 | 1.00 |

Directionally this still matches the paper: trust-based wins on success rate, latency, and
energy, just by smaller margins than before the fix -- expected, since letting misbehaving
nodes actually receive their proportional share of traffic (instead of almost never being
picked) means they now do real, if bounded, damage before quarantine kicks in. The exact
numbers differ from the paper's (96.2%/74.1%, 15.0ms/43.5ms, EDP 0.38); neither the RNG seed
nor several parameters above are specified precisely enough to reproduce exactly.

**Experiment A now shows real threshold sensitivity, not a flat line.** Success rate rises
gradually from 95.3% at tau=0.0 to 98.6% at tau=0.95 -- a low threshold now measurably costs
you, because weighted-random selection means a misbehaving node keeps getting *some* traffic
for as long as it stays eligible, not just a brief window before an argmax simply stops
picking it. Above tau=0.95 there's still a sharp cliff to 0%, once the threshold exceeds the
trust ceiling real hardware can reach and the eligible pool collapses. It's still not the
paper's symmetric bell curve (nothing in this model penalizes a threshold for being merely
*strict*, only for excluding literally everyone), but it's now a genuine monotonic-plus-cliff
story instead of an artifact of a selection bug. See `experiments/exp_a_threshold_sensitivity.py`.

**Experiment D's resilience curve is more believable now too:** trust-based and baseline start
close together at 0% malicious (96.0% vs 96.1%) and diverge as malicious saturation rises, with
trust-based ahead by about 13 points at 50% malicious (73.2% vs 59.9%) -- a real, gradually
widening advantage, rather than the suspiciously flat ~98.6%-regardless-of-saturation line the
bug produced.

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
