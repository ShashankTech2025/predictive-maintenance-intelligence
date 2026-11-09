/**
 * Predictive Maintenance Intelligence - Dashboard Controller
 * Fetches live fleet statistics and renders responsive Plotly visualizations.
 */

document.addEventListener("DOMContentLoaded", () => {
  loadDashboardData();
});

async function loadDashboardData() {
  try {
    const res = await API.getDashboardStats();
    if (res.status === "success") {
      const data = res.data;
      renderKPIs(data);
      renderCharts(data);
      renderMachineTable(data.machine_statuses);
      renderMaintenanceList(data.recent_maintenance);
    }
  } catch (err) {
    console.error("Dashboard failed to load:", err);
    document.getElementById("fleet-status-tbody").innerHTML = `
      <tr>
        <td colspan="7" class="text-center text-danger py-4">
          <i class="bi bi-exclamation-triangle fs-3 d-block mb-2"></i>
          Failed to load live fleet telemetry. Please check API connection.
        </td>
      </tr>
    `;
  }
}

function renderKPIs(data) {
  document.getElementById("kpi-total-machines").textContent = data.total_machines || 0;
  document.getElementById("kpi-high-risk").textContent = data.high_risk_alerts || 0;
  document.getElementById("kpi-total-predictions").textContent = data.total_predictions || 0;
  document.getElementById("kpi-sensor-readings").textContent = data.total_sensor_readings || 0;
}

function renderCharts(data) {
  // 1. Risk Distribution Donut Chart
  const riskDist = data.risk_distribution || {};
  const donutLabels = ["LOW Risk", "MEDIUM Risk", "HIGH Risk", "Unmonitored"];
  const donutValues = [
    riskDist.LOW || 0,
    riskDist.MEDIUM || 0,
    riskDist.HIGH || 0,
    riskDist.UNMONITORED || 0
  ];
  const donutColors = ["#10B981", "#F59E0B", "#EF4444", "#94A3B8"];

  const donutData = [{
    values: donutValues,
    labels: donutLabels,
    type: "pie",
    hole: 0.65,
    marker: { colors: donutColors },
    textinfo: "value",
    hoverinfo: "label+percent+value",
    textposition: "inside"
  }];

  const donutLayout = {
    showlegend: true,
    legend: { orientation: "h", y: -0.1, x: 0.1 },
    margin: { t: 10, b: 30, l: 10, r: 10 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "Inter, sans-serif", size: 11, color: "#475569" }
  };

  Plotly.newPlot("chart-risk-distribution", donutData, donutLayout, { responsive: true, displayModeBar: false });

  // 2. Machine-wise Failure Probability Bar Chart
  const machines = data.machine_statuses || [];
  const names = machines.map(m => m.machine_name);
  const probs = machines.map(m => m.failure_probability !== null ? m.failure_probability : 0);
  const barColors = probs.map(p => {
    if (p >= 40.0) return "#EF4444";
    if (p >= 20.0) return "#F59E0B";
    return "#10B981";
  });

  const barData = [{
    x: names,
    y: probs,
    type: "bar",
    marker: { color: barColors, borderRadius: 4 },
    text: probs.map(p => `${p.toFixed(1)}%`),
    textposition: "auto"
  }];

  const barLayout = {
    margin: { t: 20, b: 40, l: 40, r: 10 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "Inter, sans-serif", size: 11, color: "#475569" },
    yaxis: {
      title: "Failure Probability (%)",
      range: [0, 100],
      gridcolor: "#F1F5F9"
    },
    xaxis: {
      gridcolor: "transparent"
    },
    shapes: [{
      type: "line",
      x0: -0.5,
      x1: Math.max(names.length - 0.5, 0.5),
      y0: 40,
      y1: 40,
      line: { color: "#DC2626", width: 1.5, dash: "dot" }
    }]
  };

  Plotly.newPlot("chart-machine-probabilities", barData, barLayout, { responsive: true, displayModeBar: false });
}

function renderMachineTable(machines) {
  const tbody = document.getElementById("fleet-status-tbody");
  if (!machines || machines.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-4 text-muted">
          No registered machines found. Click "New Prediction" or visit Machine Monitoring to register equipment.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = machines.map(m => {
    const prob = m.failure_probability !== null ? m.failure_probability : null;
    const probDisplay = prob !== null ? `${prob.toFixed(2)}%` : "Not assessed";
    
    let riskBadge = `<span class="badge bg-light text-muted border">UNMONITORED</span>`;
    let statusClass = "text-muted";
    let progressColor = "bg-secondary";

    if (m.risk_level === "HIGH") {
      riskBadge = `<span class="badge-risk badge-risk-high"><i class="bi bi-exclamation-octagon-fill"></i> HIGH</span>`;
      statusClass = "text-danger fw-bold";
      progressColor = "bg-danger";
    } else if (m.risk_level === "MEDIUM") {
      riskBadge = `<span class="badge-risk badge-risk-medium"><i class="bi bi-exclamation-circle-fill"></i> MEDIUM</span>`;
      statusClass = "text-warning fw-bold";
      progressColor = "bg-warning";
    } else if (m.risk_level === "LOW") {
      riskBadge = `<span class="badge-risk badge-risk-low"><i class="bi bi-check-circle-fill"></i> LOW</span>`;
      statusClass = "text-success fw-bold";
      progressColor = "bg-success";
    }

    const lastTime = m.predicted_at ? m.predicted_at.replace("T", " ").substring(0, 19) : "Never";

    return `
      <tr>
        <td class="fw-semibold text-primary">
          <i class="bi bi-hdd me-1 text-muted"></i> ${m.machine_name}
        </td>
        <td>
          <span class="badge-type">Type ${m.machine_type}</span>
        </td>
        <td style="min-width: 140px;">
          <div class="d-flex align-items-center gap-2">
            <span class="small fw-semibold">${probDisplay}</span>
            ${prob !== null ? `
              <div class="progress flex-grow-1" style="height: 6px;">
                <div class="progress-bar ${progressColor}" style="width: ${Math.min(prob, 100)}%"></div>
              </div>
            ` : ""}
          </div>
        </td>
        <td class="${statusClass}">
          ${m.machine_status || "UNASSESSED"}
        </td>
        <td>${riskBadge}</td>
        <td class="text-muted small">${lastTime}</td>
        <td class="text-end">
          <a href="/predict?machine_id=${m.machine_id}" class="btn btn-sm btn-outline-primary me-1" title="Run Diagnostics">
            <i class="bi bi-lightning-charge"></i>
          </a>
          <a href="/api/reports/pdf/${m.machine_id}" target="_blank" class="btn btn-sm btn-outline-secondary" title="Download PDF Certificate">
            <i class="bi bi-file-earmark-pdf"></i>
          </a>
        </td>
      </tr>
    `;
  }).join("");
}

function renderMaintenanceList(records) {
  const container = document.getElementById("recent-maintenance-list");
  if (!records || records.length === 0) {
    container.innerHTML = `
      <div class="empty-state py-3">
        <i class="bi bi-check2-circle fs-3 text-success"></i>
        <p class="mb-0">No active maintenance directives. All machines within safe operating bounds.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = records.slice(0, 5).map(r => {
    let priorityClass = "priority-low";
    let badgeClass = "badge-risk-low";
    if (r.priority === "HIGH") {
      priorityClass = "priority-high";
      badgeClass = "badge-risk-high";
    } else if (r.priority === "MEDIUM") {
      priorityClass = "priority-medium";
      badgeClass = "badge-risk-medium";
    }

    const isResolved = r.status === "RESOLVED";

    return `
      <div class="directive-card ${priorityClass} ${isResolved ? 'status-resolved' : ''}">
        <div>
          <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge-risk ${badgeClass}" style="font-size: 0.65rem;">${r.priority} PRIORITY</span>
            <span class="fw-semibold text-primary" style="font-size: 0.85rem;">${r.machine_name}</span>
            <span class="text-muted" style="font-size: 0.75rem;">&bull; ${r.created_at ? r.created_at.substring(0, 16) : ""}</span>
          </div>
          <div style="font-size: 0.85rem; color: #334155;">${r.action_item}</div>
        </div>
        <div class="ms-3">
          ${isResolved 
            ? `<span class="badge bg-light text-muted border"><i class="bi bi-check-lg"></i> Resolved</span>`
            : `<button class="btn btn-sm btn-outline-secondary" onclick="resolveDirective(${r.record_id}, this)">
                <i class="bi bi-check2"></i> Complete
               </button>`
          }
        </div>
      </div>
    `;
  }).join("");
}

async function resolveDirective(recordId, btn) {
  btn.disabled = true;
  try {
    const res = await API.updateMaintenanceStatus(recordId, "RESOLVED");
    if (res.status === "success") {
      API.showToast("Maintenance task marked as completed.", "success");
      loadDashboardData();
    }
  } catch (err) {
    btn.disabled = false;
  }
}

