import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Api } from "../../api/endpoints";
import type { RiskRow } from "../../api/types";
import { useAsync } from "../../hooks/useAsync";
import DataTable from "../../components/DataTable";
import RiskBreakdown from "../../components/RiskBreakdown";
import { Card, ErrorBanner, PageHeader, RiskChip } from "../../components/ui";

export default function Risk() {
  const risk = useAsync(() => Api.risk(), []);
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (id: number) => setOpen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const columns = useMemo<ColumnDef<RiskRow>[]>(
    () => [
      { header: "", id: "x", enableSorting: false, cell: (c) => (open.has(c.row.original.college_id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />) },
      { header: "Institution", accessorKey: "name", cell: (c) => <Link onClick={(e) => e.stopPropagation()} to={`/aicte/colleges/${c.row.original.college_id}`} className="font-medium text-navy hover:underline">{c.row.original.name}</Link> },
      { header: "State", accessorKey: "state" },
      { header: "Score", accessorKey: "score", cell: (c) => <RiskChip score={c.row.original.score} band={c.row.original.band} /> },
      { header: "Top reason", id: "reason", accessorFn: (r) => r.reasons[0] || "", enableSorting: false, cell: (c) => <span className="text-slate-700">{c.row.original.reasons[0] || "–"}</span> },
    ],
    [open],
  );
  return (
    <>
      <PageHeader title="Institution risk scores" subtitle="Explainable 0–100 score from five weighted components. Click a row to see the breakdown." />
      <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-sev-medium">
        Risk score prioritises inspections; it is not a penalty decision.
      </div>
      <Card>
        <ErrorBanner message={risk.error} onRetry={risk.reload} />
        <DataTable
          data={risk.data || []}
          columns={columns}
          loading={risk.loading}
          onRowClick={(r) => toggle(r.college_id)}
          isExpanded={(r) => open.has(r.college_id)}
          renderExpanded={(r) => <RiskBreakdown risk={r} />}
        />
      </Card>
    </>
  );
}
