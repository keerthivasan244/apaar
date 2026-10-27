import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { CheckCircle2, Download, FileSpreadsheet, RotateCcw, UploadCloud } from "lucide-react";
import { download } from "../../api/client";
import { Api } from "../../api/endpoints";
import type { UploadResult, UploadRow } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import { precheckCsv, Problem } from "../../lib/precheck";
import { useToast } from "../../components/Toast";
import { Button, Card, cx, ErrorBanner, KpiTile, PageHeader, Select, SeverityBadge, StatusChip } from "../../components/ui";

const STEPS = ["Choose file", "Pre-check", "Server dry-run", "Confirm and submit"];

export default function Upload() {
  const { config } = useAuth();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [precheck, setPrecheck] = useState<{ problems: Problem[]; rows: number; missingColumns: string[]; skipped?: boolean } | null>(null);
  const [dry, setDry] = useState<UploadResult | null>(null);
  const [committed, setCommitted] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rowFilter, setRowFilter] = useState("all");

  const step = committed ? 3 : dry ? 2 : precheck ? 1 : 0;

  function reset() {
    setFile(null);
    setPrecheck(null);
    setDry(null);
    setCommitted(null);
    setError(null);
  }

  async function onFile(f: File) {
    reset();
    setFile(f);
    if (f.size > 5 * 1024 * 1024) {
      setError("File is larger than 5 MB");
      return;
    }
    if (f.name.toLowerCase().endsWith(".csv") && config) {
      const text = await f.text();
      setPrecheck(precheckCsv(text, config.policy));
    } else {
      setPrecheck({ problems: [], rows: 0, missingColumns: [], skipped: true });
    }
  }

  const dz = useDropzone({
    multiple: false,
    accept: { "text/csv": [".csv"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"] },
    onDrop: (accepted, rejected) => {
      if (accepted[0]) onFile(accepted[0]);
      else if (rejected[0]) setError("Only .csv or .xlsx files are accepted");
    },
  });

  async function runDry() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      setDry(await Api.uploadStudents(file, true));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await Api.uploadStudents(file, false);
      setCommitted(res);
      toast(`${res.rows_saved} records saved`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const savable = dry ? dry.summary.ok + dry.summary.warnings : 0;
  const filteredRows = useMemo(
    () => (dry?.rows || []).filter((r) => (rowFilter === "all" ? true : rowFilter === "issues" ? r.status !== "ok" : r.status === rowFilter)),
    [dry, rowFilter],
  );

  return (
    <>
      <PageHeader
        title="Upload students"
        subtitle="Bulk upload keyed on APAAR ID. Nothing is saved until you confirm."
        actions={
          <Button variant="secondary" onClick={() => download("/templates/students.csv", "students_template.csv")}>
            <Download size={16} /> Download template
          </Button>
        }
      />
      <ol className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STEPS.map((label, i) => (
          <li key={label} className={cx("rounded-lg border px-3 py-2 text-sm", i < step ? "border-teal/40 bg-emerald-50 text-teal" : i === step ? "border-navy bg-white font-semibold text-navy" : "border-slate-200 bg-white text-slate-400")}>
            <span className="mr-1 font-semibold">{i + 1}.</span>
            {label}
          </li>
        ))}
      </ol>
      <ErrorBanner message={error} />

      <Card className="mb-6">
        <div
          {...dz.getRootProps()}
          className={cx("flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition", dz.isDragActive ? "border-teal bg-emerald-50" : "border-slate-300 hover:border-navy")}
        >
          <input {...dz.getInputProps()} aria-label="Choose file" />
          {file ? <FileSpreadsheet size={36} className="text-navy" /> : <UploadCloud size={36} className="text-slate-400" />}
          {file ? (
            <div>
              <div className="font-medium text-slate-800">{file.name}</div>
              <div className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB · click or drop to replace</div>
            </div>
          ) : (
            <div>
              <div className="font-medium text-slate-700">Drag and drop a .csv or .xlsx file, or click to choose</div>
              <div className="text-xs text-slate-500">Maximum 5 MB and 5,000 rows</div>
            </div>
          )}
        </div>
      </Card>

      {precheck && !committed && (
        <Card title="Step 2 · Pre-check (in your browser)" className="mb-6">
          {precheck.skipped ? (
            <p className="text-sm text-slate-600">Pre-check runs on CSV files. XLSX files are checked fully by the server dry-run.</p>
          ) : precheck.missingColumns.length > 0 ? (
            <ErrorBanner message={`Missing required columns: ${precheck.missingColumns.join(", ")}. Use the template.`} />
          ) : (
            <>
              <div className={cx("mb-3 rounded-lg px-4 py-2 text-sm font-medium", precheck.problems.length ? "bg-amber-50 text-sev-medium" : "bg-emerald-50 text-teal")}>
                {precheck.rows} rows checked · {precheck.problems.length === 0 ? "0 problems found" : `${precheck.problems.length} problem${precheck.problems.length === 1 ? "" : "s"} found`}
              </div>
              {precheck.problems.length > 0 && (
                <div className="max-h-72 overflow-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs uppercase text-slate-500">
                        <th className="px-3 py-2">Row</th>
                        <th className="px-3 py-2">Field</th>
                        <th className="px-3 py-2">Problem</th>
                        <th className="px-3 py-2">Suggested fix</th>
                      </tr>
                    </thead>
                    <tbody>
                      {precheck.problems.map((p, i) => (
                        <tr key={i} className="border-b border-slate-100">
                          <td className="px-3 py-2">{p.row}</td>
                          <td className="px-3 py-2 font-mono text-xs">{p.field}</td>
                          <td className="px-3 py-2">{p.problem}</td>
                          <td className="px-3 py-2 text-slate-600">{p.fix}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <p className="mt-3 text-xs text-slate-500">Rows with problems can still be sent: the server skips rows with blocking errors and saves warnings as flags.</p>
            </>
          )}
          <div className="mt-4 flex gap-2">
            <Button onClick={runDry} loading={busy} disabled={precheck.missingColumns.length > 0}>
              Run server dry-run
            </Button>
          </div>
        </Card>
      )}

      {dry && !committed && (
        <Card title="Step 3 · Server dry-run" className="mb-6">
          <div className="grid gap-3 sm:grid-cols-4">
            <KpiTile label="Total rows" value={dry.summary.total} />
            <KpiTile label="OK" value={dry.summary.ok} tone="teal" />
            <KpiTile label="Warnings (saved + flagged)" value={dry.summary.warnings} tone="amber" />
            <KpiTile label="Errors (skipped)" value={dry.summary.errors} tone="red" />
          </div>
          <div className="mt-4 flex items-center justify-between">
            <Select label="Filter rows" value={rowFilter} onChange={setRowFilter} options={[
              { value: "all", label: "All rows" }, { value: "issues", label: "Rows with issues" },
              { value: "warning", label: "Warnings" }, { value: "error", label: "Errors" }, { value: "ok", label: "OK" },
            ]} />
          </div>
          <RowTable rows={filteredRows} />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button variant="accent" onClick={commit} loading={busy} disabled={savable === 0}>
              Step 4 · Confirm and save {savable} row{savable === 1 ? "" : "s"}
            </Button>
            {dry.summary.errors > 0 && <span className="text-sm text-slate-600">{dry.summary.errors} row(s) with errors will be skipped.</span>}
            <Button variant="ghost" onClick={reset}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {committed && (
        <Card className="mb-6 border-teal/40">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-1 text-teal" size={28} />
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-slate-800">Upload complete</h2>
              <p className="text-sm text-slate-600">Batch #{committed.batch_id} from {file?.name}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <KpiTile label="Rows saved" value={committed.rows_saved ?? 0} tone="teal" />
                <KpiTile label="Rows skipped" value={committed.rows_skipped ?? 0} tone={committed.rows_skipped ? "red" : "navy"} />
                <KpiTile label="New flags" value={committed.new_flags ?? 0} tone={committed.new_flags ? "amber" : "navy"} />
                <KpiTile label="New probable duplicates" value={committed.new_matches ?? 0} tone={committed.new_matches ? "red" : "navy"} />
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <Link to="/institution/flags">
                  <Button>View flags</Button>
                </Link>
                <Button variant="secondary" onClick={reset}>
                  <RotateCcw size={16} /> Upload another file
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}
    </>
  );
}

function RowTable({ rows }: { rows: UploadRow[] }) {
  if (rows.length === 0) return <p className="py-6 text-center text-sm text-slate-500">No rows match this filter.</p>;
  return (
    <div className="mt-3 max-h-96 overflow-auto">
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 bg-white">
          <tr className="border-b text-left text-xs uppercase text-slate-500">
            <th className="px-3 py-2">Row</th>
            <th className="px-3 py-2">Student</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Issues</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.row} className="border-b border-slate-100 align-top">
              <td className="px-3 py-2">{r.row}</td>
              <td className="px-3 py-2">
                <div className="font-medium">{r.data.name || "–"}</div>
                <div className="text-xs text-slate-500">{r.data.student_code}</div>
              </td>
              <td className="px-3 py-2">
                <StatusChip status={r.status} />
              </td>
              <td className="px-3 py-2">
                <div className="flex flex-col gap-1">
                  {r.issues.map((i, k) => (
                    <div key={k} className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={i.severity} />
                      <span className="font-mono text-xs">{i.code}</span>
                      <span>{i.message}</span>
                      {i.hint && <span className="text-xs text-slate-500">({i.hint})</span>}
                    </div>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
