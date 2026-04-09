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
  kpiStudio: {
    items: [],
    activeItemId: null,
    activeVersionId: null,
    roleName: "",
    isGenerating: false,
    lastError: "",
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
const reviewNoteInput = document.getElementById("review-note");
const applyReviewBtn = document.getElementById("apply-review-btn");
const publishRoleBtn = document.getElementById("publish-role-btn");
const reviewBackToRolesBtn = document.getElementById("review-back-to-roles-btn");
const trainerCourseTitle = document.getElementById("trainer-course-title");
const roleSelect = document.getElementById("role-select");
const trainerCoursePreview = document.getElementById("trainer-course-preview");
const trainerRoleLibrary = document.getElementById("trainer-role-library");
const backToRolesBtn = document.getElementById("back-to-roles-btn");
const kpiStudioSummary = document.getElementById("kpi-studio-summary");
const kpiStudioList = document.getElementById("kpi-studio-list");
const kpiStudioDetail = document.getElementById("kpi-studio-detail");
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
const hotspots = document.getElementById("hotspots");
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

function currentStudioItem() {
  return state.kpiStudio.items.find((item) => item.id === state.kpiStudio.activeItemId) || state.kpiStudio.items[0] || null;
}

function currentStudioVersion(item) {
  if (!item) {
    return null;
  }
  return item.video_versions.find((version) => version.id === state.kpiStudio.activeVersionId)
    || item.video_versions[item.video_versions.length - 1]
    || null;
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
  if (group === "admin" && panelId === "trainer-review") {
    renderKpiStudio();
  }
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
    ? publishedRoles.map((role) => `<option value="${role.id}">${escapeHtml(role.title)} · ${escapeHtml(role.level)}</option>`).join("")
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
      <h3 class="section-title">Review History</h3>
      <div class="stack">
        ${role.review_notes?.length ? role.review_notes.map((item, index) => `
          <div class="spotlight">
            <strong>Review ${index + 1}</strong>
            <div class="meta">${escapeHtml(item.text)}</div>
          </div>
        `).join("") : `<div class="meta">No review notes added yet.</div>`}
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
  `;
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
        <span class="chip">${escapeHtml(role.level)}</span>
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
      <div class="meta">${escapeHtml(role.level)} · ${escapeHtml(role.summary || role.work_summary || "")}</div>
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

function renderKpiStudio() {
  if (!kpiStudioSummary || !kpiStudioList || !kpiStudioDetail) {
    return;
  }

  const items = state.kpiStudio.items || [];
  const activeItem = currentStudioItem();
  if (activeItem && state.kpiStudio.activeItemId !== activeItem.id) {
    state.kpiStudio.activeItemId = activeItem.id;
  }
  const activeVersion = currentStudioVersion(activeItem);
  if (activeVersion && state.kpiStudio.activeVersionId !== activeVersion.id) {
    state.kpiStudio.activeVersionId = activeVersion.id;
  }

  const approvedCount = items.filter((item) => item.published).length;
  const generatedCount = items.filter((item) => (item.video_versions || []).length > 0).length;
  kpiStudioSummary.innerHTML = `
    <div class="card">
      <div class="inline">
        <strong>${escapeHtml(state.kpiStudio.roleName || activeItem?.role_name || "Role pending")}</strong>
        <span class="chip soft">${items.length} KPI tracks</span>
        <span class="chip">${generatedCount} videos generated</span>
        <span class="chip ${approvedCount ? "soft" : "warn"}">${approvedCount} approved</span>
      </div>
      <div class="meta">Create one training video per KPI, refine a selected draft with feedback, then approve the final version to unlock the quiz.</div>
      <div class="actions">
        <button class="primary studio-generate-all-btn" ${state.kpiStudio.isGenerating || !items.length ? "disabled" : ""}>Generate Missing Videos</button>
        ${state.kpiStudio.isGenerating ? `<span class="chip warn">Generating in sequence...</span>` : ""}
      </div>
      ${state.kpiStudio.lastError ? `<div class="empty">${escapeHtml(state.kpiStudio.lastError)}</div>` : ""}
    </div>
  `;

  if (!items.length) {
    kpiStudioList.innerHTML = `<div class="empty">Submit the role form to create KPI video drafts.</div>`;
    kpiStudioDetail.innerHTML = `<div class="empty">Select a KPI once the studio session is ready.</div>`;
    return;
  }

  kpiStudioList.innerHTML = `
    <div class="card">
      <div class="inline">
        <strong>KPI Queue</strong>
        <span class="chip">${items.length} items</span>
      </div>
      <div class="meta">Pick a KPI to review the current version, request changes, or approve the final video.</div>
    </div>
    ${items.map((item) => {
      const latestVersion = item.video_versions[item.video_versions.length - 1];
      const status = item.published ? "approved" : latestVersion ? latestVersion.status : item.studio_status;
      return `
      <div class="card role-card-clickable studio-item-card ${item.id === state.kpiStudio.activeItemId ? "is-active" : ""}" data-studio-item="${item.id}">
        <div class="inline">
          <strong>${escapeHtml(item.kpi_name)}</strong>
          <span class="chip ${item.published ? "soft" : statusTone(status)}">${escapeHtml(titleCaseLabel(status))}</span>
        </div>
        <div class="meta">${escapeHtml(item.category)} · ${escapeHtml(item.training_objective)}</div>
        <div class="meta">${item.video_versions.length} version(s) ${latestVersion?.generation_job?.error ? `· ${escapeHtml(latestVersion.generation_job.error)}` : ""}</div>
        <div class="actions">
          <button class="secondary studio-item-open-btn" data-item="${item.id}">Open</button>
          <button class="secondary studio-item-generate-btn" data-item="${item.id}" ${state.kpiStudio.isGenerating ? "disabled" : ""}>${item.video_versions.length ? "Regenerate" : "Generate"}</button>
        </div>
      </div>
    `;
    }).join("")}
  `;

  if (!activeItem) {
    kpiStudioDetail.innerHTML = `<div class="empty">Select a KPI to review its training video.</div>`;
    return;
  }

  const versionCards = (activeItem.video_versions || []).map((version) => `
    <button class="secondary studio-version-btn ${version.id === state.kpiStudio.activeVersionId ? "studio-version-active" : ""}" data-version="${version.id}">
      V${escapeHtml(version.version_number)} · ${escapeHtml(titleCaseLabel(version.status))}
    </button>
  `).join("");
  const quizMarkup = activeItem.quiz ? `
    <div class="card">
      <div class="inline">
        <strong>Approved Quiz</strong>
        <span class="chip soft">${activeItem.quiz.questions.length} questions</span>
      </div>
      <div class="stack">
        ${activeItem.quiz.questions.map((question, index) => `
          <div class="question">
            <strong>Q${index + 1}. ${escapeHtml(question.prompt)}</strong>
            <div class="question-options">
              ${question.options.map((option, optionIndex) => `
                <div class="question-option ${optionIndex === question.correct_option_index ? "selected" : ""}">
                  <span>${escapeHtml(option)}</span>
                </div>
              `).join("")}
            </div>
            <div class="meta">${escapeHtml(question.explanation)}</div>
          </div>
        `).join("")}
      </div>
    </div>
  ` : `<div class="card"><strong>Quiz pending</strong><div class="meta">Approve a video version for this KPI to generate the quiz.</div></div>`;

  kpiStudioDetail.innerHTML = `
    <div class="card">
      <div class="inline">
        <strong>Selected KPI</strong>
        <span class="chip">${escapeHtml(activeItem.kpi_name)}</span>
        <span class="chip">${escapeHtml(activeItem.category)}</span>
        ${activeItem.published ? `<span class="chip soft">Approved</span>` : ""}
      </div>
      <div class="meta">${escapeHtml(activeItem.training_objective)}</div>
      <div class="meta">Role: ${escapeHtml(activeItem.role_name || state.kpiStudio.roleName || "Pending")}</div>
      ${versionCards ? `<div class="actions">${versionCards}</div>` : ""}
    </div>
    ${activeVersion ? `
      <div class="card">
        <div class="inline">
          <strong>Video Review</strong>
          <span class="chip">Version ${escapeHtml(activeVersion.version_number)}</span>
          <span class="chip ${statusTone(activeVersion.status)}">${escapeHtml(titleCaseLabel(activeVersion.status))}</span>
          <span class="chip">${escapeHtml(activeVersion.generation_job.provider)}</span>
        </div>
        <div class="meta">${escapeHtml(activeVersion.operator_notes || "Initial video draft for this KPI.")}</div>
        ${activeVersion.video_url ? `<video class="studio-video-player" src="${escapeHtml(activeVersion.video_url)}" controls playsinline></video>` : `<div class="empty">Video file is not ready yet.</div>`}
        <div class="stack">
          ${(activeVersion.scene_plan || []).map((scene) => `
            <div class="spotlight">
              <div class="inline">
                <strong>Scene ${escapeHtml(scene.scene_number)}. ${escapeHtml(scene.title)}</strong>
                <span class="chip">${escapeHtml(scene.duration_seconds)}s</span>
              </div>
              <div class="meta">${escapeHtml(scene.narration)}</div>
            </div>
          `).join("")}
        </div>
        <div class="actions">
          <button class="primary studio-approve-btn" ${activeItem.published ? "disabled" : ""}>Approve Video</button>
          <button class="secondary studio-reopen-btn" ${activeItem.published ? "" : "disabled"}>Reopen KPI</button>
        </div>
      </div>
      <form class="form studio-feedback-form">
        <label>Feedback For Changes
          <textarea name="revision_prompt" rows="4" placeholder="Example: add stronger floor examples, simplify the closing coaching cue."></textarea>
        </label>
        <div class="actions">
          <button type="submit" class="primary" ${state.kpiStudio.isGenerating ? "disabled" : ""}>Create Revised Video</button>
        </div>
      </form>
    ` : `
      <div class="empty">No video generated yet for this KPI. Generate the first version to start review.</div>
    `}
    ${quizMarkup}
  `;

  document.querySelector(".studio-generate-all-btn")?.addEventListener("click", () => {
    generateMissingStudioVideos().catch((error) => alert(error.message));
  });
  document.querySelectorAll(".studio-item-open-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.kpiStudio.activeItemId = button.dataset.item;
      state.kpiStudio.activeVersionId = null;
      renderKpiStudio();
    });
  });
  document.querySelectorAll(".studio-item-generate-btn").forEach((button) => {
    button.addEventListener("click", () => {
      generateStudioVideo(button.dataset.item).catch((error) => alert(error.message));
    });
  });
  document.querySelectorAll(".studio-item-card").forEach((card) => {
    card.addEventListener("click", () => {
      state.kpiStudio.activeItemId = card.dataset.studioItem;
      state.kpiStudio.activeVersionId = null;
      renderKpiStudio();
    });
  });
  document.querySelectorAll(".studio-version-btn").forEach((button) => {
    button.addEventListener("click", () => {
      state.kpiStudio.activeVersionId = button.dataset.version;
      renderKpiStudio();
    });
  });
  document.querySelector(".studio-approve-btn")?.addEventListener("click", () => {
    approveStudioVideo().catch((error) => alert(error.message));
  });
  document.querySelector(".studio-reopen-btn")?.addEventListener("click", () => {
    reopenStudioItem().catch((error) => alert(error.message));
  });
  document.querySelector(".studio-feedback-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const revisionPrompt = String(formData.get("revision_prompt") || "").trim();
    generateStudioVideo(activeItem.id, revisionPrompt).catch((error) => alert(error.message));
  });
}

async function refreshKpiStudio() {
  const res = await fetchJson("/studio/kpis");
  state.kpiStudio.items = res.items;
  if (!state.kpiStudio.activeItemId || !state.kpiStudio.items.some((item) => item.id === state.kpiStudio.activeItemId)) {
    state.kpiStudio.activeItemId = state.kpiStudio.items[0]?.id || null;
  }
  const activeItem = currentStudioItem();
  if (activeItem) {
    state.kpiStudio.roleName = activeItem.role_name || state.kpiStudio.roleName;
    const activeVersion = currentStudioVersion(activeItem);
    state.kpiStudio.activeVersionId = activeVersion?.id || null;
  }
  renderKpiStudio();
}

async function generateStudioVideo(itemId, revisionPrompt = "") {
  const item = state.kpiStudio.items.find((entry) => entry.id === itemId);
  const roleName = state.kpiStudio.roleName || item?.role_name || currentSelectedRole()?.title || "";
  state.kpiStudio.isGenerating = true;
  state.kpiStudio.lastError = "";
  renderKpiStudio();
  try {
    const res = await fetchJson(`/studio/kpis/${itemId}/versions`, {
      method: "POST",
      body: JSON.stringify({ role_name: roleName, revision_prompt: revisionPrompt }),
    });
    state.kpiStudio.activeItemId = itemId;
    state.kpiStudio.activeVersionId = res.item.id;
    await refreshKpiStudio();
  } catch (error) {
    state.kpiStudio.lastError = error.message;
    renderKpiStudio();
    throw error;
  } finally {
    state.kpiStudio.isGenerating = false;
    renderKpiStudio();
  }
}

async function generateMissingStudioVideos() {
  if (state.kpiStudio.isGenerating) {
    return;
  }
  state.kpiStudio.isGenerating = true;
  state.kpiStudio.lastError = "";
  renderKpiStudio();
  try {
    for (const item of state.kpiStudio.items.filter((entry) => !(entry.video_versions || []).length)) {
      const res = await fetchJson(`/studio/kpis/${item.id}/versions`, {
        method: "POST",
        body: JSON.stringify({ role_name: state.kpiStudio.roleName || item.role_name }),
      });
      state.kpiStudio.activeItemId = item.id;
      state.kpiStudio.activeVersionId = res.item.id;
      await refreshKpiStudio();
    }
  } catch (error) {
    state.kpiStudio.lastError = error.message;
    renderKpiStudio();
    throw error;
  } finally {
    state.kpiStudio.isGenerating = false;
    renderKpiStudio();
  }
}

async function approveStudioVideo() {
  const item = currentStudioItem();
  const version = currentStudioVersion(item);
  if (!item || !version) {
    return;
  }
  await fetchJson(`/studio/kpis/${item.id}/versions/${version.id}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  await refreshKpiStudio();
}

async function reopenStudioItem() {
  const item = currentStudioItem();
  if (!item) {
    return;
  }
  await fetchJson(`/studio/kpis/${item.id}/reopen`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  await refreshKpiStudio();
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
  const topRoleByCompletion = [...roleItems].sort((a, b) => (b.completion_percentage || 0) - (a.completion_percentage || 0))[0];
  const topRoleByAssessment = [...roleItems]
    .filter((item) => item.latest_attempt_average !== null && item.latest_attempt_average !== undefined)
    .sort((a, b) => (b.latest_attempt_average || 0) - (a.latest_attempt_average || 0))[0];
  const weakestSkill = (data.weak_skills || [])[0];
  const weakestKpi = (data.weak_kpis || [])[0];

  trainerSummary.innerHTML = Object.entries(data.summary).map(([key, value], index) => `
    <div class="summary-card ${index < 2 ? "emphasis" : ""}">
      <p class="eyebrow">${escapeHtml(titleCaseLabel(key))}</p>
      <strong class="summary-value">${escapeHtml(value)}</strong>
    </div>
  `).join("");

  trainerOverviewDetail.innerHTML = `
    <div class="split-two">
      <div class="mini-stat">
        <span class="meta">Published roles</span>
        <strong>${escapeHtml(summary.roles_published ?? 0)}</strong>
      </div>
      <div class="mini-stat">
        <span class="meta">Learners in platform</span>
        <strong>${escapeHtml(summary.learners ?? 0)}</strong>
      </div>
      <div class="mini-stat">
        <span class="meta">Completion health</span>
        <strong>${escapeHtml(summary.course_completion_percentage ?? 0)}%</strong>
      </div>
      <div class="mini-stat">
        <span class="meta">Assessment average</span>
        <strong>${escapeHtml(summary.assessment_average ?? "--")}</strong>
      </div>
    </div>
    <div class="card">
      <h3 class="section-title">Operational status</h3>
      <div class="meta">Open remediation assignments: ${escapeHtml(summary.open_remediation_assignments ?? 0)}</div>
      <div class="meta">Current weak KPI observations: ${escapeHtml(summary.weak_kpi_observations ?? 0)}</div>
    </div>
  `;

  trainerInsights.innerHTML = `
    <div class="spotlight">
      <strong>Best completion role</strong>
      <div class="meta">${topRoleByCompletion ? `${escapeHtml(topRoleByCompletion.role_title)} · ${escapeHtml(topRoleByCompletion.completion_percentage)}% complete` : "No published role completion data yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Best assessment role</strong>
      <div class="meta">${topRoleByAssessment ? `${escapeHtml(topRoleByAssessment.role_title)} · ${escapeHtml(topRoleByAssessment.latest_attempt_average)} average score` : "No assessment attempts recorded yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Weakest repeated skill</strong>
      <div class="meta">${weakestSkill ? `${escapeHtml(weakestSkill.label)} · ${escapeHtml(weakestSkill.count)} repeated weak hits` : "No weak skill pattern recorded yet."}</div>
    </div>
    <div class="spotlight">
      <strong>Most exposed KPI</strong>
      <div class="meta">${weakestKpi ? `${escapeHtml(weakestKpi.label)} · ${escapeHtml(weakestKpi.count)} weak signals` : "No weak KPI pattern recorded yet."}</div>
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
          <strong>${(item.completion_percentage || 0) >= 80 ? "On Track" : "Needs Focus"}</strong>
        </div>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${Math.max(0, Math.min(100, item.completion_percentage || 0))}%"></div></div>
    </div>
  `).join("") || `<div class="empty">No trainer metrics yet.</div>`;
  hotspots.innerHTML = `
    <div class="split-two">
      <div class="card">
        <h3 class="section-title">Weak Skills</h3>
        ${(data.weak_skills || []).length ? data.weak_skills.map((item, index) => `
          <div class="metric-row">
            <div>
              <strong>${index + 1}. ${escapeHtml(item.label)}</strong>
              <div class="meta">${escapeHtml(item.count)} repeated weak outcomes</div>
            </div>
            <span class="chip warn">${escapeHtml(item.count)}</span>
          </div>
        `).join("") : `<div class="meta">No weak skills recorded.</div>`}
      </div>
      <div class="card">
        <h3 class="section-title">Weak KPIs</h3>
        ${(data.weak_kpis || []).length ? data.weak_kpis.map((item, index) => `
          <div class="metric-row">
            <div>
              <strong>${index + 1}. ${escapeHtml(item.label)}</strong>
              <div class="meta">${escapeHtml(item.count)} weak KPI signals</div>
            </div>
            <span class="chip warn">${escapeHtml(item.count)}</span>
          </div>
        `).join("") : `<div class="meta">No weak KPIs recorded.</div>`}
      </div>
    </div>
  `;
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
    level: formData.get("level"),
    legacy_mappings: parseLines(formData.get("legacy_mappings")),
    work_summary: formData.get("work_summary"),
    responsibilities: parseLines(formData.get("responsibilities")),
    skills: parseLines(formData.get("skills")),
    kpis: parseKpis(formData.get("kpis")),
  };
  try {
    const [roleRes, studioRes] = await Promise.all([
      fetchJson("/api/roles/generate", { method: "POST", body: JSON.stringify(payload) }),
      fetchJson("/studio/session", {
        method: "POST",
        body: JSON.stringify({ ...payload, role_name: payload.title }),
      }),
    ]);
    state.selectedRoleId = roleRes.item.id;
    state.kpiStudio.items = studioRes.items;
    state.kpiStudio.roleName = String(payload.title || "");
    state.kpiStudio.activeItemId = studioRes.items[0]?.id || null;
    state.kpiStudio.activeVersionId = null;
    state.kpiStudio.lastError = "";
    setSubtab("admin", "trainer-review");
    await refreshTrainerData();
    renderKpiStudio();
    await generateMissingStudioVideos();
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
    await Promise.all([refreshTrainerData(), refreshKpiStudio()]);
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
