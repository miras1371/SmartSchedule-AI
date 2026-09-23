import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const bytes = await fs.readFile("input_lab2.xlsx");
const wb = await SpreadsheetFile.importXlsx(new FileBlob(bytes));
const overview = await wb.inspect({
  kind: "workbook,sheet,table",
  maxChars: 7000,
  tableMaxRows: 4,
  tableMaxCols: 10,
  tableMaxCellChars: 80,
});
console.log(overview.ndjson);
const help = wb.help("pivot", { include: "index,examples,notes", maxChars: 6000 });
console.log("PIVOT_HELP");
console.log(help.ndjson);
