const apiBase = window.location.protocol === "file:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : window.location.origin;
const tokenKey = "smart_schedule_token";
const page = document.body.dataset.page;
const configs = {
  dashboard: ["Обзор", "Ключевые показатели системы", "analytics"],
  generation: ["Генерация", "Проверка данных и запуск построения расписания", "generation"],
  versions: ["Версии расписания", "Публикация и архивирование результатов генерации", "versions"],
  periods: ["Учебные периоды", "Семестры и календарные параметры", "periods"],
  curricula: ["Учебные планы", "Планы, подключённые к учебным периодам", "curriculum_plans"],
  streams: ["Лекционные потоки", "Общие потоки и входящие учебные группы", "lecture_streams"],
  subjects: ["Предметы", "Дисциплины, доступные для планирования", "subjects"],
  groups: ["Группы и студенты", "Просмотр и управление составом групп", "groups"],
  teachers: ["Преподаватели", "Преподавательский состав и кафедры", "teachers"],
  qualifications: ["Квалификации", "Предметы и часы преподавателей", "qualification_summary"],
  classrooms: ["Аудитории", "Вместимость, тип и оборудование помещений", "classrooms"],
  availability: ["Доступность", "Временные слоты и доступность ресурсов", "periods"],
  constraints: ["Ограничения", "Пользовательские ограничения расписания", "constraints"],
  analytics: ["Аналитика", "Сводка по расписаниям и ресурсам", "analytics"],
  occupancy: ["Аудитории", "Интерактивная карта помещений текущего расписания", "occupancy"],
  settings: ["Настройки", "Внешний вид и параметры интерфейса", "settings"],
  profile: ["Личный профиль", "Настройки администратора", "profile"],
};
const nav = [
  ["ОСНОВНОЕ", [["dashboard.html", "⌂", "Обзор", "dashboard"]]],
  ["РАСПИСАНИЕ", [["home.html", "▦", "Расписание", "schedule"], ["occupancy.html", "⌘", "Загрузка аудиторий", "occupancy"], ["generation.html", "✦", "Создать расписание", "generation"], ["versions.html", "◫", "Версии", "versions"]]],
  ["ДАННЫЕ", [["periods.html", "◫", "Семестры", "periods"], ["curricula.html", "▤", "Учебные планы", "curricula"], ["streams.html", "◎", "Лекционные потоки", "streams"], ["subjects.html", "◈", "Предметы", "subjects"], ["groups.html", "♙", "Группы и студенты", "groups"]]],
  ["ЛЮДИ", [["teachers.html", "♙", "Преподаватели", "teachers"], ["qualifications.html", "✓", "Квалификации", "qualifications"]]],
  ["РЕСУРСЫ", [["classrooms.html", "▣", "Аудитории", "classrooms"], ["availability.html", "◷", "Доступность", "availability"]]],
  ["СИСТЕМА", [["constraints.html", "◌", "Ограничения", "constraints"], ["analytics.html", "▥", "Аналитика", "analytics"]]],
];
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;" }[char])); }
function statusLabel(value) { return ({ draft: "Черновик", generated: "Сгенерирована", published: "Опубликована", archived: "Архивная", failed: "Ошибка" }[value] || value || "Неизвестен"); }
function headers() { return { Authorization: `Bearer ${localStorage.getItem(tokenKey)}`, "Content-Type": "application/json" }; }
async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${apiBase}${path}`, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
  } catch (error) {
    throw new Error(`Не удалось подключиться к серверу. Проверьте, что SmartSchedule API запущен (${error.message}).`);
  }
  if (response.status === 401) { localStorage.removeItem(tokenKey); location.href = "login.html"; }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg || String(item)).join("; ")
      : typeof data.detail === "string" ? data.detail : data.detail?.message;
    throw new Error(detail || `API: ${response.status}`);
  }
  return data;
}
function renderVersions(versions, root) {
  const statusNames = { draft: "Черновик", generated: "Сгенерирована", published: "Опубликована", archived: "Архивная", failed: "Ошибка" };
  root.innerHTML = `<div class="versions-list">${versions.length ? versions.map((version) => `<article class="version-card"><div><div class="detail-kicker">ВЕРСИЯ №${version.version_number}</div><h2>${escapeHtml(version.name || `Расписание №${version.version_number}`)}</h2><p>${escapeHtml(version.academic_period_name || "Учебный период")} · ${version.items_count} занятий · ${escapeHtml(new Date(version.created_at).toLocaleString("ru-RU"))}</p></div><span class="version-status status-${version.status}">${statusNames[version.status] || version.status}</span><div class="version-actions"><a class="secondary-button" href="occupancy.html?version_id=${version.id}">Просмотреть</a>${version.status !== "published" && version.status !== "archived" ? `<button class="small-button" data-version-action="publish" data-id="${version.id}">Опубликовать</button>` : ""}${version.status !== "published" && version.status !== "archived" ? `<button class="small-button" data-version-action="archive" data-id="${version.id}">Архивировать</button>` : ""}${version.status === "published" ? `<a class="primary-button" href="home.html?version_id=${version.id}">Открыть</a>` : ""}</div></article>`).join("") : '<div class="empty-panel">Версии расписания пока не созданы.</div>'}</div>`;
  root.querySelectorAll("[data-version-action]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api(`/schedules/${button.dataset.id}/${button.dataset.versionAction}`, { method: "POST" });
      render();
    } catch (error) { alert(error.message); button.disabled = false; }
  }));
}
function shell() {
  const savedAvatar = localStorage.getItem("smart_schedule_avatar");
  const links = nav.map(([title, items]) => {
    const section = `<div class="nav-section-title">${title}</div>${items.map(([href, icon, label, key]) => `<a href="${href}" class="nav-item ${key === page ? "active" : ""}"><span class="nav-icon">${icon}</span><span>${label}</span></a>`).join("")}`;
    if (title !== "РАСПИСАНИЕ") return section;
    return `<div class="nav-section-title">${title}</div>${items.map(([href, icon, label, key]) => `<a href="${href}" class="nav-item ${key === page ? "active" : ""}"><span class="nav-icon">${icon}</span><span>${label}</span></a>`).join("")}`;
  }).join("");
  const addable = ["groups", "classrooms", "teachers", "subjects", "periods", "constraints", "qualifications", "curricula", "streams"].includes(page);
  const addButton = addable ? `<button id="add-record" class="primary-button page-add-button" type="button">Добавить ${page === "groups" ? "группу" : page === "classrooms" ? "аудиторию" : page === "teachers" ? "преподавателя" : page === "subjects" ? "предмет" : page === "periods" ? "период" : page === "qualifications" ? "нагрузку" : page === "curricula" ? "учебный план" : page === "streams" ? "поток" : "ограничение"}</button>` : "";
  document.querySelector(".app").innerHTML = `<aside class="sidebar" id="app-sidebar"><div><div class="logo"><div class="logo-icon">S</div><div class="logo-text"><span>SmartSchedule</span><small>AI workspace</small></div></div><nav class="navigation">${links}</nav></div><div class="sidebar-bottom"><a href="settings.html" class="nav-item ${page === "settings" ? "active" : ""}"><span class="nav-icon">⚙</span><span>Настройки</span></a><a href="profile.html" class="profile-mini" id="profile-menu-button"><div class="avatar">${savedAvatar ? `<img src="${savedAvatar}" alt="">` : "М"}</div><div class="profile-info"><strong>Администратор</strong><span>Личный профиль</span></div><span class="profile-arrow">›</span></a></div></aside><button class="sidebar-backdrop" id="sidebar-backdrop" type="button" aria-label="Закрыть меню"></button><main class="main"><header class="topbar"><div class="topbar-leading"><button class="mobile-menu-button" id="mobile-menu" type="button" aria-label="Открыть меню"><span></span><span></span><span></span></button><div class="breadcrumbs"><span>Рабочее пространство</span><span>/</span><strong>${configs[page][0]}</strong></div></div><div class="topbar-actions"><a class="topbar-schedule-link" href="home.html">Открыть расписание</a><button class="icon-button" id="logout-top" type="button" title="Выйти" aria-label="Выйти">↗</button><a class="topbar-avatar" id="toolbar-avatar" href="profile.html" aria-label="Открыть профиль">${savedAvatar ? `<img src="${savedAvatar}" alt="">` : "М"}</a></div></header><div class="content"><section class="page-header"><div><div class="eyebrow">SMARTSCHEDULE</div><h1>${configs[page][0]}</h1><p>${configs[page][1]}</p></div><div class="panel-actions">${addButton}</div></section><div id="page-content"><div class="empty-panel">Загрузка данных…</div></div></div></main><div id="record-modal" class="lesson-modal" hidden><div class="lesson-modal-backdrop" data-close-record></div><section class="lesson-modal-content entity-modal-content"><button class="lesson-modal-close" type="button" data-close-record aria-label="Закрыть">×</button><div class="eyebrow">УПРАВЛЕНИЕ ДАННЫМИ</div><h2 id="record-modal-title"></h2><form id="record-form" class="entity-form"></form></section></div>`;
  document.querySelectorAll("#logout-button,#logout-top").forEach((button) => button.addEventListener("click", () => { localStorage.removeItem(tokenKey); location.href = "login.html"; }));
  const closeNavigation = () => document.body.classList.remove("sidebar-open");
  document.querySelector("#mobile-menu").addEventListener("click", () => document.body.classList.toggle("sidebar-open"));
  document.querySelector("#sidebar-backdrop").addEventListener("click", closeNavigation);
  document.querySelectorAll(".sidebar .nav-item").forEach((link) => link.addEventListener("click", closeNavigation));
}
const labels = { room_type: "Тип", equipment: "Оборудование", student_count: "Студентов", subjects_count: "Дисциплины", loads_count: "Нагрузки", academic_year: "Учебный год", semester: "Семестр", weeks: "Недель", specialty: "Специальность", course: "Курс", language: "Язык", capacity: "Вместимость", position: "Должность", department: "Кафедра", email: "Email", subject: "Предмет", hours: "Часы", lecture_hours: "Лекции", practice_hours: "Практика", lab_hours: "Лабораторные", lecture_per_week: "Лекций/нед.", practice_per_week: "Практик/нед.", lab_per_week: "Лаб./нед.", code: "Код", name: "Название", group: "Группа", streams: "Потоки", full_name: "ФИО", teacher: "Преподаватель", constraint_type: "Тип ограничения", title: "Название", description: "Описание", start_time: "Начало", end_time: "Окончание", is_active: "Статус", academic_period_name: "Учебный период", version_number: "Номер версии", status: "Статус", items_count: "Занятий", day: "День", lesson_number: "Пара" };
const roomTypes = { ordinary: "Обычная аудитория", classroom: "Учебная аудитория", lecture: "Лекционная аудитория", lecture_hall: "Лекционная аудитория", computer_lab: "Компьютерная аудитория", laboratory: "Лаборатория", lab: "Лаборатория", seminar: "Семинарская аудитория", gym: "Спортивный зал", auditorium: "Актовый зал" };
function formatValue(field, value) { if (field === "room_type") return roomTypes[value] || value || "—"; if (field === "equipment" && value) { const [type, count] = String(value).split(":"); return `${type === "computers" ? "Компьютеры" : type}${count ? ` · ${count} шт.` : ""}`; } return value ?? "—"; }
const occupancyDays = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница"];
function occupancyGroup(roomType) { return roomType === "computer_lab" ? "Компьютерные классы" : ["lecture", "lecture_hall"].includes(roomType) ? "Большие лекционные" : "Обычные аудитории"; }
function occupancyTime(value) { return String(value || "").slice(0, 5); }
function occupancyReportExcel(rows, version) {
  const table = `<table><tr><th>Аудитория</th><th>Тип</th><th>Вместимость</th><th>Занятые слоты</th><th>Доступные слоты</th><th>Загрузка</th><th>Статус</th></tr>${rows.map((row) => `<tr><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.type)}</td><td>${row.capacity}</td><td>${row.busy}</td><td>${row.total}</td><td>${row.percent}%</td><td>${row.status}</td></tr>`).join("")}</table>`;
  const html = `<html><head><meta charset="UTF-8"><style>body{font-family:Arial;color:#17233d}h1{font-size:20px}p{color:#657189}table{border-collapse:collapse;width:100%}th{background:#5267e8;color:#fff}th,td{border:1px solid #dfe4ef;padding:8px;text-align:left}tr:nth-child(even){background:#f5f7fb}</style></head><body><h1>Отчёт по загрузке аудиторий</h1><p>Версия расписания: ${escapeHtml(version.name || `№${version.version_number}`)}</p>${table}</body></html>`;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([`\uFEFF${html}`], { type: "application/vnd.ms-excel;charset=utf-8" }));
  link.download = "отчет-загрузка-аудиторий.xls";
  link.click();
  URL.revokeObjectURL(link.href);
}
function renderOccupancy(data, root) {
  let selectedRoomId = data.classrooms[0]?.id;
  let filter = "all";
  let search = "";
  let mode = "week";
  let day = Math.min(5, Math.max(1, new Date().getDay() || 1));
  let lessonNumber = null;
  const draw = () => {
    const slots = data.time_slots.filter((slot) => mode === "week" || slot.day_of_week === day).filter((slot) => lessonNumber === null || slot.lesson_number === lessonNumber);
    const visibleRooms = data.classrooms.filter((room) => (filter === "all" || occupancyGroup(room.room_type) === filter) && room.name.toLowerCase().includes(search.toLowerCase()));
    const selected = data.classrooms.find((room) => room.id === selectedRoomId) || visibleRooms[0] || data.classrooms[0];
    if (selected) selectedRoomId = selected.id;
    const activityAt = (room, slot) => room.activities.find((item) => item.time_slot.day_of_week === slot.day_of_week && item.time_slot.lesson_number === slot.lesson_number);
    const occupancy = (room) => Math.round((room.activities.filter((item) => mode === "week" || item.time_slot.day_of_week === day).length / Math.max(1, mode === "week" ? data.time_slots.length : data.time_slots.filter((slot) => slot.day_of_week === day).length)) * 100);
    const roomCard = (room) => { const focusActivity = mode === "today" && lessonNumber !== null ? room.activities.find((item) => item.time_slot.day_of_week === day && item.time_slot.lesson_number === lessonNumber) : null; const status = focusActivity ? "Занята" : mode === "today" && lessonNumber !== null ? "Свободна" : `${occupancy(room)}% за период`; return `<button class="occupancy-room ${room.id === selected?.id ? "selected" : ""}" data-room-id="${room.id}" type="button"><div class="room-plan room-plan-${room.room_type}">${Array.from({ length: room.room_type === "lecture" ? 12 : 15 }, () => `<i>${room.room_type === "computer_lab" ? "▣" : room.room_type === "lecture" ? "○" : "▫"}</i>`).join("")}</div><div class="room-card-title"><strong>${escapeHtml(room.name)}</strong><span>${room.capacity} мест</span></div><div class="room-card-meta"><span>${escapeHtml(roomTypes[room.room_type] || room.room_type)}</span><b>${escapeHtml(status)}</b></div><div class="room-load"><i style="width:${Math.min(100, occupancy(room))}%"></i></div></button>`; };
    const detailSlots = mode === "week" ? data.time_slots : data.time_slots.filter((slot) => slot.day_of_week === day);
    const detailDays = mode === "week" ? [1, 2, 3, 4, 5] : [day];
    const detailTimeline = detailDays.map((dayNumber) => {
      const daySlots = detailSlots.filter((slot) => slot.day_of_week === dayNumber);
      return `<section class="occupancy-day-section"><h3>${occupancyDays[dayNumber]}</h3><div class="occupancy-day-slots">${daySlots.map((slot) => {
        const activity = activityAt(selected, slot);
        return `<div class="occupancy-slot ${activity ? "busy" : "free"}"><div><b>${slot.lesson_number} пара</b><small>${occupancyTime(slot.start_time)}–${occupancyTime(slot.end_time)}</small></div>${activity ? `<section><strong>Занято</strong><span>${escapeHtml(activity.subject?.name || "Занятие")} · ${escapeHtml(activity.lesson_type)}</span><span>${escapeHtml(activity.group_names.join(" + ") || "Общая лекция")}${activity.subgroup_names.length ? ` · ${escapeHtml(activity.subgroup_names.join(", "))}` : ""}</span><span>${escapeHtml(activity.teacher?.full_name || "Преподаватель не указан")}</span></section>` : `<span class="occupancy-free">Свободно</span>`}</div>`;
      }).join("")}</div></section>`;
    }).join("");
    const reportRows = visibleRooms.map((room) => { const busy = room.activities.filter((item) => mode === "week" || item.time_slot.day_of_week === day).length; const total = mode === "week" ? data.time_slots.length : data.time_slots.filter((slot) => slot.day_of_week === day).length; const percent = Math.round((busy / Math.max(1, total)) * 100); return { name: room.name, type: roomTypes[room.room_type] || room.room_type, capacity: room.capacity, busy, total, percent, status: percent === 0 ? "Свободна" : percent >= 75 ? "Высокая загрузка" : "Частично занята" }; });
    const average = reportRows.length ? Math.round(reportRows.reduce((sum, row) => sum + row.percent, 0) / reportRows.length) : 0;
    const reportTable = `<table class="occupancy-report-table"><thead><tr><th>Аудитория</th><th>Тип</th><th>Мест</th><th>Занято</th><th>Доступно</th><th>Загрузка</th><th>Статус</th></tr></thead><tbody>${reportRows.map((row) => `<tr><td><strong>${escapeHtml(row.name)}</strong></td><td>${escapeHtml(row.type)}</td><td>${row.capacity}</td><td>${row.busy}</td><td>${row.total}</td><td><div class="report-progress"><i style="width:${Math.min(100, row.percent)}%"></i></div><b>${row.percent}%</b></td><td>${row.status}</td></tr>`).join("")}</tbody></table>`;
    const reportMarkup = `<section class="occupancy-report"><div class="report-heading"><div><div class="detail-kicker">ОТЧЁТ ПО РАСПИСАНИЮ</div><h2>Загрузка аудиторий</h2><p>Версия ${data.version.version_number} · ${mode === "week" ? "учебная неделя" : occupancyDays[day]}</p></div><div class="report-actions"><button class="secondary-button" id="export-occupancy-excel" type="button">Экспорт в Excel</button><button class="primary-button" id="print-occupancy-report" type="button">Экспорт в PDF</button></div></div><div class="report-summary"><div><span>Аудиторий</span><strong>${reportRows.length}</strong></div><div><span>Занято за период</span><strong>${reportRows.filter((row) => row.busy > 0).length}</strong></div><div><span>Свободно за период</span><strong>${reportRows.filter((row) => row.busy === 0).length}</strong></div><div><span>Средняя загрузка</span><strong>${average}%</strong></div></div>${reportTable}</section>`;
    const groupsMarkup = ["Обычные аудитории", "Компьютерные классы", "Большие лекционные"].map((group) => {
      const groupRooms = visibleRooms.filter((room) => occupancyGroup(room.room_type) === group);
      if (!groupRooms.length) return "";
      return `<section class="occupancy-group"><div class="section-heading"><div><h2>${group}</h2><p>${groupRooms.length} помещений</p></div></div><div class="occupancy-grid">${groupRooms.map(roomCard).join("")}</div></section>`;
    }).join("");
    root.innerHTML = `<div class="occupancy-toolbar"><div class="view-switcher"><button class="view-button ${mode === "week" ? "active" : ""}" data-mode="week" type="button">Неделя</button><button class="view-button ${mode === "today" ? "active" : ""}" data-mode="today" type="button">День</button></div><div class="occupancy-days">${occupancyDays.slice(1).map((name, index) => `<button class="day-chip ${day === index + 1 ? "active" : ""}" data-day="${index + 1}" type="button">${name.slice(0, 2).toUpperCase()}</button>`).join("")}</div><select class="occupancy-lesson-filter" aria-label="Выбор пары"><option value="">Все пары</option>${[...new Set(data.time_slots.map((slot) => slot.lesson_number))].map((number) => `<option value="${number}" ${lessonNumber === number ? "selected" : ""}>${number} пара</option>`).join("")}</select><input class="occupancy-search" value="${escapeHtml(search)}" placeholder="Поиск аудитории..." aria-label="Поиск аудитории"><span class="occupancy-version">Версия ${data.version.version_number}</span></div><div class="occupancy-filters">${["all", "Обычные аудитории", "Компьютерные классы", "Большие лекционные"].map((item) => `<button class="filter-chip ${filter === item ? "active" : ""}" data-filter="${item}" type="button">${item === "all" ? "Все" : item}</button>`).join("")}</div><div class="occupancy-layout"><div class="occupancy-map">${groupsMarkup || `<div class="empty-panel">Нет аудиторий по выбранному фильтру.</div>`}</div><aside class="occupancy-detail">${selected ? `<div class="detail-kicker">ВЫБРАННОЕ ПОМЕЩЕНИЕ</div><h2>Аудитория ${escapeHtml(selected.name)}</h2><p class="occupancy-detail-type">${escapeHtml(roomTypes[selected.room_type] || selected.room_type)} · ${selected.capacity} мест</p><div class="occupancy-detail-stat"><strong>${occupancy(selected)}%</strong><span>загрузка ${mode === "week" ? "за неделю" : "за день"}</span></div><div class="occupancy-timeline">${detailTimeline}</div>` : `<div class="empty-panel">Нет аудиторий для отображения.</div>`}</aside></div>`;
    root.insertAdjacentHTML("beforeend", reportMarkup);
    const occupancyLayout = root.querySelector(".occupancy-layout");
    const occupancyReport = root.querySelector(".occupancy-report");
    if (occupancyLayout && occupancyReport) occupancyLayout.after(occupancyReport);
    root.querySelector("#export-occupancy-excel").addEventListener("click", () => occupancyReportExcel(reportRows, data.version));
    root.querySelector("#print-occupancy-report").addEventListener("click", () => { document.body.classList.add("printing-occupancy-report"); window.print(); setTimeout(() => document.body.classList.remove("printing-occupancy-report"), 500); });
    root.querySelectorAll("[data-room-id]").forEach((button) => button.addEventListener("click", () => { selectedRoomId = Number(button.dataset.roomId); draw(); }));
    root.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => { mode = button.dataset.mode; draw(); }));
    root.querySelectorAll("[data-day]").forEach((button) => button.addEventListener("click", () => { day = Number(button.dataset.day); mode = "today"; draw(); }));
    root.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { filter = button.dataset.filter; draw(); }));
    root.querySelector(".occupancy-search").addEventListener("input", (event) => { search = event.target.value; draw(); });
    root.querySelector(".occupancy-lesson-filter").addEventListener("change", (event) => { lessonNumber = event.target.value ? Number(event.target.value) : null; draw(); });
  };
  draw();
}
function renderDashboard(data, versions, root) {
  const students = data.groups.reduce((sum, group) => sum + (Number(group.student_count) || 0), 0);
  const latest = versions.versions[0];
  const cards = [["Учебные группы", data.groups.length, "blue"], ["Студенты", students, "purple"], ["Преподаватели", data.teachers.length, "green"], ["Предметы", data.subjects.length, "orange"], ["Аудитории", data.classrooms.length, "blue"], ["Занятия", latest?.items_count || 0, "purple"]];
  root.innerHTML = `<div class="dashboard-summary">${cards.map(([label, value, tone]) => `<div class="stat-card"><div class="stat-icon ${tone}">▦</div><div><span class="stat-label">${label}</span><strong>${value}</strong></div></div>`).join("")}</div><section class="dashboard-panel"><div class="panel-heading"><div><div class="eyebrow">СОСТОЯНИЕ РАСПИСАНИЯ</div><h2>Последняя версия</h2><p>${latest ? `${escapeHtml(latest.name)} · ${latest.items_count} занятий · ${statusLabel(latest.status)}` : "Версии расписания пока не созданы."}</p></div>${latest ? `<a class="primary-button" href="home.html">Открыть расписание</a>` : ""}</div><div class="diagnostics-grid"><div class="diagnostic-card ok"><span>Временные слоты</span><strong>${data.time_slots.length}</strong></div><div class="diagnostic-card ok"><span>Лекционные потоки</span><strong>${data.lecture_streams.length}</strong></div><div class="diagnostic-card ok"><span>Аудитории с вместимостью</span><strong>${data.classrooms.filter((room) => room.capacity > 0).length}/${data.classrooms.length}</strong></div><div class="diagnostic-card ok"><span>Активные ограничения</span><strong>${data.constraints.filter((item) => item.is_active).length}</strong></div></div></section>`;
}
function tableCell(field, value, key) {
  if (key === "groups" && field === "student_count") {
    const count = Math.max(0, Number(value) || 0);
    return `<div class="group-capacity"><span>${count} / 25</span><span class="group-capacity-track"><span style="width:${Math.min(100, count / 25 * 100)}%"></span></span></div>`;
  }
  if (field === "language") return `<span class="data-badge data-badge-language">${escapeHtml(value || "—")}</span>`;
  if (field === "is_active") return `<span class="data-badge ${value ? "data-badge-active" : "data-badge-muted"}">${value ? "Активен" : "Неактивен"}</span>`;
  if (field === "group_names" && Array.isArray(value)) return value.length ? value.map((name) => `<span class="data-badge data-badge-group">${escapeHtml(name)}</span>`).join(" ") : "—";
  return escapeHtml(formatValue(field, value));
}
function columnsFor(key, data) {
  const defaults = { periods: ["name", "academic_year", "semester", "weeks", "start_date", "end_date"], curriculum_plans: ["specialty", "academic_period_name", "course", "semester", "academic_year", "subjects_count"], lecture_streams: ["name", "group_names", "is_active"], subjects: ["code", "name"], groups: ["name", "specialty", "course", "language", "student_count"], teachers: ["full_name", "position", "department", "email", "phone"], qualifications: ["teacher", "subject", "language", "lecture_hours", "practice_hours", "lab_hours"], classrooms: ["name", "capacity", "room_type", "equipment"], constraints: ["constraint_type", "title", "description", "start_time", "end_time", "is_active"] };
  return defaults[key] || Object.keys(data[0] || {}).filter((field) => !["id", "group_id", "teacher_id", "classroom_id"].includes(field));
}
function renderTable(rows, key) {
  const root = document.querySelector("#page-content");
  const columns = columnsFor(key, rows);
  const actions = ["groups", "classrooms", "teachers", "subjects", "periods", "constraints", "qualifications", "curriculum_plans", "lecture_streams"].includes(key);
  root.innerHTML = `<div class="management-tools"><input id="page-search" class="schedule-search" type="search" placeholder="Поиск по списку"><select id="page-sort"><option value="">Сортировка</option>${columns.map((field) => `<option value="${field}">${labels[field] || field}</option>`).join("")}</select><button id="sort-direction" class="secondary-button" type="button">↑ По возрастанию</button></div><div class="management-table-wrap page-table-wrap"><table class="management-table ${actions ? "management-table-actions" : ""}"><thead><tr>${actions ? "<th>Действия</th>" : ""}${columns.map((field) => `<th>${labels[field] || field}</th>`).join("")}</tr></thead><tbody id="page-table-body"></tbody></table></div><div class="status" id="page-count"></div>`;
  let direction = 1;
  const draw = () => { const query = document.querySelector("#page-search").value.toLowerCase(); const sort = document.querySelector("#page-sort").value; const filtered = rows.filter((row) => columns.some((field) => String(formatValue(field, row[field])).toLowerCase().includes(query))).sort((a, b) => sort ? String(formatValue(sort, a[sort])).localeCompare(String(formatValue(sort, b[sort])), "ru", { numeric: true }) * direction : 0); document.querySelector("#page-table-body").innerHTML = filtered.length ? filtered.map((row) => `<tr>${actions ? `<td class="management-actions"><button class="small-button" data-action="edit" data-id="${row.id}">Изменить</button><button class="small-button" data-action="delete" data-id="${row.id}">Удалить</button></td>` : ""}${columns.map((field) => `<td>${tableCell(field, row[field], key)}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${columns.length + (actions ? 1 : 0)}">Нет данных.</td></tr>`; document.querySelector("#page-count").textContent = `Показано: ${filtered.length} из ${rows.length}`; };
  document.querySelector("#page-search").addEventListener("input", draw); document.querySelector("#page-sort").addEventListener("change", draw); document.querySelector("#sort-direction").addEventListener("click", (event) => { direction *= -1; event.target.textContent = direction === 1 ? "↑ По возрастанию" : "↓ По убыванию"; draw(); }); draw();
}
function renderStudentsTable(students) {
  const section = document.querySelector(".students-panel");
  const rows = students.map((student) => ({
    ...student,
    group: student.group_name || "—",
    streams_text: student.streams.map((stream) => stream.name).join(", ") || "—",
  }));
  section.insertAdjacentHTML("beforeend", `<div class="management-tools student-tools"><input id="student-search" class="schedule-search" type="search" placeholder="Поиск студента, группы или потока"><select id="student-sort"><option value="">Сортировка</option><option value="full_name">ФИО</option><option value="group">Группа</option><option value="streams_text">Потоки</option></select><button id="student-sort-direction" class="secondary-button" type="button">↑ По возрастанию</button></div><div class="management-table-wrap page-table-wrap"><table class="management-table"><thead><tr><th>ФИО</th><th>Группа</th><th>Потоки</th><th>Действия</th></tr></thead><tbody id="student-table-body"></tbody></table></div><div class="status" id="student-count"></div>`);
  let direction = 1;
  const draw = () => {
    const query = document.querySelector("#student-search").value.toLowerCase();
    const sort = document.querySelector("#student-sort").value;
    const filtered = rows.filter((row) => [row.full_name, row.group, row.streams_text].some((value) => String(value).toLowerCase().includes(query))).sort((a, b) => sort ? String(a[sort]).localeCompare(String(b[sort]), "ru", { numeric: true }) * direction : 0);
    document.querySelector("#student-table-body").innerHTML = filtered.length ? filtered.map((student) => `<tr><td>${escapeHtml(student.full_name)}</td><td>${escapeHtml(student.group)}</td><td>${escapeHtml(student.streams_text)}</td><td class="management-actions"><button class="small-button" data-student-action="edit" data-id="${student.id}">Изменить</button><button class="small-button" data-student-action="delete" data-id="${student.id}">Удалить</button></td></tr>`).join("") : '<tr><td colspan="4">Нет студентов по выбранному поиску.</td></tr>';
    document.querySelector("#student-count").textContent = `Показано студентов: ${filtered.length} из ${rows.length}`;
  };
  document.querySelector("#student-search").addEventListener("input", draw);
  document.querySelector("#student-sort").addEventListener("change", draw);
  document.querySelector("#student-sort-direction").addEventListener("click", (event) => { direction *= -1; event.target.textContent = direction === 1 ? "↑ По возрастанию" : "↓ По убыванию"; draw(); });
  draw();
}
function renderQualificationSummary(rows, root) {
  root.innerHTML = `<div class="data-summary-note">Преподавателей: <strong>${rows.length}</strong> · с назначенной предметной нагрузкой: <strong>${rows.filter((row) => row.loads_count > 0).length}</strong></div><div class="management-tools"><input id="page-search" class="schedule-search" type="search" placeholder="Поиск преподавателя или предмета"><select id="page-sort"><option value="">Сортировка</option><option value="teacher">Преподаватель</option><option value="loads_count">Количество нагрузок</option></select><button id="sort-direction" class="secondary-button" type="button">↑ По возрастанию</button></div><div class="management-table-wrap page-table-wrap"><table class="management-table"><thead><tr><th>Преподаватель</th><th>Предметы</th><th>Язык</th><th>Нагрузки</th><th>Действия</th></tr></thead><tbody id="page-table-body"></tbody></table></div><div class="status" id="page-count"></div>`;
  let direction = 1;
  const draw = () => {
    const query = document.querySelector("#page-search").value.toLowerCase();
    const sort = document.querySelector("#page-sort").value;
    const filtered = rows.filter((row) => `${row.teacher} ${row.subjects.join(" ")} ${row.languages.join(" ")}`.toLowerCase().includes(query)).sort((a, b) => sort ? String(a[sort]).localeCompare(String(b[sort]), "ru", { numeric: true }) * direction : 0);
    document.querySelector("#page-table-body").innerHTML = filtered.length ? filtered.map((row) => `<tr><td><strong>${escapeHtml(row.teacher)}</strong></td><td>${row.subjects.length ? row.subjects.map((subject) => `<span class="data-badge data-badge-group">${escapeHtml(subject)}</span>`).join(" ") : '<span class="data-badge data-badge-muted">Не назначено</span>'}</td><td>${row.languages.length ? row.languages.map((language) => `<span class="data-badge data-badge-language">${escapeHtml(language)}</span>`).join(" ") : "—"}</td><td>${row.loads_count}</td><td class="management-actions"><button class="small-button" data-qualification-teacher="${row.teacher_id}">Добавить нагрузку</button></td></tr>`).join("") : '<tr><td colspan="5">Нет данных.</td></tr>';
    document.querySelector("#page-count").textContent = `Показано: ${filtered.length} из ${rows.length}`;
  };
  document.querySelector("#page-search").addEventListener("input", draw);
  document.querySelector("#page-sort").addEventListener("change", draw);
  document.querySelector("#sort-direction").addEventListener("click", (event) => { direction *= -1; event.target.textContent = direction === 1 ? "↑ По возрастанию" : "↓ По убыванию"; draw(); });
  root.addEventListener("click", (event) => { const button = event.target.closest("[data-qualification-teacher]"); if (button) openQualificationForm({ teacher_id: Number(button.dataset.qualificationTeacher) }); });
  draw();
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
    + `<div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">${item ? "Изменить" : "Добавить"}</button></div>`;
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
  form.innerHTML = `<label><span>ФИО студента</span><input name="full_name" required maxlength="255" value="${escapeHtml(item?.full_name || "")}"></label><label><span>Группа</span><select name="group_id" required>${data.groups.map((group) => `<option value="${group.id}" ${Number(item?.group_id) === group.id ? "selected" : ""}>${escapeHtml(group.name)} — ${group.course} курс</option>`).join("")}</select></label><label><span>Потоки</span><select name="lecture_stream_ids" multiple size="5">${data.lecture_streams.map((stream) => `<option value="${stream.id}" ${selectedStreams.has(String(stream.id)) ? "selected" : ""}>${escapeHtml(stream.name)}</option>`).join("")}</select></label><small class="form-hint">Для выбора нескольких потоков удерживайте Ctrl (или Command на macOS).</small><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">${item ? "Изменить" : "Добавить"}</button></div>`;
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
function openTeacherForm(item = null) {
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} преподавателя`;
  form.innerHTML = `<label><span>ФИО</span><input name="full_name" required maxlength="255" value="${escapeHtml(item?.full_name || "")}"></label><label><span>Должность</span><input name="position" required maxlength="100" value="${escapeHtml(item?.position || "")}"></label><label><span>Кафедра</span><input name="department" required maxlength="255" value="${escapeHtml(item?.department || "")}"></label><label><span>Email</span><input name="email" type="email" value="${escapeHtml(item?.email || "")}"></label><label><span>Телефон</span><input name="phone" value="${escapeHtml(item?.phone || "")}"></label><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">Сохранить</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    try {
      await api(item ? `/teachers/${item.id}` : "/teachers", { method: item ? "PATCH" : "POST", body: JSON.stringify(values) });
      modal.hidden = true;
      render();
    } catch (error) { alert(error.message); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
}
function openSimpleForm(type, item = null) {
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} ${type === "subjects" ? "предмет" : type === "periods" ? "учебный период" : "ограничение"}`;
  const subjectFields = `<label><span>Код</span><input name="code" required value="${escapeHtml(item?.code || "")}"></label><label><span>Название</span><input name="name" required value="${escapeHtml(item?.name || "")}"></label>`;
  const periodFields = `<label><span>Название</span><input name="name" required value="${escapeHtml(item?.name || "")}"></label><label><span>Учебный год</span><input name="academic_year" required value="${escapeHtml(item?.academic_year || "")}"></label><label><span>Семестр</span><input name="semester" type="number" min="1" max="2" required value="${item?.semester || 1}"></label><label><span>Начало</span><input name="start_date" type="date" required value="${escapeHtml(item?.start_date || "")}"></label><label><span>Окончание</span><input name="end_date" type="date" required value="${escapeHtml(item?.end_date || "")}"></label><label><span>Недель</span><input name="weeks" type="number" min="1" max="60" required value="${item?.weeks || 16}"></label>`;
  const constraintFields = `<label><span>Тип ограничения</span><input name="constraint_type" required value="${escapeHtml(item?.constraint_type || "")}"></label><label><span>Название</span><input name="title" required value="${escapeHtml(item?.title || "")}"></label><label><span>Описание</span><textarea name="description" required>${escapeHtml(item?.description || "")}</textarea></label><label><span>Начало</span><input name="start_time" pattern="^\\d{2}:\\d{2}$" value="${escapeHtml(item?.start_time || "")}"></label><label><span>Окончание</span><input name="end_time" pattern="^\\d{2}:\\d{2}$" value="${escapeHtml(item?.end_time || "")}"></label>`;
  form.innerHTML = `${type === "subjects" ? subjectFields : type === "periods" ? periodFields : constraintFields}<div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">Сохранить</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    if (type === "periods") { values.semester = Number(values.semester); values.weeks = Number(values.weeks); }
    try {
      const resource = type === "subjects" ? "subjects" : type === "periods" ? "periods" : "constraints";
      await api(item ? `/${resource}/${item.id}` : `/${resource}`, { method: item ? "PATCH" : "POST", body: JSON.stringify(values) });
      modal.hidden = true;
      render();
    } catch (error) { alert(error.message); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
}
async function openQualificationForm(item = null) {
  const overview = window.pageOverview || await api("/catalog/overview");
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} нагрузку преподавателя`;
  const value = (field) => item?.[field] ?? item?.load?.[field] ?? (field === "language" ? "Русский" : 0);
  form.innerHTML = `<label><span>Преподаватель</span><select name="teacher_id" required>${overview.teachers.map((row) => `<option value="${row.id}" ${Number(item?.teacher_id) === row.id ? "selected" : ""}>${escapeHtml(row.full_name)}</option>`).join("")}</select></label><label><span>Предмет учебного плана</span><select name="curriculum_subject_id" required>${overview.curricula.map((row) => `<option value="${row.id}" ${Number(item?.curriculum_subject_id) === row.id ? "selected" : ""}>${escapeHtml(row.subject || "Предмет")} · ${row.hours} ч.</option>`).join("")}</select></label><label><span>Язык преподавания</span><select name="language">${["Русский", "Казахский", "Английский"].map((language) => `<option ${value("language") === language ? "selected" : ""}>${language}</option>`).join("")}</select></label>${["lecture_hours", "practice_hours", "lab_hours", "lecture_per_week", "practice_per_week", "lab_per_week"].map((field) => `<label><span>${labels[field] || field}</span><input name="${field}" type="number" min="0" value="${value(field)}"></label>`).join("")}<div id="qualification-form-status" class="status"></div><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">Сохранить</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    ["teacher_id", "curriculum_subject_id", "lecture_hours", "practice_hours", "lab_hours", "lecture_per_week", "practice_per_week", "lab_per_week"].forEach((key) => { values[key] = Number(values[key] || 0); });
    values.lecture_max_students = item?.lecture_max_students || 70;
    values.practice_max_students = item?.practice_max_students || null;
    values.lab_max_students = item?.lab_max_students || null;
    try {
      await api(item ? `/teacher-loads/${item.id}` : "/teacher-loads/", { method: item ? "PUT" : "POST", body: JSON.stringify(values) });
      modal.hidden = true; render();
    } catch (error) {
      const status = form.querySelector("#qualification-form-status");
      status.textContent = error.message;
      status.classList.add("status-error");
    }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
}
async function openCurriculumForm(item = null) {
  const overview = window.pageOverview || await api("/catalog/overview");
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  const modalContent = modal.querySelector(".lesson-modal-content");
  modalContent.classList.toggle("curriculum-modal-content", Boolean(item));
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} учебный план`;
  const subjectManager = item ? `<section class="curriculum-subject-manager"><div class="section-heading"><div><h3>Дисциплины учебного плана</h3><p>Добавляйте предметы, меняйте часы или удаляйте их из плана.</p></div></div><div class="management-table-wrap curriculum-subject-table"><table class="management-table"><thead><tr><th>Предмет</th><th>Часы</th><th>В неделю</th><th>Нагрузки</th><th>Действия</th></tr></thead><tbody id="curriculum-subject-list"><tr><td colspan="5">Загрузка...</td></tr></tbody></table></div><div class="curriculum-subject-editor"><h3 id="curriculum-subject-editor-title">Добавить дисциплину</h3><div class="curriculum-subject-fields"><label><span>Предмет</span><select name="cs_subject_id">${overview.subjects.map((row) => `<option value="${row.id}">${escapeHtml(row.code)} — ${escapeHtml(row.name)}</option>`).join("")}</select></label><label><span>Всего часов</span><input name="cs_hours" type="number" min="1" value="108"></label><label><span>Лекции, часов</span><input name="cs_lecture_hours" type="number" min="0" value="36"></label><label><span>Практика, часов</span><input name="cs_practice_hours" type="number" min="0" value="36"></label><label><span>Лабораторные, часов</span><input name="cs_lab_hours" type="number" min="0" value="36"></label><label><span>Лекций в неделю</span><input name="cs_lecture_per_week" type="number" min="0" value="2"></label><label><span>Практик в неделю</span><input name="cs_practice_per_week" type="number" min="0" value="2"></label><label><span>Лабораторных в неделю</span><input name="cs_lab_per_week" type="number" min="0" value="2"></label></div><div class="curriculum-subject-controls"><button id="cancel-curriculum-subject" class="secondary-button" type="button" hidden>Отменить изменение</button><button id="save-curriculum-subject" class="primary-button" type="button">Добавить дисциплину</button></div><div id="curriculum-subject-status" class="status"></div></div></section>` : `<div class="data-summary-note">После создания откройте учебный план повторно, чтобы добавить дисциплины.</div>`;
  form.innerHTML = `<div class="curriculum-plan-fields"><label><span>Специальность</span><select name="specialty_id" required>${overview.specialties.map((row) => `<option value="${row.id}" ${Number(item?.specialty_id) === row.id ? "selected" : ""}>${escapeHtml(row.code)} — ${escapeHtml(row.name)}</option>`).join("")}</select></label><label><span>Учебный период</span><select name="academic_period_id" required>${overview.periods.map((row) => `<option value="${row.id}" ${Number(item?.academic_period_id) === row.id ? "selected" : ""}>${escapeHtml(row.name)}</option>`).join("")}</select></label><label><span>Курс</span><input name="course" type="number" min="1" max="10" value="${item?.course || 1}" required></label><label><span>Семестр</span><input name="semester" type="number" min="1" max="2" value="${item?.semester || 1}" required></label><label><span>Учебный год</span><input name="academic_year" value="${escapeHtml(item?.academic_year || "")}" required></label></div>${subjectManager}<div id="curriculum-plan-status" class="status"></div><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Закрыть</button><button type="submit" class="primary-button">Сохранить параметры плана</button></div>`;

  let editingSubjectId = null;
  let editingSubject = null;
  let curriculumSubjects = [];
  const subjectStatus = form.querySelector("#curriculum-subject-status");
  const setSubjectStatus = (message, error = false) => {
    if (!subjectStatus) return;
    subjectStatus.textContent = message;
    subjectStatus.classList.toggle("status-error", error);
  };
  const resetSubjectEditor = () => {
    if (!item) return;
    editingSubjectId = null;
    editingSubject = null;
    form.elements.cs_hours.value = 108;
    form.elements.cs_lecture_hours.value = 36;
    form.elements.cs_practice_hours.value = 36;
    form.elements.cs_lab_hours.value = 36;
    form.elements.cs_lecture_per_week.value = 2;
    form.elements.cs_practice_per_week.value = 2;
    form.elements.cs_lab_per_week.value = 2;
    form.querySelector("#curriculum-subject-editor-title").textContent = "Добавить дисциплину";
    form.querySelector("#save-curriculum-subject").textContent = "Добавить дисциплину";
    form.querySelector("#cancel-curriculum-subject").hidden = true;
    setSubjectStatus("");
  };
  const fillSubjectEditor = (row) => {
    editingSubjectId = row.id;
    editingSubject = row;
    ["subject_id", "hours", "lecture_hours", "practice_hours", "lab_hours", "lecture_per_week", "practice_per_week", "lab_per_week"].forEach((key) => {
      form.elements[`cs_${key}`].value = row[key] ?? 0;
    });
    form.querySelector("#curriculum-subject-editor-title").textContent = `Изменить: ${row.subject}`;
    form.querySelector("#save-curriculum-subject").textContent = "Сохранить дисциплину";
    form.querySelector("#cancel-curriculum-subject").hidden = false;
    setSubjectStatus("");
  };
  const renderSubjectRows = () => {
    if (!item) return;
    const body = form.querySelector("#curriculum-subject-list");
    body.innerHTML = curriculumSubjects.length ? curriculumSubjects.map((row) => `<tr><td><strong>${escapeHtml(row.subject_code || "")}</strong> ${escapeHtml(row.subject || "")}</td><td>${row.hours} (${row.lecture_hours}/${row.practice_hours}/${row.lab_hours})</td><td>${row.lecture_per_week}/${row.practice_per_week}/${row.lab_per_week}</td><td>${row.teacher_loads_count}</td><td class="management-actions"><button class="small-button" type="button" data-curriculum-subject-edit="${row.id}">Изменить</button><button class="small-button" type="button" data-curriculum-subject-delete="${row.id}">Удалить</button></td></tr>`).join("") : '<tr><td colspan="5">В учебном плане пока нет дисциплин.</td></tr>';
  };
  const reloadSubjects = async () => {
    if (!item) return;
    const result = await api(`/curricula/${item.id}/subjects`);
    curriculumSubjects = result.subjects;
    renderSubjectRows();
  };

  if (item) {
    await reloadSubjects();
    form.querySelector("#cancel-curriculum-subject").onclick = resetSubjectEditor;
    form.querySelector("#save-curriculum-subject").onclick = async () => {
      const numeric = (name) => Number(form.elements[`cs_${name}`].value || 0);
      const payload = {
        subject_id: numeric("subject_id"), hours: numeric("hours"),
        lecture_hours: numeric("lecture_hours"), practice_hours: numeric("practice_hours"), lab_hours: numeric("lab_hours"),
        lecture_per_week: numeric("lecture_per_week"), practice_per_week: numeric("practice_per_week"), lab_per_week: numeric("lab_per_week"),
        lecture_max_students: editingSubject?.lecture_max_students || 70,
        practice_max_students: editingSubject?.practice_max_students || null,
        lab_max_students: editingSubject?.lab_max_students || null,
      };
      try {
        await api(editingSubjectId ? `/curricula/${item.id}/subjects/${editingSubjectId}` : `/curricula/${item.id}/subjects`, { method: editingSubjectId ? "PATCH" : "POST", body: JSON.stringify(payload) });
        await reloadSubjects(); resetSubjectEditor(); setSubjectStatus("Список дисциплин обновлён.");
      } catch (error) { setSubjectStatus(error.message, true); }
    };
    form.querySelector("#curriculum-subject-list").onclick = async (event) => {
      const editButton = event.target.closest("[data-curriculum-subject-edit]");
      if (editButton) return fillSubjectEditor(curriculumSubjects.find((row) => row.id === Number(editButton.dataset.curriculumSubjectEdit)));
      const deleteButton = event.target.closest("[data-curriculum-subject-delete]");
      if (!deleteButton) return;
      if (deleteButton.dataset.confirmed !== "true") {
        deleteButton.dataset.confirmed = "true";
        deleteButton.textContent = "Подтвердить";
        setSubjectStatus("Нажмите «Подтвердить» ещё раз для удаления дисциплины из плана.");
        return;
      }
      try {
        await api(`/curricula/${item.id}/subjects/${deleteButton.dataset.curriculumSubjectDelete}`, { method: "DELETE" });
        await reloadSubjects(); resetSubjectEditor(); setSubjectStatus("Дисциплина удалена из учебного плана.");
      } catch (error) { setSubjectStatus(error.message, true); }
    };
  }
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = { specialty_id: Number(form.elements.specialty_id.value), academic_period_id: Number(form.elements.academic_period_id.value), course: Number(form.elements.course.value), semester: Number(form.elements.semester.value), academic_year: form.elements.academic_year.value };
    const planStatus = form.querySelector("#curriculum-plan-status");
    try { await api(item ? `/curricula/${item.id}` : "/curricula", { method: item ? "PATCH" : "POST", body: JSON.stringify(values) }); modal.hidden = true; modalContent.classList.remove("curriculum-modal-content"); render(); } catch (error) { planStatus.textContent = error.message; planStatus.classList.add("status-error"); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; modalContent.classList.remove("curriculum-modal-content"); }; });
  modal.hidden = false;
}
async function openStreamForm(item = null) {
  const overview = window.pageOverview || await api("/catalog/overview");
  const modal = document.querySelector("#record-modal");
  const form = document.querySelector("#record-form");
  document.querySelector("#record-modal-title").textContent = `${item ? "Изменить" : "Добавить"} лекционный поток`;
  const selected = new Set((item?.group_ids || []).map(String));
  form.innerHTML = `<label><span>Название</span><input name="name" required value="${escapeHtml(item?.name || "")}"></label><label><span>Специальность</span><select name="specialty_id" required>${overview.specialties.map((row) => `<option value="${row.id}" ${Number(item?.specialty_id) === row.id ? "selected" : ""}>${escapeHtml(row.code)}</option>`).join("")}</select></label><label><span>Учебный период</span><select name="academic_period_id" required>${overview.periods.map((row) => `<option value="${row.id}" ${Number(item?.academic_period_id) === row.id ? "selected" : ""}>${escapeHtml(row.name)}</option>`).join("")}</select></label><fieldset class="checkbox-fieldset"><legend>Группы потока</legend><div class="checkbox-grid">${overview.groups.map((row) => `<label class="checkbox-option"><input type="checkbox" name="group_ids" value="${row.id}" ${selected.has(String(row.id)) ? "checked" : ""}><span>${escapeHtml(row.name)}</span></label>`).join("")}</div></fieldset><div class="entity-form-actions"><button type="button" class="secondary-button" data-close-record>Отмена</button><button type="submit" class="primary-button">Сохранить</button></div>`;
  form.onsubmit = async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form).entries());
    values.specialty_id = Number(values.specialty_id); values.academic_period_id = Number(values.academic_period_id); values.group_ids = [...form.querySelectorAll("input[name='group_ids']:checked")].map((option) => Number(option.value));
    try { await api(item ? `/lecture-streams/${item.id}` : "/lecture-streams", { method: item ? "PATCH" : "POST", body: JSON.stringify(values) }); modal.hidden = true; render(); } catch (error) { alert(error.message); }
  };
  modal.querySelectorAll("[data-close-record]").forEach((button) => { button.onclick = () => { modal.hidden = true; }; });
  modal.hidden = false;
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
  if (button.dataset.action === "edit") {
    if (page === "groups") return editGroup(id);
    if (page === "classrooms") return editClassroom(id);
    if (page === "teachers") return openTeacherForm((window.pageOverview?.teachers || []).find((item) => item.id === id));
    if (page === "qualifications") return openQualificationForm((window.pageRows || []).find((item) => item.id === id));
    if (page === "curricula") return openCurriculumForm((window.pageRows || []).find((item) => item.id === id));
    if (page === "streams") return openStreamForm((window.pageRows || []).find((item) => item.id === id));
    return openSimpleForm(page, (window.pageRows || []).find((item) => item.id === id));
  }
  if (button.dataset.confirmed !== "true") {
    button.dataset.confirmed = "true";
    button.textContent = "Подтвердить";
    const status = document.querySelector("#page-count");
    if (status) status.textContent = "Нажмите «Подтвердить» ещё раз для удаления записи.";
    return;
  }
  const resource = page === "groups" ? "groups" : page === "qualifications" ? "teacher-loads" : page === "streams" ? "lecture-streams" : page;
  try {
    const deletePath = page === "qualifications" && button.dataset.removeAssignments === "true"
      ? `/teacher-loads/${id}/with-assignments`
      : `/${resource}/${id}`;
    await api(deletePath, { method: "DELETE" });
    render();
  } catch (error) {
    if (page === "qualifications" && error.message.includes("remove_assignments=true")) {
      button.dataset.confirmed = "true";
      button.dataset.removeAssignments = "true";
      button.textContent = "Удалить занятия и нагрузку";
      const status = document.querySelector("#page-count");
      if (status) status.textContent = "Внимание: повторное нажатие удалит назначения преподавателя и связанные пары из сохранённых расписаний. После этого расписание нужно сгенерировать заново.";
      return;
    }
    button.dataset.confirmed = "false";
    button.textContent = "Удалить";
    const status = document.querySelector("#page-count");
    if (status) status.textContent = error.message;
  }
}
async function render() {
  if (page !== "settings" && !localStorage.getItem(tokenKey)) { location.href = "login.html"; return; }
  shell();
  const root = document.querySelector("#page-content");
  if (page === "dashboard") { const data = await api("/catalog/overview"); const versions = await api("/schedules/versions"); renderDashboard(data, versions, root); return; }
  if (page === "analytics") { const data = await api("/catalog/overview"); renderDashboard(data, { versions: [] }, root); return; }
  if (page === "generation") {
    const data = await api("/catalog/overview");
    root.innerHTML = `<section class="generation-card"><div class="generation-controls"><label>Учебный период<select id="generation-period">${data.periods.map((period) => `<option value="${period.id}">${escapeHtml(period.name)}</option>`).join("")}</select></label><div class="generation-actions"><button id="diagnose-button" class="secondary-button" type="button">Проверить готовность</button><button id="generate-page-button" class="primary-button" type="button">Запустить генерацию</button></div></div><div id="diagnose-result" class="diagnostics-grid"><div class="diagnostic-card"><span>Группы</span><strong>${data.groups.length}</strong></div><div class="diagnostic-card"><span>Преподаватели</span><strong>${data.teachers.length}</strong></div><div class="diagnostic-card"><span>Аудитории</span><strong>${data.classrooms.length}</strong></div><div class="diagnostic-card"><span>Предметы</span><strong>${data.subjects.length}</strong></div><div class="diagnostic-card"><span>Временные слоты</span><strong>${data.time_slots.length}</strong></div></div><div class="generation-progress" hidden><i></i></div><div id="generation-status" class="status">Перед запуском проверьте входные данные.</div></section>`;
    const period = () => document.querySelector("#generation-period").value;
    document.querySelector("#diagnose-button").addEventListener("click", async () => { const result = await api(`/schedules/diagnostics/${period()}`); document.querySelector("#generation-status").textContent = result.valid ? `Данные готовы: ${result.lessons_count} занятий можно запланировать.` : result.error || "Есть проблемы во входных данных."; document.querySelector("#generation-status").classList.toggle("status-error", !result.valid); });
    document.querySelector("#generate-page-button").addEventListener("click", async (event) => { const button = event.currentTarget; button.disabled = true; const status = document.querySelector("#generation-status"); const progress = document.querySelector(".generation-progress"); progress.hidden = false; try { const response = await api("/schedules/generate", { method: "POST", body: JSON.stringify({ academic_period_id: Number(period()) }) }); status.textContent = "Генерация выполняется..."; for (;;) { const result = await api(`/schedules/generation/${response.job.job_id}`); if (result.job.status === "generated") { progress.querySelector("i").style.width = "100%"; status.innerHTML = `Генерация завершена. Версия №${result.job.version_id}. <a href="occupancy.html?version_id=${result.job.version_id}">Открыть схему аудиторий</a>`; break; } if (result.job.status === "failed") throw new Error(result.job.error || "Генерация завершилась ошибкой."); progress.querySelector("i").style.width = "60%"; await new Promise((resolve) => setTimeout(resolve, 1200)); } } catch (error) { status.textContent = error.message; status.classList.add("status-error"); } finally { button.disabled = false; } });
    return;
  }
  if (page === "occupancy") { const versionId = new URLSearchParams(location.search).get("version_id"); const data = await api(`/schedules/classroom-map${versionId ? `?version_id=${encodeURIComponent(versionId)}` : ""}`); renderOccupancy(data, root); return; }
  if (page === "versions") { const data = await api("/schedules/versions"); renderVersions(data.versions, root); return; }
  if (page === "availability") { const data = await api("/catalog/overview"); renderTable(data.time_slots.map((slot) => ({ day: ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"][slot.day_of_week], lesson_number: slot.lesson_number, start_time: slot.start_time, end_time: slot.end_time, is_active: slot.is_active ? "Доступен" : "Недоступен" })), "availability"); return; }
  if (page === "groups") { const data = await api("/catalog/overview"); window.pageOverview = data; const students = await api("/groups/students"); renderTable(data.groups, page); const rootContent = document.querySelector("#page-content"); const totalStudents = students.students.length; rootContent.insertAdjacentHTML("afterbegin", `<div class="diagnostics-grid groups-summary"><div class="diagnostic-card ok"><span>Всего групп</span><strong>${data.groups.length}</strong></div><div class="diagnostic-card ok"><span>Всего студентов</span><strong>${totalStudents}</strong></div><div class="diagnostic-card ok"><span>Максимум в группе</span><strong>25</strong></div></div>`); const old = document.querySelector("#page-content"); const studentPanel = document.createElement("section"); studentPanel.className = "students-panel"; studentPanel.innerHTML = `<div class="section-heading"><div><h2>Студенты</h2><p>Состав групп и назначенные потоки</p></div><button id="add-student" class="primary-button section-add-button" type="button">Добавить студента</button></div>`; old.appendChild(studentPanel); renderStudentsTable(students.students); document.querySelector("#add-record").addEventListener("click", addGroup); document.querySelector("#add-student").addEventListener("click", addStudent); old.addEventListener("click", handleActions); studentPanel.addEventListener("click", async (event) => { const button = event.target.closest("[data-student-action]"); if (!button) return; const id = Number(button.dataset.id); if (button.dataset.studentAction === "edit") return editStudent(id); if (confirm("Удалить студента?")) { await api(`/groups/students/${id}`, { method: "DELETE" }); render(); } }); return; }
  if (page === "teachers") {
    const data = await api("/catalog/overview");
    window.pageOverview = data;
    renderTable(data.teachers, page);
    document.querySelector("#add-record").addEventListener("click", () => openTeacherForm());
    document.querySelector("#page-content").addEventListener("click", async (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) return;
      const item = data.teachers.find((teacher) => teacher.id === Number(button.dataset.id));
      if (button.dataset.action === "edit") return openTeacherForm(item);
      if (button.dataset.action === "delete" && confirm("Удалить преподавателя?")) {
        await api(`/teachers/${button.dataset.id}`, { method: "DELETE" });
        render();
      }
    });
    return;
  }
  if (page === "settings") { root.innerHTML = `<section class="settings-card"><div class="detail-kicker">ВНЕШНИЙ ВИД</div><h2>Тема интерфейса</h2><p>Настройка сохраняется локально и применяется ко всем страницам приложения.</p><div class="theme-options">${[["light", "Светлая"], ["dark", "Тёмная"], ["system", "Системная"]].map(([value, label]) => `<label class="theme-option"><input type="radio" name="theme" value="${value}" ${selectedTheme === value ? "checked" : ""}><span>${label}</span></label>`).join("")}</div></section>`; root.querySelectorAll("[name='theme']").forEach((input) => input.addEventListener("change", () => { localStorage.setItem("smart_schedule_theme", input.value); document.documentElement.dataset.theme = input.value === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : input.value === "system" ? "light" : input.value; })); return; }
  if (page === "profile") { const user = await api("/auth/me"); root.innerHTML = `<section class="profile-card"><div class="detail-kicker">ЛИЧНЫЙ ПРОФИЛЬ</div><h2>${escapeHtml(user.full_name)}</h2><p>Изменение логина, пароля и изображения профиля.</p><label class="avatar-upload">Аватар<input id="profile-avatar" type="file" accept="image/png,image/jpeg,image/webp"></label><form id="profile-update-form" class="profile-form"><label>Логин<input name="username" value="${escapeHtml(user.username)}" required></label><label>Имя<input name="full_name" value="${escapeHtml(user.full_name)}" required></label><label>Текущий пароль<input name="current_password" type="password" required></label><label>Новый пароль<input name="new_password" type="password" minlength="4"></label><button class="primary-button" type="submit">Сохранить изменения</button><div id="profile-update-status" class="status"></div></form></section>`; root.querySelector("#profile-avatar").addEventListener("change", (event) => { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => { localStorage.setItem("smart_schedule_avatar", String(reader.result)); render(); }; reader.readAsDataURL(file); }); root.querySelector("#profile-update-form").addEventListener("submit", async (event) => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget).entries()); try { const result = await api("/auth/profile", { method: "PUT", body: JSON.stringify(values) }); localStorage.setItem(tokenKey, result.access_token); root.querySelector("#profile-update-status").textContent = result.message; } catch (error) { root.querySelector("#profile-update-status").textContent = error.message; root.querySelector("#profile-update-status").classList.add("status-error"); } }); return; }
  if (page === "qualifications") {
    const data = await api("/catalog/overview");
    window.pageOverview = data;
    window.pageRows = data.qualifications || [];
    renderTable(window.pageRows, "qualifications");
    document.querySelector("#add-record").addEventListener("click", () => openQualificationForm());
    document.querySelector("#page-content").addEventListener("click", handleActions);
    return;
  }
  const data = await api("/catalog/overview"); window.pageOverview = data; const rows = data[configs[page][2]] || []; window.pageRows = rows; renderTable(rows, configs[page][2]); if (["groups", "classrooms", "teachers", "subjects", "periods", "constraints", "qualifications", "curricula", "streams"].includes(page)) { document.querySelector("#add-record").addEventListener("click", () => page === "groups" ? addGroup() : page === "classrooms" ? addClassroom() : page === "teachers" ? openTeacherForm() : page === "qualifications" ? openQualificationForm() : page === "curricula" ? openCurriculumForm() : page === "streams" ? openStreamForm() : openSimpleForm(page)); document.querySelector("#page-content").addEventListener("click", handleActions); }
}
const selectedTheme = localStorage.getItem("smart_schedule_theme") || "light";
document.documentElement.dataset.theme = selectedTheme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : selectedTheme === "system" ? "light" : selectedTheme;
render().catch((error) => { document.querySelector("#page-content").innerHTML = `<div class="empty-panel status-error">${escapeHtml(error.message)}</div>`; });
