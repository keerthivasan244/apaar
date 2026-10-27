import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnDef } from "@tanstack/react-table";
import { Api } from "../../api/endpoints";
import type { CollegeRow } from "../../api/types";
import { useAsync } from "../../hooks/useAsync";
import DataTable from "../../components/DataTable";
import { Card, ErrorBanner, PageHeader, RiskChip } from "../../components/ui";

export default function Colleges() {
  const colleges = useAsync(() => Api.colleges(), []);
  const navigate = useNavigate();
  const columns = useMemo<ColumnDef<CollegeRow>[]>(
    () => [
      { header: "AICTE ID", accessorKey: "aicte_id", cell: (c) => <span className="font-mono text-xs">{c.row.original.aicte_id}</span> },
      { header: "Institution", accessorKey: "name", cell: (c) => <div><div className="font-medium text-navy">{c.row.original.name}</div><div className="text-xs text-slate-500">{c.row.original.type}</div></div> },
      { header: "City", accessorKey: "city" },
      { header: "State", accessorKey: "state" },
      { header: "Students", accessorKey: "students" },
      { header: "Open flags", accessorKey: "open_flags" },
      { header: "Risk", accessorKey: "risk_score", cell: (c) => <RiskChip score={c.row.original.risk_score ?? 0} band={c.row.original.risk_band ?? "low"} /> },
    ],
    [],
  );
  return (
    <>
      <PageHeader title="Institutions" subtitle="All approved institutions with current-year enrolment and risk." />
      <Card>
        <ErrorBanner message={colleges.error} onRetry={colleges.reload} />
        <DataTable data={colleges.data || []} columns={columns} loading={colleges.loading} onRowClick={(c) => navigate(`/aicte/colleges/${c.id}`)} />
      </Card>
    </>
  );
}
