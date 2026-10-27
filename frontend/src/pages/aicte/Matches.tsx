import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Api } from "../../api/endpoints";
import type { MatchRow } from "../../api/types";
import { useAsync } from "../../hooks/useAsync";
import DataTable from "../../components/DataTable";
import { Card, ErrorBanner, PageHeader, Select, StatusChip } from "../../components/ui";

export function ScoreBadge({ score, band }: { score: number; band: string }) {
  const style = band === "probable" ? "bg-red-50 text-sev-high ring-red-200" : "bg-amber-50 text-sev-medium ring-amber-200";
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${style}`}>{score.toFixed(2)}</span>;
}

export default function Matches() {
  const [status, setStatus] = useState("pending");
  const [band, setBand] = useState("");
  const [page, setPage] = useState(1);
  const navigate = useNavigate();
  const matches = useAsync(() => Api.matches({ status, band, page, page_size: 25 }), [status, band, page]);
  const columns = useMemo<ColumnDef<MatchRow>[]>(
    () => [
      { header: "#", accessorKey: "id" },
      { header: "Score", accessorKey: "score", cell: (c) => <ScoreBadge score={c.row.original.score} band={c.row.original.band} /> },
      { header: "Band", accessorKey: "band", cell: (c) => <span className="capitalize">{c.row.original.band}</span> },
      { header: "Record A (older)", id: "a", accessorFn: (r) => r.student_a.name, cell: (c) => <Side s={c.row.original.student_a} /> },
      { header: "Record B (newer)", id: "b", accessorFn: (r) => r.student_b.name, cell: (c) => <Side s={c.row.original.student_b} /> },
      { header: "Why", id: "why", enableSorting: false, cell: (c) => <span className="text-xs text-slate-600">{c.row.original.top_explanation}</span> },
      { header: "Status", accessorKey: "status", cell: (c) => <StatusChip status={c.row.original.status} /> },
    ],
    [],
  );
  return (
    <>
      <PageHeader title="Duplicate review" subtitle="Fuzzy identity matches across institutions. Nothing is rejected automatically; an officer decides." />
      <Card>
        <div className="mb-4 flex flex-wrap gap-2">
          <Select label="Status" value={status} onChange={(v) => { setStatus(v); setPage(1); }} options={[
            { value: "pending", label: "Pending" }, { value: "confirmed", label: "Confirmed" }, { value: "dismissed", label: "Dismissed" }, { value: "", label: "All" },
          ]} />
          <Select label="Band" value={band} onChange={(v) => { setBand(v); setPage(1); }} options={[
            { value: "", label: "All bands" }, { value: "probable", label: "Probable (≥ 0.90)" }, { value: "review", label: "Review (0.75–0.90)" },
          ]} />
        </div>
        <ErrorBanner message={matches.error} onRetry={matches.reload} />
        <DataTable
          data={matches.data?.items || []}
          columns={columns}
          loading={matches.loading}
          onRowClick={(m) => navigate(`/aicte/matches/${m.id}`)}
          emptyTitle="No matches"
          emptyText={status === "pending" ? "No suspected duplicates are waiting for review." : undefined}
          server={{ total: matches.data?.total || 0, page, pageSize: 25, onPage: setPage }}
        />
      </Card>
    </>
  );
}

function Side({ s }: { s: MatchRow["student_a"] }) {
  return (
    <div>
      <div className="font-medium">{s.name}</div>
      <div className="text-xs text-slate-500">{s.college_name}</div>
    </div>
  );
}
