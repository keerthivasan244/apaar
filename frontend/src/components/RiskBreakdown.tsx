import type { RiskRow } from "../api/types";
import { BAND_COLOR, ProgressBar } from "./ui";

export const COMPONENT_LABEL: Record<string, string> = {
  over_intake: "Over-intake",
  duplicates: "Suspected duplicates",
  data_quality: "Data quality",
  flag_ageing: "Unresolved flag age",
  anomaly: "Enrolment growth anomaly",
};

export default function RiskBreakdown({ risk }: { risk: RiskRow }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="space-y-3">
        {Object.entries(risk.components).map(([key, c]) => (
          <div key={key}>
            <div className="flex justify-between text-xs">
              <span className="font-medium text-slate-700">{COMPONENT_LABEL[key] || key}</span>
              <span className="text-slate-600">
                value {(c.value * 100).toFixed(0)}% × weight {c.weight} = <strong>{c.contribution.toFixed(1)}</strong>
              </span>
            </div>
            <ProgressBar className="mt-1 h-3" value={c.contribution} max={c.weight} color={BAND_COLOR[risk.band]} />
          </div>
        ))}
        <div className="flex justify-between border-t pt-2 text-sm">
          <span className="font-medium">Score</span>
          <span className="font-semibold" style={{ color: BAND_COLOR[risk.band] }}>{risk.score} / 100 ({risk.band})</span>
        </div>
      </div>
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Top reasons</div>
        {risk.reasons.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No risk indicators for this institution.</p>
        ) : (
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-800">
            {risk.reasons.map((r) => <li key={r}>{r}</li>)}
          </ol>
        )}
        <p className="mt-4 text-xs text-slate-500">Risk score prioritises inspections; it is not a penalty decision.</p>
      </div>
    </div>
  );
}
