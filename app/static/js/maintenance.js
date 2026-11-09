/**
 * Predictive Maintenance Intelligence - Maintenance Directives Controller
 * Handles maintenance lifecycle management and priority filtering.
 */

let allTasks = [];

document.addEventListener("DOMContentLoaded", () => {
  loadMaintenanceData();

  document.getElementById("maint-search").addEventListener("input", filterAndRenderTasks);
  document.getElementById("maint-status-filter").addEventListener("change", filterAndRenderTasks);
  document.getElementById("maint-priority-filter").addEventListener("change", filterAndRenderTasks);
  document.getElementById("maint-reset-btn").addEventListener("click", () => {
    document.getElementById("maint-search").value = "";
    document.getElementById("maint-status-filter").value = "";
    document.getElementById("maint-priority-filter").value = "";
    filterAndRenderTasks();
  });
});

async function loadMaintenanceData() {
  try {
    const res = await API.getMaintenance({ limit: 200 });
    if (res.status === "success") {
      allTasks = res.data || [];
      updateCounters(allTasks);
      filterAndRenderTasks();
    }
  } catch (err) {
    document.getElementById("maintenance-tasks-container").innerHTML = `
      <div class="empty-state py-4 text-danger">
        <i class="bi bi-exclamation-triangle fs-3"></i>
        <p>Failed to load maintenance records.</p>
      </div>
    `;
  }
}

function updateCounters(tasks) {
  document.getElementById("maint-total-count").textContent = tasks.length;
  document.getElementById("maint-pending-count").textContent = tasks.filter(t => t.status === "PENDING").length;
  document.getElementById("maint-progress-count").textContent = tasks.filter(t => t.status === "IN_PROGRESS").length;
  document.getElementById("maint-resolved-count").textContent = tasks.filter(t => t.status === "RESOLVED").length;
}

function filterAndRenderTasks() {
  const search = document.getElementById("maint-search").value.trim().toLowerCase();
  const statusFilter = document.getElementById("maint-status-filter").value;
  const priorityFilter = document.getElementById("maint-priority-filter").value;

  const filtered = allTasks.filter(t => {
    const matchesSearch = !search || t.machine_name.toLowerCase().includes(search) || t.action_item.toLowerCase().includes(search);
    const matchesStatus = !statusFilter || t.status === statusFilter;
    const matchesPriority = !priorityFilter || t.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  document.getElementById("filtered-task-count").textContent = filtered.length;
  renderTasks(filtered);
}

function renderTasks(tasks) {
  const container = document.getElementById("maintenance-tasks-container");
  if (!tasks || tasks.length === 0) {
    container.innerHTML = `
      <div class="empty-state py-5">
        <i class="bi bi-check2-circle fs-1 text-success"></i>
        <h3>No Matching Maintenance Directives</h3>
        <p>All equipment tasks match current filter limits or have been successfully addressed.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = tasks.map(t => {
    let priorityClass = "priority-low";
    let badgeClass = "badge-risk-low";
    if (t.priority === "HIGH") {
      priorityClass = "priority-high";
      badgeClass = "badge-risk-high";
    } else if (t.priority === "MEDIUM") {
      priorityClass = "priority-medium";
      badgeClass = "badge-risk-medium";
    }

    const isResolved = t.status === "RESOLVED";
    const isInProgress = t.status === "IN_PROGRESS";

    let statusPill = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle">PENDING ACTION</span>`;
    if (isInProgress) {
      statusPill = `<span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle">IN PROGRESS</span>`;
    } else if (isResolved) {
      statusPill = `<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check2"></i> RESOLVED</span>`;
    }

    return `
      <div class="directive-card ${priorityClass} ${isResolved ? 'status-resolved' : ''}">
        <div class="flex-grow-1">
          <div class="d-flex align-items-center gap-2 mb-1">
            <span class="badge-risk ${badgeClass}" style="font-size: 0.65rem;">${t.priority} PRIORITY</span>
            <span class="fw-bold text-primary" style="font-size: 0.88rem;">${t.machine_name}</span>
            <span class="badge-type">Type ${t.machine_type}</span>
            ${statusPill}
          </div>
          <div class="text-secondary fw-medium my-1" style="font-size: 0.88rem;">${t.action_item}</div>
          <div class="text-muted small mt-1">
            <span>Created: ${t.created_at ? t.created_at.substring(0, 16) : "N/A"}</span>
            ${t.resolved_at ? `&bull; <span class="text-success">Resolved: ${t.resolved_at.substring(0, 16)}</span>` : ""}
          </div>
        </div>

        <div class="d-flex align-items-center gap-2 ms-3 flex-shrink-0">
          ${t.status === "PENDING" ? `
            <button class="btn btn-sm btn-outline-warning" onclick="changeStatus(${t.record_id}, 'IN_PROGRESS', this)">
              <i class="bi bi-play-fill"></i> Start
            </button>
            <button class="btn btn-sm btn-outline-success" onclick="changeStatus(${t.record_id}, 'RESOLVED', this)">
              <i class="bi bi-check2"></i> Resolve
            </button>
          ` : ""}
          ${t.status === "IN_PROGRESS" ? `
            <button class="btn btn-sm btn-outline-success" onclick="changeStatus(${t.record_id}, 'RESOLVED', this)">
              <i class="bi bi-check2"></i> Mark Resolved
            </button>
          ` : ""}
          ${t.status === "RESOLVED" ? `
            <button class="btn btn-sm btn-outline-secondary" onclick="changeStatus(${t.record_id}, 'PENDING', this)">
              <i class="bi bi-arrow-counterclockwise"></i> Reopen
            </button>
          ` : ""}
        </div>
      </div>
    `;
  }).join("");
}

async function changeStatus(recordId, newStatus, btn) {
  btn.disabled = true;
  try {
    const res = await API.updateMaintenanceStatus(recordId, newStatus);
    if (res.status === "success") {
      API.showToast(`Task status updated to ${newStatus}.`, "success");
      loadMaintenanceData();
    }
  } catch (err) {
    btn.disabled = false;
  }
}

