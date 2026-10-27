import Papa from "papaparse";
import type { Policy } from "../api/types";

export interface Problem {
  row: number;
  field: string;
  problem: string;
  fix: string;
}

export const ADMISSION_CATEGORIES = ["Regular", "EWS", "Sports", "TFW", "PMSSS", "NRI", "OCI", "FN"];
export const REQUIRED = [
  "student_id", "name", "father_name", "dob", "gender", "programme", "level", "shift", "admission_category", "social_category", "year",
];

export function parseDob(value: string): Date | null {
  const v = value.trim();
  let y: number, m: number, d: number;
  let match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v);
  if (match) {
    [y, m, d] = [Number(match[1]), Number(match[2]), Number(match[3])];
  } else if ((match = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/.exec(v))) {
    [d, m, y] = [Number(match[1]), Number(match[2]), Number(match[3])];
  } else {
    return null;
  }
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d ? dt : null;
}

const inList = (value: string, list: string[]) => list.some((x) => x.toLowerCase() === value.trim().toLowerCase());

/** Browser-only checks mirroring the server's blocking rules plus the APAAR format. */
export function precheckCsv(text: string, policy: Policy): { problems: Problem[]; rows: number; missingColumns: string[] } {
  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: "greedy",
    transformHeader: (h) => h.trim().toLowerCase(),
  });
  const columns = parsed.meta.fields || [];
  const missingColumns = REQUIRED.filter((c) => !columns.includes(c));
  const problems: Problem[] = [];
  if (missingColumns.length) return { problems, rows: parsed.data.length, missingColumns };

  const apaarRe = new RegExp(policy.apaar_regex);
  const seen = new Set<string>();
  parsed.data.forEach((raw, i) => {
    const row = i + 2;
    const get = (k: string) => (raw[k] ?? "").trim();
    const add = (field: string, problem: string, fix: string) => problems.push({ row, field, problem, fix });
    REQUIRED.forEach((col) => {
      if (!get(col)) add(col, "Required value is empty", `Fill in ${col}`);
    });
    const apaar = get("apaar_id");
    if (apaar && !apaarRe.test(apaar)) add("apaar_id", `"${apaar}" is not a 12-digit APAAR`, "Must be exactly 12 digits, remove spaces or letters");
    if (get("dob") && !parseDob(get("dob"))) add("dob", `"${get("dob")}" is not a valid date`, "Use YYYY-MM-DD or DD/MM/YYYY");
    if (get("gender") && !inList(get("gender"), policy.genders)) add("gender", `"${get("gender")}" is not valid`, "Use M, F or O");
    if (get("level") && !inList(get("level"), policy.levels)) add("level", `"${get("level")}" is not valid`, `Use one of: ${policy.levels.join(", ")}`);
    if (get("shift") && !inList(get("shift"), policy.shifts)) add("shift", `"${get("shift")}" is not valid`, "Use Day or Evening");
    if (get("admission_category") && !inList(get("admission_category"), ADMISSION_CATEGORIES))
      add("admission_category", `"${get("admission_category")}" is not valid`, `Use one of: ${ADMISSION_CATEGORIES.join(", ")}`);
    if (get("social_category") && !inList(get("social_category"), policy.social_categories))
      add("social_category", `"${get("social_category")}" is not valid`, `Use one of: ${policy.social_categories.join(", ")}`);
    if (get("year") && get("year") !== String(policy.academic_year)) add("year", `"${get("year")}" is not the current academic year`, `Use ${policy.academic_year}`);
    const id = get("student_id");
    if (id && seen.has(id)) add("student_id", `Student ID "${id}" repeats`, "Each student ID must be unique in the file");
    seen.add(id);
  });
  return { problems, rows: parsed.data.length, missingColumns };
}
