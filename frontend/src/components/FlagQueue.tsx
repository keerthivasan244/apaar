import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Api } from "../api/endpoints";
import type { FlagRow } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import DataTable from "./DataTable";
import { useToast } from "./Toast";
import { Button, CODE_LABEL, ErrorBanner, inputClass, Modal, Select, SeverityBadge, StatusChip } from "./ui";

const PAGE_SIZE = 25;

export default function FlagQueue({ officer }: { officer: boolean }) {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "open";
  const code = params.get("code") ?? "";
  const severity = params.get("severity") ?? "";
  const collegeId = params.get("college_id") ?? "";
  const page = Number(params.get("page") || 1);
  const toast = useToast();
  const [reviewing, setReviewing] = useState<FlagRow | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const flags = useAsync(
    () => Api.flags({ status, code, severity, college_id: officer ? collegeId : undefined, page, page_size: PAGE_SIZE }),
    [status, code, severity, collegeId, page],
  );
  const colleges = useAsync(() => (officer ? Api.colleges() : Promise.resolve([])), [officer]);

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.delete("page");
    setParams(next, { replace: true });
  };

  async function review(decision: "confirmed" | "dismissed") {
    if (!reviewing) return;
    setBusy(true);
    try {
      await Api.reviewFlag(reviewing.id, decision, note);
      toast(`Flag #${reviewing.id} marked ${decision}`);
      setReviewing(null);
      setNote("");
      flags.reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo<ColumnDef<FlagRow>[]>(
    () => [
      { header: "#", accessorKey: "id" },
      { header: "Type", accessorKey: "code", cell: (c) => <span className="whitespace-nowrap font-medium">{CODE_LABEL[c.row.original.code] || c.row.original.code}</span> },
      { header: "Severity", accessorKey: "severity", cell: (c) => <SeverityBadge severity={c.row.original.severity} /> },
      ...(officer ? [{ header: "Institution", accessorKey: "college_name" } as ColumnDef<FlagRow>] : []),
      {
        header: "Record",
        id: "record",
        accessorFn: (r) => r.student?.name || r.programme || "",
        cell: (c) => {
          const f = c.row.original;
          return f.student ? (
            <div>
              <div className="font-medium">{f.student.name}</div>
              <div className="text-xs text-slate-500">{f.student.student_code}</div>
            </div>
          ) : (
            <span className="text-slate-700">{f.programme}</span>
          );
        },
      },
      {
        header: "Details",
        accessorKey: "message",
        enableSorting: false,
        cell: (c) => {
          const f = c.row.original;
          const cp = f.counterpart;
          return (
            <div className="max-w-md">
              <div>{f.message}</div>
              {cp && (
                <div className="mt-1 text-xs text-slate-500">
                  Counterpart: {typeof cp === "string" ? cp : `${cp.name} (${cp.student_code}), ${cp.college_name}`}
                </div>
              )}
              {officer && f.match_id && (
                <Link to={`/aicte/matches/${f.match_id}`} className="mt-1 inline-block text-xs font-medium text-teal underline">
                  Open match review →
                </Link>
              )}
            </div>
          );
        },
      },
      { header: "Age", accessorKey: "age_days", cell: (c) => `${c.row.original.age_days} d` },
      { header: "Status", accessorKey: "status", cell: (c) => <StatusChip status={c.row.original.status} /> },
      {
        header: "",
        id: "actions",
        enableSorting: false,
        cell: (c) =>
          c.row.original.status === "open" ? (
            <Button variant="secondary" className="px-3 py-1" onClick={() => setReviewing(c.row.original)}>
              Review
            </Button>
          ) : null,
      },
    ],
    [officer],
  );

  const codeOptions = [{ value: "", label: "All types" }, ...Object.entries(CODE_LABEL).map(([value, label]) => ({ value, label }))];

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        <Select label="Status" value={status} onChange={(v) => set("status", v)} options={[
          { value: "open", label: "Open" }, { value: "confirmed", label: "Confirmed" }, { value: "dismissed", label: "Dismissed" },
          { value: "resolved_auto", label: "Resolved automatically" }, { value: "", label: "All statuses" },
        ]} />
        <Select label="Type" value={code} onChange={(v) => set("code", v)} options={codeOptions} />
        <Select label="Severity" value={severity} onChange={(v) => set("severity", v)} options={[
          { value: "", label: "All severities" }, { value: "critical", label: "Critical" }, { value: "high", label: "High" }, { value: "medium", label: "Medium" },
        ]} />
        {officer && (
          <Select label="Institution" value={collegeId} onChange={(v) => set("college_id", v)} options={[
            { value: "", label: "All institutions" },
            ...(colleges.data || []).map((c) => ({ value: String(c.id), label: c.name })),
          ]} />
        )}
      </div>
      <ErrorBanner message={flags.error} onRetry={flags.reload} />
      <DataTable
        data={flags.data?.items || []}
        columns={columns}
        loading={flags.loading}
        emptyTitle="No flags match these filters"
        emptyText={status === "open" ? "Nothing needs attention right now." : "Try a different status or type."}
        server={{ total: flags.data?.total || 0, page, pageSize: PAGE_SIZE, onPage: (p) => set("page", String(p)) }}
      />
      <Modal
        open={!!reviewing}
        title={`Review flag #${reviewing?.id}`}
        onClose={() => setReviewing(null)}
        footer={
          <>
            {officer && (
              <Button variant="secondary" loading={busy} onClick={() => review("dismissed")}>
                Dismiss (false positive)
              </Button>
            )}
            <Button variant={officer ? "danger" : "primary"} loading={busy} onClick={() => review("confirmed")}>
              {officer ? "Confirm issue" : "Acknowledge"}
            </Button>
          </>
        }
      >
        {reviewing && (
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <SeverityBadge severity={reviewing.severity} />
              <span className="font-medium">{CODE_LABEL[reviewing.code] || reviewing.code}</span>
            </div>
            <p>{reviewing.message}</p>
            {!officer && <p className="text-xs text-slate-500">Institutions can acknowledge a flag; only AICTE officers can dismiss one.</p>}
            <textarea className={inputClass} rows={3} placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        )}
      </Modal>
    </>
  );
}
