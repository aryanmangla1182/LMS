const state = {
  token: localStorage.getItem("lms_token") || "",
  currentUser: null,
  roles: [],
  users: [],
  selectedRoleId: null,
  learnerDashboard: null,
};

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
const authPanel = document.getElementById("auth-panel");
const workspace = document.getElementById("workspace");
const configBadge = document.getElementById("config-badge");
const seedBtn = document.getElementById("seed-btn");
const requestCodeForm = document.getElementById("request-code-form");
const verifyCodeForm = document.getElementById("verify-code-form");
const requestCodeResult = document.getElementById("request-code-result");
const verifyCodeResult = document.getElementById("verify-code-result");
const logoutBtn = document.getElementById("logout-btn");
const userBannerTitle = document.getElementById("user-banner-title");
const userBannerCopy = document.getElementById("user-banner-copy");
const roleForm = document.getElementById("role-form");
const learnerForm = document.getElementById("learner-form");
const roleStatus = document.getElementById("role-status");
const roleDetail = document.getElementById("role-detail");
const reviewNoteInput = document.getElementById("review-note");
const applyReviewBtn = document.getElementById("apply-review-btn");
const publishRoleBtn = document.getElementById("publish-role-btn");
const roleSelect = document.getElementById("role-select");
const adminSummary = document.getElementById("admin-summary");
const learnerMetrics = document.getElementById("learner-metrics");
const courseView = document.getElementById("course-view");
const assessmentForm = document.getElementById("assessment-form");
const submitAssessmentBtn = document.getElementById("submit-assessment-btn");
const assessmentResult = document.getElementById("assessment-result");
const kpiForm = document.getElementById("kpi-form");
const kpiSelect = document.getElementById("kpi-select");
const kpiView = document.getElementById("kpi-view");
const ownerSummary = document.getElementById("owner-summary");
const roleMetrics = document.getElementById("role-metrics");
const hotspots = document.getElementById("hotspots");
const activityLog = document.getElementById("activity-log");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseLines(value) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseKpis(value) {
  return value
    .split(/\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, description, targetValue, unit, weakThreshold] = line.split("|").map((item) => item.trim());
      return {
        name,
        description,
        target_value: Number(targetValue || 100),
        unit: unit || "%",
        weak_threshold: Number(weakThreshold || 0.85),
      };
    });
}

function titleCaseLabel(value) {
  return String(value)
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusTone(value) {
  if (value === "published" || value === "healthy" || value === "resolved" || value === "passed") {
    return "soft";
  }
  if (value === "weak" || value === "assigned" || value === "draft" || value === "needs_work") {
    return "warn";
  }
  return "";
}

function setTab(tabName) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === tabName));
}

tabs.forEach((tab) => tab.addEventListener("click", () => setTab(tab.dataset.tab)));

async function fetchJson(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed for ${path}`);
  }
  return data;
}

function showAuth() {
  authPanel.classList.remove("hidden");
  workspace.classList.add("hidden");
}

function showWorkspace() {
  authPanel.classList.add("hidden");
  workspace.classList.remove("hidden");
}

function setVisibilityForUser() {
  const isOwner = state.currentUser?.user_type === "owner";
  document.querySelectorAll(".owner-only").forEach((node) => node.classList.toggle("hidden", !isOwner));
  document.querySelectorAll(".learner-only").forEach((node) => node.classList.toggle("hidden", isOwner));
  seedBtn.classList.toggle("hidden", !isOwner);
  if (isOwner) {
    setTab("admin");
    userBannerTitle.textContent = "Owner Workspace";
    userBannerCopy.textContent = `Signed in as ${state.currentUser.name} · ${state.currentUser.phone_number}`;
  } else {
    setTab("learner");
    userBannerTitle.textContent = "Learner Workspace";
    userBannerCopy.textContent = `Signed in as ${state.currentUser.name} · role-based access only`;
  }
}

function renderRoleOptions() {
  const publishedRoles = state.roles.filter((role) => role.status === "published");
  roleSelect.innerHTML = publishedRoles.length
    ? publishedRoles.map((role) => `<option value="${role.id}">${escapeHtml(role.title)} · ${escapeHtml(role.level)}</option>`).join("")
    : `<option value="">Publish a role first</option>`;
}

function renderAdminSummary() {
  if (!state.users.length && !state.roles.length) {
    adminSummary.innerHTML = `<div class="empty">No roles or users yet.</div>`;
    return;
  }
  adminSummary.innerHTML = `
    <div class="metric-grid">
      <div class="metric-item"><span class="meta">Roles</span><strong>${state.roles.length}</strong></div>
      <div class="metric-item"><span class="meta">Published</span><strong>${state.roles.filter((role) => role.status === "published").length}</strong></div>
      <div class="metric-item"><span class="meta">Users</span><strong>${state.users.length}</strong></div>
      <div class="metric-item"><span class="meta">Learners</span><strong>${state.users.filter((user) => user.user_type === "learner").length}</strong></div>
    </div>
    ${state.users.map((user) => `
      <div class="card">
        <div class="inline">
          <strong>${escapeHtml(user.name)}</strong>
          <span class="chip ${user.user_type === "owner" ? "soft" : "warn"}">${escapeHtml(titleCaseLabel(user.user_type))}</span>
        </div>
        <div class="meta">${escapeHtml(user.phone_number)}</div>
        <div class="meta">${user.role_id ? `Assigned role ${escapeHtml(user.role_id)}` : "Platform owner access"}</div>
      </div>
    `).join("")}
  `;
}

function renderRoleDetail(role) {
  if (!role) {
    roleStatus.innerHTML = "No generated role yet.";
    roleDetail.innerHTML = "";
    applyReviewBtn.disabled = true;
    publishRoleBtn.disabled = true;
    return;
  }
  roleStatus.innerHTML = `
    <div class="card card-emphasis">
      <div class="inline">
        <strong>${escapeHtml(role.title)}</strong>
        <span class="chip ${statusTone(role.status)}">${escapeHtml(titleCaseLabel(role.status))}</span>
      </div>
      <div class="meta">${escapeHtml(role.segment)} · ${escapeHtml(role.level)}</div>
      <div class="meta">${escapeHtml(role.summary || role.legacy_mapping_notes)}</div>
    </div>
  `;
  roleDetail.innerHTML = `
    <div class="split-two">
      <div class="card">
        <h3 class="section-title">Responsibilities</h3>
        <div class="tag-row">${role.responsibilities.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>
      </div>
      <div class="card">
        <h3 class="section-title">Role Notes</h3>
        <div class="meta">${escapeHtml(role.legacy_mapping_notes)}</div>
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Skills</h3>
      <div class="tag-row">${role.skills.map((item) => `<span class="chip">${escapeHtml(item.name)}</span>`).join("")}</div>
    </div>
    <div class="card">
      <h3 class="section-title">KPIs</h3>
      <div class="split-two">
        ${role.kpis.map((kpi) => `
          <div class="mini-stat">
            <strong>${escapeHtml(kpi.name)}</strong>
            <div class="meta">${escapeHtml(kpi.description)}</div>
            <div class="meta">Target ${escapeHtml(kpi.target_value)}${escapeHtml(kpi.unit)}</div>
          </div>
        `).join("")}
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Learning Path</h3>
      <div class="stack">
        ${role.learning_path.sections.map((section, index) => `
          <div class="spotlight">
            <div class="inline">
              <strong>${index + 1}. ${escapeHtml(section.title)}</strong>
              <span class="chip">${escapeHtml(titleCaseLabel(section.key))}</span>
            </div>
            <div class="meta">${escapeHtml(section.goal)}</div>
            <div class="tag-row">${section.items.map((item) => `<span class="chip soft">${escapeHtml(item.title)}</span>`).join("")}</div>
          </div>
        `).join("")}
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Assessment Coverage</h3>
      <div class="meta">${role.course_template.assessment.questions.length} generated questions linked to role skills and KPIs.</div>
    </div>
  `;
  applyReviewBtn.disabled = false;
  publishRoleBtn.disabled = role.status === "published";
}

function renderLearnerDashboard(dashboard) {
  state.learnerDashboard = dashboard;
  const metrics = dashboard.metrics;
  learnerMetrics.innerHTML = `
    <div class="inline">
      <strong>${escapeHtml(dashboard.role.title)}</strong>
      <span class="chip soft">${escapeHtml(dashboard.role.segment)}</span>
      <span class="chip">${escapeHtml(dashboard.role.level)}</span>
    </div>
    <div class="meta">${escapeHtml(dashboard.role.summary || dashboard.role.work_summary || "")}</div>
    <div class="progress-track"><div class="progress-fill" style="width:${metrics.completion_percentage}%"></div></div>
    <div class="metric-grid">
      <div class="metric-item"><span class="meta">Completion</span><strong>${metrics.completion_percentage}%</strong></div>
      <div class="metric-item"><span class="meta">Assessment</span><strong>${metrics.latest_assessment_score ?? "--"}</strong></div>
      <div class="metric-item"><span class="meta">Weak Skills</span><strong>${metrics.weak_skill_count}</strong></div>
      <div class="metric-item"><span class="meta">Weak KPIs</span><strong>${metrics.weak_kpis}</strong></div>
    </div>
  `;

  courseView.innerHTML = dashboard.enrollment.course.sections.map((section) => `
    <div class="card">
      <h3 class="section-title">${escapeHtml(section.title)}</h3>
      <div class="meta">${escapeHtml(section.description)}</div>
      <div class="stack">
        ${section.lessons.map((lesson) => {
          const complete = dashboard.enrollment.completed_lesson_ids.includes(lesson.id);
          return `
            <div class="lesson ${complete ? "lesson-complete" : ""}">
              <div class="inline">
                <strong>${escapeHtml(lesson.title)}</strong>
                <span class="chip">${escapeHtml(lesson.resource_type)}</span>
                ${complete ? `<span class="chip soft">Completed</span>` : ""}
              </div>
              <div class="meta">${escapeHtml(lesson.summary)}</div>
              <div class="lesson-content">${escapeHtml(lesson.content)}</div>
              <button class="secondary complete-lesson-btn" data-lesson="${lesson.id}" ${complete ? "disabled" : ""}>${complete ? "Completed" : "Mark Complete"}</button>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `).join("");

  assessmentForm.innerHTML = dashboard.enrollment.course.assessment.questions.map((question, index) => `
    <div class="question">
      <strong>Q${index + 1}. ${escapeHtml(question.prompt)}</strong>
      <div class="question-options">
        ${question.options.map((option, optionIndex) => `
          <label class="question-option">
            <input type="radio" name="${question.id}" value="${optionIndex}">
            <span>${escapeHtml(option)}</span>
          </label>
        `).join("")}
      </div>
    </div>
  `).join("");
  submitAssessmentBtn.disabled = false;

  kpiSelect.innerHTML = dashboard.role.kpis.map((kpi) => `<option value="${kpi.id}" data-target="${kpi.target_value}">${escapeHtml(kpi.name)} · target ${escapeHtml(kpi.target_value)}${escapeHtml(kpi.unit)}</option>`).join("");
  if (dashboard.role.kpis.length) {
    kpiForm.target_value.value = dashboard.role.kpis[0].target_value;
  }

  renderAssessmentResult(dashboard.latest_assessment);
  renderKpiView(dashboard);
  attachLessonHandlers();
}

function renderAssessmentResult(attempt) {
  if (!attempt) {
    assessmentResult.innerHTML = `<div class="empty">No assessment submitted yet.</div>`;
    return;
  }
  assessmentResult.innerHTML = `
    <div class="card">
      <div class="inline">
        <strong>Score ${attempt.score_percentage}%</strong>
        <span class="chip ${attempt.passed ? "soft" : "warn"}">${attempt.passed ? "Passed" : "Needs Work"}</span>
      </div>
      <div class="meta">${escapeHtml(attempt.analysis_summary)}</div>
    </div>
    <div class="split-two">
      <div class="card">
        <h3 class="section-title">Weak Skills</h3>
        ${attempt.weak_skills.length ? attempt.weak_skills.map((item) => `<div class="meta">${escapeHtml(item.skill_name)} · ${item.accuracy}%</div>`).join("") : `<div class="meta">No weak skills in this attempt.</div>`}
      </div>
      <div class="card">
        <h3 class="section-title">KPI Risk Areas</h3>
        ${attempt.weak_kpis.length ? attempt.weak_kpis.map((item) => `<div class="meta">${escapeHtml(item.kpi_name)} · ${item.accuracy}%</div>`).join("") : `<div class="meta">No KPI risk areas in this attempt.</div>`}
      </div>
    </div>
  `;
}

function renderKpiView(dashboard) {
  const observations = dashboard.kpi_observations || [];
  const assignments = dashboard.remediation_assignments || [];
  kpiView.innerHTML = `
    <div class="grid two">
      <div class="card">
        <h3 class="section-title">KPI Observations</h3>
        ${observations.length ? observations.map((item) => `
          <div class="spotlight">
            <div class="inline">
              <strong>${escapeHtml(item.kpi_name)}</strong>
              <span class="chip ${statusTone(item.status)}">${escapeHtml(titleCaseLabel(item.status))}</span>
            </div>
            <div class="meta">${item.value} / ${item.target_value} · ${escapeHtml(item.period_label)}</div>
            ${item.notes ? `<div class="meta">${escapeHtml(item.notes)}</div>` : ""}
          </div>
        `).join("") : `<div class="meta">No KPI observations yet.</div>`}
      </div>
      <div class="card">
        <h3 class="section-title">Remediation</h3>
        ${assignments.length ? assignments.map((item) => `
          <div class="spotlight">
            <div class="inline">
              <strong>${escapeHtml(item.title)}</strong>
              <span class="chip ${statusTone(item.status)}">${escapeHtml(titleCaseLabel(item.status))}</span>
            </div>
            <div class="meta">${escapeHtml(item.summary)}</div>
          </div>
        `).join("") : `<div class="meta">No remediation assignments yet.</div>`}
      </div>
    </div>
  `;
}

function renderOwnerDashboard(data) {
  ownerSummary.innerHTML = Object.entries(data.summary).map(([key, value], index) => `
    <div class="summary-card ${index < 2 ? "emphasis" : ""}">
      <p class="eyebrow">${escapeHtml(titleCaseLabel(key))}</p>
      <strong class="summary-value">${escapeHtml(value)}</strong>
    </div>
  `).join("");
  roleMetrics.innerHTML = data.role_metrics.map((item) => `
    <div class="spotlight">
      <div class="inline">
        <strong>${escapeHtml(item.role_title)}</strong>
        <span class="chip">${escapeHtml(item.segment)}</span>
      </div>
      <div class="meta">Learners ${item.learner_count} · Completion ${item.completion_percentage}% · Assessment ${item.latest_attempt_average ?? "--"}</div>
      <div class="progress-track"><div class="progress-fill" style="width:${Math.max(0, Math.min(100, item.completion_percentage || 0))}%"></div></div>
    </div>
  `).join("") || `<div class="empty">No owner metrics yet.</div>`;
  hotspots.innerHTML = `
    <div class="split-two">
      <div class="card">
        <h3 class="section-title">Weak Skills</h3>
        ${data.weak_skills.length ? data.weak_skills.map((item) => `<div class="meta">${escapeHtml(item.label)} · ${item.count}</div>`).join("") : `<div class="meta">No weak skills recorded.</div>`}
      </div>
      <div class="card">
        <h3 class="section-title">Weak KPIs</h3>
        ${data.weak_kpis.length ? data.weak_kpis.map((item) => `<div class="meta">${escapeHtml(item.label)} · ${item.count}</div>`).join("") : `<div class="meta">No weak KPIs recorded.</div>`}
      </div>
    </div>
  `;
  activityLog.innerHTML = data.activity_log.map((item) => `
    <div class="activity">
      <strong>${escapeHtml(titleCaseLabel(item.type))}</strong>
      <div class="meta">${escapeHtml(JSON.stringify(item.payload))}</div>
      <div class="meta">${escapeHtml(item.created_at)}</div>
    </div>
  `).join("") || `<div class="empty">No activity yet.</div>`;
}

async function refreshOwnerData() {
  const [rolesRes, usersRes, dashboardRes] = await Promise.all([
    fetchJson("/api/roles"),
    fetchJson("/api/users"),
    fetchJson("/api/dashboard/owner"),
  ]);
  state.roles = rolesRes.items;
  state.users = usersRes.items;
  renderRoleOptions();
  renderAdminSummary();
  const selectedRole = state.roles.find((role) => role.id === state.selectedRoleId) || state.roles[state.roles.length - 1];
  if (selectedRole) {
    state.selectedRoleId = selectedRole.id;
    renderRoleDetail(selectedRole);
  } else {
    renderRoleDetail(null);
  }
  renderOwnerDashboard(dashboardRes.item);
}

async function refreshLearnerData() {
  const dashboard = await fetchJson("/api/my/dashboard");
  renderLearnerDashboard(dashboard.item);
}

function attachLessonHandlers() {
  document.querySelectorAll(".complete-lesson-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await fetchJson(`/api/my/lessons/${button.dataset.lesson}/complete`, { method: "POST", body: JSON.stringify({}) });
        await refreshLearnerData();
      } catch (error) {
        alert(error.message);
      }
    });
  });
}

requestCodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(requestCodeForm).entries());
  try {
    const res = await fetchJson("/api/auth/request-code", { method: "POST", body: JSON.stringify(payload) });
    requestCodeResult.innerHTML = `<div class="card card-emphasis"><strong>Code generated</strong><div class="meta">For MVP testing, use code <strong>${escapeHtml(res.item.code)}</strong> for ${escapeHtml(payload.phone_number)}.</div></div>`;
  } catch (error) {
    requestCodeResult.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
});

verifyCodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(verifyCodeForm).entries());
  try {
    const res = await fetchJson("/api/auth/verify-code", { method: "POST", body: JSON.stringify(payload) });
    state.token = res.item.token;
    localStorage.setItem("lms_token", state.token);
    state.currentUser = res.item.user;
    verifyCodeResult.innerHTML = "";
    await bootWorkspace();
  } catch (error) {
    verifyCodeResult.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
});

logoutBtn.addEventListener("click", () => {
  state.token = "";
  state.currentUser = null;
  localStorage.removeItem("lms_token");
  showAuth();
});

seedBtn.addEventListener("click", async () => {
  try {
    await fetchJson("/api/demo/seed", { method: "POST", body: JSON.stringify({}) });
    await refreshOwnerData();
  } catch (error) {
    alert(error.message);
  }
});

roleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(roleForm);
  const payload = {
    segment: formData.get("segment"),
    title: formData.get("title"),
    level: formData.get("level"),
    legacy_mappings: parseLines(formData.get("legacy_mappings")),
    work_summary: formData.get("work_summary"),
    responsibilities: parseLines(formData.get("responsibilities")),
    skills: parseLines(formData.get("skills")),
    kpis: parseKpis(formData.get("kpis")),
  };
  try {
    const res = await fetchJson("/api/roles/generate", { method: "POST", body: JSON.stringify(payload) });
    state.selectedRoleId = res.item.id;
    await refreshOwnerData();
  } catch (error) {
    alert(error.message);
  }
});

applyReviewBtn.addEventListener("click", async () => {
  if (!state.selectedRoleId) return;
  try {
    await fetchJson(`/api/roles/${state.selectedRoleId}/review`, {
      method: "POST",
      body: JSON.stringify({ review_note: reviewNoteInput.value }),
    });
    await refreshOwnerData();
  } catch (error) {
    alert(error.message);
  }
});

publishRoleBtn.addEventListener("click", async () => {
  if (!state.selectedRoleId) return;
  try {
    await fetchJson(`/api/roles/${state.selectedRoleId}/publish`, { method: "POST", body: JSON.stringify({}) });
    await refreshOwnerData();
  } catch (error) {
    alert(error.message);
  }
});

learnerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(learnerForm).entries());
  try {
    const res = await fetchJson("/api/users", { method: "POST", body: JSON.stringify(payload) });
    adminSummary.insertAdjacentHTML(
      "afterbegin",
      `<div class="card"><strong>${escapeHtml(res.item.user.name)}</strong><div class="meta">Created learner user with phone ${escapeHtml(res.item.user.phone_number)}.</div></div>`
    );
    await refreshOwnerData();
  } catch (error) {
    alert(error.message);
  }
});

submitAssessmentBtn.addEventListener("click", async () => {
  const answers = state.learnerDashboard.enrollment.course.assessment.questions.map((question) => {
    const selected = assessmentForm.querySelector(`input[name="${question.id}"]:checked`);
    return { question_id: question.id, selected_option_index: selected ? Number(selected.value) : -1 };
  });
  try {
    await fetchJson("/api/my/assessment/submit", { method: "POST", body: JSON.stringify({ answers }) });
    await refreshLearnerData();
  } catch (error) {
    alert(error.message);
  }
});

kpiSelect.addEventListener("change", () => {
  const option = kpiSelect.options[kpiSelect.selectedIndex];
  if (option) {
    kpiForm.target_value.value = option.dataset.target || "";
  }
});

kpiForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(kpiForm).entries());
  try {
    await fetchJson("/api/my/kpis", { method: "POST", body: JSON.stringify(payload) });
    await refreshLearnerData();
  } catch (error) {
    alert(error.message);
  }
});

async function loadConfig() {
  const res = await fetchJson("/api/config");
  configBadge.className = `badge ${res.item.ai_enabled ? "soft" : "warn"}`;
  configBadge.textContent = res.item.ai_enabled
    ? `AI connected · ${res.item.openai_model}`
    : `AI fallback mode · owner login ${res.item.owner_phone} / 111111`;
}

async function bootWorkspace() {
  const me = await fetchJson("/api/auth/me");
  state.currentUser = me.item;
  showWorkspace();
  setVisibilityForUser();
  if (state.currentUser.user_type === "owner") {
    await refreshOwnerData();
  } else {
    await refreshLearnerData();
  }
}

async function boot() {
  await loadConfig();
  if (!state.token) {
    showAuth();
    return;
  }
  try {
    await bootWorkspace();
  } catch (_error) {
    state.token = "";
    localStorage.removeItem("lms_token");
    showAuth();
  }
}

boot().catch((error) => alert(error.message));
