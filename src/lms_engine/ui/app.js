const summaryCards = document.getElementById("summary-cards");
const employeeSelect = document.getElementById("employee-select");
const employeeAnalysis = document.getElementById("employee-analysis");
const employeeReadiness = document.getElementById("employee-readiness");
const managerInsights = document.getElementById("manager-insights");
const seedButton = document.getElementById("seed-demo");
const refreshButton = document.getElementById("refresh-dashboard");

async function fetchJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed for ${path}`);
  }
  return data;
}

function metricCard(label, value) {
  return `
    <article class="card stat">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
    </article>
  `;
}

function renderSummary(item) {
  summaryCards.innerHTML = [
    metricCard("Roles", item.roles),
    metricCard("Competencies", item.competencies),
    metricCard("Assets", item.assets),
    metricCard("Assessments", item.assessments),
    metricCard("Employees", item.employees),
    metricCard("KPIs", item.kpis),
    metricCard("Weak KPI Patterns", item.weak_kpi_patterns),
  ].join("");
}

function emptyState(copy) {
  return `<div class="empty-state">${copy}</div>`;
}

function renderEmployeeOptions(employees) {
  if (!employees.length) {
    employeeSelect.innerHTML = `<option value="">No employees yet</option>`;
    return;
  }

  employeeSelect.innerHTML = employees
    .map((employee) => `<option value="${employee.id}">${employee.name} · ${employee.org_unit}</option>`)
    .join("");
}

function renderReadiness(readiness) {
  const statusClass = readiness.ready ? "status ready" : "status";
  employeeReadiness.innerHTML = `
    <div class="${statusClass}">
      Readiness ${readiness.ready ? "healthy" : "needs work"}
    </div>
    <div class="kpi-meta">
      Compliance ${readiness.compliance_score}% · Competency coverage ${readiness.competency_coverage}% ·
      Readiness score ${readiness.readiness_score}%
    </div>
  `;
}

function renderAnalysis(analysis) {
  if (!analysis.weak_kpis.length) {
    employeeAnalysis.innerHTML = emptyState("No weak KPIs for the selected employee right now.");
    return;
  }

  employeeAnalysis.innerHTML = analysis.weak_kpis
    .map(
      (item) => `
        <article class="recommendation">
          <h3>${item.kpi_name}</h3>
          <div class="kpi-meta">Gap to target: ${item.gap_to_target}</div>
          <p>${item.action_summary}</p>
          <div class="tag-row">
            ${item.competency_ids.map((id) => `<span class="tag">${id}</span>`).join("")}
          </div>
          <div class="tag-row">
            <span class="tag alt">Assets ${item.asset_ids.length}</span>
            <span class="tag alt">Assessments ${item.assessment_ids.length}</span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderInsights(report) {
  if (!report.weak_kpis.length) {
    managerInsights.innerHTML = emptyState("No weak KPI patterns have been recorded yet.");
    return;
  }

  managerInsights.innerHTML = report.weak_kpis
    .map(
      (item) => `
        <article class="insight">
          <h3>${item.kpi_name}</h3>
          <div class="kpi-meta">
            Weak observations ${item.weak_observation_count} · Affected employees ${item.affected_employee_count}
          </div>
          <p>${item.action_summary}</p>
          <div class="tag-row">
            <span class="tag alt">Competencies ${item.linked_competency_ids.length}</span>
            <span class="tag alt">Assets ${item.linked_asset_count}</span>
            <span class="tag alt">Assessments ${item.linked_assessment_count}</span>
          </div>
        </article>
      `
    )
    .join("");
}

async function loadEmployeePanels(employeeId) {
  if (!employeeId) {
    employeeAnalysis.innerHTML = emptyState("Seed the demo or create employees to inspect remediation.");
    employeeReadiness.innerHTML = "No employee selected.";
    return;
  }

  const [analysisRes, readinessRes] = await Promise.all([
    fetchJson(`/employees/${employeeId}/kpi-analysis`),
    fetchJson(`/employees/${employeeId}/readiness`),
  ]);
  renderAnalysis(analysisRes.item);
  renderReadiness(readinessRes.item);
}

async function loadDashboard() {
  const [summaryRes, employeesRes, insightsRes] = await Promise.all([
    fetchJson("/dashboard/summary"),
    fetchJson("/employees"),
    fetchJson("/analytics/weak-kpis"),
  ]);

  renderSummary(summaryRes.item);
  renderEmployeeOptions(employeesRes.items);
  renderInsights(insightsRes.item);
  await loadEmployeePanels(employeeSelect.value);
}

seedButton.addEventListener("click", async () => {
  seedButton.disabled = true;
  seedButton.textContent = "Loading...";
  try {
    await fetchJson("/demo/seed", { method: "POST", body: JSON.stringify({}) });
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  } finally {
    seedButton.disabled = false;
    seedButton.textContent = "Load Demo Data";
  }
});

refreshButton.addEventListener("click", async () => {
  try {
    await loadDashboard();
  } catch (error) {
    alert(error.message);
  }
});

employeeSelect.addEventListener("change", async (event) => {
  try {
    await loadEmployeePanels(event.target.value);
  } catch (error) {
    alert(error.message);
  }
});

loadDashboard().catch((error) => {
  summaryCards.innerHTML = emptyState(error.message);
  employeeAnalysis.innerHTML = emptyState("Dashboard could not be loaded.");
  managerInsights.innerHTML = emptyState("Manager insights unavailable.");
});
