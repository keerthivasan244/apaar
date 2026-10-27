import { FormEvent, useState } from "react";
import { Building2, Search } from "lucide-react";
import { Api } from "../api/endpoints";
import type { ConsentField, ConsentRow, LookupResult } from "../api/types";
import { useAsync } from "../hooks/useAsync";
import { useToast } from "../components/Toast";
import { Button, Card, EmptyState, ErrorBanner, fmtDate, inputClass, LoadingBlock, Modal, PageHeader, StatusChip } from "../components/ui";

const FIELDS: { key: ConsentField; label: string }[] = [
  { key: "name", label: "Name" },
  { key: "dob", label: "Date of birth" },
  { key: "programme", label: "Programme" },
  { key: "admission_category", label: "Admission category" },
  { key: "student_code", label: "Student code" },
];
const LABEL = Object.fromEntries(FIELDS.map((f) => [f.key, f.label])) as Record<ConsentField, string>;
const STATUS_REASON: Record<string, string> = {
  requested: "Waiting for the student to approve with their OTP.",
  denied: "The student declined this request.",
  revoked: "The student revoked access.",
  expired: "Access expired; request again if you still need it.",
};

export default function Verifier() {
  const toast = useToast();
  const [apaar, setApaar] = useState("");
  const [lookup, setLookup] = useState<{ apaar: string; result: LookupResult } | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);
  const [fields, setFields] = useState<ConsentField[]>(["name", "programme"]);
  const [purpose, setPurpose] = useState("");
  const requests = useAsync(() => Api.myConsents(), []);
  const [viewing, setViewing] = useState<number | null>(null);

  async function doLookup(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setLookupError(null);
    try {
      const id = apaar.trim();
      setLookup({ apaar: id, result: await Api.lookup(id) });
    } catch (err) {
      setLookupError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function sendRequest() {
    if (!lookup) return;
    setBusy(true);
    try {
      await Api.requestConsent(lookup.apaar, fields, purpose);
      toast("Request sent to the student");
      setRequestOpen(false);
      setPurpose("");
      requests.reload();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  const r = lookup?.result;
  return (
    <>
      <PageHeader title="Verify a student" subtitle="Check enrolment by APAAR ID. Personal details are shared only with the student's consent." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Enrolment lookup">
          <form onSubmit={doLookup} className="flex gap-2">
            <input className={inputClass} placeholder="12-digit APAAR ID" value={apaar} onChange={(e) => setApaar(e.target.value)} aria-label="APAAR ID" required />
            <Button type="submit" loading={busy}><Search size={16} /> Look up</Button>
          </form>
          <ErrorBanner message={lookupError} />
          {r && (
            <div className="mt-4 rounded-lg border border-slate-200 p-4">
              {r.found ? (
                <>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-medium"><Building2 size={18} className="text-navy" /> {r.institution_name}</div>
                    <StatusChip status={r.enrolment_status || "unknown"} />
                  </div>
                  <dl className="mt-3 grid grid-cols-3 gap-y-1 text-sm">
                    <dt className="text-slate-500">APAAR</dt><dd className="col-span-2 font-mono">{lookup!.apaar}</dd>
                    <dt className="text-slate-500">Programme</dt><dd className="col-span-2">{r.programme}</dd>
                    <dt className="text-slate-500">Year</dt><dd className="col-span-2">{r.year}</dd>
                  </dl>
                  <p className="mt-3 text-xs text-slate-500">Name, date of birth and contact details are never shown without consent.</p>
                  <Button className="mt-3" onClick={() => setRequestOpen(true)}>Request detailed verification</Button>
                </>
              ) : (
                <p className="text-sm text-slate-600">No current enrolment found for this APAAR ID.</p>
              )}
            </div>
          )}
        </Card>
        <Card title="How consent works">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
            <li>Look up the APAAR ID to confirm enrolment (status, institution, programme, year).</li>
            <li>Request only the fields you need and state your purpose.</li>
            <li>The student approves with a one-time password, or declines.</li>
            <li>You see exactly the approved fields until the grant expires or the student revokes it.</li>
          </ol>
        </Card>
      </div>
      <Card title="My requests" className="mt-6">
        <ErrorBanner message={requests.error} onRetry={requests.reload} />
        {requests.loading && !requests.data ? <LoadingBlock rows={3} /> : (requests.data || []).length === 0 ? (
          <EmptyState title="No requests yet">Look up an APAAR ID and request detailed verification.</EmptyState>
        ) : (
          <div className="space-y-3">
            {requests.data!.map((c) => (
              <RequestRow key={c.id} c={c} open={viewing === c.id} onToggle={() => setViewing(viewing === c.id ? null : c.id)} />
            ))}
          </div>
        )}
      </Card>
      <Modal
        open={requestOpen}
        title="Request detailed verification"
        onClose={() => setRequestOpen(false)}
        footer={<Button loading={busy} disabled={fields.length === 0 || purpose.trim().length < 3} onClick={sendRequest}>Send request</Button>}
      >
        <div className="space-y-4 text-sm">
          <div>
            <div className="mb-2 font-medium text-slate-700">Fields requested</div>
            <div className="grid grid-cols-2 gap-2">
              {FIELDS.map((f) => (
                <label key={f.key} className="flex items-center gap-2">
                  <input type="checkbox" checked={fields.includes(f.key)} onChange={(e) => setFields(e.target.checked ? [...fields, f.key] : fields.filter((x) => x !== f.key))} />
                  {f.label}
                </label>
              ))}
            </div>
          </div>
          <label className="block">
            <span className="mb-1 block font-medium text-slate-700">Purpose</span>
            <textarea className={inputClass} rows={3} placeholder="e.g. Pre-employment background verification" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
          </label>
        </div>
      </Modal>
    </>
  );
}

function RequestRow({ c, open, onToggle }: { c: ConsentRow; open: boolean; onToggle: () => void }) {
  const result = useAsync(() => (open && c.status === "approved" ? Api.consentResult(c.id) : Promise.resolve(null)), [open, c.id, c.status]);
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="font-mono text-sm">{c.apaar_id}</div>
          <div className="text-xs text-slate-500">{c.institution_name} · {c.fields.map((f) => LABEL[f]).join(", ")}</div>
          <div className="text-xs text-slate-500">Purpose: {c.purpose} · requested {fmtDate(c.created_at, true)}</div>
        </div>
        <div className="flex items-center gap-2">
          <StatusChip status={c.status} />
          {c.status === "approved" && <Button variant="secondary" className="px-3 py-1" onClick={onToggle}>{open ? "Hide result" : "View result"}</Button>}
        </div>
      </div>
      {c.status !== "approved" && <p className="mt-2 text-sm text-slate-600">{STATUS_REASON[c.status]}</p>}
      {open && c.status === "approved" && (
        <div className="mt-3 rounded-lg bg-emerald-50/60 p-3">
          <ErrorBanner message={result.error} />
          {result.data && (
            <>
              <dl className="grid grid-cols-3 gap-y-1 text-sm">
                {Object.entries(result.data.data).map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="text-slate-500">{LABEL[k as ConsentField]}</dt>
                    <dd className="col-span-2 font-medium">{v}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-xs text-slate-500">Access expires {fmtDate(result.data.expires_at, true)}. Only the approved fields are shown.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
