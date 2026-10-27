import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, XCircle } from "lucide-react";
import { Api } from "../../api/endpoints";
import type { MatchSide } from "../../api/types";
import { useAsync } from "../../hooks/useAsync";
import { useToast } from "../../components/Toast";
import { Button, Card, ErrorBanner, fmtDate, inputClass, LoadingBlock, PageHeader, ProgressBar, StatusChip } from "../../components/ui";
import { ScoreBadge } from "./Matches";

const FIELD_LABEL: Record<string, string> = { name: "Name", father_name: "Father's name", dob: "Date of birth", gender: "Gender", phone: "Phone" };

export default function MatchReview() {
  const id = Number(useParams().id);
  const match = useAsync(() => Api.match(id), [id]);
  const toast = useToast();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const m = match.data;

  async function decide(status: "confirmed" | "dismissed") {
    setBusy(true);
    try {
      const updated = await Api.reviewMatch(id, status, note);
      match.setData(updated);
      toast(status === "confirmed" ? "Duplicate confirmed; linked flag updated" : "Match dismissed; linked flag updated");
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Link to="/aicte/matches" className="mb-3 inline-flex items-center gap-1 text-sm text-teal">
        <ArrowLeft size={14} /> All matches
      </Link>
      <PageHeader
        title={`Match #${id}`}
        subtitle={m ? <span className="flex items-center gap-2"><ScoreBadge score={m.score} band={m.band} /><span className="font-medium capitalize">{m.band === "probable" ? "Probable duplicate" : "Needs review"}</span><StatusChip status={m.status} /></span> : undefined}
      />
      <ErrorBanner message={match.error} onRetry={match.reload} />
      {!m ? (
        <LoadingBlock rows={8} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <RecordCard label="Record A (older)" s={m.student_a} />
            <RecordCard label="Record B (newer)" s={m.student_b} />
          </div>
          <Card title="Field-by-field comparison" className="mt-6">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs uppercase text-slate-500">
                    <th className="px-3 py-2">Field</th>
                    <th className="px-3 py-2">Record A</th>
                    <th className="px-3 py-2">Record B</th>
                    <th className="w-48 px-3 py-2">Similarity</th>
                    <th className="px-3 py-2">Weight</th>
                    <th className="px-3 py-2">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(m.components || {}).map(([field, c]) => (
                    <tr key={field} className={`border-b border-slate-100 ${c.excluded ? "text-slate-400" : ""}`}>
                      <td className="px-3 py-2 font-medium">{FIELD_LABEL[field] || field}</td>
                      <td className="px-3 py-2">{c.value_a ?? <em>missing</em>}</td>
                      <td className="px-3 py-2">{c.value_b ?? <em>missing</em>}</td>
                      <td className="px-3 py-2">
                        {c.similarity === null ? (
                          <span className="text-xs">excluded</span>
                        ) : (
                          <div className="flex items-center gap-2">
                            <ProgressBar value={c.similarity} color={c.similarity >= 0.9 ? "#0F6E56" : c.similarity >= 0.6 ? "#B7791F" : "#C0392B"} />
                            <span className="w-10 text-right text-xs">{c.similarity.toFixed(2)}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs">{c.excluded ? "0 (redistributed)" : `${(c.weight * 100).toFixed(1)}%`}</td>
                      <td className="px-3 py-2 font-medium">{c.contribution.toFixed(3)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td className="px-3 py-2 font-semibold" colSpan={5}>Total score</td>
                    <td className="px-3 py-2 font-semibold">{m.score.toFixed(3)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
          <Card title="Why these records match" className="mt-6">
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {(m.explanations || []).map((e) => <li key={e}>{e}</li>)}
            </ul>
          </Card>
          <Card title="Decision" className="mt-6">
            {m.status !== "pending" ? (
              <p className="text-sm">
                <StatusChip status={m.status} /> by {m.reviewed_by} on {fmtDate(m.reviewed_at, true)}
                {m.note && <span className="text-slate-600"> · “{m.note}”</span>}
              </p>
            ) : (
              <>
                <textarea className={inputClass} rows={3} placeholder="Note for the record (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="danger" loading={busy} onClick={() => decide("confirmed")}>
                    <CheckCircle2 size={16} /> Confirm duplicate
                  </Button>
                  <Button variant="secondary" loading={busy} onClick={() => decide("dismissed")}>
                    <XCircle size={16} /> Dismiss (different people)
                  </Button>
                </div>
              </>
            )}
          </Card>
        </>
      )}
    </>
  );
}

function RecordCard({ label, s }: { label: string; s: MatchSide }) {
  const rows: [string, string | null | undefined][] = [
    ["Institution", `${s.college_name} (${s.college_aicte_id})`],
    ["Programme", s.programme],
    ["Student code", s.student_code],
    ["Name", s.name],
    ["Father's name", s.father_name],
    ["Date of birth", s.dob],
    ["Gender", s.gender],
    ["APAAR", s.apaar_id || "missing"],
    ["Phone", s.phone_last4 ? `ending ${s.phone_last4}` : "not given"],
  ];
  return (
    <Card title={label}>
      <dl className="grid grid-cols-3 gap-y-1.5 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-slate-500">{k}</dt>
            <dd className={`col-span-2 font-medium ${v === "missing" ? "text-sev-medium" : ""}`}>{v || "–"}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
