/**
 * Predictive Maintenance Intelligence - Reports Portal Controller
 * Manages CSV streaming and ReportLab PDF certificate downloads.
 */

document.addEventListener("DOMContentLoaded", () => {
  loadReportsCatalog();

  document.getElementById("btn-download-selected-pdf").addEventListener("click", () => {
    const select = document.getElementById("report-machine-select");
    const machineId = select.value;
    if (!machineId) {
      API.showToast("Please select an equipment unit from the dropdown.", "warning");
      return;
    }
    window.open(`/api/reports/pdf/${machineId}`, "_blank");
  });
});

async function loadReportsCatalog() {
  try {
    const res = await API.getMachines();
    if (res.status === "success") {
      const machines = res.data || [];
      populateDropdown(machines);
      renderReportsTable(machines);
    }
  } catch (err) {
    document.getElementById("reports-library-tbody").innerHTML = `
      <tr>
        <td colspan="7" class="text-center text-danger py-4">Failed to load reports catalog.</td>
      </tr>
    `;
  }
}

function populateDropdown(machines) {
  const select = document.getElementById("report-machine-select");
  if (!machines || machines.length === 0) {
    select.innerHTML = `<option value="" disabled selected>No registered machines found</option>`;
    return;
  }

  select.innerHTML = `
    <option value="" disabled selected>Select machine unit...</option>
    ${machines.map(m => `
      <option value="${m.machine_id}">
        ${m.machine_name} (Type ${m.machine_type}) - ${m.machine_status || 'Unassessed'}
      </option>
    `).join("")}
  `;
}

function renderReportsTable(machines) {
  const tbody = document.getElementById("reports-library-tbody");
  if (!machines || machines.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-4 text-muted">No machines registered in fleet catalog.</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = machines.map(m => {
    const prob = m.failure_probability !== null ? `${m.failure_probability.toFixed(2)}%` : "Not evaluated";
    const isFailure = m.machine_status === "FAILURE RISK";
    const statusClass = isFailure ? "text-danger fw-bold" : "text-success fw-bold";
    const lastTime = m.predicted_at ? m.predicted_at.replace("T", " ").substring(0, 19) : "Never";

    return `
      <tr>
        <td class="text-muted fw-semibold">#${m.machine_id}</td>
        <td class="fw-semibold text-primary">
          <i class="bi bi-hdd me-1 text-muted"></i> ${m.machine_name}
        </td>
        <td><span class="badge-type">Type ${m.machine_type}</span></td>
        <td class="fw-semibold">${prob}</td>
        <td class="${statusClass}">${m.machine_status || "UNASSESSED"}</td>
        <td class="text-muted small">${lastTime}</td>
        <td class="text-end">
          <a href="/api/reports/pdf/${m.machine_id}" target="_blank" class="btn btn-sm btn-outline-primary" title="Download Official PDF Certificate">
            <i class="bi bi-file-earmark-pdf-fill me-1"></i> PDF Certificate
          </a>
        </td>
      </tr>
    `;
  }).join("");
}

