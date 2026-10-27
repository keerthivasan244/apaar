import { useParams } from "react-router-dom";
import { Download } from "lucide-react";
import { download } from "../../api/client";
import { Api } from "../../api/endpoints";
import { useAsync } from "../../hooks/useAsync";
import ProgrammeTable from "../../components/ProgrammeTable";
import RiskBreakdown from "../../components/RiskBreakdown";
import StudentRoster from "../../components/StudentRoster";
import { Button, Card, CODE_LABEL, ErrorBanner, KpiTile, LoadingBlock, PageHeader, RiskChip } from "../../components/ui";
import { Link } from "react-router-dom";

export default function CollegeDetail() {
  const id = Number(useParams().id);
  const college = useAsync(() => Api.college(id), [id]);
  const analytics = useAsync(() => Api.collegeAnalytics(id), [id]);
  const risk = useAsync(() => Api.riskFor(id), [id]);
  const c = college.data;
  const a = analytics.data;
  return (
    <>
      <PageHeader
        title={c?.name || "Institution"}
        subtitle={c ? `${c.aicte_id} · ${c.city}, ${c.state} · ${c.type} · previous year enrolment ${c.prev_year_enrolment}` : undefined}
        actions={
          <>
            {risk.data && <RiskChip score={risk.data.score} band={risk.data.band} />}
            <Button variant="secondary" onClick={() => download(`/reports/roster?college_id=${id}&format=csv`, `roster_${c?.aicte_id}.csv`)}>
              <Download size={16} /> Roster
            </Button>
          </>
        }
      />
      <ErrorBanner message={college.error || analytics.error} />
      <div className="grid gap-4 sm:grid-cols-4">
        <KpiTile label="Students" value={a?.totals.students ?? "–"} />
        <KpiTile label="Admitted / approved" value={a ? `${a.totals.admitted} / ${a.totals.approved_intake}` : "–"} />
        <KpiTile label="Open flags" value={a?.totals.open_flags ?? "–"} tone="amber" to={`/aicte/flags?college_id=${id}`} />
        <KpiTile label="Programmes over intake" value={a?.totals.programmes_over_intake ?? "–"} tone={a?.totals.programmes_over_intake ? "red" : "teal"} />
      </div>
      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <Card title="Programmes" className="xl:col-span-2">{a ? <ProgrammeTable programmes={a.programmes} /> : <LoadingBlock />}</Card>
        <Card title="Open flags">
          {a && a.flags_by_code.length === 0 && <p className="text-sm text-slate-500">No open flags.</p>}
          <ul className="space-y-2 text-sm">
            {a?.flags_by_code.map((f) => (
              <li key={f.code} className="flex justify-between">
                <Link className="text-navy hover:underline" to={`/aicte/flags?college_id=${id}&code=${f.code}`}>{CODE_LABEL[f.code] || f.code}</Link>
                <span className="font-semibold">{f.count}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
      {risk.data && (
        <Card title="Risk breakdown" className="mt-6">
          <RiskBreakdown risk={risk.data} />
        </Card>
      )}
      <Card title="Students" className="mt-6">
        <StudentRoster collegeId={id} />
      </Card>
    </>
  );
}
