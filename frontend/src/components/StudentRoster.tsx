import { ReactNode, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { Search } from "lucide-react";
import { Api } from "../api/endpoints";
import type { StudentRow } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import DataTable from "./DataTable";
import { CODE_LABEL, ErrorBanner, inputClass, Select } from "./ui";

const PAGE_SIZE = 25;

export default function StudentRoster({ collegeId, action }: { collegeId?: number; action?: (s: StudentRow) => ReactNode }) {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [flagged, setFlagged] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(q);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const students = useAsync(
    () => Api.students({ q: debounced, has_flag: flagged === "" ? undefined : flagged, college_id: collegeId, page, page_size: PAGE_SIZE }),
    [debounced, flagged, page, collegeId],
  );

  const columns = useMemo<ColumnDef<StudentRow>[]>(
    () => [
      { header: "Code", accessorKey: "student_code", cell: (c) => <span className="font-mono text-xs">{c.row.original.student_code}</span> },
      { header: "Name", accessorKey: "name", cell: (c) => <span className="font-medium">{c.row.original.name}</span> },
      { header: "APAAR", accessorKey: "apaar_id", cell: (c) => <span className="font-mono text-xs">{c.row.original.apaar_id || <em className="text-slate-400">missing</em>}</span> },
      { header: "Programme", accessorKey: "programme" },
      { header: "Category", accessorKey: "admission_category" },
      {
        header: "Flags",
        id: "flags",
        accessorFn: (r) => r.open_flags.length,
        cell: (c) => (
          <div className="flex flex-wrap gap-1">
            {c.row.original.open_flags.map((f, i) => (
              <span key={i} className="rounded bg-amber-50 px-1.5 py-0.5 text-xs text-sev-medium ring-1 ring-amber-200">
                {CODE_LABEL[f] || f}
              </span>
            ))}
          </div>
        ),
      },
      ...(action ? [{ header: "", id: "action", enableSorting: false, cell: (c) => action(c.row.original) } as ColumnDef<StudentRow>] : []),
    ],
    [action],
  );

  return (
    <>
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[16rem] flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className={`${inputClass} pl-9`} placeholder="Search name, student code or APAAR" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search students" />
        </div>
        <Select label="Flag filter" value={flagged} onChange={(v) => { setFlagged(v); setPage(1); }} options={[
          { value: "", label: "All students" }, { value: "true", label: "With open flags" }, { value: "false", label: "Without flags" },
        ]} />
      </div>
      <ErrorBanner message={students.error} onRetry={students.reload} />
      <DataTable
        data={students.data?.items || []}
        columns={columns}
        loading={students.loading}
        emptyTitle="No students found"
        emptyText={debounced ? "No records match your search." : "Upload a file to add students."}
        server={{ total: students.data?.total || 0, page, pageSize: PAGE_SIZE, onPage: setPage }}
      />
    </>
  );
}
