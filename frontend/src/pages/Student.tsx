import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Copy, ExternalLink, GraduationCap } from "lucide-react";
import { Api } from "../api/endpoints";
import type { ConsentRow, CredentialRow } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useAsync } from "../hooks/useAsync";
import { useToast } from "../components/Toast";
import { Button, Card, EmptyState, ErrorBanner, fmtDate, inputClass, LoadingBlock, PageHeader, StatusChip } from "../components/ui";

const FIELD_LABEL: Record<string, string> = { name: "Name", dob: "Date of birth", programme: "Programme", admission_category: "Admission category", student_code: "Student code" };

export default function StudentWallet() {
  const profile = useAsync(() => Api.myProfile(), []);
  const creds = useAsync(() => Api.myCredentials(), []);
  const consents = useAsync(() => Api.myConsents(), []);
  const p = profile.data;
  const current = creds.data?.[0];
  const pending = (consents.data || []).filter((c) => c.status === "requested");
  const active = (consents.data || []).filter((c) => c.status === "approved");
  const past = (consents.data || []).filter((c) => !["requested", "approved"].includes(c.status));

  return (
    <>
      <PageHeader title="My wallet" subtitle="Your enrolment credential and who can see your data." />
      <ErrorBanner message={profile.error || creds.error || consents.error} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Profile">
          {!p ? <LoadingBlock rows={3} /> : (
            <div className="flex gap-4">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-navy/10 text-navy"><GraduationCap /></div>
              <dl className="grid flex-1 grid-cols-3 gap-y-1.5 text-sm">
                {([["Name", p.name], ["Institution", p.institution_name], ["Programme", p.programme], ["Year", String(p.year)], ["Student code", p.student_code], ["APAAR", p.apaar_id || "missing"]] as [string, string][]).map(([k, v]) => (
                  <div key={k} className="contents">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="col-span-2 font-medium">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </Card>
        <CredentialCard cred={current} loading={creds.loading} />
      </div>
      <Card title={`Consent inbox (${pending.length} pending)`} className="mt-6">
        {consents.loading && !consents.data ? <LoadingBlock rows={2} /> : pending.length === 0 ? (
          <EmptyState title="No pending requests">When an employer or university asks to see your details, the request appears here.</EmptyState>
        ) : (
          <div className="space-y-4">{pending.map((c) => <PendingRequest key={c.id} c={c} onDone={consents.reload} />)}</div>
        )}
      </Card>
      <Card title="Active grants" className="mt-6">
        {active.length === 0 ? <p className="text-sm text-slate-500">You have not granted anyone access right now.</p> : (
          <GrantTable rows={active} onChange={consents.reload} revocable />
        )}
      </Card>
      {past.length > 0 && (
        <Card title="History" className="mt-6">
          <GrantTable rows={past} onChange={consents.reload} />
        </Card>
      )}
    </>
  );
}

function CredentialCard({ cred, loading }: { cred?: CredentialRow; loading: boolean }) {
  const toast = useToast();
  const status = useAsync(() => (cred ? Api.credentialStatus(cred.id) : Promise.resolve(null)), [cred?.id]);
  if (loading) return <Card title="Enrolment credential"><LoadingBlock rows={4} /></Card>;
  if (!cred) return <Card title="Enrolment credential"><EmptyState title="No credential yet">Your institution has not issued a signed credential.</EmptyState></Card>;
  const url = `${window.location.origin}/verify?token=${encodeURIComponent(cred.token)}`;
  const st = status.data?.status ?? cred.status;
  return (
    <Card title="Enrolment credential" actions={<StatusChip status={st} />}>
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        <div className="rounded-lg border bg-white p-3">
          <QRCodeSVG value={url} level="L" size={176} />
        </div>
        <div className="flex-1 space-y-2 text-sm">
          <p className="text-slate-600">Show this QR code to anyone who needs to check your enrolment. They can verify it even without internet.</p>
          <p className="text-xs text-slate-500">Issued {fmtDate(cred.issued_at)} · ID {cred.id.slice(0, 8)}…</p>
          {st === "revoked" && <p className="text-sm font-medium text-sev-high">Revoked: {status.data?.reason}</p>}
          <div className="flex flex-wrap gap-2 pt-2">
            <Button variant="secondary" onClick={() => navigator.clipboard.writeText(cred.token).then(() => toast("Token copied"), () => toast("Copy failed", "error"))}>
              <Copy size={16} /> Copy token
            </Button>
            <a href={url} target="_blank" rel="noreferrer">
              <Button variant="accent"><ExternalLink size={16} /> Open verification page</Button>
            </a>
          </div>
        </div>
      </div>
    </Card>
  );
}

function PendingRequest({ c, onDone }: { c: ConsentRow; onDone: () => void }) {
  const { config } = useAuth();
  const toast = useToast();
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  async function act(fn: () => Promise<unknown>, msg: string) {
    setBusy(true);
    try {
      await fn();
      toast(msg);
      onDone();
    } catch (e) {
      toast((e as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="font-medium">{c.verifier_organisation}</div>
          <div className="text-sm text-slate-600">Purpose: {c.purpose}</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {c.fields.map((f) => <span key={f} className="rounded bg-navy/10 px-2 py-0.5 text-xs text-navy">{FIELD_LABEL[f]}</span>)}
          </div>
        </div>
        <span className="text-xs text-slate-500">{fmtDate(c.created_at, true)}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <div>
          <input className={`${inputClass} w-36`} inputMode="numeric" placeholder="OTP" value={otp} onChange={(e) => setOtp(e.target.value)} aria-label="One-time password" />
          {config?.demo_otp_hint && <div className="mt-1 text-xs text-slate-500">Demo OTP: {config.demo_otp_hint}</div>}
        </div>
        <Button variant="accent" loading={busy} disabled={!otp} onClick={() => act(() => Api.approveConsent(c.id, otp), "Request approved")}>Approve</Button>
        <Button variant="secondary" loading={busy} onClick={() => act(() => Api.denyConsent(c.id), "Request denied")}>Deny</Button>
      </div>
    </div>
  );
}

function GrantTable({ rows, onChange, revocable }: { rows: ConsentRow[]; onChange: () => void; revocable?: boolean }) {
  const toast = useToast();
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs uppercase text-slate-500">
            <th className="px-3 py-2">Organisation</th><th className="px-3 py-2">Fields</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">{revocable ? "Expires" : "Requested"}</th><th />
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id} className="border-b border-slate-100">
              <td className="px-3 py-2"><div className="font-medium">{c.verifier_organisation}</div><div className="text-xs text-slate-500">{c.purpose}</div></td>
              <td className="px-3 py-2 text-xs">{c.fields.map((f) => FIELD_LABEL[f]).join(", ")}</td>
              <td className="px-3 py-2"><StatusChip status={c.status} /></td>
              <td className="px-3 py-2 text-xs">{fmtDate(revocable ? c.expires_at : c.created_at, true)}</td>
              <td className="px-3 py-2 text-right">
                {revocable && (
                  <Button variant="secondary" className="px-3 py-1" onClick={() => Api.revokeConsent(c.id).then(() => { toast("Access revoked"); onChange(); }, (e: Error) => toast(e.message, "error"))}>
                    Revoke
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
