import type { ProgrammeLedger } from "../api/types";
import { ProgressBar } from "./ui";

export default function ProgrammeTable({ programmes }: { programmes: ProgrammeLedger[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="px-3 py-2 font-medium">Programme</th>
            <th className="px-3 py-2 font-medium">Level</th>
            <th className="w-1/3 px-3 py-2 font-medium">Admitted vs approved</th>
            <th className="px-3 py-2 font-medium">Supernumerary (count / cap)</th>
          </tr>
        </thead>
        <tbody>
          {programmes.map((p) => {
            const supers = Object.entries(p.supernumerary).filter(([, s]) => s.count > 0);
            return (
              <tr key={p.id} className="border-b border-slate-100">
                <td className="px-3 py-3 font-medium text-slate-800">{p.name}</td>
                <td className="px-3 py-3 text-slate-600">{p.level}</td>
                <td className="px-3 py-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className={p.over_by > 0 ? "font-semibold text-sev-high" : "text-slate-700"}>
                      {p.admitted} / {p.approved_intake}
                    </span>
                    {p.over_by > 0 && <span className="font-semibold text-sev-high">over by {p.over_by}</span>}
                  </div>
                  <ProgressBar className="mt-1" value={p.admitted} max={p.approved_intake} color={p.over_by > 0 ? "#C0392B" : "#0F6E56"} />
                </td>
                <td className="px-3 py-3">
                  {supers.length === 0 ? (
                    <span className="text-xs text-slate-400">none</span>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {supers.map(([cat, s]) => (
                        <span
                          key={cat}
                          className={`rounded px-1.5 py-0.5 text-xs ${s.over_by > 0 ? "bg-red-50 font-semibold text-sev-high" : "bg-slate-100 text-slate-700"}`}
                          title={s.over_by > 0 ? `Over cap by ${s.over_by}` : undefined}
                        >
                          {cat} {s.count}/{s.cap}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
