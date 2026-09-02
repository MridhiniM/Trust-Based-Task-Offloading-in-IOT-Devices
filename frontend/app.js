const API_BASE_URL = "https://trust-offload-api-production.up.railway.app";

const CHART_COLORS = {
  trust: "#5b9dff",
  baseline: "#ff6b6b",
};

// Mirrors trust_offload/trust.py's TRUSTED_CUTOFF / QUARANTINE_CUTOFF.
const TRUSTED_CUTOFF = 0.75;
const QUARANTINE_CUTOFF = 0.55;

let cdfChart, edpChart, thresholdChart, saturationChart;

async function fetchJSON(path, options) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return res.json();
}

function toCdfPoints(sortedLatencies) {
  const n = sortedLatencies.length;
  return sortedLatencies.map((value, i) => ({ x: value, y: (i + 1) / n }));
}

function fmtPct(x) {
  return `${(x * 100).toFixed(1)}%`;
}

function fmtMs(x) {
  return `${x.toFixed(1)} ms`;
}

// ---- Simulate panel ----

function renderResultsTable(data) {
  const tbody = document.getElementById("results-tbody");
  const rows = [
    ["Success Rate", fmtPct(data.trust_based.success_rate), fmtPct(data.baseline.success_rate)],
    ["Average Latency", fmtMs(data.trust_based.avg_latency_ms), fmtMs(data.baseline.avg_latency_ms)],
    ["Tasks Failed", data.trust_based.failures, data.baseline.failures],
    ["Normalized EDP", data.trust_based.edp_normalized.toFixed(2), data.baseline.edp_normalized.toFixed(2)],
  ];
  tbody.innerHTML = rows
    .map(([label, trust, base]) => `<tr><td>${label}</td><td>${trust}</td><td>${base}</td></tr>`)
    .join("");
}

function renderCdfChart(data) {
  const ctx = document.getElementById("cdf-chart");
  if (cdfChart) cdfChart.destroy();
  cdfChart = new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Trust-Based",
          data: toCdfPoints(data.trust_based.latencies),
          borderColor: CHART_COLORS.trust,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Random Baseline",
          data: toCdfPoints(data.baseline.latencies),
          borderColor: CHART_COLORS.baseline,
          pointRadius: 0,
          borderWidth: 2,
          borderDash: [5, 4],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { type: "linear", title: { display: true, text: "Completion Latency (ms)" } },
        y: { title: { display: true, text: "Cumulative Probability" }, min: 0, max: 1 },
      },
    },
  });
}

function renderEdpChart(data) {
  const ctx = document.getElementById("edp-chart");
  if (edpChart) edpChart.destroy();
  edpChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Random Baseline", "Trust-Based"],
      datasets: [
        {
          data: [data.baseline.edp_normalized, data.trust_based.edp_normalized],
          backgroundColor: [CHART_COLORS.baseline, CHART_COLORS.trust],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { title: { display: true, text: "Normalized EDP" }, min: 0 } },
    },
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function nodeStateClass(trust, quarantined) {
  if (quarantined) return "quarantined";
  if (trust >= TRUSTED_CUTOFF) return "trusted";
  if (trust >= QUARANTINE_CUTOFF) return "suspicious";
  return "quarantined";
}

function layoutNodes(nodeSummaries) {
  const container = document.getElementById("network-viz");
  container.querySelectorAll(".node-box, .connector").forEach((el) => el.remove());

  const rect = container.getBoundingClientRect();
  const cx = rect.width / 2;
  const cy = rect.height / 2;
  const radius = Math.min(cx, cy) * 0.78;
  const n = nodeSummaries.length;

  const positions = {};
  const nodeBoxEls = {};

  nodeSummaries.forEach((node, i) => {
    const angle = (i / n) * 2 * Math.PI - Math.PI / 2;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    positions[node.node_id] = { x, y };

    const dx = x - cx;
    const dy = y - cy;
    const connector = document.createElement("div");
    connector.className = "connector";
    connector.style.width = `${Math.hypot(dx, dy)}px`;
    connector.style.left = `${cx}px`;
    connector.style.top = `${cy}px`;
    connector.style.transform = `rotate(${(Math.atan2(dy, dx) * 180) / Math.PI}deg)`;
    container.appendChild(connector);

    const box = document.createElement("div");
    box.className = `node-box ${nodeStateClass(node.initial_trust, false)}`;
    box.style.left = `${x}px`;
    box.style.top = `${y}px`;
    box.innerHTML = `<div class="node-id">${node.node_id}</div><div class="node-trust">τ=${node.initial_trust.toFixed(2)}</div>`;
    container.appendChild(box);
    nodeBoxEls[node.node_id] = box;
  });

  return { positions, nodeBoxEls, hubPos: { x: cx, y: cy } };
}

async function animatePacket(ev, positions, hubPos, nodeBoxEls, container, flightMs) {
  const pos = positions[ev.node_id];
  if (!pos) return;

  const packet = document.createElement("div");
  packet.className = `packet${ev.success ? "" : " fail"}`;
  packet.style.transition = `left ${flightMs}ms linear, top ${flightMs}ms linear`;
  packet.style.left = `${hubPos.x}px`;
  packet.style.top = `${hubPos.y}px`;
  container.appendChild(packet);
  packet.getBoundingClientRect(); // force reflow so the position change transitions
  packet.style.left = `${pos.x}px`;
  packet.style.top = `${pos.y}px`;

  await sleep(flightMs);
  packet.remove();

  const box = nodeBoxEls[ev.node_id];
  if (!box) return;

  box.classList.remove("pulse-success", "pulse-fail");
  void box.offsetWidth; // restart the pulse animation even on repeat outcomes
  box.classList.add(ev.success ? "pulse-success" : "pulse-fail");

  const trustLabel = box.querySelector(".node-trust");
  if (ev.trust_after != null) trustLabel.textContent = `τ=${ev.trust_after.toFixed(2)}`;

  box.classList.remove("trusted", "suspicious", "quarantined");
  box.classList.add(nodeStateClass(ev.trust_after ?? 0, ev.quarantined));

  if (ev.quarantined && !box.querySelector(".quarantine-badge")) {
    const badge = document.createElement("div");
    badge.className = "quarantine-badge";
    box.appendChild(badge);
  }
}

async function playTrace(events, positions, hubPos, nodeBoxEls, container) {
  const total = events.length;
  let dispatched = 0;
  let successes = 0;
  const quarantined = new Set();

  const taskStat = document.getElementById("stat-task");
  const successStat = document.getElementById("stat-success");
  const quarantinedStat = document.getElementById("stat-quarantined");
  const speedSelect = document.getElementById("live_speed");

  for (const ev of events) {
    const flightMs = Number(speedSelect.value); // read live so mid-playback speed changes apply
    if (ev.node_id) {
      dispatched += 1;
      if (ev.success) successes += 1;
      await animatePacket(ev, positions, hubPos, nodeBoxEls, container, flightMs);
      if (ev.quarantined) quarantined.add(ev.node_id);
    } else {
      await sleep(flightMs); // no eligible node -- still pace the stalled step visibly
    }

    taskStat.textContent = `${ev.task_index + 1} / ${total}`;
    successStat.textContent = dispatched ? fmtPct(successes / dispatched) : "—";
    quarantinedStat.textContent = String(quarantined.size);
  }
}

async function runLiveSimulation(event) {
  event.preventDefault();
  const statusEl = document.getElementById("live-status");
  const runBtn = document.getElementById("live-run-btn");
  const resultsEl = document.getElementById("simulate-results");
  const statsEl = document.getElementById("live-stats");
  const container = document.getElementById("network-viz");

  const params = {
    n_nodes: Number(document.getElementById("live_n_nodes").value),
    n_tasks: Number(document.getElementById("live_n_tasks").value),
    malicious_fraction: Number(document.getElementById("live_malicious_pct").value) / 100,
    tau_threshold: Number(document.getElementById("live_tau_threshold").value),
    seed: Math.floor(Math.random() * 1e6),
  };

  runBtn.disabled = true;
  statusEl.hidden = false;
  statusEl.classList.remove("error");
  statusEl.textContent = "Starting live run...";
  statsEl.hidden = false;
  resultsEl.hidden = true;

  try {
    const tracePromise = fetchJSON("/simulate/live", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    const comparisonPromise = fetchJSON("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });

    const traceData = await tracePromise;
    statusEl.hidden = true;

    const { positions, nodeBoxEls, hubPos } = layoutNodes(traceData.nodes);
    const playPromise = playTrace(traceData.events, positions, hubPos, nodeBoxEls, container);

    const [comparisonData] = await Promise.all([comparisonPromise, playPromise]);

    renderResultsTable(comparisonData);
    renderCdfChart(comparisonData);
    renderEdpChart(comparisonData);
    resultsEl.hidden = false;
  } catch (err) {
    statusEl.hidden = false;
    statusEl.classList.add("error");
    statusEl.textContent = `Failed to reach the simulator API: ${err.message}. The backend may be waking up (Railway free tier sleeps when idle) -- try again in a few seconds.`;
  } finally {
    runBtn.disabled = false;
  }
}

// ---- Threshold sensitivity panel ----

async function loadThresholdSensitivity() {
  const btn = document.getElementById("threshold-rerun");
  btn.disabled = true;
  try {
    const data = await fetchJSON("/experiments/threshold-sensitivity");
    const ctx = document.getElementById("threshold-chart");
    if (thresholdChart) thresholdChart.destroy();
    thresholdChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.thresholds,
        datasets: [
          {
            label: "Task Success Rate",
            data: data.success_rates.map((r) => r * 100),
            borderColor: CHART_COLORS.trust,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: "Trust Threshold (τ)" } },
          y: { title: { display: true, text: "Success Rate (%)" }, min: 0, max: 100 },
        },
      },
    });
  } catch (err) {
    console.error(err);
  } finally {
    btn.disabled = false;
  }
}

// ---- Saturation panel ----

async function loadSaturation() {
  const btn = document.getElementById("saturation-rerun");
  btn.disabled = true;
  try {
    const data = await fetchJSON("/experiments/saturation");
    const ctx = document.getElementById("saturation-chart");
    if (saturationChart) saturationChart.destroy();
    saturationChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.malicious_pcts,
        datasets: [
          {
            label: "Trust-Based",
            data: data.trust_rates.map((r) => r * 100),
            borderColor: CHART_COLORS.trust,
            borderWidth: 2,
          },
          {
            label: "Random Baseline",
            data: data.baseline_rates.map((r) => r * 100),
            borderColor: CHART_COLORS.baseline,
            borderWidth: 2,
            borderDash: [5, 4],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: "Malicious Nodes (%)" } },
          y: { title: { display: true, text: "Success Rate (%)" }, min: 0, max: 100 },
        },
      },
    });
  } catch (err) {
    console.error(err);
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("live-form").addEventListener("submit", runLiveSimulation);
document.getElementById("threshold-rerun").addEventListener("click", loadThresholdSensitivity);
document.getElementById("saturation-rerun").addEventListener("click", loadSaturation);

loadThresholdSensitivity();
loadSaturation();
