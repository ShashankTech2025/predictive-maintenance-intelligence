/**
 * Predictive Maintenance Intelligence - API Client
 * Centralized AJAX wrapper for REST endpoints with standardized toast notifications.
 */

const API = {
  baseUrl: "/api",

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const defaultHeaders = {
      "Content-Type": "application/json",
      "Accept": "application/json"
    };

    options.headers = { ...defaultHeaders, ...options.headers };

    try {
      const response = await fetch(url, options);
      const data = await response.json();

      if (!response.ok) {
        const errorMsg = data.message || data.error || `HTTP Error ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      this.showToast(err.message || "Network communication failure", "danger");
      throw err;
    }
  },

  // Health
  getHealth() {
    return this.request("/health");
  },

  // Dashboard stats
  getDashboardStats() {
    return this.request("/dashboard/stats");
  },

  // Machines
  getMachines(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/machines${query ? "?" + query : ""}`);
  },

  getMachine(id) {
    return this.request(`/machines/${id}`);
  },

  createMachine(payload) {
    return this.request("/machines", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  updateMachine(id, payload) {
    return this.request(`/machines/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    });
  },

  getMachineHistory(id) {
    return this.request(`/machines/${id}/history`);
  },

  // Predictions
  predict(payload) {
    return this.request("/predict", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  getPredictions(limit = 50, offset = 0) {
    return this.request(`/predictions?limit=${limit}&offset=${offset}`);
  },

  // Maintenance
  getMaintenance(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/maintenance${query ? "?" + query : ""}`);
  },

  updateMaintenanceStatus(id, status) {
    return this.request(`/maintenance/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status })
    });
  },

  // UI Toast notification helper
  showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `custom-toast border-${type}`;

    let icon = "bi-info-circle-fill text-primary";
    if (type === "success") icon = "bi-check-circle-fill text-success";
    if (type === "danger") icon = "bi-exclamation-triangle-fill text-danger";
    if (type === "warning") icon = "bi-exclamation-circle-fill text-warning";

    toast.innerHTML = `
      <i class="bi ${icon} fs-5"></i>
      <div class="flex-grow-1" style="font-size: 0.85rem;">${message}</div>
      <button type="button" class="btn-close btn-sm" onclick="this.parentElement.remove()"></button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      if (toast && toast.parentElement) {
        toast.remove();
      }
    }, 4500);
  }
};

