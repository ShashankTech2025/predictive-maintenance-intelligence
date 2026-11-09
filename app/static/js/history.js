/**
 * Predictive Maintenance Intelligence - Prediction History Controller
 * Displays historical prediction audit trail with filtering and export capabilities.
 */

let historyRecords = [];

document.addEventListener("DOMContentLoaded", () => {
  loadHistoryData();

  document.getElementById("history-search").addEventListener("input", filterAndRenderHistory);
  document.getElementById("history-status-filter").addEventListener("change", filterAndRenderHistory);
  document.getElementById("history-reset-btn").addEventListener("click", () => {
    document.getElementById("history-search").value = "";
    document.getElementById("history-status-filter").value = "";
    filterAndRenderHistory();
  });
});

async function loadHistoryData() {
  try {
    const res = await API.getPredictions(100, 0);
    if (res.status === "success") {
      historyRecords = res.data || [];
      filterAndRenderHistory();
    }
  } catch (err) {
    document.getElementById("history-tbody").innerHTML = `
      <tr>
        <td colspan="9" class="text-center text-danger py-4">
          <i class="bi bi-exclamation-triangle fs-4 d-block mb-1"></i>
          Failed to load historical predictions.
        </td>
      </tr>
    `;
  }
}

function filterAndRenderHistory() {
  const search = document.getElementById("history-search").value.trim().toLowerCase();
  const statusFilter = document.getElementById("history-status-filter").value;

  const filtered = historyRecords.filter(r => {
    const matchesSearch = !search || r.machine_name.toLowerCase().includes(search) || String(r.prediction_id).includes(search);
    const matchesStatus = !statusFilter || r.machine_status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  document.getElementById("history-count").textContent = filtered.length;
  renderHistoryTable(filtered);
}

function renderHistoryTable(records) {
  const tbody = document.getElementById("history-tbody");
  if (!records || records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-5">
          <div class="empty-state py-2">
            <i class="bi bi-clock-history fs-2"></i>
            <h3>No Prediction Logs Recorded</h3>
            <p>No historical telemetry assessments match your query.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const prob = r.failure_probability !== null ? r.failure_probability : 0;
    const isFailure = r.machine_status === "FAILURE RISK";
    const statusClass = isFailure ? "text-danger fw-bold" : "text-success fw-bold";
    const progressColor = isFailure ? "bg-danger" : (prob >= 20 ? "bg-warning" : "bg-success");

    let riskBadge = `<span class="badge-risk badge-risk-low">LOW</span>`;
    if (r.risk_level === "HIGH") {
      riskBadge = `<span class="badge-risk badge-risk-high">HIGH</span>`;
    } else if (r.risk_level === "MEDIUM") {
      riskBadge = `<span class="badge-risk badge-risk-medium">MEDIUM</span>`;
    }

    return `
      <tr>
        <td class="text-muted fw-semibold">#${r.prediction_id}</td>
        <td class="fw-semibold text-primary">
          <i class="bi bi-hdd me-1 text-muted"></i> ${r.machine_name}
        </td>
        <td><span class="badge-type">Type ${r.machine_type}</span></td>
        <td style="min-width: 130px;">
          <div class="d-flex align-items-center gap-2">
            <span class="small fw-semibold">${prob.toFixed(2)}%</span>
            <div class="progress flex-grow-1" style="height: 6px;">
              <div class="progress-bar ${progressColor}" style="width: ${Math.min(prob, 100)}%"></div>
            </div>
          </div>
        </td>
        <td class="${statusClass}">${r.machine_status}</td>
        <td>${riskBadge}</td>
        <td class="small text-secondary" style="max-width: 320px;">
          <div class="text-truncate" title="${r.recommendations || ''}">${r.recommendations || "None"}</div>
        </td>
        <td class="text-muted small">${r.predicted_at ? r.predicted_at.substring(0, 19) : "N/A"}</td>
        <td class="text-end">
          <a href="/api/reports/pdf/${r.machine_id}" target="_blank" class="btn btn-sm btn-outline-secondary" title="Download PDF Certificate">
            <i class="bi bi-file-earmark-pdf"></i> PDF
          </a>
        </td>
      </tr>
    `;
  }).join("");
}

