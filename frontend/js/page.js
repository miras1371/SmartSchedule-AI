const apiBase = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : window.location.origin;
const tokenKey = "smart_schedule_token";
const page = document.body.dataset.page;
const configs = {
  dashboard: ["Обзор", "Ключевые показатели системы", "analytics"],
  generation: ["Генерация", "Проверка данных и запуск построения расписания", "generation"],
  versions: ["Версии расписания", "Публикация и архивирование результатов генерации", "versions"],
  periods: ["Учебные периоды", "Семестры и календарные параметры", "periods"],
  curricula: ["Учебные планы", "Планы, подключённые к учебным периодам", "curricula"],
  subjects: ["Предметы", "Дисциплины, доступные для планирования", "subjects"],
  groups: ["Группы и студенты", "Просмотр и управление составом групп", "groups"],
  teachers: ["Преподаватели", "Преподавательский состав и кафедры", "teachers"],
  qualifications: ["Квалификации", "Предметы и часы преподавателей", "qualifications"],
  classrooms: ["Аудитории", "Вместимость, тип и оборудование помещений", "classrooms"],
  availability: ["Доступность", "Временные слоты и доступность ресурсов", "periods"],
  constraints: ["Ограничения", "Пользовательские ограничения расписания", "constraints"],
  analytics: ["Аналитика", "Сводка по расписаниям и ресурсам", "analytics"],
  profile: ["Личный профиль", "Настройки администратора", "profile"],
};
const nav = [
  ["ОСНОВНОЕ", [["dashboard.html", "⌂", "Dashboard", "dashboard"]]],
  ["РАСПИСАНИЕ", [["home.html", "▦", "Просмотр расписания", "schedule"], ["generation.html", "✦", "Генерация", "generation"], ["versions.html", "◫", "Версии", "versions"]]],
  ["УЧЕБНЫЕ ДАННЫЕ", [["periods.html", "◫", "Семестры", "periods"], ["curricula.html", "▤", "Учебные планы", "curricula"], ["subjects.html", "◈", "Предметы", "subjects"], ["groups.html", "♙", "Группы и студенты", "groups"]]],
  ["ЛЮДИ", [["teachers.html", "♙", "Преподаватели", "teachers"], ["qualifications.html", "✓", "Квалификации", "qualifications"]]],
  ["РЕСУРСЫ", [["classrooms.html", "▣", "Аудитории", "classrooms"], ["availability.html", "◷", "Доступность", "availability"]]],
  ["СИСТЕМА", [["constraints.html", "◌", "Ограничения", "constraints"], ["analytics.html", "▥", "Аналитика", "analytics"]]],
];
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;" }[char])); }
function headers() { return { Authorization: `Bearer ${localStorage.getItem(tokenKey)}`, "Content-Type": "application/json" }; }
async function api(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
  if (response.status === 401) { localStorage.removeItem(tokenKey); location.href = "login.html"; }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `API: ${response.status}`);
  return data;
}
function shell() {
  const links = nav.map(([title, items]) => `<div class="nav-section-title">${title}</div>${items.map(([href, icon, label, key]) => `<a href="${href}" class="nav-item ${key === page ? "active" : ""}"><span class="nav-icon">${icon}</span><span>${label}</span></a>`).join("")}`).join("");
  const addButton = ["groups", "classrooms"].includes(page) ? `<button id="add-record" class="primary-button page-add-button" type="button">Добавить ${page === "groups" ? "группу" : "аудиторию"}</button>` : "";
  document.querySelector(".app").innerHTML = `<aside class="sidebar"><div><div class="logo"><div class="logo-icon">S</div><div class="logo-text"><span>SmartSchedule</span><small>AI</small></div></div><nav class="navigation">${links}</nav></div><div class="sidebar-bottom"><a href="profile.html" class="nav-item ${page === "profile" ? "active" : ""}"><span class="nav-icon">⚙</span><span>Настройки</span></a><button class="profile-mini" id="logout-button" type="button"><div class="avatar">М</div><div class="profile-info"><strong>Администратор</strong><span>Администратор</span></div></button></div></aside><main class="main"><header class="topbar"><div class="breadcrumbs"><span>SmartSchedule</span><span>/</span><span>${configs[page][0]}</span></div><div class="topbar-actions"><button class="icon-button" id="logout-top" type="button">⎋</button><div class="topbar-avatar">М</div></div></header><div class="content"><section class="page-header"><div><div class="eyebrow">УПРАВЛЕНИЕ СИСТЕМОЙ</div><h1>${configs[page][0]}</h1><p>${configs[page][1]}</p></div><div class="panel-actions">${addButton}</div></section><div id="page-content"><div class="empty-panel">Загрузка...</div></div></div></main><div id="record-modal" class="lesson-modal" hidden><div class="lesson-modal-backdrop" data-close-record></div><section class="lesson-modal-content entity-modal-content"><button class="lesson-modal-close" type="button" data-close-record>×</button><div class="eyebrow">УПРАВЛЕНИЕ ДАННЫМИ</div><h2 id="record-modal-title"></h2><form id="record-form" class="entity-form"></form></section></div>`;
  document.querySelectorAll("#logout-button,#logout-top").forEach((button) => button.addEventListener("click", () => { localStorage.removeItem(tokenKey); location.href = "login.html"; }));
}
const labels = { room_type: "Тип", equipment: "Оборудование", student_count: "Студентов", academic_year: "Учебный год", semester: "Семестр", weeks: "Недель", specialty: "Специальность", course: "Курс", language: "Язык", capacity: "Вместимость", position: "Должность", department: "Кафедра", email: "Email", subject: "Предмет", hours: "Часы", lecture_hours: "Лекции", practice_hours: "Практика", lab_hours: "Лабораторные", code: "Код", name: "Название", group: "Группа", streams: "Потоки", full_name: "ФИО", teacher: "Преподаватель", constraint_type: "Тип ограничения", title: "Название", description: "Описание", start_time: "Начало", end_time: "Окончание", is_active: "Статус", academic_period_name: "Учебный период", version_number: "Номер версии", status: "Статус", items_count: "Занятий", day: "День", lesson_number: "Пара" };
const roomTypes = { ordinary: "Обычная аудитория", classroom: "Учебная аудитория", lecture: "Лекционная аудитория", lecture_hall: "Лекционная аудитория", computer_lab: "Компьютерная аудитория", laboratory: "Лаборатория", lab: "Лаборатория", seminar: "Семинарская аудитория", gym: "Спортивный зал", auditorium: "Актовый зал" };
function formatValue(field, value) { if (field === "room_type") return roomTypes[value] || value || "—"; if (field === "equipment" && value) { const [type, count] = String(value).split(":"); return `${type === "computers" ? "Компьютеры" : type}${count ? ` · ${count} шт.` : ""}`; } return value ?? "—"; }
function columnsFor(key, data) {
  const defaults = { periods: ["name", "academic_year", "semester", "weeks", "start_date", "end_date"], curricula: ["curriculum_id", "subject", "hours", "lecture_hours", "practice_hours", "lab_hours"], subjects: ["code", "name"], groups: ["name", "specialty", "course", "language", "student_count"], teachers: ["full_name", "position", "department", "email"], qualifications: ["teacher", "subject", "lecture_hours", "practice_hours", "lab_hours"], classrooms: ["name", "capacity", "room_type", "equipment"], constraints: ["constraint_type", "title", "description", "start_time", "end_time", "is_active"] };
  return defaults[key] || Object.keys(data[0] || {}).filter((field) => !["id", "group_id", "teacher_id", "classroom_id"].includes(field));
}
function renderTable(rows, key) {
  const root = document.querySelector("#page-content");
  const columns = columnsFor(key, rows);
  const actions = ["groups", "classrooms"].includes(key);
  root.innerHTML = `<div class="management-tools"><input id="page-search" class="schedule-search" type="search" placeholder="Поиск по списку"><select id="page-sort"><option value="">Сортировка</option>${columns.map((field) => `<option value="${field}">${labels[field] || field}</option>`).join("")}</select><button id="sort-direction" class="secondary-button" type="button">↑ По возрастанию</button></div><div class="management-table-wrap page-table-wrap"><table class="management-table"><thead><tr>${columns.map((field) => `<th>${labels[field] || field}</th>`).join("")}${actions ? "<th>Действия</th>" : ""}</tr></thead><tbody id="page-table-body"></tbody></table></div><div class="status" id="page-count"></div>`;
  let direction = 1;
  const draw = () => { const query = document.querySelector("#page-search").value.toLowerCase(); const sort = document.querySelector("#page-sort").value; const filtered = rows.filter((row) => columns.some((field) => String(formatValue(field, row[field])).toLowerCase().includes(query))).sort((a, b) => sort ? String(formatValue(sort, a[sort])).localeCompare(String(formatValue(sort, b[sort])), "ru", { numeric: true }) * direction : 0); document.querySelector("#page-table-body").innerHTML = filtered.length ? filtered.map((row) => `<tr>${columns.map((field) => `<td>${escapeHtml(formatValue(field, row[field]))}</td>`).join("")}${actions ? `<td class="management-actions"><button class="small-button" data-action="edit" data-id="${row.id}">Изменить</button><button class="small-button" data-action="delete" data-id="${row.id}">Удалить</button></td>` : ""}</tr>`).join("") : `<tr><td colspan="${columns.length + (actions ? 1 : 0)}">Нет данных.</td></tr>`; document.querySelector("#page-count").textContent = `Показано: ${filtered.length} из ${rows.length}`; };
  document.querySelector("#page-search").addEventListener("input", draw); document.querySelector("#page-sort").addEventListener("change", draw); document.querySelector("#sort-direction").addEventListener("click", (event) => { direction *= -1; event.target.textContent = direction === 1 ? "↑ По возрастанию" : "↓ По убыванию"; draw(); }); draw();
}
function openRecordForm(type, item = null, overview = null) {
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  const isGroup = type === "group";
  const data = overview || window.pageOverview;
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} ${isGroup ? "группу" : "аудиторию"}`;
  const roomTypes = { ordinary: "Обычная аудитория", classroom: "Учебная аудитория", lecture: "Лекционная аудитория", lecture_hall: "Лекционная аудитория", computer_lab: "Компьютерная аудитория", laboratory: "Лаборатория", seminar: "Семинарская аудитория", gym: "Спортивный зал", auditorium: "Актовый зал" };
  const equipment = { none: "Без оборудования", computers: "Компьютеры", projector: "Проектор", interactive_board: "Интерактивная доска", laboratory: "Лабораторное оборудование" };
  let equipmentType = "none";
  let equipmentQuantity = 0;
  if (item?.equipment) [equipmentType, equipmentQuantity] = String(item.equipment).split(":");
  form.innerHTML = isGroup
    ? `<label><span>Название группы</span><input name="name" required maxlength="50" value="${escapeHtml(item?.name || "")}"></label><label><span>Специальность</span><select name="specialty_id" required>${(data?.specialties || []).map((specialty) => `<option value="${specialty.id}" ${Number(item?.specialty_id) === specialty.id ? "selected" : ""}>${escapeHtml(specialty.code)} — ${escapeHtml(specialty.name)}</option>`).join("")}</select></label><label><span>Курс</span><select name="course" required>${[1, 2, 3, 4, 5, 6].map((course) => `<option value="${course}" ${Number(item?.course || 1) === course ? "selected" : ""}>${course} курс</option>`).join("")}</select></label><label><span>Язык обучения</span><select name="language" required>${["Русский", "Казахский", "Английский"].map((language) => `<option ${item?.language === language ? "selected" : ""}>${language}</option>`).join("")}</select></label>`
    : `<label><span>Название аудитории</span><input name="name" required maxlength="50" value="${escapeHtml(item?.name || "")}"></label><label><span>Вместимость</span><input name="capacity" type="number" min="1" required value="${item?.capacity || ""}"></label><label><span>Тип аудитории</span><select name="room_type" required>${Object.entries(roomTypes).map(([value, label]) => `<option value="${value}" ${item?.room_type === value ? "selected" : ""}>${label}</option>`).join("")}</select></label><label><span>Оборудование</span><select name="equipment_type">${Object.entries(equipment).map(([value, label]) => `<option value="${value}" ${equipmentType === value ? "selected" : ""}>${label}</option>`).join("")}</select></label><label><span>Количество оборудования</span><input name="equipment_quantity" type="number" min="0" value="${equipmentQuantity || 0}"></label>`
    + `<div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">${item ? "Сохранить" : "Добавить"}</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      if (isGroup) {
        values.specialty_id = Number(values.specialty_id);
        values.course = Number(values.course);
        await api(item ? `/groups/${item.id}` : "/groups", { method: item ? "PATCH" : "POST", body: JSON.stringify(values) });
      } else {
        values.capacity = Number(values.capacity);
        values.equipment = values.equipment_type === "none" ? null : `${values.equipment_type}:${Number(values.equipment_quantity) || 0}`;
        delete values.equipment_type;
        delete values.equipment_quantity;
        await api(item ? `/classrooms/${item.id}` : "/classrooms", { method: item ? "PATCH" : "POST", body: JSON.stringify(values) });
      }
      modal.hidden = true;
      render();
    } catch (error) { alert(error.message); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
}
async function openStudentForm(item = null) {
  const data = window.pageOverview || await api("/catalog/overview");
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} студента`;
  const selectedStreams = new Set((item?.streams || []).map((stream) => String(stream.id)));
  form.innerHTML = `<label><span>ФИО студента</span><input name="full_name" required maxlength="255" value="${escapeHtml(item?.full_name || "")}"></label><label><span>Группа</span><select name="group_id" required>${data.groups.map((group) => `<option value="${group.id}" ${Number(item?.group_id) === group.id ? "selected" : ""}>${escapeHtml(group.name)} — ${group.course} курс</option>`).join("")}</select></label><label><span>Потоки</span><select name="lecture_stream_ids" multiple size="5">${data.lecture_streams.map((stream) => `<option value="${stream.id}" ${selectedStreams.has(String(stream.id)) ? "selected" : ""}>${escapeHtml(stream.name)}</option>`).join("")}</select></label><small class="form-hint">Для выбора нескольких потоков удерживайте Ctrl (или Command на macOS).</small><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">Добавить</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    values.group_id = Number(values.group_id);
    values.lecture_stream_ids = [...form.elements.lecture_stream_ids.selectedOptions].map((option) => Number(option.value));
    try {
      if (item) await api(`/groups/students/${item.id}`, { method: "PATCH", body: JSON.stringify(values) });
      else {
        const created = await api(`/groups/${values.group_id}/students`, { method: "POST", body: JSON.stringify({ students: [{ full_name: values.full_name }] }) });
        if (created.students?.[0]) await api(`/groups/students/${created.students[0].id}`, { method: "PATCH", body: JSON.stringify(values) });
      }
      modal.hidden = true;
      render();
    } catch (error) { alert(error.message); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
}
async function editClassroom(id) {
  const data = await api("/catalog/overview");
  const item = data.classrooms.find((row) => row.id === id);
  if (!item) return;
  openRecordForm("classroom", item);
}
async function addClassroom() {
  openRecordForm("classroom");
}
async function editGroup(id) {
  const data = await api("/catalog/overview");
  const item = data.groups.find((row) => row.id === id);
  if (!item) return;
  openRecordForm("group", item, data);
}
async function addGroup() {
  const data = await api("/catalog/overview");
  openRecordForm("group", null, data);
}
async function editStudent(id) {
  const students = await api("/groups/students");
  const item = students.students.find((row) => row.id === id);
  if (!item) return;
  openStudentForm(item);
}
async function addStudent() {
  openStudentForm();
}
async function handleActions(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") return page === "groups" ? editGroup(id) : editClassroom(id);
  if (!confirm(`Удалить ${page === "groups" ? "группу" : "аудиторию"}?`)) return;
  await api(`/${page === "groups" ? "groups" : "classrooms"}/${id}`, { method: "DELETE" });
  render();
}
async function render() {
  if (!localStorage.getItem(tokenKey)) { location.href = "login.html"; return; }
  shell();
  const root = document.querySelector("#page-content");
  if (page === "dashboard" || page === "analytics") { const data = await api("/catalog/overview"); const counts = [["Периоды", data.periods.length], ["Группы", data.groups.length], ["Предметы", data.subjects.length], ["Преподаватели", data.teachers.length], ["Аудитории", data.classrooms.length]]; root.innerHTML = `<div class="diagnostics-grid">${counts.map(([label, value]) => `<div class="diagnostic-card ok"><span>${label}</span><strong>${value}</strong></div>`).join("")}</div>`; return; }
  if (page === "generation") { const data = await api("/catalog/overview"); root.innerHTML = `<div class="management-tools"><select id="generation-period">${data.periods.map((period) => `<option value="${period.id}">${escapeHtml(period.name)}</option>`).join("")}</select><button id="diagnose-button" class="primary-button">Проверить данные</button></div><div id="diagnose-result" class="diagnostics-grid"></div>`; document.querySelector("#diagnose-button").addEventListener("click", async () => { const result = await api(`/schedules/diagnostics/${document.querySelector("#generation-period").value}`); document.querySelector("#diagnose-result").innerHTML = result.valid ? [["Занятий", result.lessons_count], ["Слотов", result.time_slots_count], ["Аудиторий", result.classrooms_count]].map(([label, value]) => `<div class="diagnostic-card ok"><span>${label}</span><strong>${value}</strong></div>`).join("") : `<div class="empty-panel status-error">${escapeHtml(result.error)}</div>`; }); return; }
  if (page === "versions") { const data = await api("/schedules/versions"); renderTable(data.versions.map((version) => ({ name: version.name, academic_period_name: version.academic_period_name, version_number: version.version_number, status: version.status, items_count: version.items_count })), "versions"); return; }
  if (page === "availability") { const data = await api("/catalog/overview"); renderTable(data.time_slots.map((slot) => ({ day: ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"][slot.day_of_week], lesson_number: slot.lesson_number, start_time: slot.start_time, end_time: slot.end_time, is_active: slot.is_active ? "Доступен" : "Недоступен" })), "availability"); return; }
  if (page === "groups") { const data = await api("/catalog/overview"); window.pageOverview = data; renderTable(data.groups, page); const students = await api("/groups/students"); const old = document.querySelector("#page-content"); const studentPanel = document.createElement("section"); studentPanel.className = "students-panel"; studentPanel.innerHTML = `<div class="section-heading"><div><h2>Студенты</h2><p>Состав групп и назначенные потоки</p></div><button id="add-student" class="primary-button section-add-button" type="button">Добавить студента</button></div>`; old.appendChild(studentPanel); const table = document.createElement("div"); table.className = "management-table-wrap page-table-wrap"; table.innerHTML = `<table class="management-table"><thead><tr><th>ФИО</th><th>Группа</th><th>Потоки</th><th>Действия</th></tr></thead><tbody>${students.students.map((student) => `<tr><td>${escapeHtml(student.full_name)}</td><td>${escapeHtml(student.group_name)}</td><td>${escapeHtml(student.streams.map((stream) => stream.name).join(", ") || "—")}</td><td class="management-actions"><button class="small-button" data-student-action="edit" data-id="${student.id}">Изменить</button><button class="small-button" data-student-action="delete" data-id="${student.id}">Удалить</button></td></tr>`).join("")}</tbody></table>`; old.appendChild(table); document.querySelector("#add-record").addEventListener("click", addGroup); document.querySelector("#add-student").addEventListener("click", addStudent); old.addEventListener("click", handleActions); table.addEventListener("click", async (event) => { const button = event.target.closest("[data-student-action]"); if (!button) return; const id = Number(button.dataset.id); if (button.dataset.studentAction === "edit") return editStudent(id); if (confirm("Удалить студента?")) { await api(`/groups/students/${id}`, { method: "DELETE" }); render(); } }); return; }
  if (page === "profile") { root.innerHTML = `<div class="empty-panel">Настройки профиля доступны в основном интерфейсе.</div>`; return; }
  const data = await api("/catalog/overview"); window.pageOverview = data; renderTable(data[configs[page][2]] || [], configs[page][2]); if (["groups", "classrooms"].includes(page)) { document.querySelector("#add-record").addEventListener("click", page === "groups" ? addGroup : addClassroom); document.querySelector("#page-content").addEventListener("click", handleActions); }
}
const selectedTheme = localStorage.getItem("smart_schedule_theme") || "light";
document.documentElement.dataset.theme = selectedTheme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : selectedTheme === "system" ? "light" : selectedTheme;
render().catch((error) => { document.querySelector("#page-content").innerHTML = `<div class="empty-panel status-error">${escapeHtml(error.message)}</div>`; });
