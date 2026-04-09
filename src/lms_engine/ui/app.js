const state = {
  token: localStorage.getItem("lms_token") || "",
  currentUser: null,
  roles: [],
  users: [],
  selectedRoleId: null,
  learnerDashboard: null,
  assessmentAnswers: {},
  currentQuestionIndex: 0,
  inlineVideoPlayers: {},
  activeLessonPlayer: null,
  activeLessonSceneIndex: 0,
  lessonVideoUrl: "",
  trainerCourseView: {
    mode: "overview",
    lessonId: null,
  },
  learnerCourseView: {
    mode: "overview",
    lessonId: null,
  },
  activeSubtabs: {
    admin: "trainer-role-input",
    learner: "learner-course",
    trainer: "trainer-overview",
  },
};

const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".tab-panel");
const subtabs = document.querySelectorAll(".subtab");
const subtabPanels = document.querySelectorAll(".subtab-panel");
const landingHeader = document.getElementById("landing-header");
const authPanel = document.getElementById("auth-panel");
const workspace = document.getElementById("workspace");
const requestCodeForm = document.getElementById("request-code-form");
const verifyCodeForm = document.getElementById("verify-code-form");
const requestCodeResult = document.getElementById("request-code-result");
const verifyCodeResult = document.getElementById("verify-code-result");
const logoutBtn = document.getElementById("logout-btn");
const userBannerTitle = document.getElementById("user-banner-title");
const userBannerCopy = document.getElementById("user-banner-copy");
const workspaceRoleChip = document.getElementById("workspace-role-chip");
const workspaceSummary = document.getElementById("workspace-summary");
const roleForm = document.getElementById("role-form");
const learnerForm = document.getElementById("learner-form");
const roleStatus = document.getElementById("role-status");
const roleDetail = document.getElementById("role-detail");
const roleReviewHistory = document.getElementById("role-review-history");
const reviewNoteInput = document.getElementById("review-note");
const applyReviewBtn = document.getElementById("apply-review-btn");
const publishRoleBtn = document.getElementById("publish-role-btn");
const reviewBackToRolesBtn = document.getElementById("review-back-to-roles-btn");
const trainerCourseTitle = document.getElementById("trainer-course-title");
const roleSelect = document.getElementById("role-select");
const trainerCoursePreview = document.getElementById("trainer-course-preview");
const trainerRoleLibrary = document.getElementById("trainer-role-library");
const backToRolesBtn = document.getElementById("back-to-roles-btn");
const adminSummary = document.getElementById("admin-summary");
const learnerCourseTitle = document.getElementById("learner-course-title");
const learnerReviewBackBtn = document.getElementById("learner-review-back-btn");
const learnerMetrics = document.getElementById("learner-metrics");
const courseView = document.getElementById("course-view");
const learnerReviewSummary = document.getElementById("learner-review-summary");
const assessmentResult = document.getElementById("assessment-result");
const kpiView = document.getElementById("kpi-view");
const lessonPlayerModal = document.getElementById("lesson-player-modal");
const lessonPlayerTitle = document.getElementById("lesson-player-title");
const lessonPlayerBadge = document.getElementById("lesson-player-badge");
const lessonPlayerSection = document.getElementById("lesson-player-section");
const lessonPlayerVideo = document.getElementById("lesson-player-video");
const lessonPlayerCanvas = document.getElementById("lesson-player-canvas");
const lessonPlayerScene = document.getElementById("lesson-player-scene");
const lessonPlayerProgress = document.getElementById("lesson-player-progress");
const lessonPlayerMeta = document.getElementById("lesson-player-meta");
const closeLessonPlayerBtn = document.getElementById("close-lesson-player-btn");
const trainerSummary = document.getElementById("trainer-summary");
const trainerOverviewDetail = document.getElementById("trainer-overview-detail");
const trainerInsights = document.getElementById("trainer-insights");
const roleMetrics = document.getElementById("role-metrics");
let pendingPhoneNumber = "";

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

function lessonScenesFromContent(lesson) {
  const lines = String(lesson.content || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const chunks = [];
  for (let index = 0; index < lines.length; index += 3) {
    chunks.push(lines.slice(index, index + 3));
  }
  return chunks.length ? chunks : [[lesson.summary || "Lesson overview"]];
}

function formatClock(milliseconds) {
  const totalSeconds = Math.max(0, Math.floor(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function stopAllInlineVideos() {
  Object.values(state.inlineVideoPlayers || {}).forEach((player) => {
    if (player?.timer) {
      window.clearInterval(player.timer);
      player.timer = null;
    }
  });
}

function initializeInlineVideoPlayers(dashboard) {
  stopAllInlineVideos();
  const videoLessons = dashboard.enrollment.course.sections.flatMap((section) =>
    section.lessons.filter((lesson) => lesson.resource_type === "video")
  );
  state.inlineVideoPlayers = Object.fromEntries(
    videoLessons.map((lesson) => [
      lesson.id,
      {
        elapsedMs: 0,
        durationMs: Math.max(60000, lesson.duration_minutes * 60000),
        timer: null,
      },
    ])
  );
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

function displayUserType(value) {
  if (value === "trainer" || value === "owner") {
    return "Trainer";
  }
  if (value === "learner") {
    return "Learner";
  }
  return titleCaseLabel(value);
}

function normalizeDisplayName(user) {
  const name = String(user?.name || "").trim();
  if (!name) {
    return user?.user_type === "trainer" ? "Cultfit Trainer" : "Cultfit Learner";
  }
  if (user?.user_type === "trainer") {
    return name.replace(/\bowner\b/gi, "Trainer");
  }
  return name;
}

function currentSelectedRole() {
  return state.roles.find((role) => role.id === state.selectedRoleId) || null;
}

function formatTargetValue(kpi) {
  const target = kpi?.target_value ?? "";
  const unit = String(kpi?.unit || "").trim();
  return unit ? `${target} ${unit}` : String(target);
}

function flattenCourseLessons(role) {
  return (role?.course_template?.sections || []).flatMap((section) =>
    (section.lessons || []).map((lesson) => ({ ...lesson, section_key: section.key, section_title: section.title }))
  );
}

function openTrainerCourseMode(mode, lessonId = null) {
  const role = currentSelectedRole();
  if (!role) {
    return;
  }
  state.trainerCourseView = { mode, lessonId };
  setSubtab("admin", "trainer-role-course");
  renderTrainerCoursePreview(role);
}

function attachTrainerReviewHandlers(role) {
  document.querySelectorAll(".review-jump-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const target = document.getElementById(button.dataset.reviewTarget);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  document.querySelectorAll(".trainer-review-open-video-btn").forEach((button) => {
    button.addEventListener("click", () => openLessonPlayer(button.dataset.lesson));
  });
  document.querySelectorAll(".trainer-review-open-assignment-btn, .trainer-review-open-lesson-btn").forEach((button) => {
    button.addEventListener("click", () => openTrainerCourseMode("lesson", button.dataset.lesson));
  });
  document.querySelectorAll(".trainer-review-open-assessment-btn").forEach((button) => {
    button.addEventListener("click", () => openTrainerCourseMode("assessment"));
  });
  document.querySelectorAll(".trainer-review-open-course-btn").forEach((button) => {
    button.addEventListener("click", () => openTrainerCourseMode("overview"));
  });
}

function assignmentPromptsForLesson(lesson) {
  if (lesson.assignment_prompts?.length) {
    return lesson.assignment_prompts;
  }
  const lines = String(lesson.content || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => line.length > 14)
    .slice(0, 2);
  return [
    {
      id: `${lesson.id}-prompt-1`,
      prompt: lines[0] || `What action will you take after completing ${lesson.title}?`,
      expected_response: "Describe the concrete action.",
    },
    {
      id: `${lesson.id}-prompt-2`,
      prompt: lines[1] || "How will you apply this assignment on the floor?",
      expected_response: "Describe your execution step.",
    },
    {
      id: `${lesson.id}-prompt-3`,
      prompt: "How will you measure whether this assignment worked?",
      expected_response: "Mention the KPI, behaviour, or observation.",
    },
  ];
}

function setTab(tabName) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === tabName));
}

tabs.forEach((tab) => tab.addEventListener("click", () => setTab(tab.dataset.tab)));

function setSubtab(group, panelId) {
  const nextTab = [...subtabs].find((tab) => tab.dataset.group === group && tab.dataset.subtab === panelId);
  if (nextTab?.disabled) {
    return;
  }
  state.activeSubtabs[group] = panelId;
  subtabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.group === group && tab.dataset.subtab === panelId);
  });
subtabPanels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.group === group && panel.id === panelId);
  });
}

subtabs.forEach((tab) => {
  tab.addEventListener("click", () => setSubtab(tab.dataset.group, tab.dataset.subtab));
});

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
  landingHeader.classList.remove("hidden");
  authPanel.classList.remove("hidden");
  workspace.classList.add("hidden");
  verifyCodeForm.classList.add("hidden");
  verifyCodeForm.reset();
  requestCodeResult.innerHTML = "";
  verifyCodeResult.innerHTML = "";
  pendingPhoneNumber = "";
}

function showWorkspace() {
  landingHeader.classList.add("hidden");
  authPanel.classList.add("hidden");
  workspace.classList.remove("hidden");
}

function setVisibilityForUser() {
  const isTrainer = state.currentUser?.user_type === "trainer";
  const displayName = normalizeDisplayName(state.currentUser);
  document.querySelectorAll(".trainer-only").forEach((node) => node.classList.toggle("hidden", !isTrainer));
  document.querySelectorAll(".learner-only").forEach((node) => node.classList.toggle("hidden", isTrainer));
  if (isTrainer) {
    setTab("admin");
    setSubtab("admin", state.activeSubtabs.admin || "trainer-role-input");
    workspaceRoleChip.textContent = "Trainer";
    userBannerTitle.textContent = "Trainer Studio";
    userBannerCopy.textContent = `${displayName} · ${state.currentUser.phone_number}`;
    workspaceSummary.innerHTML = `
      <div class="workspace-pill">
        <span class="meta">Access</span>
        <strong>Role setup, review, publishing</strong>
      </div>
      <div class="workspace-pill">
        <span class="meta">View</span>
        <strong>Trainer metrics and learner progress</strong>
      </div>
    `;
  } else {
    setTab("learner");
    setSubtab("learner", state.activeSubtabs.learner || "learner-course");
    workspaceRoleChip.textContent = "Learner";
    userBannerTitle.textContent = "My Learning";
    userBannerCopy.textContent = `${displayName} · role-based access only`;
    workspaceSummary.innerHTML = `
      <div class="workspace-pill">
        <span class="meta">Access</span>
        <strong>Assigned lessons, assignments, assessment</strong>
      </div>
      <div class="workspace-pill">
        <span class="meta">Focus</span>
        <strong>KPI actions and improvement plan</strong>
      </div>
    `;
  }
}

function renderRoleOptions() {
  const publishedRoles = state.roles.filter((role) => role.status === "published");
  roleSelect.innerHTML = publishedRoles.length
    ? publishedRoles.map((role) => `<option value="${role.id}">${escapeHtml(role.title)}</option>`).join("")
    : `<option value="">Publish a role first</option>`;
}

function updateTrainerStudioState(selectedRole) {
  const reviewTab = [...subtabs].find((tab) => tab.dataset.group === "admin" && tab.dataset.subtab === "trainer-review");
  const usersTab = [...subtabs].find((tab) => tab.dataset.group === "admin" && tab.dataset.subtab === "trainer-users");
  const hasRole = Boolean(selectedRole);
  const isPublished = selectedRole?.status === "published";

  if (reviewTab) {
    reviewTab.disabled = !hasRole;
  }
  if (usersTab) {
    usersTab.disabled = !isPublished;
  }

  if (!hasRole && state.activeSubtabs.admin !== "trainer-role-input" && state.activeSubtabs.admin !== "trainer-roles") {
    setSubtab("admin", "trainer-role-input");
  }
  if (hasRole && !isPublished && ["trainer-role-course", "trainer-users"].includes(state.activeSubtabs.admin)) {
    setSubtab("admin", "trainer-review");
  }
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
          <span class="chip ${user.user_type === "trainer" ? "soft" : "warn"}">${escapeHtml(displayUserType(user.user_type))}</span>
        </div>
        <div class="meta">${escapeHtml(user.phone_number)}</div>
        <div class="meta">${user.role_id ? `Assigned role ${escapeHtml(user.role_id)}` : "Platform trainer access"}</div>
      </div>
    `).join("")}
  `;
}

function renderRoleDetail(role) {
  if (!role) {
    roleStatus.innerHTML = "No generated role yet.";
    roleDetail.innerHTML = "";
    roleReviewHistory.innerHTML = "";
    applyReviewBtn.disabled = true;
    publishRoleBtn.disabled = true;
    return;
  }
  const inputSummary = role.work_summary || role.summary || "Role input summary not available yet.";
  const courseLessons = flattenCourseLessons(role);
  roleStatus.innerHTML = `
    <div class="review-status-card">
      <div class="review-status-copy">
        <p class="eyebrow">Role Overview</p>
        <div class="inline">
          <strong>${escapeHtml(role.title)}</strong>
          <span class="chip ${statusTone(role.status)}">${escapeHtml(titleCaseLabel(role.status))}</span>
        </div>
        <div class="meta">${escapeHtml(role.segment)}</div>
        <div class="meta">${escapeHtml(inputSummary)}</div>
        <div class="actions review-nav">
          <button class="secondary review-jump-btn" data-review-target="review-input-data">Input Data</button>
          <button class="secondary review-jump-btn" data-review-target="review-learning-path">Learning Path</button>
          <button class="secondary review-jump-btn" data-review-target="review-input-section">Review Input</button>
        </div>
      </div>
      <div class="review-status-metrics">
        <div class="mini-stat">
          <span class="meta">Path Sections</span>
          <strong>${escapeHtml(role.learning_path.sections.length)}</strong>
        </div>
        <div class="mini-stat">
          <span class="meta">Assessment Questions</span>
          <strong>${escapeHtml(role.course_template.assessment.questions.length)}</strong>
        </div>
      </div>
    </div>
  `;
  const skillNameById = Object.fromEntries((role.skills || []).map((item) => [item.id, item.name]));
  const kpiNameById = Object.fromEntries((role.kpis || []).map((item) => [item.id, item.name]));
  roleReviewHistory.innerHTML = role.review_notes?.length
    ? role.review_notes.map((item, index) => `
      <div class="review-note-card">
        <div class="inline">
          <strong>Review ${index + 1}</strong>
          <span class="chip soft">Saved</span>
        </div>
        <div class="meta">${escapeHtml(item.text)}</div>
      </div>
    `).join("")
    : `<div class="empty review-empty">No review notes added yet.</div>`;
  roleDetail.innerHTML = `
    <section id="review-input-data" class="review-stage review-stage-box">
      <div class="review-stage-head">
        <div>
          <p class="eyebrow">1. Input Data</p>
          <h3>Role Input Data</h3>
        </div>
        <p class="meta">Original role details captured before course generation.</p>
      </div>
      <div class="review-grid">
        <div class="card review-card">
          <h4 class="section-title">Role Details</h4>
          <div class="review-key-value">
            <div><span class="meta">Segment</span><strong>${escapeHtml(role.segment)}</strong></div>
            <div><span class="meta">Role</span><strong>${escapeHtml(role.title)}</strong></div>
            <div><span class="meta">Status</span><strong>${escapeHtml(titleCaseLabel(role.status))}</strong></div>
          </div>
        </div>
        <div class="card review-card review-card-wide">
          <h4 class="section-title">Work Summary</h4>
          <div class="review-copy">${escapeHtml(role.work_summary || "No work summary added.")}</div>
        </div>
        <div class="card review-card">
          <h4 class="section-title">Responsibilities</h4>
          <div class="tag-row">${role.responsibilities.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("")}</div>
        </div>
        <div class="card review-card">
          <h4 class="section-title">Skills</h4>
          <div class="tag-row">${role.skills.map((item) => `<span class="chip">${escapeHtml(item.name)}</span>`).join("")}</div>
        </div>
        <div class="card review-card review-card-wide">
          <h4 class="section-title">KPIs</h4>
          <div class="review-kpi-grid">
            ${role.kpis.map((kpi) => `
              <div class="mini-stat review-kpi-card">
                <strong>${escapeHtml(kpi.name)}</strong>
                <div class="meta">${escapeHtml(kpi.description)}</div>
                <div class="meta">Target ${escapeHtml(formatTargetValue(kpi))}</div>
                <div class="meta">Weak threshold ${escapeHtml(kpi.weak_threshold)}</div>
              </div>
            `).join("")}
          </div>
        </div>
      </div>
    </section>
    <section id="review-learning-path" class="review-stage review-stage-box">
      <div class="review-stage-head">
        <div>
          <p class="eyebrow">2. Learning Path</p>
          <h3>Learner Course Preview</h3>
        </div>
        <p class="meta">Review the exact lesson flow the learner will see before approval.</p>
      </div>
      <div class="stack detail-list">
        ${(role.course_template.sections || []).map((section, index) => `
          <details class="learning-path-section review-path-card" ${index === 0 ? "open" : ""}>
            <summary class="learning-path-summary">
              <div class="learning-path-head">
                <div>
                  <div class="inline">
                    <strong>${index + 1}. ${escapeHtml(section.title)}</strong>
                    <span class="chip">${section.lessons.length} lessons</span>
                  </div>
                  <div class="meta">${escapeHtml(section.description)}</div>
                </div>
              </div>
            </summary>
            <div class="stack learning-path-content">
              ${section.lessons.map((lesson) => `
                <div class="lesson lesson-card">
                  <div class="inline">
                    <strong>${escapeHtml(lesson.title)}</strong>
                    <span class="chip">${escapeHtml(lesson.resource_type)}</span>
                    <span class="chip">${escapeHtml(lesson.duration_minutes)} min</span>
                  </div>
                  <div class="meta">${escapeHtml(lesson.summary)}</div>
                  <div class="meta">Skills: ${lesson.skill_ids?.length ? lesson.skill_ids.map((id) => escapeHtml(skillNameById[id] || id)).join(", ") : "None linked"}</div>
                  <div class="meta">KPIs: ${lesson.kpi_ids?.length ? lesson.kpi_ids.map((id) => escapeHtml(kpiNameById[id] || id)).join(", ") : "None linked"}</div>
                  <div class="actions">
                    ${lesson.resource_type === "video" ? `<button class="secondary trainer-review-open-video-btn" data-lesson="${lesson.id}">Open Video</button>` : ""}
                    ${lesson.resource_type === "assignment" ? `<button class="secondary trainer-review-open-assignment-btn" data-lesson="${lesson.id}">Open Assignment</button>` : ""}
                    ${lesson.resource_type === "document" ? `<button class="secondary trainer-review-open-lesson-btn" data-lesson="${lesson.id}">Open Lesson</button>` : ""}
                  </div>
                </div>
              `).join("")}
            </div>
          </details>
        `).join("")}
        <div class="card review-card">
          <h4 class="section-title">Assessment Preview</h4>
          <div class="meta">${role.course_template.assessment.questions.length} MCQs with learner-facing preview access from this page.</div>
          <div class="meta">${courseLessons.filter((lesson) => lesson.resource_type === "video").length} videos · ${courseLessons.filter((lesson) => lesson.resource_type === "assignment").length} assignments · ${courseLessons.filter((lesson) => lesson.resource_type === "document").length} lessons</div>
          <div class="actions">
            <button class="secondary trainer-review-open-assessment-btn">Open MCQ Preview</button>
          </div>
        </div>
      </div>
    </section>
  `;
  attachTrainerReviewHandlers(role);
  applyReviewBtn.disabled = false;
  publishRoleBtn.disabled = role.status === "published";
}

function renderTrainerCoursePreview(role) {
  if (!role) {
    trainerCourseTitle.textContent = "Role Course";
    trainerCoursePreview.innerHTML = `<div class="empty">Select or create a role first.</div>`;
    return;
  }
  if (role.status !== "published") {
    trainerCourseTitle.textContent = `${role.title} Course`;
    trainerCoursePreview.innerHTML = `<div class="empty">Approve the role first to open the generated course.</div>`;
    return;
  }

  const sections = role.course_template.sections || [];
  trainerCourseTitle.textContent = `${role.title} Course`;

  if (state.trainerCourseView.mode === "lesson" && state.trainerCourseView.lessonId) {
    const lesson = sections.flatMap((section) => section.lessons).find((item) => item.id === state.trainerCourseView.lessonId);
    if (!lesson) {
      state.trainerCourseView = { mode: "overview", lessonId: null };
      return renderTrainerCoursePreview(role);
    }
    trainerCoursePreview.innerHTML = `
      <div class="card">
        <div class="inline">
          <strong>${escapeHtml(lesson.title)}</strong>
          <span class="chip">${escapeHtml(lesson.resource_type)}</span>
          <span class="chip">${escapeHtml(lesson.duration_minutes)} min</span>
        </div>
        <div class="meta">${escapeHtml(lesson.summary)}</div>
        <div class="actions">
          <button class="secondary trainer-course-back-btn">Back To Course</button>
          <button class="secondary trainer-open-review-btn">Back To Review</button>
          ${lesson.resource_type === "video" ? `<button class="primary trainer-open-video-btn" data-lesson="${lesson.id}">Open Video</button>` : ""}
        </div>
      </div>
      <div class="card">
        <h3 class="section-title">${lesson.resource_type === "assignment" ? "Assignment Brief" : "Lesson Brief"}</h3>
        <div class="lesson-content">${escapeHtml(lesson.content)}</div>
      </div>
      ${lesson.resource_type === "assignment" ? `
        <div class="card">
          <h3 class="section-title">Assignment Questions</h3>
          <div class="stack">
            ${assignmentPromptsForLesson(lesson).map((prompt, index) => `
              <div class="spotlight">
                <strong>Question ${index + 1}</strong>
                <div class="meta">${escapeHtml(prompt.prompt)}</div>
              </div>
            `).join("")}
          </div>
        </div>
      ` : ""}
    `;
    attachTrainerCourseHandlers(role);
    return;
  }

  if (state.trainerCourseView.mode === "assessment") {
    const assessment = role.course_template.assessment;
    trainerCoursePreview.innerHTML = `
      <div class="card">
        <div class="inline">
          <strong>${escapeHtml(assessment.title)}</strong>
          <span class="chip">${assessment.questions.length} MCQs</span>
          <span class="chip soft">Passing ${assessment.passing_score}%</span>
        </div>
        <div class="meta">Preview the generated MCQ bank for this role before assigning learners.</div>
        <div class="actions">
          <button class="secondary trainer-course-back-btn">Back To Course</button>
          <button class="secondary trainer-open-review-btn">Back To Review</button>
        </div>
      </div>
      <div class="stack">
        ${assessment.questions.map((question, index) => `
          <div class="card">
            <strong>Q${index + 1}. ${escapeHtml(question.prompt)}</strong>
            <div class="stack">
              ${question.options.map((option, optionIndex) => `
                <div class="question-option ${optionIndex === question.correct_option_index ? "selected" : ""}">
                  <span>${escapeHtml(option)}</span>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>
    `;
    attachTrainerCourseHandlers(role);
    return;
  }

  trainerCoursePreview.innerHTML = `
    <div class="card">
      <div class="inline">
        <strong>${escapeHtml(role.course_template.title)}</strong>
        <span class="chip soft">Published</span>
        <span class="chip">${escapeHtml(role.segment)}</span>
      </div>
      <div class="meta">${escapeHtml(role.course_template.description)}</div>
      <div class="actions">
        <button class="secondary trainer-open-review-btn">Open Review</button>
        <button class="secondary trainer-open-assessment-btn">Open Assessment</button>
      </div>
    </div>
    ${sections.map((section) => `
      <div class="card">
        <h3 class="section-title">${escapeHtml(section.title)}</h3>
        <div class="meta">${escapeHtml(section.description)}</div>
        <div class="stack">
          ${section.lessons.map((lesson) => `
            <div class="spotlight">
              <div class="inline">
                <strong>${escapeHtml(lesson.title)}</strong>
                <span class="chip">${escapeHtml(lesson.resource_type)}</span>
                <span class="chip">${escapeHtml(lesson.duration_minutes)} min</span>
              </div>
              <div class="meta">${escapeHtml(lesson.summary)}</div>
              <div class="actions">
                ${lesson.resource_type === "video" ? `<button class="secondary trainer-open-video-btn" data-lesson="${lesson.id}">Open Video</button>` : ""}
                ${lesson.resource_type === "assignment" ? `<button class="secondary trainer-open-assignment-btn" data-lesson="${lesson.id}">Open Assignment</button>` : ""}
                ${lesson.resource_type === "document" ? `<button class="secondary trainer-open-lesson-btn" data-lesson="${lesson.id}">Open Lesson</button>` : ""}
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `).join("")}
    <div class="card">
      <h3 class="section-title">Assessment</h3>
      <div class="meta">${role.course_template.assessment.questions.length} questions · passing score ${role.course_template.assessment.passing_score}%</div>
      <div class="actions">
        <button class="secondary trainer-open-assessment-btn">Open MCQ Preview</button>
      </div>
    </div>
  `;
  attachTrainerCourseHandlers(role);
}

function attachTrainerCourseHandlers(role) {
  document.querySelectorAll(".trainer-open-video-btn").forEach((button) => {
    button.addEventListener("click", () => openLessonPlayer(button.dataset.lesson));
  });
  document.querySelectorAll(".trainer-open-lesson-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.trainerCourseView = { mode: "lesson", lessonId: button.dataset.lesson };
      renderTrainerCoursePreview(role);
    });
  });
  document.querySelectorAll(".trainer-open-assignment-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.trainerCourseView = { mode: "lesson", lessonId: button.dataset.lesson };
      renderTrainerCoursePreview(role);
    });
  });
  document.querySelectorAll(".trainer-open-assessment-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.trainerCourseView = { mode: "assessment", lessonId: null };
      renderTrainerCoursePreview(role);
    });
  });
  document.querySelectorAll(".trainer-course-back-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.trainerCourseView = { mode: "overview", lessonId: null };
      renderTrainerCoursePreview(role);
    });
  });
  document.querySelectorAll(".trainer-open-review-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.trainerCourseView = { mode: "overview", lessonId: null };
      setSubtab("admin", "trainer-review");
    });
  });
}

function renderTrainerRoleLibrary() {
  if (!state.roles.length) {
    trainerRoleLibrary.innerHTML = `<div class="empty">No roles created yet.</div>`;
    return;
  }

  trainerRoleLibrary.innerHTML = `
    <div class="card">
      <strong>Roles</strong>
      <div class="meta">Published roles open their course page. Draft roles stay in review until approved.</div>
    </div>
    ${state.roles.map((role) => `
    <div class="card role-library-card ${role.status === "published" ? "role-card-clickable" : ""}" data-role-open-target="${role.status === "published" ? "course" : ""}" data-role-id="${role.id}">
      <div class="inline">
        <strong>${escapeHtml(role.title)}</strong>
        <span class="chip ${statusTone(role.status)}">${escapeHtml(titleCaseLabel(role.status))}</span>
        <span class="chip">${escapeHtml(role.segment)}</span>
      </div>
      <div class="meta">${escapeHtml(role.summary || role.work_summary || "")}</div>
      <div class="actions">
        <button class="secondary role-open-review" data-role-id="${role.id}">Open Review</button>
        <button class="secondary role-open-course" data-role-id="${role.id}" ${role.status !== "published" ? "disabled" : ""}>Open Course Page</button>
      </div>
    </div>
  `).join("")}
  `;

  document.querySelectorAll(".role-open-review").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      state.selectedRoleId = button.dataset.roleId;
      state.trainerCourseView = { mode: "overview", lessonId: null };
      refreshTrainerData().catch((error) => alert(error.message));
      setSubtab("admin", "trainer-review");
    });
  });

  document.querySelectorAll(".role-open-course").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      state.selectedRoleId = button.dataset.roleId;
      state.trainerCourseView = { mode: "overview", lessonId: null };
      refreshTrainerData().catch((error) => alert(error.message));
      setSubtab("admin", "trainer-role-course");
    });
  });

  document.querySelectorAll(".role-library-card[data-role-open-target='course']").forEach((card) => {
    card.addEventListener("click", () => {
      state.selectedRoleId = card.dataset.roleId;
      state.trainerCourseView = { mode: "overview", lessonId: null };
      refreshTrainerData().catch((error) => alert(error.message));
      setSubtab("admin", "trainer-role-course");
    });
  });
}

function renderLearnerDashboard(dashboard) {
  state.learnerDashboard = dashboard;
  initializeInlineVideoPlayers(dashboard);
  const questions = dashboard.enrollment.course.assessment.questions || [];
  const previousAnswers = state.assessmentAnswers || {};
  state.assessmentAnswers = Object.fromEntries(
    questions.map((question) => [question.id, Object.prototype.hasOwnProperty.call(previousAnswers, question.id) ? previousAnswers[question.id] : null])
  );
  state.currentQuestionIndex = Math.min(state.currentQuestionIndex, Math.max(questions.length - 1, 0));
  const metrics = dashboard.metrics;
  learnerMetrics.innerHTML = `
    <div class="inline">
      <strong>${escapeHtml(dashboard.role.title)}</strong>
      <span class="chip soft">${escapeHtml(dashboard.role.segment)}</span>
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

  renderLearnerCoursePage(dashboard);
  renderLearnerReview(dashboard);
}

function renderLearnerCoursePage(dashboard) {
  const latestAttempt = dashboard.latest_assessment;
  const openImprovementPlan = (dashboard.remediation_assignments || []).find((item) => item.status === "assigned");
  const sections = dashboard.enrollment.course.sections || [];
  learnerCourseTitle.textContent = `${dashboard.role.title} Course`;

  if (state.learnerCourseView.mode === "lesson" && state.learnerCourseView.lessonId) {
    const lesson = sections.flatMap((section) => section.lessons).find((item) => item.id === state.learnerCourseView.lessonId);
    if (!lesson) {
      state.learnerCourseView = { mode: "overview", lessonId: null };
      return renderLearnerCoursePage(dashboard);
    }
    const complete = dashboard.enrollment.completed_lesson_ids.includes(lesson.id);
    const existingSubmission = (dashboard.assignment_submissions || []).find((item) => item.lesson_id === lesson.id);
    courseView.innerHTML = `
      <div class="card">
        <div class="inline">
          <strong>${escapeHtml(lesson.title)}</strong>
          <span class="chip">${escapeHtml(lesson.resource_type)}</span>
          <span class="chip">${escapeHtml(lesson.duration_minutes)} min</span>
          ${complete ? `<span class="chip soft">Completed</span>` : ""}
        </div>
        <div class="meta">${escapeHtml(lesson.summary)}</div>
        <div class="actions">
          <button class="secondary learner-course-back-btn">Back To Course</button>
          ${lesson.resource_type === "video" ? `<button class="primary learner-open-video-btn" data-lesson="${lesson.id}">Open Video</button>` : ""}
          ${!complete ? `<button class="secondary complete-lesson-btn" data-lesson="${lesson.id}">${lesson.resource_type === "assignment" ? "Submit Assignment" : "Mark Complete"}</button>` : ""}
        </div>
      </div>
      <div class="card">
        <h3 class="section-title">${lesson.resource_type === "assignment" ? "Assignment Brief" : "Lesson Brief"}</h3>
        <div class="lesson-content">${escapeHtml(lesson.content)}</div>
      </div>
      ${lesson.resource_type === "assignment" ? `
        <form id="learner-assignment-form" class="card form">
          <h3 class="section-title">Assignment Questions</h3>
          ${assignmentPromptsForLesson(lesson).map((prompt, index) => `
            <label>
              Question ${index + 1}
              <div class="meta">${escapeHtml(prompt.prompt)}</div>
              <textarea name="${prompt.id}" rows="4" placeholder="${escapeHtml(prompt.expected_response || "Write your response")}" ${existingSubmission ? "disabled" : ""}>${existingSubmission ? escapeHtml((existingSubmission.responses || []).find((item) => item.prompt_id === prompt.id)?.response_text || "") : ""}</textarea>
            </label>
          `).join("")}
          <div class="actions">
            ${existingSubmission ? `<span class="chip soft">Assignment submitted</span>` : `<button type="submit" class="primary">Submit Assignment</button>`}
          </div>
        </form>
      ` : ""}
    `;
    attachLearnerCourseHandlers(dashboard);
    return;
  }

  if (state.learnerCourseView.mode === "assessment") {
    const assessment = dashboard.enrollment.course.assessment;
    courseView.innerHTML = `
      <div class="card">
        <div class="inline">
          <strong>${escapeHtml(assessment.title)}</strong>
          <span class="chip">${assessment.questions.length} MCQs</span>
          <span class="chip soft">Passing ${assessment.passing_score}%</span>
        </div>
        <div class="meta">Complete the assessment and your review page will update with weak skills, KPI risk areas, and question analysis.</div>
        <div class="actions">
          <button class="secondary learner-course-back-btn">Back To Course</button>
          <button class="primary learner-submit-assessment-btn" ${assessment.questions.some((question) => state.assessmentAnswers[question.id] === null || state.assessmentAnswers[question.id] === undefined) ? "disabled" : ""}>Submit Assessment</button>
        </div>
      </div>
      <form id="course-assessment-form" class="stack">
        ${assessment.questions.map((question, index) => `
          <div class="card">
            <strong>Q${index + 1}. ${escapeHtml(question.prompt)}</strong>
            <div class="question-options">
              ${question.options.map((option, optionIndex) => `
                <label class="question-option ${state.assessmentAnswers[question.id] === optionIndex ? "selected" : ""}">
                  <input type="radio" name="${question.id}" value="${optionIndex}" ${state.assessmentAnswers[question.id] === optionIndex ? "checked" : ""}>
                  <span>${escapeHtml(option)}</span>
                </label>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </form>
    `;
    attachLearnerCourseHandlers(dashboard);
    return;
  }

  if (state.learnerCourseView.mode === "kpi") {
    courseView.innerHTML = `
      <div class="card">
        <div class="inline">
          <strong>Record KPI Observation</strong>
          <span class="chip soft">${dashboard.role.kpis.length} KPIs</span>
        </div>
        <div class="meta">Record current performance against your role KPIs. The review page will update with KPI health and improvement plans.</div>
        <div class="actions">
          <button class="secondary learner-course-back-btn">Back To Course</button>
        </div>
      </div>
      <form id="course-kpi-form" class="form card">
        <label>KPI<select id="course-kpi-select" name="kpi_id">${dashboard.role.kpis.map((kpi) => `<option value="${kpi.id}" data-target="${kpi.target_value}">${escapeHtml(kpi.name)} · target ${escapeHtml(kpi.target_value)}${escapeHtml(kpi.unit)}</option>`).join("")}</select></label>
        <label>Actual Value<input name="value" type="number" step="0.01" required></label>
        <label>Target Value<input name="target_value" type="number" step="0.01" value="${dashboard.role.kpis[0]?.target_value ?? ""}" required></label>
        <label>Period<input name="period_label" value="Current Month"></label>
        <label>Notes<textarea name="notes" rows="3"></textarea></label>
        <button type="submit" class="primary">Save KPI Observation</button>
      </form>
    `;
    attachLearnerCourseHandlers(dashboard);
    return;
  }

  courseView.innerHTML = `
    <div class="grid two learner-overview-grid">
      <div class="card">
        <h3 class="section-title">Current Focus</h3>
        <div class="stack">
          <div class="spotlight">
            <strong>${openImprovementPlan ? "Improvement plan active" : "Current focus"}</strong>
            <div class="meta">${escapeHtml(openImprovementPlan ? openImprovementPlan.summary : "Finish the remaining lessons and complete the mastery check for your role.")}</div>
          </div>
          <div class="spotlight">
            <strong>${latestAttempt ? "Latest assessment summary" : "Assessment not submitted yet"}</strong>
            <div class="meta">${escapeHtml(latestAttempt ? latestAttempt.analysis_summary : "Complete the course first, then take the assessment to get skill and KPI analysis.")}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <h3 class="section-title">Course Status</h3>
        <div class="metric-grid">
          <div class="metric-item"><span class="meta">Lessons Done</span><strong>${dashboard.metrics.lessons_completed}/${dashboard.metrics.total_lessons}</strong></div>
          <div class="metric-item"><span class="meta">Healthy KPIs</span><strong>${dashboard.metrics.healthy_kpis}</strong></div>
        </div>
        <div class="actions">
          <button class="secondary learner-open-assessment-btn">Open Assessment</button>
          <button class="secondary learner-open-kpi-btn">Record KPI</button>
        </div>
      </div>
    </div>
    ${sections.map((section) => `
    <div class="card">
      <div class="inline">
        <h3 class="section-title">${escapeHtml(section.title)}</h3>
        <span class="chip">${section.lessons.length} lessons</span>
      </div>
      <div class="meta">${escapeHtml(section.description)}</div>
      <div class="stack">
        ${section.lessons.map((lesson) => {
          const complete = dashboard.enrollment.completed_lesson_ids.includes(lesson.id);
          return `
            <div class="lesson lesson-card ${complete ? "lesson-complete" : ""}">
              <div class="inline">
                <strong>${escapeHtml(lesson.title)}</strong>
                <span class="chip">${escapeHtml(lesson.resource_type)}</span>
                <span class="chip">${escapeHtml(lesson.duration_minutes)} min</span>
                ${complete ? `<span class="chip soft">Completed</span>` : ""}
              </div>
              <div class="meta">${escapeHtml(lesson.summary)}</div>
              <div class="actions">
                ${lesson.resource_type === "video" ? `<button class="secondary learner-open-video-btn" data-lesson="${lesson.id}">Open Video</button>` : ""}
                ${lesson.resource_type === "assignment" ? `<button class="secondary learner-open-assignment-btn" data-lesson="${lesson.id}">Open Assignment</button>` : ""}
                ${lesson.resource_type === "document" ? `<button class="secondary learner-open-lesson-btn" data-lesson="${lesson.id}">Open Lesson</button>` : ""}
                ${!complete ? `<button class="secondary complete-lesson-btn" data-lesson="${lesson.id}">${lesson.resource_type === "assignment" ? "Submit Assignment" : "Mark Complete"}</button>` : ""}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `).join("")}
  `;

  attachLearnerCourseHandlers(dashboard);
}

function renderLearnerReview(dashboard) {
  learnerReviewSummary.innerHTML = `
    <div class="card">
      <span class="meta">Completion</span>
      <strong class="summary-value">${dashboard.metrics.completion_percentage}%</strong>
      <div class="meta">${dashboard.metrics.lessons_completed}/${dashboard.metrics.total_lessons} lessons completed</div>
    </div>
    <div class="card">
      <span class="meta">Assessment</span>
      <strong class="summary-value">${dashboard.metrics.latest_assessment_score ?? "--"}</strong>
      <div class="meta">${dashboard.metrics.weak_skill_count} weak skills · ${dashboard.metrics.weak_kpis} weak KPIs</div>
    </div>
  `;
  renderAssessmentResult(dashboard.latest_assessment);
  renderKpiView(dashboard);
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
    ${attempt.question_results?.length ? `
      <div class="card">
        <h3 class="section-title">Question Review</h3>
        <div class="stack">
          ${attempt.question_results.map((item, index) => `
            <div class="spotlight">
              <div class="inline">
                <strong>Q${index + 1}</strong>
                <span class="chip ${item.is_correct ? "soft" : "warn"}">${item.is_correct ? "Correct" : "Incorrect"}</span>
              </div>
              <div class="meta">${escapeHtml(item.prompt)}</div>
              <div class="meta">${escapeHtml(item.explanation)}</div>
            </div>
          `).join("")}
        </div>
      </div>
    ` : ""}
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
        <h3 class="section-title">Improvement Plan</h3>
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

function attachLearnerCourseHandlers(dashboard) {
  attachLessonHandlers();
  document.querySelectorAll(".learner-open-video-btn").forEach((button) => {
    button.addEventListener("click", () => openLessonPlayer(button.dataset.lesson));
  });
  document.querySelectorAll(".learner-open-lesson-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnerCourseView = { mode: "lesson", lessonId: button.dataset.lesson };
      renderLearnerCoursePage(dashboard);
    });
  });
  document.querySelectorAll(".learner-open-assignment-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnerCourseView = { mode: "lesson", lessonId: button.dataset.lesson };
      renderLearnerCoursePage(dashboard);
    });
  });
  document.querySelectorAll(".learner-open-assessment-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnerCourseView = { mode: "assessment", lessonId: null };
      renderLearnerCoursePage(dashboard);
    });
  });
  document.querySelectorAll(".learner-open-kpi-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnerCourseView = { mode: "kpi", lessonId: null };
      renderLearnerCoursePage(dashboard);
    });
  });
  document.querySelectorAll(".learner-course-back-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.learnerCourseView = { mode: "overview", lessonId: null };
      renderLearnerCoursePage(dashboard);
    });
  });

  const assessmentForm = document.getElementById("course-assessment-form");
  if (assessmentForm) {
    assessmentForm.querySelectorAll("input[type='radio']").forEach((input) => {
      input.addEventListener("change", () => {
        state.assessmentAnswers[input.name] = Number(input.value);
        renderLearnerCoursePage(dashboard);
      });
    });
  }

  const submitAssessmentBtn = document.querySelector(".learner-submit-assessment-btn");
  if (submitAssessmentBtn) {
    submitAssessmentBtn.addEventListener("click", async () => {
      const answers = dashboard.enrollment.course.assessment.questions.map((question) => ({
        question_id: question.id,
        selected_option_index: state.assessmentAnswers[question.id] ?? -1,
      }));
      try {
        await fetchJson("/api/my/assessment/submit", { method: "POST", body: JSON.stringify({ answers }) });
        state.learnerCourseView = { mode: "overview", lessonId: null };
        setSubtab("learner", "learner-review");
        await refreshLearnerData();
      } catch (error) {
        alert(error.message);
      }
    });
  }

  const kpiSelect = document.getElementById("course-kpi-select");
  const kpiForm = document.getElementById("course-kpi-form");
  if (kpiSelect && kpiForm) {
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
        state.learnerCourseView = { mode: "overview", lessonId: null };
        setSubtab("learner", "learner-review");
        await refreshLearnerData();
      } catch (error) {
        alert(error.message);
      }
    });
  }

  const assignmentForm = document.getElementById("learner-assignment-form");
  if (assignmentForm) {
    assignmentForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const lessonId = state.learnerCourseView.lessonId;
      const lesson = (dashboard.enrollment.course.sections || []).flatMap((section) => section.lessons).find((item) => item.id === lessonId);
      const prompts = assignmentPromptsForLesson(lesson || { id: lessonId, content: "" });
      const formData = new FormData(assignmentForm);
      const responses = prompts.map((prompt) => ({
        prompt_id: prompt.id,
        response_text: String(formData.get(prompt.id) || "").trim(),
      }));
      try {
        await fetchJson(`/api/my/assignments/${lessonId}/submit`, { method: "POST", body: JSON.stringify({ responses }) });
        state.learnerCourseView = { mode: "overview", lessonId: null };
        setSubtab("learner", "learner-review");
        await refreshLearnerData();
      } catch (error) {
        alert(error.message);
      }
    });
  }
}

function renderInlineVideoPlayer(lessonId) {
  const sections = state.learnerDashboard?.enrollment?.course?.sections || [];
  let lesson = null;
  sections.forEach((section) => {
    section.lessons.forEach((item) => {
      if (item.id === lessonId) {
        lesson = item;
      }
    });
  });
  const player = state.inlineVideoPlayers[lessonId];
  if (!lesson || !player) {
    return;
  }
  const scenes = lessonScenesFromContent(lesson);
  const sceneIndex = Math.min(scenes.length - 1, Math.floor((player.elapsedMs / player.durationMs) * scenes.length));
  const scene = scenes[Math.max(0, sceneIndex)];
  const progress = Math.max(0, Math.min(100, (player.elapsedMs / player.durationMs) * 100));
  const timeNode = document.getElementById(`video-time-${lessonId}`);
  const sceneNode = document.getElementById(`video-scene-${lessonId}`);
  const progressNode = document.getElementById(`video-progress-${lessonId}`);
  const toggleButton = document.querySelector(`.lesson-video-toggle-btn[data-lesson="${lessonId}"]`);
  if (timeNode) {
    timeNode.textContent = `${formatClock(player.elapsedMs)} / ${formatClock(player.durationMs)}`;
  }
  if (sceneNode) {
    sceneNode.textContent = scene.join(" ");
  }
  if (progressNode) {
    progressNode.style.width = `${progress}%`;
  }
  if (toggleButton) {
    toggleButton.textContent = player.timer ? "Pause" : (player.elapsedMs >= player.durationMs ? "Replay" : "Play");
  }
}

function toggleInlineVideo(lessonId) {
  const player = state.inlineVideoPlayers[lessonId];
  if (!player) {
    return;
  }
  if (player.timer) {
    window.clearInterval(player.timer);
    player.timer = null;
    renderInlineVideoPlayer(lessonId);
    return;
  }
  if (player.elapsedMs >= player.durationMs) {
    player.elapsedMs = 0;
  }
  player.timer = window.setInterval(() => {
    player.elapsedMs += 250;
    if (player.elapsedMs >= player.durationMs) {
      player.elapsedMs = player.durationMs;
      window.clearInterval(player.timer);
      player.timer = null;
    }
    renderInlineVideoPlayer(lessonId);
  }, 250);
  renderInlineVideoPlayer(lessonId);
}

function resetInlineVideo(lessonId) {
  const player = state.inlineVideoPlayers[lessonId];
  if (!player) {
    return;
  }
  if (player.timer) {
    window.clearInterval(player.timer);
    player.timer = null;
  }
  player.elapsedMs = 0;
  renderInlineVideoPlayer(lessonId);
}

function wrapCanvasText(context, text, x, y, maxWidth, lineHeight) {
  const words = String(text).split(/\s+/);
  let line = "";
  let cursorY = y;
  words.forEach((word) => {
    const testLine = line ? `${line} ${word}` : word;
    if (context.measureText(testLine).width > maxWidth && line) {
      context.fillText(line, x, cursorY);
      line = word;
      cursorY += lineHeight;
    } else {
      line = testLine;
    }
  });
  if (line) {
    context.fillText(line, x, cursorY);
    cursorY += lineHeight;
  }
  return cursorY;
}

function drawLessonFrame(context, lesson, sceneLines, sceneIndex, totalScenes) {
  const gradient = context.createLinearGradient(0, 0, 1280, 720);
  gradient.addColorStop(0, "#0f172a");
  gradient.addColorStop(1, "#155e75");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 1280, 720);

  context.fillStyle = "rgba(255,255,255,0.12)";
  context.fillRect(72, 72, 1136, 576);

  context.fillStyle = "#ffffff";
  context.font = "bold 52px Arial";
  wrapCanvasText(context, lesson.title, 110, 150, 980, 64);

  context.font = "28px Arial";
  context.fillStyle = "#99f6e4";
  context.fillText(`${titleCaseLabel(lesson.resource_type)} lesson`, 110, 230);

  context.font = "bold 26px Arial";
  context.fillStyle = "#ffffff";
  context.fillText(`Scene ${sceneIndex + 1} of ${totalScenes}`, 1000, 230);

  context.font = "32px Arial";
  context.fillStyle = "#e2e8f0";
  let cursorY = 320;
  sceneLines.forEach((line) => {
    cursorY = wrapCanvasText(context, line, 110, cursorY, 1060, 42) + 10;
  });

  context.fillStyle = "rgba(255,255,255,0.18)";
  context.fillRect(110, 620, 1060, 12);
  context.fillStyle = "#14b8a6";
  context.fillRect(110, 620, (1060 * (sceneIndex + 1)) / totalScenes, 12);
}

async function generateLessonVideoBlob(lesson, options = {}) {
  const canvas = options.canvas || lessonPlayerCanvas;
  if (!window.MediaRecorder || !canvas.captureStream) {
    return null;
  }
  canvas.width = 1280;
  canvas.height = 720;
  const context = canvas.getContext("2d");
  const scenes = lessonScenesFromContent(lesson);
  const stream = canvas.captureStream(1);
  const chunks = [];
  const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
    ? "video/webm;codecs=vp9"
    : "video/webm";
  const recorder = new MediaRecorder(stream, { mimeType });
  recorder.ondataavailable = (event) => {
    if (event.data && event.data.size) {
      chunks.push(event.data);
    }
  };

  const finished = new Promise((resolve) => {
    recorder.onstop = () => resolve(new Blob(chunks, { type: mimeType }));
  });

  recorder.start();
  for (let index = 0; index < scenes.length; index += 1) {
    drawLessonFrame(context, lesson, scenes[index], index, scenes.length);
    if (options.onProgress) {
      options.onProgress(index + 1, scenes.length);
    }
    await new Promise((resolve) => window.setTimeout(resolve, options.frameDelayMs || 900));
  }
  recorder.stop();
  return finished;
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = String(reader.result || "");
      const [, encoded = ""] = result.split(",", 2);
      resolve(encoded);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function ensureStoredLessonVideo(lesson) {
  if (lesson.media_asset?.kind === "video" && lesson.media_asset?.url) {
    return lesson.media_asset;
  }
  const blob = await generateLessonVideoBlob(lesson, {
    frameDelayMs: 350,
    onProgress(completed, total) {
      lessonPlayerSection.textContent = `Saving scene ${completed} of ${total}`;
      lessonPlayerProgress.style.width = `${(completed / total) * 100}%`;
    },
  });
  if (!blob) {
    return null;
  }
  if (state.currentUser?.user_type === "trainer") {
    return {
      kind: "video_local_preview",
      url: URL.createObjectURL(blob),
    };
  }
  const encoded = await blobToBase64(blob);
  const uploaded = await fetchJson(`/api/my/lessons/${lesson.id}/media`, {
    method: "POST",
    body: JSON.stringify({
      base64_data: encoded,
      extension: "webm",
      mime_type: blob.type || "video/webm",
    }),
  });
  lesson.media_asset = uploaded.item;
  return lesson.media_asset;
}

function cleanupLessonVideo() {
  lessonPlayerVideo.pause();
  lessonPlayerVideo.removeAttribute("src");
  lessonPlayerVideo.load();
  if (state.lessonVideoUrl && state.lessonVideoUrl.startsWith("blob:")) {
    URL.revokeObjectURL(state.lessonVideoUrl);
  }
  state.lessonVideoUrl = "";
}

async function renderLessonPlayer() {
  const lesson = state.activeLessonPlayer;
  if (!lesson) {
    return;
  }
  const scenes = lessonScenesFromContent(lesson);
  lessonPlayerTitle.textContent = lesson.title;
  lessonPlayerBadge.textContent = `${titleCaseLabel(lesson.resource_type)} lesson`;
  lessonPlayerSection.textContent = "Generating lesson video";
  lessonPlayerProgress.style.width = "8%";
  lessonPlayerMeta.textContent = `${lesson.duration_minutes} min module · Browser-generated video from lesson scenes.`;
  lessonPlayerScene.innerHTML = scenes.map((sceneLines, index) => `
    <div class="spotlight">
      <strong>Scene ${index + 1}</strong>
      <div class="meta">${escapeHtml(sceneLines.join(" "))}</div>
    </div>
  `).join("");

  cleanupLessonVideo();
  const storedVideo = await ensureStoredLessonVideo(lesson);
  if (!state.activeLessonPlayer || state.activeLessonPlayer.id !== lesson.id) {
    return;
  }
  if (!storedVideo?.url) {
    lessonPlayerSection.textContent = "Video rendering unavailable";
    lessonPlayerMeta.textContent = "This browser does not support local video generation for lesson playback.";
    lessonPlayerProgress.style.width = "0%";
    return;
  }
  state.lessonVideoUrl = storedVideo.url;
  lessonPlayerVideo.src = storedVideo.url;
  lessonPlayerSection.textContent = `Video ready · ${scenes.length} scenes`;
  lessonPlayerProgress.style.width = "100%";
  lessonPlayerVideo.play().catch(() => {});
}

function openLessonPlayer(lessonId) {
  const sections = state.learnerDashboard?.enrollment?.course?.sections
    || currentSelectedRole()?.course_template?.sections
    || [];
  let lesson = null;
  sections.forEach((section) => {
    section.lessons.forEach((item) => {
      if (item.id === lessonId) {
        lesson = item;
      }
    });
  });
  if (!lesson) {
    return;
  }
  state.activeLessonPlayer = lesson;
  lessonPlayerModal.classList.remove("hidden");
  renderLessonPlayer().catch(() => {
    lessonPlayerSection.textContent = "Video generation failed";
    lessonPlayerMeta.textContent = "The lesson could not be converted into a playable video in this browser.";
  });
}

function closeLessonPlayer() {
  cleanupLessonVideo();
  state.activeLessonPlayer = null;
  lessonPlayerModal.classList.add("hidden");
}

function renderTrainerDashboard(data) {
  const summary = data.summary || {};
  const roleItems = data.role_metrics || [];
  const activeRoleItems = roleItems.filter((item) => (item.learner_count || 0) > 0);
  const rolesNeedingAttention = activeRoleItems.filter((item) => (item.completion_percentage || 0) < 80);
  const topRoleByCompletion = [...roleItems].sort((a, b) => (b.completion_percentage || 0) - (a.completion_percentage || 0))[0];
  const topRoleByAssessment = [...roleItems]
    .filter((item) => item.latest_attempt_average !== null && item.latest_attempt_average !== undefined)
    .sort((a, b) => (b.latest_attempt_average || 0) - (a.latest_attempt_average || 0))[0];
  const lowestRoleByCompletion = [...activeRoleItems].sort((a, b) => (a.completion_percentage || 0) - (b.completion_percentage || 0))[0];
  const lowestRoleByAssessment = [...activeRoleItems]
    .filter((item) => item.latest_attempt_average !== null && item.latest_attempt_average !== undefined)
    .sort((a, b) => (a.latest_attempt_average || 0) - (b.latest_attempt_average || 0))[0];
  const weakestSkill = (data.weak_skills || [])[0];
  const weakestKpi = (data.weak_kpis || [])[0];
  const avgLearnersPerRole = summary.roles_published ? (summary.learners || 0) / summary.roles_published : 0;

  trainerSummary.innerHTML = `
    <div class="summary-card emphasis">
      <p class="eyebrow">Published Roles</p>
      <strong class="summary-value">${escapeHtml(summary.roles_published ?? 0)}</strong>
      <div class="meta">Active role academies available for assignment.</div>
    </div>
    <div class="summary-card emphasis">
      <p class="eyebrow">Assigned Learners</p>
      <strong class="summary-value">${escapeHtml(summary.learners ?? 0)}</strong>
      <div class="meta">${escapeHtml(avgLearnersPerRole.toFixed(1))} learners per published role on average.</div>
    </div>
    <div class="summary-card">
      <p class="eyebrow">Completion Rate</p>
      <strong class="summary-value">${escapeHtml(summary.course_completion_percentage ?? 0)}%</strong>
      <div class="meta">${escapeHtml(rolesNeedingAttention.length)} roles are below the expected completion mark.</div>
    </div>
    <div class="summary-card">
      <p class="eyebrow">Assessment Quality</p>
      <strong class="summary-value">${escapeHtml(summary.assessment_average ?? "--")}</strong>
      <div class="meta">Latest learner attempt average across active roles.</div>
    </div>
  `;

  trainerOverviewDetail.innerHTML = `
    <div class="card">
      <h3 class="section-title">Coverage</h3>
      <div class="metric-row">
        <div>
          <strong>Role adoption</strong>
          <div class="meta">${escapeHtml(activeRoleItems.length)} roles currently have learners assigned.</div>
        </div>
        <span class="chip soft">${escapeHtml(summary.roles_published ?? 0)} roles</span>
      </div>
      <div class="metric-row">
        <div>
          <strong>Learner distribution</strong>
          <div class="meta">${escapeHtml(avgLearnersPerRole.toFixed(1))} learners per published role.</div>
        </div>
        <span class="chip">${escapeHtml(summary.learners ?? 0)} learners</span>
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Learning Health</h3>
      <div class="metric-row">
        <div>
          <strong>Completion health</strong>
          <div class="meta">Overall progress across all assigned course lessons.</div>
        </div>
        <span class="chip ${(summary.course_completion_percentage ?? 0) >= 80 ? "soft" : "warn"}">${escapeHtml(summary.course_completion_percentage ?? 0)}%</span>
      </div>
      <div class="metric-row">
        <div>
          <strong>Assessment quality</strong>
          <div class="meta">Latest average attempt score across active learners.</div>
        </div>
        <span class="chip ${((summary.assessment_average ?? 0) >= 75) ? "soft" : "warn"}">${escapeHtml(summary.assessment_average ?? "--")}</span>
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Risk Signals</h3>
      <div class="metric-row">
        <div>
          <strong>Open improvement plans</strong>
          <div class="meta">Learners with unresolved KPI-driven follow-up learning.</div>
        </div>
        <span class="chip ${(summary.open_remediation_assignments ?? 0) > 0 ? "warn" : "soft"}">${escapeHtml(summary.open_remediation_assignments ?? 0)}</span>
      </div>
      <div class="metric-row">
        <div>
          <strong>Current weak KPI observations</strong>
          <div class="meta">Latest KPI observations still under target.</div>
        </div>
        <span class="chip ${(summary.weak_kpi_observations ?? 0) > 0 ? "warn" : "soft"}">${escapeHtml(summary.weak_kpi_observations ?? 0)}</span>
      </div>
    </div>
  `;

  trainerInsights.innerHTML = `
    <div class="spotlight">
      <strong>Role needing completion focus</strong>
      <div class="meta">${lowestRoleByCompletion ? `${escapeHtml(lowestRoleByCompletion.role_title)} is at ${escapeHtml(lowestRoleByCompletion.completion_percentage)}% completion.` : "No role has active learner progress yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Role needing assessment support</strong>
      <div class="meta">${lowestRoleByAssessment ? `${escapeHtml(lowestRoleByAssessment.role_title)} is averaging ${escapeHtml(lowestRoleByAssessment.latest_attempt_average)} in the latest attempts.` : "No assessment attempts recorded yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Most repeated weak skill</strong>
      <div class="meta">${weakestSkill ? `${escapeHtml(weakestSkill.label)} is recurring ${escapeHtml(weakestSkill.count)} times across learner attempts.` : "No repeated weak skill pattern recorded yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Most exposed KPI</strong>
      <div class="meta">${weakestKpi ? `${escapeHtml(weakestKpi.label)} is the KPI with the highest repeated weakness at ${escapeHtml(weakestKpi.count)} signals.` : "No weak KPI pattern recorded yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Best performing role</strong>
      <div class="meta">${topRoleByCompletion ? `${escapeHtml(topRoleByCompletion.role_title)} leads on completion at ${escapeHtml(topRoleByCompletion.completion_percentage)}%.` : "No published role completion data yet."}</div>
    </div>
  `;

  roleMetrics.innerHTML = roleItems.map((item) => `
    <div class="spotlight role-metric-card">
      <div class="inline">
        <strong>${escapeHtml(item.role_title)}</strong>
        <span class="chip">${escapeHtml(item.segment)}</span>
      </div>
      <div class="metric-grid">
        <div class="mini-stat">
          <span class="meta">Learners</span>
          <strong>${escapeHtml(item.learner_count)}</strong>
        </div>
        <div class="mini-stat">
          <span class="meta">Completion</span>
          <strong>${escapeHtml(item.completion_percentage)}%</strong>
        </div>
        <div class="mini-stat">
          <span class="meta">Assessment Avg</span>
          <strong>${escapeHtml(item.latest_attempt_average ?? "--")}</strong>
        </div>
        <div class="mini-stat">
          <span class="meta">Current status</span>
          <strong>${(item.learner_count || 0) === 0 ? "No Learners" : ((item.completion_percentage || 0) >= 80 ? "On Track" : "Needs Focus")}</strong>
        </div>
      </div>
      <div class="meta">
        ${(item.learner_count || 0) === 0
          ? "No learners assigned to this role yet."
          : ((item.completion_percentage || 0) >= 80
            ? "Learner progress is healthy for this role."
            : "Completion is below target and needs trainer attention.")}
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${Math.max(0, Math.min(100, item.completion_percentage || 0))}%"></div></div>
    </div>
  `).join("") || `<div class="empty">No trainer metrics yet.</div>`;
}

async function refreshTrainerData() {
  const [rolesRes, usersRes, dashboardRes] = await Promise.all([
    fetchJson("/api/roles"),
    fetchJson("/api/users"),
    fetchJson("/api/dashboard/trainer"),
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
  updateTrainerStudioState(selectedRole || null);
  renderTrainerCoursePreview(selectedRole || null);
  renderTrainerRoleLibrary();
  renderTrainerDashboard(dashboardRes.item);
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
  document.querySelectorAll(".lesson-video-toggle-btn").forEach((button) => {
    button.addEventListener("click", () => toggleInlineVideo(button.dataset.lesson));
  });
  document.querySelectorAll(".lesson-video-reset-btn").forEach((button) => {
    button.addEventListener("click", () => resetInlineVideo(button.dataset.lesson));
  });
  Object.keys(state.inlineVideoPlayers || {}).forEach((lessonId) => renderInlineVideoPlayer(lessonId));
}

requestCodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(requestCodeForm).entries());
  try {
    const res = await fetchJson("/api/auth/request-code", { method: "POST", body: JSON.stringify(payload) });
    pendingPhoneNumber = payload.phone_number;
    verifyCodeForm.classList.remove("hidden");
    requestCodeResult.innerHTML = `<div class="card card-emphasis"><strong>Code generated</strong><div class="meta">For MVP testing, use code <strong>${escapeHtml(res.item.code)}</strong> for ${escapeHtml(payload.phone_number)}.</div></div>`;
    verifyCodeResult.innerHTML = "";
  } catch (error) {
    verifyCodeForm.classList.add("hidden");
    requestCodeResult.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
});

verifyCodeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formValues = Object.fromEntries(new FormData(verifyCodeForm).entries());
  const payload = { phone_number: pendingPhoneNumber, code: formValues.code };
  try {
    const res = await fetchJson("/api/auth/verify-code", { method: "POST", body: JSON.stringify(payload) });
    state.token = res.item.token;
    localStorage.setItem("lms_token", state.token);
    state.currentUser = res.item.user;
    if (state.currentUser.user_type === "trainer") {
      setSubtab("admin", "trainer-role-input");
    } else {
      setSubtab("learner", "learner-course");
    }
    verifyCodeResult.innerHTML = "";
    await bootWorkspace();
  } catch (error) {
    verifyCodeResult.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
});

logoutBtn.addEventListener("click", () => {
  stopAllInlineVideos();
  closeLessonPlayer();
  state.token = "";
  state.currentUser = null;
  localStorage.removeItem("lms_token");
  showAuth();
});

roleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(roleForm);
  const payload = {
    segment: formData.get("segment"),
    title: formData.get("title"),
    level: "",
    legacy_mappings: [],
    work_summary: formData.get("work_summary"),
    responsibilities: parseLines(formData.get("responsibilities")),
    skills: parseLines(formData.get("skills")),
    kpis: parseKpis(formData.get("kpis")),
  };
  try {
    const res = await fetchJson("/api/roles/generate", { method: "POST", body: JSON.stringify(payload) });
    state.selectedRoleId = res.item.id;
    setSubtab("admin", "trainer-review");
    await refreshTrainerData();
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
    await refreshTrainerData();
  } catch (error) {
    alert(error.message);
  }
});

publishRoleBtn.addEventListener("click", async () => {
  if (!state.selectedRoleId) return;
  try {
    await fetchJson(`/api/roles/${state.selectedRoleId}/publish`, { method: "POST", body: JSON.stringify({}) });
    state.trainerCourseView = { mode: "overview", lessonId: null };
    setSubtab("admin", "trainer-roles");
    await refreshTrainerData();
  } catch (error) {
    alert(error.message);
  }
});

backToRolesBtn.addEventListener("click", () => {
  state.trainerCourseView = { mode: "overview", lessonId: null };
  setSubtab("admin", "trainer-roles");
});

reviewBackToRolesBtn.addEventListener("click", () => {
  setSubtab("admin", "trainer-roles");
});

learnerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(learnerForm).entries());
  delete payload.org_unit;
  try {
    const res = await fetchJson("/api/users", { method: "POST", body: JSON.stringify(payload) });
    adminSummary.insertAdjacentHTML(
      "afterbegin",
      `<div class="card"><strong>${escapeHtml(res.item.user.name)}</strong><div class="meta">Created learner user with phone ${escapeHtml(res.item.user.phone_number)}.</div></div>`
    );
    await refreshTrainerData();
  } catch (error) {
    alert(error.message);
  }
});

closeLessonPlayerBtn.addEventListener("click", closeLessonPlayer);
learnerReviewBackBtn.addEventListener("click", () => {
  setSubtab("learner", "learner-course");
});
lessonPlayerModal.addEventListener("click", (event) => {
  if (event.target.dataset.closeModal === "true") {
    closeLessonPlayer();
  }
});

async function loadConfig() {
  await fetchJson("/api/config");
}

async function bootWorkspace() {
  const me = await fetchJson("/api/auth/me");
  state.currentUser = me.item;
  showWorkspace();
  setVisibilityForUser();
  if (state.currentUser.user_type === "trainer") {
    await refreshTrainerData();
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
