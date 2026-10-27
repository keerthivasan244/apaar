import { AlertTriangle, Flag, Users } from "lucide-react";
import { Api } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import ProgrammeTable from "../../components/ProgrammeTable";
import { Card, CODE_LABEL, ErrorBanner, KpiTile, LoadingBlock, PageHeader, RiskChip } from "../../components/ui";
import { Link } from "react-router-dom";

export default function InstitutionDashboard() {
  const { user } = useAuth();
  const cid = user!.college_id!;
  const college = useAsync(() => Api.college(cid), [cid]);
  const analytics = useAsync(() => Api.collegeAnalytics(cid), [cid]);
  const risk = useAsync(() => Api.riskFor(cid), [cid]);
  const a = analytics.data;

  return (
    <>
      <PageHeader
        title={college.data?.name || "Institution dashboard"}
        subtitle={college.data ? `${college.data.aicte_id} · ${college.data.city}, ${college.data.state}` : undefined}
        actions={risk.data && <RiskChip score={risk.data.score} band={risk.data.band} />}
      />
      <ErrorBanner message={analytics.error} onRetry={analytics.reload} />
      <div className="grid gap-4 sm:grid-cols-3">
        <KpiTile label="Students" value={a?.totals.students ?? "–"} to="/institution/students" icon={<Users />} />
        <KpiTile label="Open flags" value={a?.totals.open_flags ?? "–"} tone={a && a.totals.open_flags > 0 ? "amber" : "teal"} to="/institution/flags" icon={<Flag />} />
        <KpiTile
          label="Programmes over intake"
          value={a?.totals.programmes_over_intake ?? "–"}
          tone={a && a.totals.programmes_over_intake > 0 ? "red" : "teal"}
          to="/institution/flags"
          icon={<AlertTriangle />}
        />
      </div>
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card title="Programmes and seat usage" className="lg:col-span-2">
          {analytics.loading && !a ? <LoadingBlock /> : a && <ProgrammeTable programmes={a.programmes} />}
        </Card>
        <div className="space-y-6">
          <Card title="Open flags by type">
            {a && a.flags_by_code.length === 0 && <p className="text-sm text-slate-500">No open flags. Your data is clean.</p>}
            <ul className="space-y-2 text-sm">
              {a?.flags_by_code.map((f) => (
                <li key={f.code} className="flex justify-between">
                  <Link className="text-navy hover:underline" to={`/institution/flags?code=${f.code}`}>
                    {CODE_LABEL[f.code] || f.code}
                  </Link>
                  <span className="font-semibold">{f.count}</span>
                </li>
              ))}
            </ul>
          </Card>
          {risk.data && (
            <Card title="Risk indicators">
              {risk.data.reasons.length === 0 ? (
                <p className="text-sm text-slate-500">No risk indicators.</p>
              ) : (
                <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                  {risk.data.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs text-slate-500">{risk.data.disclaimer}</p>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
