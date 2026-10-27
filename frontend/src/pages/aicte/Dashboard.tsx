import { Link, useNavigate } from "react-router-dom";
import { AlertOctagon, Flag, GitCompare, School, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Api } from "../../api/endpoints";
import { useAsync } from "../../hooks/useAsync";
import { Card, CODE_LABEL, ErrorBanner, fmtDate, KpiTile, LoadingBlock, PageHeader, RiskChip } from "../../components/ui";

// Fixed categorical order (validated reference palette); colour follows the category, never its rank.
export const CATEGORY_COLOR: Record<string, string> = {
  Regular: "#2a78d6", EWS: "#eb6834", Sports: "#1baf7a", TFW: "#eda100",
  PMSSS: "#e87ba4", NRI: "#008300", OCI: "#6250d6", FN: "#e34948",
};
const AXIS = { stroke: "#c3c2b7", tick: { fill: "#52514e", fontSize: 12 } };

export default function AicteDashboard() {
  const ov = useAsync(() => Api.overview(), []);
  const navigate = useNavigate();
  const d = ov.data;
  const shortName = (n: string) => n.split(" ")[0];

  return (
    <>
      <PageHeader title="AICTE regulator console" subtitle="Academic year 2026 · all approved institutions" />
      <ErrorBanner message={ov.error} onRetry={ov.reload} />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <KpiTile label="Institutions" value={d?.totals.colleges ?? "–"} to="/aicte/colleges" icon={<School />} />
        <KpiTile label="Students" value={d?.totals.students.toLocaleString() ?? "–"} to="/aicte/colleges" icon={<Users />} />
        <KpiTile label="Open flags" value={d?.totals.open_flags ?? "–"} tone="amber" to="/aicte/flags" icon={<Flag />} />
        <KpiTile label="Pending matches" value={d?.totals.pending_matches ?? "–"} tone="red" to="/aicte/matches" icon={<GitCompare />} />
        <KpiTile label="High-risk institutions" value={d?.totals.high_risk_colleges ?? "–"} tone="red" to="/aicte/risk" icon={<AlertOctagon />} />
      </div>
      {!d ? (
        <Card className="mt-6"><LoadingBlock rows={6} /></Card>
      ) : (
        <>
          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Card title="Approved intake vs admitted (largest excess)" className="xl:col-span-2">
              <div className="h-80">
                <ResponsiveContainer>
                  <BarChart data={d.top_over_intake.map((r) => ({ ...r, short: shortName(r.college) }))} barGap={2} margin={{ left: -10, bottom: 30 }}>
                    <CartesianGrid vertical={false} stroke="#e1e0d9" />
                    <XAxis dataKey="short" {...AXIS} interval={0} angle={-30} textAnchor="end" height={60} />
                    <YAxis {...AXIS} />
                    <Tooltip
                      cursor={{ fill: "rgba(31,58,95,0.06)" }}
                      formatter={(v: number, name: string) => [v, name]}
                      labelFormatter={(_l, p) => (p?.[0] ? `${p[0].payload.college} (excess ${p[0].payload.excess})` : "")}
                    />
                    <Legend verticalAlign="top" height={30} formatter={(v: string) => <span className="text-xs text-slate-700">{v}</span>} />
                    <Bar dataKey="approved" name="Approved intake" fill="#9ec5f4" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(p) => navigate(`/aicte/colleges/${p.college_id}`)} />
                    <Bar dataKey="admitted" name="Admitted" fill="#1F3A5F" radius={[4, 4, 0, 0]} cursor="pointer" onClick={(p) => navigate(`/aicte/colleges/${p.college_id}`)} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Admission categories">
              <div className="h-64">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={d.category_breakdown} dataKey="count" nameKey="category" innerRadius="55%" outerRadius="85%" paddingAngle={1} stroke="#fff" strokeWidth={2} isAnimationActive={false}>
                      {d.category_breakdown.map((c) => (
                        <Cell key={c.category} fill={CATEGORY_COLOR[c.category] || "#898781"} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number, n: string) => [v.toLocaleString(), n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-700">
                {d.category_breakdown.map((c) => (
                  <li key={c.category} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CATEGORY_COLOR[c.category] || "#898781" }} />
                    <span className="flex-1">{c.category}</span>
                    <span className="font-medium">{c.count.toLocaleString()}</span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Card title="Open flags by code">
              <div className="h-72">
                <ResponsiveContainer>
                  <BarChart layout="vertical" data={d.flags_by_code.map((f) => ({ ...f, label: CODE_LABEL[f.code] || f.code }))} margin={{ left: 0, right: 8 }} barCategoryGap={4}>
                    <CartesianGrid horizontal={false} stroke="#e1e0d9" />
                    <XAxis type="number" {...AXIS} allowDecimals={false} />
                    <YAxis type="category" dataKey="label" {...AXIS} width={160} interval={0} />
                    <Tooltip cursor={{ fill: "rgba(31,58,95,0.06)" }} formatter={(v: number) => [v, "Open flags"]} />
                    <Bar dataKey="count" fill="#1F3A5F" radius={[0, 4, 4, 0]} cursor="pointer" onClick={(p) => navigate(`/aicte/flags?code=${p.code}`)} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="Highest-risk institutions" actions={<Link to="/aicte/risk" className="text-sm text-teal underline">All scores</Link>}>
              <ul className="divide-y divide-slate-100">
                {d.top_risk.map((r) => (
                  <li key={r.college_id} className="py-2">
                    <Link to={`/aicte/colleges/${r.college_id}`} className="flex items-start justify-between gap-2 hover:text-navy">
                      <div>
                        <div className="text-sm font-medium">{r.name}</div>
                        <div className="text-xs text-slate-500">{r.top_reason || "No risk indicators"}</div>
                      </div>
                      <RiskChip score={r.score} band={r.band} />
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-slate-500">Risk score prioritises inspections; it is not a penalty decision.</p>
            </Card>
            <Card title="Recent audit activity" actions={<Link to="/aicte/audit" className="text-sm text-teal underline">Audit chain</Link>}>
              <ul className="divide-y divide-slate-100 text-sm">
                {d.recent_audit.map((a) => (
                  <li key={a.id} className="flex items-start justify-between gap-2 py-2">
                    <div>
                      <div className="font-mono text-xs font-semibold text-navy">{a.action}</div>
                      <div className="text-xs text-slate-500">{a.actor} · {a.entity_type} {a.entity_id}</div>
                    </div>
                    <div className="text-right text-xs text-slate-500">#{a.id}<br />{fmtDate(a.ts, true)}</div>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
