/**
 * Predictive Maintenance Intelligence - Failure Prediction Controller
 * Handles sensory form submissions, live XGBoost inference, and Plotly SHAP visualizations.
 */

let machinesList = [];

document.addEventListener("DOMContentLoaded", () => {
  initMachineSelector();
  setupPresets();

  document.getElementById("prediction-form").addEventListener("submit", handlePredictionSubmit);
  document.getElementById("btn-reset-prediction").addEventListener("click", resetPredictionView);
  document.getElementById("pred-machine-select").addEventListener("change", handleMachineSelectChange);
});

async function initMachineSelector() {
  const select = document.getElementById("pred-machine-select");
  const urlParams = new URLSearchParams(window.location.search);
  const targetMachineId = urlParams.get("machine_id");

  try {
    const res = await API.getMachines();
    if (res.status === "success") {
      machinesList = res.data || [];
      select.innerHTML = `
        <option value="" disabled ${!targetMachineId ? 'selected' : ''}>Select registered unit...</option>
        ${machinesList.map(m => `
          <option value="${m.machine_id}" data-type="${m.machine_type}">
            ${m.machine_name} (Type ${m.machine_type})
          </option>
        `).join("")}
        <option value="__NEW__">+ Register / Custom Unit</option>
      `;

      if (targetMachineId) {
        select.value = targetMachineId;
        handleMachineSelectChange();
      }
    }
  } catch (err) {
    select.innerHTML = `<option value="__NEW__">+ Custom Unit (Offline)</option>`;
  }
}

function handleMachineSelectChange() {
  const select = document.getElementById("pred-machine-select");
  const typeSelect = document.getElementById("pred-machine-type");
  const customNameBox = document.getElementById("new-machine-name-container");

  if (select.value === "__NEW__") {
    customNameBox.style.display = "block";
    typeSelect.disabled = false;
  } else {
    customNameBox.style.display = "none";
    const selectedOption = select.options[select.selectedIndex];
    const mType = selectedOption.getAttribute("data-type");
    if (mType) {
      typeSelect.value = mType;
    }
  }
}

function setupPresets() {
  document.getElementById("preset-normal").addEventListener("click", () => {
    applyPreset({
      name: "Machine A",
      type: "L",
      air: 300.1,
      proc: 310.2,
      rpm: 1500,
      torque: 40.0,
      wear: 50
    });
  });

  document.getElementById("preset-high-risk").addEventListener("click", () => {
    applyPreset({
      name: "Machine B",
      type: "M",
      air: 302.0,
      proc: 311.0,
      rpm: 1400,
      torque: 55.0,
      wear: 220
    });
  });

  document.getElementById("preset-heavy-press").addEventListener("click", () => {
    applyPreset({
      name: "Machine C",
      type: "H",
      air: 300.1,
      proc: 310.2,
      rpm: 1500,
      torque: 40.0,
      wear: 120
    });
  });
}

function applyPreset(p) {
  document.getElementById("input-air-temp").value = p.air;
  document.getElementById("input-proc-temp").value = p.proc;
  document.getElementById("input-rpm").value = p.rpm;
  document.getElementById("input-torque").value = p.torque;
  document.getElementById("input-tool-wear").value = p.wear;
  document.getElementById("pred-machine-type").value = p.type;

  // Try to find matching machine in select
  const select = document.getElementById("pred-machine-select");
  let matched = false;
  for (let opt of select.options) {
    if (opt.text.includes(p.name)) {
      select.value = opt.value;
      matched = true;
      break;
    }
  }
  if (!matched) {
    select.value = "__NEW__";
    document.getElementById("new-machine-name-container").style.display = "block";
    document.getElementById("pred-custom-name").value = p.name;
  } else {
    document.getElementById("new-machine-name-container").style.display = "none";
  }

  API.showToast(`Applied preset for ${p.name}`, "info");
}

async function handlePredictionSubmit(e) {
  e.preventDefault();

  const btn = document.getElementById("btn-run-prediction");
  const select = document.getElementById("pred-machine-select");
  const customNameInput = document.getElementById("pred-custom-name");
  const typeSelect = document.getElementById("pred-machine-type");

  let machineId = null;
  let machineName = null;

  if (select.value === "__NEW__") {
    machineName = customNameInput.value.trim() || "Diagnostic Machine";
  } else if (select.value) {
    machineId = parseInt(select.value);
    machineName = select.options[select.selectedIndex].text.split("(")[0].trim();
  } else {
    machineName = "Direct Sensor Assessment";
  }

  const payload = {
    machine_id: machineId,
    machine_name: machineName,
    machine_type: typeSelect.value,
    air_temperature: parseFloat(document.getElementById("input-air-temp").value),
    process_temperature: parseFloat(document.getElementById("input-proc-temp").value),
    rotational_speed: parseFloat(document.getElementById("input-rpm").value),
    torque: parseFloat(document.getElementById("input-torque").value),
    tool_wear: parseFloat(document.getElementById("input-tool-wear").value),
    save_to_db: document.getElementById("check-save-db").checked,
    include_xai: document.getElementById("check-include-xai").checked
  };

  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner" style="width: 1.1rem; height: 1.1rem;"></span> Analyzing Telemetry...`;

  try {
    const res = await API.predict(payload);
    if (res.status === "success") {
      renderResults(res.data);
      API.showToast("Prediction and failure analysis completed successfully!", "success");
    }
  } catch (err) {
    // Error caught by API.showToast
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-cpu-fill"></i> Run Predictive Failure Analysis`;
  }
}

function renderResults(data) {
  document.getElementById("results-placeholder").style.display = "none";
  const panel = document.getElementById("results-panel");
  panel.style.display = "block";

  // Machine header
  document.getElementById("res-machine-title").textContent = data.machine_name;
  document.getElementById("res-machine-type").textContent = `Type ${data.machine_type}`;
  document.getElementById("res-timestamp").textContent = `Analyzed: ${new Date().toLocaleTimeString()}`;

  // Badges
  const isFailure = data.machine_status === "FAILURE RISK";
  document.getElementById("res-status-badge").className = isFailure ? "badge bg-danger fs-6" : "badge bg-success fs-6";
  document.getElementById("res-status-badge").textContent = data.machine_status;

  const riskBadge = document.getElementById("res-risk-badge");
  riskBadge.className = `badge-risk badge-risk-${data.risk_level.toLowerCase()} fs-6`;
  riskBadge.textContent = `${data.risk_level} RISK`;

  // Probability
  const probEl = document.getElementById("res-probability");
  probEl.textContent = `${data.failure_probability.toFixed(2)}%`;
  if (data.failure_probability >= 40.0) {
    probEl.className = "display-6 fw-bold text-danger";
  } else if (data.failure_probability >= 20.0) {
    probEl.className = "display-6 fw-bold text-warning";
  } else {
    probEl.className = "display-6 fw-bold text-success";
  }

  // Engineered features
  document.getElementById("res-temp-diff").textContent = `${data.temperature_difference.toFixed(1)} K`;
  document.getElementById("res-mech-power").textContent = `${data.mechanical_power.toFixed(2)} kW`;

  // Recommendations
  const recList = document.getElementById("res-recommendations-list");
  if (!data.recommendations || data.recommendations.length === 0) {
    recList.innerHTML = `<div class="text-success"><i class="bi bi-check-circle"></i> Low failure risk: Continue routine monitoring.</div>`;
  } else {
    recList.innerHTML = data.recommendations.map((rec, i) => `
      <div class="directive-card priority-${data.risk_level.toLowerCase()} mb-2 py-2">
        <div class="d-flex align-items-center gap-2">
          <span class="badge bg-light text-secondary border">${i + 1}</span>
          <span class="small fw-semibold text-secondary">${rec}</span>
        </div>
      </div>
    `).join("");
  }

  document.getElementById("res-disclaimer").textContent = data.threshold_disclaimer || "";

  // SHAP Chart
  const shapCard = document.getElementById("shap-card");
  if (data.xai && data.xai.available) {
    shapCard.style.display = "block";
    renderShapChart(data.xai);
  } else {
    shapCard.style.display = "none";
  }

  // PDF link
  const pdfBtn = document.getElementById("btn-download-pdf");
  if (data.machine_id) {
    pdfBtn.href = `/api/reports/pdf/${data.machine_id}`;
    pdfBtn.style.display = "inline-flex";
  } else {
    pdfBtn.style.display = "none";
  }

  // Scroll to results on mobile
  if (window.innerWidth < 1200) {
    panel.scrollIntoView({ behavior: "smooth" });
  }
}

function renderShapChart(xai) {
  document.getElementById("shap-summary-box").innerHTML = `
    <i class="bi bi-info-circle-fill text-primary me-1"></i>
    <strong>Interpretation:</strong> ${xai.summary} Base attribution value: <code>${xai.base_value}</code>
  `;

  const contribs = [...xai.feature_contributions].reverse(); // bottom to top
  const yLabels = contribs.map(c => c.display_name);
  const xValues = contribs.map(c => c.shap_value);
  const colors = contribs.map(c => c.shap_value > 0 ? "#EF4444" : "#3B82F6");

  const plotData = [{
    type: "bar",
    orientation: "h",
    x: xValues,
    y: yLabels,
    marker: { color: colors, borderRadius: 4 },
    text: xValues.map(v => (v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3))),
    textposition: "auto"
  }];

  const layout = {
    margin: { t: 10, b: 30, l: 160, r: 20 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { family: "Inter, sans-serif", size: 10, color: "#334155" },
    xaxis: {
      title: "SHAP Log-Odds Margin Contribution",
      zerolinecolor: "#94A3B8",
      gridcolor: "#F1F5F9"
    },
    yaxis: {
      automargin: true
    }
  };

  Plotly.newPlot("shap-chart", plotData, layout, { responsive: true, displayModeBar: false });
}

function resetPredictionView() {
  document.getElementById("results-panel").style.display = "none";
  document.getElementById("results-placeholder").style.display = "flex";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

