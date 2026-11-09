/**
 * Predictive Maintenance Intelligence - Machine Monitoring Controller
 * Handles fleet filtering, equipment registration, and historical inspection modal.
 */

let allMachines = [];

document.addEventListener("DOMContentLoaded", () => {
  loadMachines();

  // Filter event listeners
  document.getElementById("machine-search").addEventListener("input", debounce(filterAndRender, 250));
  document.getElementById("machine-type-filter").addEventListener("change", filterAndRender);
  document.getElementById("machine-status-filter").addEventListener("change", filterAndRender);
  document.getElementById("reset-filters-btn").addEventListener("click", resetFilters);

  // Machine registration form
  document.getElementById("register-machine-form").addEventListener("submit", handleMachineRegistration);
});

function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

async function loadMachines() {
  try {
    const res = await API.getMachines();
    if (res.status === "success") {
      allMachines = res.data || [];
      filterAndRender();
    }
  } catch (err) {
    document.getElementById("machines-tbody").innerHTML = `
      <tr>
        <td colspan="8" class="text-center text-danger py-4">
          <i class="bi bi-exclamation-triangle fs-4 d-block mb-1"></i>
          Failed to load equipment list. Please verify server connection.
        </td>
      </tr>
    `;
  }
}

function filterAndRender() {
  const search = document.getElementById("machine-search").value.trim().toLowerCase();
  const typeFilter = document.getElementById("machine-type-filter").value;
  const statusFilter = document.getElementById("machine-status-filter").value;

  const filtered = allMachines.filter(m => {
    const matchesSearch = !search || m.machine_name.toLowerCase().includes(search) || String(m.machine_id).includes(search);
    const matchesType = !typeFilter || m.machine_type === typeFilter;
    const matchesStatus = !statusFilter || (m.machine_status === statusFilter);
    return matchesSearch && matchesType && matchesStatus;
  });

  document.getElementById("machine-count").textContent = filtered.length;
  renderTable(filtered);
}

function resetFilters() {
  document.getElementById("machine-search").value = "";
  document.getElementById("machine-type-filter").value = "";
  document.getElementById("machine-status-filter").value = "";
  filterAndRender();
}

function renderTable(machines) {
  const tbody = document.getElementById("machines-tbody");
  if (!machines || machines.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-5">
          <div class="empty-state py-2">
            <i class="bi bi-search fs-2"></i>
            <h3>No Equipment Found</h3>
            <p>No machines match the selected filter criteria. Try resetting filters.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = machines.map(m => {
    const prob = m.failure_probability !== null ? m.failure_probability : null;
    const probDisplay = prob !== null ? `${prob.toFixed(2)}%` : "Not evaluated";

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

    let telemetryHtml = `<span class="text-muted small">No sensor logs</span>`;
    if (m.air_temperature !== null && m.rotational_speed !== null) {
      telemetryHtml = `
        <div style="font-size: 0.78rem; line-height: 1.3;">
          <span class="text-secondary">Air: <b>${m.air_temperature}K</b></span> &bull; 
          <span class="text-secondary">RPM: <b>${m.rotational_speed}</b></span><br>
          <span class="text-secondary">Torque: <b>${m.torque}Nm</b></span> &bull; 
          <span class="text-secondary">Wear: <b>${m.tool_wear}m</b></span>
        </div>
      `;
    }

    const lastTime = m.predicted_at ? m.predicted_at.replace("T", " ").substring(0, 19) : "Never";

    return `
      <tr>
        <td class="text-muted fw-semibold">#${m.machine_id}</td>
        <td class="fw-semibold text-primary">
          <i class="bi bi-hdd me-1 text-muted"></i> ${m.machine_name}
        </td>
        <td><span class="badge-type">Type ${m.machine_type}</span></td>
        <td style="min-width: 130px;">
          <div class="d-flex align-items-center gap-2">
            <span class="small fw-semibold">${probDisplay}</span>
            ${prob !== null ? `
              <div class="progress flex-grow-1" style="height: 6px;">
                <div class="progress-bar ${progressColor}" style="width: ${Math.min(prob, 100)}%"></div>
              </div>
            ` : ""}
          </div>
        </td>
        <td class="${statusClass}">${m.machine_status || "UNASSESSED"}</td>
        <td>${telemetryHtml}</td>
        <td class="text-muted small">${lastTime}</td>
        <td class="text-end">
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-secondary" onclick="openMachineHistory(${m.machine_id})" title="Inspect History">
              <i class="bi bi-clock-history"></i>
            </button>
            <a href="/predict?machine_id=${m.machine_id}" class="btn btn-outline-primary" title="Run Diagnostics">
              <i class="bi bi-lightning-charge"></i>
            </a>
            <a href="/api/reports/pdf/${m.machine_id}" target="_blank" class="btn btn-outline-secondary" title="Download PDF Certificate">
              <i class="bi bi-file-earmark-pdf"></i>
            </a>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

async function handleMachineRegistration(e) {
  e.preventDefault();
  const nameInput = document.getElementById("reg-machine-name");
  const typeSelect = document.getElementById("reg-machine-type");
  const saveBtn = document.getElementById("btn-save-machine");

  const name = nameInput.value.trim();
  const type = typeSelect.value;

  if (!name || !type) {
    API.showToast("Machine name and type are required.", "warning");
    return;
  }

  saveBtn.disabled = true;
  saveBtn.innerHTML = `<span class="loading-spinner" style="width: 1rem; height: 1rem;"></span> Registering...`;

  try {
    const res = await API.createMachine({ machine_name: name, machine_type: type });
    if (res.status === "success") {
      API.showToast(`Machine '${name}' registered successfully!`, "success");
      
      // Close modal
      const modalEl = document.getElementById("registerMachineModal");
      const modalInstance = bootstrap.Modal.getInstance(modalEl);
      if (modalInstance) modalInstance.hide();
      
      nameInput.value = "";
      typeSelect.value = "";
      loadMachines();
    }
  } catch (err) {
    // Error handled by API.showToast in api_client.js
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = `<i class="bi bi-check-lg"></i> Register Equipment`;
  }
}

async function openMachineHistory(machineId) {
  try {
    const res = await API.getMachineHistory(machineId);
    if (res.status === "success") {
      const data = res.data;
      const machine = data.machine;

      document.getElementById("history-modal-machine-name").textContent = `${machine.machine_name} (Type ${machine.machine_type})`;
      document.getElementById("btn-modal-pdf").href = `/api/reports/pdf/${machine.machine_id}`;

      // Metadata summary
      document.getElementById("history-machine-meta").innerHTML = `
        <div class="col-sm-4">
          <small class="text-muted d-block">Machine ID</small>
          <strong>#${machine.machine_id}</strong>
        </div>
        <div class="col-sm-4">
          <small class="text-muted d-block">Variant Class</small>
          <span class="badge-type">Type ${machine.machine_type}</span>
        </div>
        <div class="col-sm-4">
          <small class="text-muted d-block">Registered Timestamp</small>
          <span>${machine.created_at ? machine.created_at.substring(0, 19) : "N/A"}</span>
        </div>
      `;

      // Render Predictions tab
      const preds = data.prediction_history || [];
      const pTbody = document.getElementById("history-predictions-tbody");
      if (preds.length === 0) {
        pTbody.innerHTML = `<tr><td colspan="6" class="text-center py-3 text-muted">No prediction history recorded.</td></tr>`;
      } else {
        pTbody.innerHTML = preds.map(p => `
          <tr>
            <td>#${p.prediction_id}</td>
            <td class="fw-bold">${p.failure_probability.toFixed(2)}%</td>
            <td class="${p.machine_status === 'FAILURE RISK' ? 'text-danger fw-bold' : 'text-success'}">${p.machine_status}</td>
            <td><span class="badge-risk badge-risk-${p.risk_level.toLowerCase()}">${p.risk_level}</span></td>
            <td class="small text-secondary">${p.recommendations || "None"}</td>
            <td class="text-muted small">${p.predicted_at ? p.predicted_at.substring(0, 19) : ""}</td>
          </tr>
        `).join("");
      }

      // Render Sensors tab
      const sensors = data.sensor_history || [];
      const sTbody = document.getElementById("history-sensors-tbody");
      if (sensors.length === 0) {
        sTbody.innerHTML = `<tr><td colspan="7" class="text-center py-3 text-muted">No telemetry logs recorded.</td></tr>`;
      } else {
        sTbody.innerHTML = sensors.map(s => `
          <tr>
            <td>#${s.reading_id}</td>
            <td>${s.air_temperature.toFixed(1)} K</td>
            <td>${s.process_temperature.toFixed(1)} K</td>
            <td>${s.rotational_speed.toFixed(0)} rpm</td>
            <td>${s.torque.toFixed(1)} Nm</td>
            <td>${s.tool_wear.toFixed(0)} min</td>
            <td class="text-muted small">${s.recorded_at ? s.recorded_at.substring(0, 19) : ""}</td>
          </tr>
        `).join("");
      }

      // Render Tasks tab
      const tasks = data.maintenance_history || [];
      const taskContainer = document.getElementById("history-tasks-container");
      if (tasks.length === 0) {
        taskContainer.innerHTML = `<div class="empty-state py-3"><p class="mb-0">No maintenance records logged.</p></div>`;
      } else {
        taskContainer.innerHTML = tasks.map(t => `
          <div class="directive-card priority-${t.priority.toLowerCase()} ${t.status === 'RESOLVED' ? 'status-resolved' : ''}">
            <div>
              <span class="badge-risk badge-risk-${t.priority.toLowerCase()} mb-1" style="font-size: 0.65rem;">${t.priority}</span>
              <div class="small fw-semibold">${t.action_item}</div>
              <small class="text-muted">Created: ${t.created_at || "N/A"}</small>
            </div>
            <div>
              <span class="badge bg-light text-secondary border">${t.status}</span>
            </div>
          </div>
        `).join("");
      }

      // Open modal
      const modal = new bootstrap.Modal(document.getElementById("machineHistoryModal"));
      modal.show();
    }
  } catch (err) {
    API.showToast("Failed to load machine historical logs.", "danger");
  }
}

