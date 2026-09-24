const apiBase = window.location.protocol === "file:"
  ? "http://localhost:8000"
  : (["localhost", "127.0.0.1"].includes(window.location.hostname) && window.location.port && window.location.port !== "8000")
    ? "http://localhost:8000"
    : window.location.origin;
const tokenKey = "smart_schedule_token";
const $ = (selector) => document.querySelector(selector);
const semesterSelect = $("#semester-select");
const versionSelect = $("#version-select");
const groupSelect = $("#group-select");
const scheduleBody = $("#schedule-body");
const statusElement = $("#status");
const lessonStat = $("#stat-lessons");
const groupStat = $("#stat-groups");
const searchInput = $("#schedule-search");
const daySelect = $("#day-select");
const dayFilter = $(".day-filter");
const lessonModal = $("#lesson-modal");
const lessonModalBody = $("#lesson-modal-body");
const managementPanel = $("#management-panel");
const profilePanel = $("#profile-panel");
const generationPanel = $("#generation-panel");
const versionsPanel = $("#versions-panel");
const scheduleCard = $(".schedule-card");
const scheduleToolbar = $(".schedule-toolbar");
const scheduleStats = $(".stats-grid");
const scheduleStatus = $("#status");
const scheduleLegend = $(".schedule-legend");
const generateButton = $("#generate-button");
const managementTitle = $("#management-title");
const managementDescription = $("#management-description");
const managementSummary = $("#management-summary");
const managementTableHead = $("#management-table-head");
const managementTableBody = $("#management-table-body");
const versionsList = $("#versions-list");
const diagnosticsResult = $("#diagnostics-result");
const entityModal = $("#entity-modal");
const entityForm = $("#entity-form");
const entityModalTitle = $("#entity-modal-title");
const managementAddButton = $("#management-add-button");
const pageTitle = $("#page-title");
const pageDescription = $("#page-description");
const breadcrumbSection = $("#breadcrumb-section");
const breadcrumbPage = $("#breadcrumb-page");
const profileForm = $("#profile-form");
const passwordForm = $("#password-form");
const profileLogoutButton = $("#profile-logout-button");
const profileMenuButton = $("#profile-menu-button");
const topbarProfileButton = $("#topbar-profile-button");
const managementFilters = $("#management-filters");

function applySavedAvatar(fallback = "М") {
  const savedAvatar = localStorage.getItem("smart_schedule_avatar");
  document.querySelectorAll(".avatar, .topbar-avatar").forEach((item) => {
    if (savedAvatar) {
      const image = document.createElement("img");
      image.src = savedAvatar;
      image.alt = "Фото профиля";
      item.replaceChildren(image);
    } else {
      item.textContent = fallback;
    }
  });
}

const dayNames = { 1: "Понедельник", 2: "Вторник", 3: "Среда", 4: "Четверг", 5: "Пятница", 6: "Суббота" };
const screenConfig = {
  schedule: ["Расписание", "Просмотр и управление расписанием учебных групп", "schedule"],
  generation: ["Генерация", "Проверьте данные и запустите построение расписания", "generation"],
  versions: ["Версии расписания", "Публикация и архивирование результатов генерации", "versions"],
  profile: ["Личный профиль", "Настройки администратора и внешний вид системы", "profile"],
  dashboard: ["Обзор", "Ключевые показатели системы", "analytics"],
  periods: ["Учебные периоды", "Семестры и календарные параметры", "periods"],
  curricula: ["Учебные планы", "Планы, подключённые к учебным периодам", "curricula"],
  subjects: ["Предметы", "Дисциплины, доступные для планирования", "subjects"],
  groups: ["Группы и студенты", "Потоки, языки обучения и численность", "groups"],
  teachers: ["Преподаватели", "Преподавательский состав и кафедры", "teachers"],
  qualifications: ["Квалификации", "Какие преподаватели могут вести конкретные предметы", "qualifications"],
  classrooms: ["Аудитории", "Вместимость, тип и оборудование помещений", "classrooms"],
  availability: ["Доступность", "Временные слоты и доступность ресурсов", "periods"],
  constraints: ["Ограничения", "Пользовательские запреты для преподавателей и аудиторий", "constraints"],
  analytics: ["Аналитика", "Сводка по расписаниям и ресурсам", "analytics"],
};
const state = { items: [], overview: null, activeView: "week", zoom: 100, preferredVersionId: null, selectedUnit: "" };
let activeManagementScreen = null;
let activeStudentId = null;
let activeClassroomId = null;
let currentUser = null;

function applyScheduleZoom() {
  const wrapper = scheduleBody.closest(".schedule-wrapper");
  if (!wrapper) return;
  wrapper.dataset.zoom = String(state.zoom);
  const resetButton = $("#zoom-reset-button");
  if (resetButton) resetButton.textContent = `${state.zoom}%`;
  const zoomOutButton = $("#zoom-out-button");
  const zoomInButton = $("#zoom-in-button");
  if (zoomOutButton) zoomOutButton.disabled = state.zoom <= 75;
  if (zoomInButton) zoomInButton.disabled = state.zoom >= 130;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;" }[char]));
}
function token() {
  const value = localStorage.getItem(tokenKey);
  if (!value) { window.location.href = "login.html"; throw new Error("Требуется авторизация"); }
  return value;
}
function headers(extra = {}) { return { ...extra, Authorization: `Bearer ${token()}` }; }
function setStatus(message, error = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle("status-error", error);
}
async function request(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: headers({ "Content-Type": "application/json", ...(options.headers || {}) }) });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) { localStorage.removeItem(tokenKey); window.location.href = "login.html"; }
  if (!response.ok) throw new Error(data.detail || `API: ${response.status}`);
  return data;
}
const api = (path) => request(path);
const formatTime = (value) => value ? value.slice(0, 5) : "";
const lessonType = (value) => ({ lecture: "Лекция", practice: "Практика", lab: "Лабораторная" }[value] || value || "Занятие");
const statusLabel = (value) => ({ draft: "Черновик", generated: "Сгенерировано", published: "Опубликовано", archived: "Архив", failed: "Ошибка" }[value] || value);

function setPanel(panel) {
  [generationPanel, versionsPanel, managementPanel, profilePanel].forEach((item) => item.classList.remove("active"));
  scheduleCard.style.display = panel === "schedule" ? "" : "none";
  [scheduleToolbar, scheduleStats, scheduleStatus, scheduleLegend, generateButton].forEach((item) => {
    if (item) item.style.display = panel === "schedule" ? "" : "none";
  });
  if (panel === "generation") generationPanel.classList.add("active");
  if (panel === "versions") versionsPanel.classList.add("active");
  if (panel === "management") managementPanel.classList.add("active");
  if (panel === "profile") profilePanel.classList.add("active");
}

function renderTable(items) {
  const selected = groupSelect.value;
  const groups = new Map();
  for (const item of items) {
    const names = new Map();
    item.targets.forEach((target) => (target.group_ids || []).forEach((id, index) => {
      const selectedGroup = selected.startsWith("group:") && String(id) === selected.slice(6);
      const stream = state.overview?.lecture_streams.find((candidate) => candidate.group_ids.includes(id));
      const selectedStream = selected.startsWith("stream:") && stream?.id === Number(selected.slice(7));
      if (!selected || selectedGroup || selectedStream) names.set(String(id), target.group_names?.[index] || `Группа ${id}`);
    }));
    if (!names.size && !selected) names.set("none", "Без группы");
    names.forEach((name, id) => {
      if (!groups.has(id)) groups.set(id, { name, items: [] });
      groups.get(id).items.push(item);
    });
  }
  lessonStat.textContent = items.length;
  groupStat.textContent = groups.size || "—";
  scheduleBody.innerHTML = [...groups.values()].sort((a, b) => a.name.localeCompare(b.name)).map((group) => {
    const slots = new Map();
    group.items.forEach((item) => {
      const key = `${item.time_slot.lesson_number}-${item.time_slot.start_time}-${item.time_slot.end_time}`;
      if (!slots.has(key)) slots.set(key, { time: item.time_slot, days: new Map() });
      slots.get(key).days.set(item.time_slot.day_of_week, item);
    });
    const rows = [...slots.values()].sort((a, b) => a.time.lesson_number - b.time.lesson_number);
    return `<tr class="group-divider"><th colspan="7">${escapeHtml(group.name)}</th></tr>${rows.map((row) => `<tr>
      <td class="time-cell"><strong>${row.time.lesson_number}</strong><br>${formatTime(row.time.start_time)}<br>${formatTime(row.time.end_time)}</td>
      ${[1, 2, 3, 4, 5, 6].map((day) => {
        if (state.activeView === "day" && String(day) !== daySelect.value) return "<td></td>";
        const item = row.days.get(day);
        if (!item) return "<td></td>";
        const rooms = item.targets.map((target) => target.classroom?.name).filter(Boolean).join(", ");
        return `<td><div class="lesson-card lesson-${escapeHtml(item.lesson_type)}" data-id="${item.id}" tabindex="0">
          <strong>${escapeHtml(item.subject?.name || "Предмет")}</strong>
          <span class="lesson-type-badge">${lessonType(item.lesson_type)}</span>
          <span>${escapeHtml(item.teacher?.full_name || "Преподаватель не указан")}</span>
          <small>${escapeHtml(rooms ? `ауд. ${rooms}` : "Аудитория не назначена")}</small>
        </div></td>`;
      }).join("")}</tr>`).join("")}`;
  }).join("") || '<tr><td colspan="7">По выбранным параметрам занятий нет.</td></tr>';
  scheduleBody.querySelectorAll(".lesson-card").forEach((card) => {
    const item = items.find((candidate) => String(candidate.id) === card.dataset.id);
    card.addEventListener("click", () => openLesson(item));
    card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openLesson(item); });
  });
}
function openLesson(item) {
  if (!item) return;
  const groups = [...new Set(item.targets.flatMap((target) => target.group_names || []))].join(", ");
  const rooms = item.targets.map((target) => target.classroom?.name).filter(Boolean).join(", ");
  lessonModalBody.innerHTML = `<div class="eyebrow">${lessonType(item.lesson_type)}</div><h2 id="lesson-modal-title">${escapeHtml(item.subject?.name || "Предмет")}</h2>
    <dl class="lesson-details"><div><dt>Преподаватель</dt><dd>${escapeHtml(item.teacher?.full_name || "Не указан")}</dd></div>
    <div><dt>Группы</dt><dd>${escapeHtml(groups || "Не указаны")}</dd></div><div><dt>Аудитории</dt><dd>${escapeHtml(rooms || "Не назначены")}</dd></div>
    <div><dt>Время</dt><dd>${dayNames[item.time_slot.day_of_week]}, пара ${item.time_slot.lesson_number}, ${formatTime(item.time_slot.start_time)}–${formatTime(item.time_slot.end_time)}</dd></div></dl>`;
  lessonModal.hidden = false;
}
function updateGroups(items) {
  const values = new Map();
  (state.overview?.groups || []).forEach((group) => values.set(`group:${group.id}`, group.name));
  const selected = groupSelect.value;
  groupSelect.replaceChildren(new Option("Все группы и потоки", ""));
  const groups = document.createElement("optgroup");
  groups.label = "Группы";
  [...values.entries()].sort((a, b) => a[1].localeCompare(b[1])).forEach(([id, name]) => groups.appendChild(new Option(name, id)));
  groupSelect.appendChild(groups);
  const streams = document.createElement("optgroup");
  streams.label = "Лекционные потоки";
  (state.overview?.lecture_streams || []).forEach((stream) => streams.appendChild(new Option(stream.name, `stream:${stream.id}`)));
  groupSelect.appendChild(streams);
  groupSelect.value = selected;
}
async function loadSchedule() {
  if (!versionSelect.value) return;
  if (!state.overview) state.overview = await api("/catalog/overview");
  const data = await api(`/schedules/${versionSelect.value}`);
  state.items = data.items; updateGroups(data.items); renderTable(filteredItems()); setStatus(`Загружено занятий: ${data.count}`);
}
function filteredItems() {
  const query = searchInput.value.trim().toLocaleLowerCase();
  return state.items.filter((item) => {
    const matchesDay = state.activeView !== "day" || String(item.time_slot.day_of_week) === String(daySelect.value);
    const text = [item.subject?.name, item.teacher?.full_name, ...item.targets.flatMap((target) => target.group_names || [])].filter(Boolean).join(" ").toLocaleLowerCase();
    return matchesDay && (!query || text.includes(query));
  });
}
async function loadVersions() {
  const period = semesterSelect.value;
  versionSelect.replaceChildren(); versionSelect.disabled = true;
  if (!period) return;
  const data = await api(`/schedules/versions?academic_period_id=${period}`);
  data.versions.forEach((version) => versionSelect.add(new Option(`${version.name} · ${statusLabel(version.status)} · ${version.items_count} занятий`, version.id)));
  if (!data.versions.length) versionSelect.add(new Option("Нет доступных версий", ""));
  versionSelect.disabled = !data.versions.length;
  if (data.versions.length) { versionSelect.value = String(data.versions.find((v) => String(v.id) === String(state.preferredVersionId))?.id || data.versions[0].id); state.preferredVersionId = null; await loadSchedule(); }
}
async function loadPeriods() {
  state.overview = await api("/catalog/overview");
  const data = await api("/schedules/versions");
  const periods = new Map(data.versions.map((version) => [version.academic_period_id, version.academic_period_name]));
  semesterSelect.replaceChildren();
  periods.forEach((name, id) => semesterSelect.add(new Option(name || `Период ${id}`, id)));
  if (periods.size) await loadVersions(); else setStatus("Нет доступных версий расписания.");
}
async function loadDiagnostics() {
  const period = semesterSelect.value;
  if (!period) return;
  const data = await api(`/schedules/diagnostics/${period}`);
  diagnosticsResult.innerHTML = data.valid ? [["Занятий", data.lessons_count], ["Слотов", data.time_slots_count], ["Аудиторий", data.classrooms_count], ["Состояние", "Готово"]].map(([label, value]) => `<div class="diagnostic-card ok"><span>${label}</span><strong>${value}</strong></div>`).join("") : `<div class="diagnostic-card error"><span>Результат проверки</span><strong>Есть проблемы</strong><p>${escapeHtml(data.error || "Исправьте входные данные.")}</p></div>`;
}
async function loadVersionsPanel() {
  const period = semesterSelect.value;
  if (!period) return;
  const data = await api(`/schedules/versions?academic_period_id=${period}`);
  versionsList.innerHTML = data.versions.length ? data.versions.map((version) => `<div class="version-row"><div class="version-info"><strong>${escapeHtml(version.name)}</strong><span>${version.items_count} занятий · ${statusLabel(version.status)}</span></div><div class="version-actions"><span class="version-status ${version.status}">${statusLabel(version.status)}</span>${version.status !== "published" ? `<button class="small-button" data-action="publish" data-id="${version.id}">Опубликовать</button>` : ""}${version.status !== "archived" && version.status !== "published" ? `<button class="small-button" data-action="archive" data-id="${version.id}">Архивировать</button>` : ""}</div></div>`).join("") : '<div class="empty-panel">Для периода пока нет версий.</div>';
}
function table(data, key) {
  const configs = {
    periods: [["name", "Учебный период"], ["academic_year", "Учебный год"], ["semester", "Семестр"], ["weeks", "Недель"], ["start_date", "Начало"], ["end_date", "Окончание"]],
    curricula: [["id", "№"], ["curriculum_id", "План"], ["subject", "Предмет"], ["hours", "Всего часов"], ["lecture_hours", "Лекции"], ["practice_hours", "Практика"], ["lab_hours", "Лабораторные"]],
    groups: [["name", "Группа"], ["specialty", "Специальность"], ["course", "Курс"], ["language", "Язык"], ["student_count", "Студенты"]],
    subjects: [["code", "Код"], ["name", "Название"]],
    teachers: [["full_name", "ФИО"], ["position", "Должность"], ["department", "Кафедра"], ["email", "Email"]],
    qualifications: [["teacher", "Преподаватель"], ["subject", "Предмет"], ["lecture_hours", "Лекции"], ["practice_hours", "Практика"], ["lab_hours", "Лабораторные"]],
    classrooms: [["name", "Аудитория"], ["capacity", "Вместимость"], ["room_type", "Тип"], ["equipment", "Оборудование"]],
    constraints: [["constraint_type", "Тип"], ["title", "Ограничение"], ["description", "Описание"], ["start_time", "С"], ["end_time", "До"], ["is_active", "Активно"]],
  };
  const rows = data[key] || [];
  const columns = configs[key] || [];
  managementTableHead.innerHTML = `<tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}</tr>`;
  const displayValue = (row, field) => {
    if (field === "room_type") return roomTypeLabel(row[field]);
    if (field === "equipment") return equipmentLabel(row[field]);
    return row[field] ?? "—";
  };
  managementTableBody.innerHTML = rows.length ? rows.map((row) => `<tr>${columns.map(([field]) => `<td>${escapeHtml(displayValue(row, field))}</td>`).join("")}${key === "classrooms" ? `<td class="management-actions"><button class="small-button" data-classroom-action="edit" data-id="${row.id}">Изменить</button><button class="small-button" data-classroom-action="delete" data-id="${row.id}">Удалить</button></td>` : ""}</tr>`).join("") : `<tr><td colspan="${Math.max(columns.length + (key === "classrooms" ? 1 : 0), 1)}">Нет данных.</td></tr>`;
  if (key === "classrooms") managementTableHead.innerHTML = `<tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}<th>Действия</th></tr>`;
  managementSummary.innerHTML = `<div class="diagnostic-card ok"><span>Записей</span><strong>${rows.length}</strong></div>`;
}
const roomTypes = { ordinary: "Обычная аудитория", classroom: "Учебная аудитория", lecture: "Лекционная аудитория", lecture_hall: "Лекционная аудитория", computer_lab: "Компьютерная аудитория", laboratory: "Лаборатория", lab: "Лаборатория", seminar: "Семинарская аудитория", gym: "Спортивный зал", auditorium: "Актовый зал" };
const equipmentTypes = { computers: "Компьютеры", projector: "Проектор", interactive_board: "Интерактивная доска", laboratory: "Лабораторное оборудование", none: "Без оборудования" };
function roomTypeLabel(value) { return roomTypes[value] || value || "—"; }
function equipmentLabel(value) {
  if (!value) return "—";
  const [type, quantity] = String(value).split(":");
  return `${equipmentTypes[type] || type}${quantity ? ` · ${quantity} шт.` : ""}`;
}
async function loadStudentsPanel() {
  const groupId = managementFilters.querySelector("[name='student-group']")?.value || "";
  const streamId = managementFilters.querySelector("[name='student-stream']")?.value || "";
  const query = new URLSearchParams();
  if (groupId) query.set("group_id", groupId);
  if (streamId) query.set("lecture_stream_id", streamId);
  const data = await api(`/groups/students?${query}`);
  managementTableHead.innerHTML = "<tr><th>ФИО</th><th>Группа</th><th>Потоки</th><th>Действия</th></tr>";
  managementTableBody.innerHTML = data.students.length ? data.students.map((student) => `<tr>
    <td>${escapeHtml(student.full_name)}</td><td>${escapeHtml(student.group_name || "—")}</td>
    <td>${escapeHtml(student.streams.map((stream) => stream.name).join(", ") || "Не назначены")}</td>
    <td class="management-actions"><button class="small-button" data-student-action="edit" data-id="${student.id}">Изменить</button><button class="small-button" data-student-action="delete" data-id="${student.id}">Удалить</button></td>
  </tr>`).join("") : '<tr><td colspan="4">Нет студентов по выбранным фильтрам.</td></tr>';
  managementSummary.innerHTML = `<div class="diagnostic-card ok"><span>Студентов</span><strong>${data.count}</strong></div>`;
}
function renderStudentFilters() {
  managementFilters.hidden = false;
  managementFilters.innerHTML = `<label>Группа<select name="student-group"><option value="">Все группы</option>${state.overview.groups.map((group) => `<option value="${group.id}">${escapeHtml(group.name)}</option>`).join("")}</select></label>
    <label>Поток<select name="student-stream"><option value="">Все потоки</option>${state.overview.lecture_streams.map((stream) => `<option value="${stream.id}">${escapeHtml(stream.name)}</option>`).join("")}</select></label>`;
  managementFilters.querySelectorAll("select").forEach((select) => select.addEventListener("change", () => loadStudentsPanel().catch((error) => setStatus(error.message, true))));
}
async function loadManagementScreen(screen) {
  const config = screenConfig[screen]; if (!config) return;
  managementTitle.textContent = config[0]; managementDescription.textContent = config[1];
  activeManagementScreen = screen;
  managementFilters.hidden = true;
  managementAddButton.hidden = !["teachers", "classrooms", "qualifications", "constraints", "groups"].includes(screen);
  managementAddButton.textContent = screen === "qualifications" ? "Назначить предмет" : screen === "groups" ? "Добавить студента" : "Добавить";
  const data = state.overview || await api("/catalog/overview"); state.overview = data;
  if (screen === "analytics" || screen === "dashboard") {
    managementSummary.innerHTML = Object.entries({ Периоды: data.periods.length, Группы: data.groups.length, Предметы: data.subjects.length, Преподаватели: data.teachers.length, Аудитории: data.classrooms.length }).map(([label, value]) => `<div class="diagnostic-card ok"><span>${label}</span><strong>${value}</strong></div>`).join("");
    managementTableHead.innerHTML = "<tr><th>Проверка</th><th>Результат</th></tr>";
    managementTableBody.innerHTML = `<tr><td>Справочники доступны</td><td>Готово</td></tr><tr><td>Аудитории с вместимостью</td><td>${data.classrooms.filter((item) => item.capacity > 0).length} из ${data.classrooms.length}</td></tr>`;
  } else if (screen === "groups") {
    renderStudentFilters();
    await loadStudentsPanel();
  } else table(data, config[2]);
}
function openEntityModal(screen) {
  const definitions = {
    teachers: {
      title: "Добавить преподавателя", endpoint: "/teachers", fields: [
        ["full_name", "ФИО", "text", true], ["position", "Должность", "text", true],
        ["department", "Кафедра", "text", true], ["email", "Email", "email", false], ["phone", "Телефон", "text", false],
      ],
    },
    classrooms: {
      title: activeClassroomId ? "Изменить аудиторию" : "Добавить аудиторию", endpoint: "/classrooms", fields: [
        ["name", "Название аудитории", "text", true], ["capacity", "Вместимость", "number", true],
        ["room_type", "Тип аудитории", "select-room-type", true], ["equipment_type", "Оборудование", "select-equipment", false],
        ["equipment_quantity", "Количество оборудования", "number", false],
      ],
    },
    groups: {
      title: activeStudentId ? "Изменить студента" : "Добавить студента", endpoint: "/groups/students", fields: [
        ["full_name", "ФИО студента", "text", true], ["group_id", "Группа", "select-group", true],
        ["lecture_stream_ids", "Потоки", "select-streams", false],
      ],
    },
    qualifications: {
      title: "Назначить преподавателю предмет", endpoint: "/teacher-loads/", fields: [
        ["teacher_id", "Преподаватель", "select-teacher", true], ["curriculum_subject_id", "Предмет учебного плана", "select-subject", true],
        ["lecture_hours", "Часы лекций", "number", false], ["practice_hours", "Часы практики", "number", false], ["lab_hours", "Часы лабораторных", "number", false],
      ],
    },
    constraints: {
      title: "Добавить ограничение", endpoint: "/constraints", fields: [
        ["constraint_type", "Тип ограничения", "select-constraint", true], ["title", "Название", "text", true],
        ["description", "Описание", "textarea", true], ["teacher_id", "Преподаватель", "select-teacher", false],
        ["classroom_id", "Аудитория", "select-classroom", false], ["day_of_week", "День недели (1–6)", "number", false],
        ["start_time", "Время с", "time", false], ["end_time", "Время до", "time", false],
      ],
    },
  };
  const definition = definitions[screen];
  if (!definition) return;
  entityModalTitle.textContent = definition.title;
  entityForm.innerHTML = definition.fields.map(([name, label, type, required]) => {
    if (type === "textarea") return `<label><span>${label}</span><textarea name="${name}" rows="3" ${required ? "required" : ""}></textarea></label>`;
    if (type === "select-streams") return `<label><span>${label}</span><select name="${name}" data-options="${type}" multiple size="4"></select></label>`;
    if (type.startsWith("select")) return `<label><span>${label}</span><select name="${name}" data-options="${type}" ${required ? "required" : ""}></select></label>`;
    return `<label><span>${label}</span><input name="${name}" type="${type}" ${required ? "required" : ""} ${type === "number" ? 'min="0"' : ""}></label>`;
  }).join("") + `<div class="entity-form-actions"><button type="button" class="secondary-button" data-close-entity-modal>Отмена</button><button type="submit" class="primary-button">Сохранить</button></div>`;
  const teacherSelect = entityForm.querySelector('[data-options="select-teacher"]');
  if (teacherSelect) state.overview.teachers.forEach((item) => teacherSelect.add(new Option(item.full_name, item.id)));
  const subjectSelect = entityForm.querySelector('[data-options="select-subject"]');
  if (subjectSelect) state.overview.curricula.forEach((item) => subjectSelect.add(new Option(`${item.subject} · ${item.hours} ч.`, item.id)));
  const classroomSelect = entityForm.querySelector('[data-options="select-classroom"]');
  if (classroomSelect) state.overview.classrooms.forEach((item) => classroomSelect.add(new Option(`${item.name} · ${item.capacity} мест`, item.id)));
  const constraintSelect = entityForm.querySelector('[data-options="select-constraint"]');
  if (constraintSelect) [["teacher_unavailable", "Преподаватель недоступен"], ["classroom_unavailable", "Аудитория на ремонте"], ["resource_restriction", "Ограничение ресурса"]].forEach(([value, label]) => constraintSelect.add(new Option(label, value)));
  const roomTypeSelect = entityForm.querySelector('[data-options="select-room-type"]');
  if (roomTypeSelect) Object.entries(roomTypes).forEach(([value, label]) => roomTypeSelect.add(new Option(label, value)));
  const equipmentSelect = entityForm.querySelector('[data-options="select-equipment"]');
  if (equipmentSelect) Object.entries(equipmentTypes).forEach(([value, label]) => equipmentSelect.add(new Option(label, value)));
  const groupSelectForStudent = entityForm.querySelector('[data-options="select-group"]');
  if (groupSelectForStudent) state.overview.groups.forEach((item) => groupSelectForStudent.add(new Option(item.name, item.id)));
  const streamsSelect = entityForm.querySelector('[data-options="select-streams"]');
  if (streamsSelect) state.overview.lecture_streams.forEach((item) => streamsSelect.add(new Option(item.name, item.id)));
  entityModal.hidden = false;
}
async function openStudentModal(studentId = null) {
  activeStudentId = studentId;
  openEntityModal("groups");
  if (studentId) {
    const data = await api("/groups/students");
    const student = data.students.find((item) => item.id === studentId);
    if (!student) return;
    entityForm.elements.full_name.value = student.full_name;
    entityForm.elements.group_id.value = student.group_id;
    [...entityForm.elements.lecture_stream_ids.options].forEach((option) => {
      option.selected = student.streams.some((stream) => stream.id === Number(option.value));
    });
  }
}
async function showScreen(screen) {
  const config = screenConfig[screen];
  document.querySelectorAll(".nav-subitem[data-screen]").forEach((item) => {
    item.classList.toggle("active-subitem", item.dataset.screen === screen);
  });
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
  const activeNavItem = ["schedule", "generation", "versions"].includes(screen)
    ? document.querySelector("[data-nav-group='schedule']")
    : document.querySelector(`.nav-item[data-screen="${screen}"]`);
  activeNavItem?.classList.add("active");
  if (config) {
    pageTitle.textContent = config[0];
    pageDescription.textContent = config[1];
    breadcrumbSection.textContent = ["schedule", "generation", "versions"].includes(screen)
      ? "Расписание"
      : "Справочники";
    breadcrumbPage.textContent = config[0];
  }
  if (screen === "schedule") { setPanel("schedule"); return; }
  if (screen === "generation") { setPanel("generation"); await loadDiagnostics(); return; }
  if (screen === "versions") { setPanel("versions"); await loadVersionsPanel(); return; }
  if (screen === "profile") { setPanel("profile"); await loadProfile(); return; }
  setPanel("management"); await loadManagementScreen(screen);
}
async function loadProfile() {
  currentUser = await api("/auth/me");
  $("#profile-username").value = currentUser.username;
  $("#profile-full-name").value = currentUser.full_name;
  $("#sidebar-profile-name").textContent = currentUser.full_name;
  $("#sidebar-profile-role").textContent = "Администратор";
  const initials = currentUser.full_name.trim().charAt(0).toUpperCase();
  applySavedAvatar(initials);
}
function logout() {
  localStorage.removeItem(tokenKey);
  localStorage.removeItem("smart_schedule_user");
  window.location.href = "login.html";
}
async function generate() {
  if (!semesterSelect.value) return setStatus("Сначала выберите учебный период.", true);
  const button = $("#generate-button"); button.disabled = true; setStatus("Генерация поставлена в очередь...");
  try { const response = await request("/schedules/generate", { method: "POST", body: JSON.stringify({ academic_period_id: Number(semesterSelect.value) }) }); for (;;) { const job = (await api(`/schedules/generation/${response.job.job_id}`)).job; if (job.status === "generated") { state.preferredVersionId = job.version_id; await loadPeriods(); setStatus("Расписание успешно сгенерировано."); break; } if (job.status === "failed") throw new Error(job.error || "Генерация завершилась ошибкой."); setStatus(job.status === "running" ? "Генерация выполняется..." : "Генерация находится в очереди..."); await new Promise((resolve) => setTimeout(resolve, 1200)); } } finally { button.disabled = false; }
}
function exportCsv() {
  const rows = [["День", "Пара", "Время", "Предмет", "Тип", "Преподаватель", "Группы", "Аудитории"]];
  filteredItems().forEach((item) => rows.push([dayNames[item.time_slot.day_of_week], item.time_slot.lesson_number, `${formatTime(item.time_slot.start_time)}-${formatTime(item.time_slot.end_time)}`, item.subject?.name || "", lessonType(item.lesson_type), item.teacher?.full_name || "", [...new Set(item.targets.flatMap((target) => target.group_names || []))].join(", "), item.targets.map((target) => target.classroom?.name).filter(Boolean).join(", ")]));
  const csv = `\uFEFF${rows.map((row) => row.map((value) => `"${String(value).replace(/"/g, "\"\"")}"`).join(";")).join("\r\n")}`;
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" })); link.download = "расписание.csv"; link.click(); URL.revokeObjectURL(link.href);
}

document.querySelectorAll("[data-screen]").forEach((item) => item.addEventListener("click", (event) => {
  if (item.getAttribute("href") && item.getAttribute("href") !== "#") return;
  event.preventDefault();
  showScreen(item.dataset.screen).catch((error) => setStatus(error.message, true));
}));
semesterSelect.addEventListener("change", () => loadVersions().catch((error) => setStatus(error.message, true)));
versionSelect.addEventListener("change", () => loadSchedule().catch((error) => setStatus(error.message, true)));
groupSelect.addEventListener("change", () => loadSchedule().catch((error) => setStatus(error.message, true)));
searchInput.addEventListener("input", () => renderTable(filteredItems()));
daySelect.addEventListener("change", () => renderTable(filteredItems()));
$("#refresh-button").addEventListener("click", () => loadPeriods().catch((error) => setStatus(error.message, true)));
$("#filters-button").addEventListener("click", () => groupSelect.focus());
$("#generate-button").addEventListener("click", () => generate().catch((error) => setStatus(error.message, true)));
$("#diagnostics-button").addEventListener("click", () => loadDiagnostics().catch((error) => setStatus(error.message, true)));
$("#versions-refresh-button").addEventListener("click", () => loadVersionsPanel().catch((error) => setStatus(error.message, true)));
$("#management-refresh-button").addEventListener("click", () => { state.overview = null; const screen = document.querySelector("[data-screen].active-subitem")?.dataset.screen || "dashboard"; loadManagementScreen(screen).catch((error) => setStatus(error.message, true)); });
managementAddButton.addEventListener("click", () => {
  activeClassroomId = null;
  activeStudentId = null;
  openEntityModal(activeManagementScreen);
});
managementPanel.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-student-action]");
  if (!button) return;
  const studentId = Number(button.dataset.id);
  if (button.dataset.studentAction === "edit") {
    openStudentModal(studentId).catch((error) => setStatus(error.message, true));
    return;
  }
  if (!window.confirm("Удалить студента из списка?")) return;
  try {
    await request(`/groups/students/${studentId}`, { method: "DELETE" });
    state.overview = null;
    await loadManagementScreen("groups");
    setStatus("Студент удалён.");
  } catch (error) { setStatus(error.message, true); }
});
managementPanel.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-classroom-action]");
  if (!button) return;
  const classroomId = Number(button.dataset.id);
  if (button.dataset.classroomAction === "edit") {
    activeClassroomId = classroomId;
    openEntityModal("classrooms");
    const classroom = state.overview.classrooms.find((item) => item.id === classroomId);
    if (classroom) {
      entityForm.elements.name.value = classroom.name;
      entityForm.elements.capacity.value = classroom.capacity;
      entityForm.elements.room_type.value = classroom.room_type;
      const [equipmentType, quantity] = String(classroom.equipment || "none:0").split(":");
      entityForm.elements.equipment_type.value = equipmentType || "none";
      entityForm.elements.equipment_quantity.value = quantity || 0;
    }
    return;
  }
  if (!window.confirm("Удалить аудиторию?")) return;
  try {
    await request(`/classrooms/${classroomId}`, { method: "DELETE" });
    state.overview = null;
    await loadManagementScreen("classrooms");
    setStatus("Аудитория удалена.");
  } catch (error) { setStatus(error.message, true); }
});
entityModal.addEventListener("click", (event) => { if (event.target.closest("[data-close-entity-modal]")) entityModal.hidden = true; });
entityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!activeManagementScreen) return;
  if (activeManagementScreen === "groups" && !activeStudentId) activeStudentId = null;
  const data = Object.fromEntries(new FormData(entityForm).entries());
  if (activeManagementScreen === "groups") {
    data.lecture_stream_ids = [...entityForm.querySelector("[name='lecture_stream_ids']").selectedOptions].map((option) => Number(option.value));
    data.group_id = Number(data.group_id);
    const endpoint = activeStudentId ? `/groups/students/${activeStudentId}` : `/groups/${data.group_id}/students`;
    if (!activeStudentId) {
      const response = await request(endpoint, { method: "POST", body: JSON.stringify({ students: [{ full_name: data.full_name }] }) });
      const created = response.students?.[0];
      if (created && data.lecture_stream_ids.length) await request(`/groups/students/${created.id}`, { method: "PATCH", body: JSON.stringify(data) });
    } else {
      await request(endpoint, { method: "PATCH", body: JSON.stringify(data) });
    }
    entityModal.hidden = true; activeStudentId = null; state.overview = null; await loadManagementScreen("groups"); setStatus("Список студентов обновлён."); return;
  }
  ["capacity", "equipment_quantity", "teacher_id", "classroom_id", "day_of_week", "lecture_hours", "practice_hours", "lab_hours", "curriculum_subject_id"].forEach((field) => {
    if (data[field] !== undefined && data[field] !== "") data[field] = Number(data[field]);
    else if (data[field] === "") delete data[field];
  });
  if (activeManagementScreen === "classrooms") {
    data.equipment = data.equipment_type && data.equipment_type !== "none" ? `${data.equipment_type}:${data.equipment_quantity || 1}` : null;
    delete data.equipment_type;
    delete data.equipment_quantity;
  }
  const endpoint = activeManagementScreen === "qualifications" ? "/teacher-loads/" : activeManagementScreen === "teachers" ? "/teachers" : activeManagementScreen === "classrooms" ? (activeClassroomId ? `/classrooms/${activeClassroomId}` : "/classrooms") : "/constraints";
  try {
    await request(endpoint, { method: activeClassroomId ? "PATCH" : "POST", body: JSON.stringify(data) });
    entityModal.hidden = true; activeClassroomId = null; state.overview = null; await loadManagementScreen(activeManagementScreen); setStatus("Запись успешно сохранена.");
  } catch (error) { setStatus(error.message, true); }
});
$("#export-excel-button").addEventListener("click", exportCsv);
$("#export-pdf-button").addEventListener("click", () => window.print());
$("#logout-button")?.addEventListener("click", logout);
const mobileMenuButton = $("#mobile-menu");
const sidebarBackdrop = $("#sidebar-backdrop");
const closeMobileNavigation = () => document.body.classList.remove("sidebar-open");
mobileMenuButton?.addEventListener("click", () => document.body.classList.toggle("sidebar-open"));
sidebarBackdrop?.addEventListener("click", closeMobileNavigation);
document.querySelectorAll(".sidebar .nav-item").forEach((link) => link.addEventListener("click", closeMobileNavigation));
profileMenuButton?.addEventListener("click", () => showScreen("profile").catch((error) => setStatus(error.message, true)));
topbarProfileButton?.addEventListener("click", () => showScreen("profile").catch((error) => setStatus(error.message, true)));
profileLogoutButton?.addEventListener("click", logout);
profileForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(profileForm).entries());
  try {
    const response = await request("/auth/profile", { method: "PUT", body: JSON.stringify(data) });
    localStorage.setItem(tokenKey, response.access_token);
    localStorage.setItem("smart_schedule_user", JSON.stringify(response.user));
    await loadProfile();
    profileForm.reset();
    $("#profile-username").value = response.user.username;
    $("#profile-full-name").value = response.user.full_name;
    setStatus("Личные данные сохранены.");
  } catch (error) { setStatus(error.message, true); }
});
passwordForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(passwordForm).entries());
  if (data.new_password !== data.repeat_password) { setStatus("Новые пароли не совпадают.", true); return; }
  delete data.repeat_password;
  try {
    const response = await request("/auth/profile", { method: "PUT", body: JSON.stringify(data) });
    localStorage.setItem(tokenKey, response.access_token);
    passwordForm.reset();
    setStatus("Пароль успешно изменён.");
  } catch (error) { setStatus(error.message, true); }
});
document.querySelectorAll("[data-theme-choice]").forEach((button) => button.addEventListener("click", () => {
  const choice = button.dataset.themeChoice;
  localStorage.setItem("smart_schedule_theme", choice);
  applyTheme(choice);
}));
$("#versions-list").addEventListener("click", async (event) => { const button = event.target.closest("[data-action]"); if (!button) return; if (button.dataset.action === "archive" && !window.confirm("Архивировать эту версию расписания?")) return; try { await request(`/schedules/${button.dataset.id}/${button.dataset.action}`, { method: "POST" }); await loadVersionsPanel(); setStatus("Операция выполнена."); } catch (error) { setStatus(error.message, true); } });
lessonModal.querySelectorAll("[data-close-modal]").forEach((element) => element.addEventListener("click", () => { lessonModal.hidden = true; }));
document.addEventListener("keydown", (event) => { if (event.key === "Escape") lessonModal.hidden = true; });
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => { state.activeView = button.dataset.view; document.querySelectorAll("[data-view]").forEach((item) => item.classList.toggle("active", item === button)); dayFilter.hidden = state.activeView !== "day"; renderTable(filteredItems()); }));
$("#zoom-out-button")?.addEventListener("click", () => { state.zoom = Math.max(75, state.zoom - 15); applyScheduleZoom(); });
$("#zoom-in-button")?.addEventListener("click", () => { state.zoom = Math.min(130, state.zoom + 15); applyScheduleZoom(); });
$("#zoom-reset-button")?.addEventListener("click", () => { state.zoom = 100; applyScheduleZoom(); });
applyScheduleZoom();
applySavedAvatar();
if (!localStorage.getItem(tokenKey)) window.location.href = "login.html";
loadPeriods().catch((error) => setStatus(`Не удалось подключиться к API: ${error.message}`, true));
function applyTheme(theme) {
  const resolved = theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : theme === "system" ? "light" : theme;
  document.documentElement.dataset.theme = resolved;
  document.querySelectorAll("[data-theme-choice]").forEach((button) => button.classList.toggle("selected", button.dataset.themeChoice === theme));
}
applyTheme(localStorage.getItem("smart_schedule_theme") || "light");
