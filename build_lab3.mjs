import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const INPUT = "input_lab2.xlsx";
const OUTPUT_DIR = path.join("outputs", "lab3_variant54");
const OUTPUT = path.join(OUTPUT_DIR, "Лабораторная_работа_3_вариант_54.xlsx");
const PREVIEW_DIR = path.join(OUTPUT_DIR, "previews");
const FONT = "Arial";
const NAVY = "#1F4E78";
const BLUE = "#D9EAF7";
const PALE = "#F3F6F9";
const BORDER = "#D9D9D9";
const TEXT = "#1F2937";
const MUTED = "#5B6573";
const SOURCE = "'Исходные данные'";
const DATA_LAST = 62;

await fs.mkdir(OUTPUT_DIR, { recursive: true });
await fs.mkdir(PREVIEW_DIR, { recursive: true });

const bytes = await fs.readFile(INPUT);
const workbook = await SpreadsheetFile.importXlsx(new FileBlob(bytes));
const source = workbook.worksheets.getItem("Исходные данные");

// В исходной книге часть формул с кириллическим именем листа была записана
// без кавычек. Excel это принимает, а встроенный движок — нет. Нормализуем
// только затронутые формулы, не меняя их расчётную логику.
const analysis = workbook.worksheets.getItem("Анализ");
for (const address of ["B5:B8", "B15:D20", "G15:G20", "B24:D26"]) {
  const range = analysis.getRange(address);
  const formulas = range.formulas.map((row) => row.map((formula) =>
    typeof formula === "string" ? formula.replaceAll("Обработка!", "'Обработка'!") : formula
  ));
  range.formulas = formulas;
}

// Исправляем вычисление категории риска так, чтобы оно корректно считалось
// и в Excel, и во встроенном движке пересчёта.
source.getRange("G3").formulas = [[
  '=IF(OR(E3>=70,D3>=5),"Высокая",IF(OR(E3>=40,D3>=2.5),"Средняя","Низкая"))',
]];
source.getRange(`G3:G${DATA_LAST}`).fillDown();
source.freezePanes.freezeRows(2);
source.showGridLines = false;

const sourceValues = source.getRange(`A3:G${DATA_LAST}`).values;
const rows = sourceValues.map((r) => ({
  id: r[0],
  district: r[1],
  type: r[2],
  vibration: Number(r[3]),
  wear: Number(r[4]),
  org: r[5],
  risk: Number(r[4]) >= 70 || Number(r[3]) >= 5
    ? "Высокая"
    : (Number(r[4]) >= 40 || Number(r[3]) >= 2.5 ? "Средняя" : "Низкая"),
}));

const unique = (field) => [...new Set(rows.map((r) => r[field]))].sort((a, b) =>
  String(a).localeCompare(String(b), "ru")
);
const districts = unique("district");
const types = unique("type");
const orgs = unique("org");
const risks = ["Высокая", "Средняя", "Низкая"];

function q(text) {
  return String(text).replaceAll('"', '""');
}

function setBase(sheet, title, subtitle) {
  sheet.showGridLines = false;
  sheet.tabColor = NAVY;
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format.font = { name: FONT, size: 14, bold: true, color: "#000000" };
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange("A3").format.font = { name: FONT, size: 10, italic: true, color: MUTED };
  sheet.getRange("A2:N40").format.font = { name: FONT, size: 10, color: TEXT };
  sheet.getRange("A2").format.font = { name: FONT, size: 14, bold: true, color: "#000000" };
  sheet.getRange("A3").format.font = { name: FONT, size: 10, italic: true, color: MUTED };
}

function styleTable(sheet, rangeAddress, headerAddress, totalAddress = null) {
  const whole = sheet.getRange(rangeAddress);
  whole.format.verticalAlignment = "center";
  whole.format.borders = { preset: "all", style: "thin", color: BORDER };
  const header = sheet.getRange(headerAddress);
  header.format = {
    fill: NAVY,
    font: { name: FONT, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: BORDER },
  };
  if (totalAddress) {
    const total = sheet.getRange(totalAddress);
    total.format.fill = BLUE;
    total.format.font = { name: FONT, size: 10, bold: true, color: TEXT };
  }
}

function bandRows(sheet, startRow, endRow, startCol, endCol) {
  for (let r = startRow; r <= endRow; r += 1) {
    if ((r - startRow) % 2 === 1) {
      sheet.getRangeByIndexes(r - 1, startCol - 1, 1, endCol - startCol + 1).format.fill = PALE;
    }
  }
}

function addBarChart(sheet, rangeAddress, title, endRow, endCol = "N") {
  const chart = sheet.charts.add("bar", sheet.getRange(rangeAddress));
  chart.title = title;
  chart.titleTextStyle.typeface = FONT;
  chart.titleTextStyle.fontSize = 12;
  chart.legend = { position: "bottom", textStyle: { typeface: FONT, fontSize: 10 } };
  chart.xAxis = { axisType: "textAxis", textStyle: { typeface: FONT, fontSize: 10 } };
  chart.yAxis = { numberFormatCode: "0", numberFormatSourceLinked: false, textStyle: { typeface: FONT, fontSize: 10 } };
  chart.setPosition("G5", `${endCol}${endRow}`);
}

function addSheet(name, title, subtitle) {
  const sheet = workbook.worksheets.add(name);
  setBase(sheet, title, subtitle);
  return sheet;
}

// 1. Распределение по категориям риска.
{
  const s = addSheet("1 Риск", "Сводная таблица 1. Распределение по категориям риска", "Количество объектов, доля и средние показатели по каждой категории риска.");
  s.getRange("A5:E5").values = [["Категория риска", "Количество объектов", "Доля", "Средняя вибрация, мм/с", "Средний индекс износа, %"]];
  risks.forEach((risk, i) => {
    const r = 6 + i;
    s.getRange(`A${r}`).values = [[risk]];
    s.getRange(`B${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`C${r}`).formulas = [[`=B${r}/COUNTA(${SOURCE}!$A$3:$A$${DATA_LAST})`]];
    s.getRange(`D${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$D$3:$D$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`E${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$E$3:$E$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
  });
  s.getRange("A9:E9").values = [["Итого", null, null, null, null]];
  s.getRange("B9").formulas = [["=SUM(B6:B8)"]];
  s.getRange("C9").formulas = [["=SUM(C6:C8)"]];
  s.getRange("D9").formulas = [[`=AVERAGE(${SOURCE}!$D$3:$D$${DATA_LAST})`]];
  s.getRange("E9").formulas = [[`=AVERAGE(${SOURCE}!$E$3:$E$${DATA_LAST})`]];
  styleTable(s, "A5:E9", "A5:E5", "A9:E9");
  bandRows(s, 6, 8, 1, 5);
  s.getRange("B6:B9").format.numberFormat = "0";
  s.getRange("C6:C9").format.numberFormat = "0.0%";
  s.getRange("D6:E9").format.numberFormat = "0.00";
  s.getRange("A:A").format.columnWidth = 22;
  s.getRange("B:E").format.columnWidth = 17;
  s.getRange("A5:E9").format.autofitRows();
  addBarChart(s, "A5:B8", "Количество объектов по категориям риска", 19);
  s.freezePanes.freezeRows(5);
}

// 2–4. Одномерные группировки по району, типу и организации.
function buildSingleDimension({ name, title, subtitle, labels, sourceColumn, firstHeader, chartTitle }) {
  const s = addSheet(name, title, subtitle);
  s.getRange("A5:F5").values = [[firstHeader, "Количество объектов", "Средняя вибрация, мм/с", "Средний индекс износа, %", "Высокий риск, объектов", "Доля высокого риска"]];
  labels.forEach((label, i) => {
    const r = 6 + i;
    s.getRange(`A${r}`).values = [[label]];
    s.getRange(`B${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},A${r})`]];
    s.getRange(`C${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$D$3:$D$${DATA_LAST},${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},A${r})`]];
    s.getRange(`D${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$E$3:$E$${DATA_LAST},${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},A${r})`]];
    s.getRange(`E${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},A${r},${SOURCE}!$G$3:$G$${DATA_LAST},"Высокая")`]];
    s.getRange(`F${r}`).formulas = [[`=IF(B${r}=0,"",E${r}/B${r})`]];
  });
  const tr = 6 + labels.length;
  s.getRange(`A${tr}:F${tr}`).values = [["Итого", null, null, null, null, null]];
  s.getRange(`B${tr}`).formulas = [[`=SUM(B6:B${tr - 1})`]];
  s.getRange(`C${tr}`).formulas = [[`=AVERAGE(${SOURCE}!$D$3:$D$${DATA_LAST})`]];
  s.getRange(`D${tr}`).formulas = [[`=AVERAGE(${SOURCE}!$E$3:$E$${DATA_LAST})`]];
  s.getRange(`E${tr}`).formulas = [[`=SUM(E6:E${tr - 1})`]];
  s.getRange(`F${tr}`).formulas = [[`=E${tr}/B${tr}`]];
  styleTable(s, `A5:F${tr}`, "A5:F5", `A${tr}:F${tr}`);
  bandRows(s, 6, tr - 1, 1, 6);
  s.getRange(`B6:B${tr}`).format.numberFormat = "0";
  s.getRange(`C6:D${tr}`).format.numberFormat = "0.00";
  s.getRange(`E6:E${tr}`).format.numberFormat = "0";
  s.getRange(`F6:F${tr}`).format.numberFormat = "0.0%";
  s.getRange("A:A").format.columnWidth = firstHeader === "Тип конструкции" ? 34 : 25;
  s.getRange("B:F").format.columnWidth = 17;
  s.getRange(`A5:F${tr}`).format.autofitRows();
  addBarChart(s, `A5:B${tr - 1}`, chartTitle, Math.max(19, tr + 6));
  s.freezePanes.freezeRows(5);
}

buildSingleDimension({
  name: "2 Районы",
  title: "Сводная таблица 2. Показатели по районам",
  subtitle: "Сопоставление количества объектов, средних показателей и высокого риска по районам.",
  labels: districts,
  sourceColumn: "B",
  firstHeader: "Район",
  chartTitle: "Количество объектов по районам",
});
buildSingleDimension({
  name: "3 Конструкции",
  title: "Сводная таблица 3. Показатели по типам конструкций",
  subtitle: "Сравнение типов конструкций по числу объектов, вибрации, износу и доле высокого риска.",
  labels: types,
  sourceColumn: "C",
  firstHeader: "Тип конструкции",
  chartTitle: "Количество объектов по типам конструкций",
});
buildSingleDimension({
  name: "4 Организации",
  title: "Сводная таблица 4. Показатели по обслуживающим организациям",
  subtitle: "Нагрузка и состояние объектов в разрезе обслуживающих организаций.",
  labels: orgs,
  sourceColumn: "F",
  firstHeader: "Организация",
  chartTitle: "Количество объектов по организациям",
});

// 5–7. Матрицы измерение × категория риска.
function buildRiskMatrix({ name, title, subtitle, labels, sourceColumn, firstHeader }) {
  const s = addSheet(name, title, subtitle);
  s.getRange("A5:E5").values = [[firstHeader, ...risks, "Итого"]];
  labels.forEach((label, i) => {
    const r = 6 + i;
    s.getRange(`A${r}`).values = [[label]];
    risks.forEach((risk, j) => {
      const col = String.fromCharCode("B".charCodeAt(0) + j);
      s.getRange(`${col}${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},$A${r},${SOURCE}!$G$3:$G$${DATA_LAST},${col}$5)`]];
    });
    s.getRange(`E${r}`).formulas = [[`=SUM(B${r}:D${r})`]];
  });
  const tr = 6 + labels.length;
  s.getRange(`A${tr}:E${tr}`).values = [["Итого", null, null, null, null]];
  s.getRange(`B${tr}`).formulas = [[`=SUM(B6:B${tr - 1})`]];
  s.getRange(`C${tr}`).formulas = [[`=SUM(C6:C${tr - 1})`]];
  s.getRange(`D${tr}`).formulas = [[`=SUM(D6:D${tr - 1})`]];
  s.getRange(`E${tr}`).formulas = [[`=SUM(E6:E${tr - 1})`]];
  styleTable(s, `A5:E${tr}`, "A5:E5", `A${tr}:E${tr}`);
  bandRows(s, 6, tr - 1, 1, 5);
  s.getRange(`B6:E${tr}`).format.numberFormat = "0";
  s.getRange("A:A").format.columnWidth = firstHeader === "Тип конструкции" ? 34 : 25;
  s.getRange("B:E").format.columnWidth = 14;
  s.getRange(`A5:E${tr}`).format.autofitRows();
  s.getRange(`B6:D${tr - 1}`).conditionalFormats.add("colorScale", {
    colors: ["#FFFFFF", "#F7C7A6", "#C00000"],
    thresholds: ["min", { type: "percentile", value: 50 }, "max"],
  });
  s.freezePanes.freezeRows(5);
}

buildRiskMatrix({ name: "5 Район и риск", title: "Сводная таблица 5. Район и категория риска", subtitle: "Количество объектов каждой категории риска в каждом районе.", labels: districts, sourceColumn: "B", firstHeader: "Район" });
buildRiskMatrix({ name: "6 Тип и риск", title: "Сводная таблица 6. Тип конструкции и категория риска", subtitle: "Распределение категорий риска по типам конструкций.", labels: types, sourceColumn: "C", firstHeader: "Тип конструкции" });
buildRiskMatrix({ name: "7 Организация и риск", title: "Сводная таблица 7. Организация и категория риска", subtitle: "Распределение категорий риска по обслуживающим организациям.", labels: orgs, sourceColumn: "F", firstHeader: "Организация" });

// 8–9. Матрицы измерение × организация.
function buildOrgMatrix({ name, title, subtitle, labels, sourceColumn, firstHeader }) {
  const s = addSheet(name, title, subtitle);
  s.getRangeByIndexes(4, 0, 1, orgs.length + 2).values = [[firstHeader, ...orgs, "Итого"]];
  labels.forEach((label, i) => {
    const r = 6 + i;
    s.getRange(`A${r}`).values = [[label]];
    orgs.forEach((org, j) => {
      const col = String.fromCharCode("B".charCodeAt(0) + j);
      s.getRange(`${col}${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$${sourceColumn}$3:$${sourceColumn}$${DATA_LAST},$A${r},${SOURCE}!$F$3:$F$${DATA_LAST},${col}$5)`]];
    });
    const totalCol = String.fromCharCode("B".charCodeAt(0) + orgs.length);
    const lastOrgCol = String.fromCharCode("A".charCodeAt(0) + orgs.length);
    s.getRange(`${totalCol}${r}`).formulas = [[`=SUM(B${r}:${lastOrgCol}${r})`]];
  });
  const tr = 6 + labels.length;
  const totalCol = String.fromCharCode("B".charCodeAt(0) + orgs.length);
  s.getRangeByIndexes(tr - 1, 0, 1, orgs.length + 2).values = [["Итого", ...Array(orgs.length + 1).fill(null)]];
  for (let j = 0; j < orgs.length + 1; j += 1) {
    const col = String.fromCharCode("B".charCodeAt(0) + j);
    s.getRange(`${col}${tr}`).formulas = [[`=SUM(${col}6:${col}${tr - 1})`]];
  }
  styleTable(s, `A5:${totalCol}${tr}`, `A5:${totalCol}5`, `A${tr}:${totalCol}${tr}`);
  bandRows(s, 6, tr - 1, 1, orgs.length + 2);
  s.getRange(`B6:${totalCol}${tr}`).format.numberFormat = "0";
  s.getRange("A:A").format.columnWidth = firstHeader === "Тип конструкции" ? 34 : 25;
  s.getRange(`B:${totalCol}`).format.columnWidth = 22;
  s.getRange(`A5:${totalCol}${tr}`).format.autofitRows();
  s.getRange(`B6:${String.fromCharCode(totalCol.charCodeAt(0) - 1)}${tr - 1}`).conditionalFormats.add("colorScale", {
    colors: ["#FFFFFF", "#D9EAF7", "#2F75B5"],
    thresholds: ["min", { type: "percentile", value: 50 }, "max"],
  });
  s.freezePanes.freezeRows(5);
}

buildOrgMatrix({ name: "8 Район и организация", title: "Сводная таблица 8. Район и обслуживающая организация", subtitle: "Количество объектов каждой организации по районам.", labels: districts, sourceColumn: "B", firstHeader: "Район" });
buildOrgMatrix({ name: "9 Тип и организация", title: "Сводная таблица 9. Тип конструкции и обслуживающая организация", subtitle: "Количество объектов каждой организации по типам конструкций.", labels: types, sourceColumn: "C", firstHeader: "Тип конструкции" });

// 10. Расширенная статистика по категориям риска.
{
  const s = addSheet("10 Метрики риска", "Сводная таблица 10. Статистические показатели по категориям риска", "Средние, минимальные и максимальные значения вибрации и индекса износа.");
  s.getRange("A5:H5").values = [["Категория риска", "Количество", "Средняя вибрация", "Минимальная вибрация", "Максимальная вибрация", "Средний износ", "Минимальный износ", "Максимальный износ"]];
  risks.forEach((risk, i) => {
    const r = 6 + i;
    s.getRange(`A${r}`).values = [[risk]];
    s.getRange(`B${r}`).formulas = [[`=COUNTIFS(${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`C${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$D$3:$D$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`D${r}`).formulas = [[`=MINIFS(${SOURCE}!$D$3:$D$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`E${r}`).formulas = [[`=MAXIFS(${SOURCE}!$D$3:$D$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`F${r}`).formulas = [[`=AVERAGEIFS(${SOURCE}!$E$3:$E$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`G${r}`).formulas = [[`=MINIFS(${SOURCE}!$E$3:$E$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
    s.getRange(`H${r}`).formulas = [[`=MAXIFS(${SOURCE}!$E$3:$E$${DATA_LAST},${SOURCE}!$G$3:$G$${DATA_LAST},A${r})`]];
  });
  styleTable(s, "A5:H8", "A5:H5");
  bandRows(s, 6, 8, 1, 8);
  s.getRange("B6:B8").format.numberFormat = "0";
  s.getRange("C6:H8").format.numberFormat = "0.00";
  s.getRange("A:A").format.columnWidth = 21;
  s.getRange("B:H").format.columnWidth = 17;
  s.getRange("A5:H8").format.autofitRows();
  addBarChart(s, "A5:B8", "Количество объектов по категориям риска", 19, "O");
  s.freezePanes.freezeRows(5);
}

// Итоговый лист лабораторной работы.
{
  const s = addSheet("ЛР3 Итоги", "Лабораторная работа 3. Анализ данных варианта 54", "Мониторинг состояния мостов и путепроводов. В книге построено 10 динамических сводных таблиц по 60 объектам.");
  s.tabColor = "#17365D";
  s.getRange("A5:D5").values = [["Показатель", "Значение", "Единица", "Комментарий"]];
  s.getRange("A6:D9").values = [
    ["Объектов в выборке", null, "объектов", "Исходные данные варианта 54"],
    ["Объектов высокого риска", null, "объектов", "По учебному правилу классификации"],
    ["Средний уровень вибрации", null, "мм/с", "По всем объектам"],
    ["Средний индекс износа", null, "%", "По всем объектам"],
  ];
  s.getRange("B6").formulas = [[`=COUNTA(${SOURCE}!$A$3:$A$${DATA_LAST})`]];
  s.getRange("B7").formulas = [[`=COUNTIFS(${SOURCE}!$G$3:$G$${DATA_LAST},"Высокая")`]];
  s.getRange("B8").formulas = [[`=AVERAGE(${SOURCE}!$D$3:$D$${DATA_LAST})`]];
  s.getRange("B9").formulas = [[`=AVERAGE(${SOURCE}!$E$3:$E$${DATA_LAST})`]];
  styleTable(s, "A5:D9", "A5:D5");
  bandRows(s, 6, 9, 1, 4);
  s.getRange("B6:B7").format.numberFormat = "0";
  s.getRange("B8:B9").format.numberFormat = "0.00";

  s.getRange("A12:C12").values = [["№", "Лист", "Содержание анализа"]];
  const descriptions = [
    [1, "1 Риск", "Распределение объектов по категориям риска"],
    [2, "2 Районы", "Показатели и высокий риск по районам"],
    [3, "3 Конструкции", "Показатели по типам конструкций"],
    [4, "4 Организации", "Показатели по обслуживающим организациям"],
    [5, "5 Район и риск", "Матрица район × категория риска"],
    [6, "6 Тип и риск", "Матрица тип конструкции × категория риска"],
    [7, "7 Организация и риск", "Матрица организация × категория риска"],
    [8, "8 Район и организация", "Матрица район × организация"],
    [9, "9 Тип и организация", "Матрица тип конструкции × организация"],
    [10, "10 Метрики риска", "Минимальные, средние и максимальные показатели по риску"],
  ];
  s.getRange("A13:C22").values = descriptions;
  styleTable(s, "A12:C22", "A12:C12");
  bandRows(s, 13, 22, 1, 3);
  s.getRange("A:A").format.columnWidth = 26;
  s.getRange("B:B").format.columnWidth = 25;
  s.getRange("C:C").format.columnWidth = 46;
  s.getRange("D:D").format.columnWidth = 36;
  s.getRange("A5:D22").format.autofitRows();
  s.freezePanes.freezeRows(5);
}

workbook.recalculate();

const checks = [];
checks.push((await workbook.inspect({ kind: "table", range: "ЛР3 Итоги!A1:D22", include: "values,formulas", tableMaxRows: 24, tableMaxCols: 6, maxChars: 12000 })).ndjson);
checks.push((await workbook.inspect({ kind: "table", range: "1 Риск!A1:E9", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 8, maxChars: 9000 })).ndjson);
checks.push((await workbook.inspect({ kind: "table", range: "5 Район и риск!A1:E20", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 8, maxChars: 12000 })).ndjson);
checks.push((await workbook.inspect({ kind: "table", range: "10 Метрики риска!A1:H8", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 10, maxChars: 12000 })).ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
  maxChars: 12000,
});
checks.push(errors.ndjson);

const renderSheets = [
  "Исходные данные", "ЛР3 Итоги", "1 Риск", "2 Районы", "3 Конструкции", "4 Организации",
  "5 Район и риск", "6 Тип и риск", "7 Организация и риск", "8 Район и организация",
  "9 Тип и организация", "10 Метрики риска",
];
for (const sheetName of renderSheets) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  const safe = sheetName.replaceAll(/[^\p{L}\p{N}]+/gu, "_");
  await fs.writeFile(path.join(PREVIEW_DIR, `${safe}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT);
await fs.writeFile(path.join(OUTPUT_DIR, "verification.txt"), checks.join("\n\n"), "utf8");
console.log(JSON.stringify({ output: path.resolve(OUTPUT), previews: path.resolve(PREVIEW_DIR), verification: path.resolve(path.join(OUTPUT_DIR, "verification.txt")) }));
