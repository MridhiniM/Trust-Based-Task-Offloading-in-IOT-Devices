const API_BASE_URL = "https://trust-offload-api-production.up.railway.app";

const CHART_COLORS = {
  trust: "#5b9dff",
  baseline: "#ff6b6b",
};

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

async function runSimulation(event) {
  event.preventDefault();
  const statusEl = document.getElementById("simulate-status");
  const resultsEl = document.getElementById("simulate-results");
  const runBtn = document.getElementById("run-btn");

  const body = {
    n_nodes: Number(document.getElementById("n_nodes").value),
    n_tasks: Number(document.getElementById("n_tasks").value),
    malicious_fraction: Number(document.getElementById("malicious_pct").value) / 100,
    tau_threshold: Number(document.getElementById("tau_threshold").value),
    seed: Math.floor(Math.random() * 1e6),
  };

  runBtn.disabled = true;
  statusEl.hidden = false;
  statusEl.classList.remove("error");
  statusEl.textContent = "Running simulation...";
  resultsEl.hidden = true;

  try {
    const data = await fetchJSON("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderResultsTable(data);
    renderCdfChart(data);
    renderEdpChart(data);
    resultsEl.hidden = false;
    statusEl.hidden = true;
  } catch (err) {
    statusEl.textContent = `Failed to reach the simulator API: ${err.message}. The backend may be waking up (Railway free tier sleeps when idle) -- try again in a few seconds.`;
    statusEl.classList.add("error");
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

document.getElementById("simulate-form").addEventListener("submit", runSimulation);
document.getElementById("threshold-rerun").addEventListener("click", loadThresholdSensitivity);
document.getElementById("saturation-rerun").addEventListener("click", loadSaturation);

loadThresholdSensitivity();
loadSaturation();
