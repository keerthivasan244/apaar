import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, CloudOff, HelpCircle, ShieldCheck, ShieldX, WifiOff } from "lucide-react";
import { Api } from "../api/endpoints";
import type { CredentialStatus, PublicKeyInfo } from "../api/types";
import { Brand, Footer } from "../components/Layout";
import { Button, Card, fmtDate, inputClass, StatusChip } from "../components/ui";
import { cachedKey, cacheKey, tokenFromInput, verifyToken, VerifyOutcome } from "../lib/credential";

export default function PublicVerify() {
  const [params] = useSearchParams();
  const [input, setInput] = useState(params.get("token") || "");
  const [key, setKey] = useState<PublicKeyInfo | null>(cachedKey);
  const [offline, setOffline] = useState(false);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<VerifyOutcome | null>(null);
  const [revocation, setRevocation] = useState<CredentialStatus | "error" | null>(null);
  const [checking, setChecking] = useState(false);
  const [samples, setSamples] = useState<{ label: string; token: string }[]>([]);

  useEffect(() => {
    Api.publicKey()
      .then((k) => {
        cacheKey(k);
        setKey(k);
        setOffline(false);
      })
      .catch(() => {
        setOffline(true);
        if (!cachedKey()) setKeyError("The public key could not be fetched and none is cached. Open this page once while online.");
      });
    Api.demoTokens().then(setSamples).catch(() => setSamples([]));
  }, []);

  const token = tokenFromInput(input);

  function verify() {
    if (!key) return;
    setRevocation(null);
    setOutcome(verifyToken(token, key));
  }

  async function checkRevocation() {
    if (!outcome?.payload) return;
    setChecking(true);
    try {
      setRevocation(await Api.credentialStatus(outcome.payload.cid));
    } catch {
      setRevocation("error");
    } finally {
      setChecking(false);
    }
  }

  const p = outcome?.payload;
  return (
    <div className="flex min-h-full flex-col">
      <header className="flex items-center justify-between border-b bg-white px-4 py-3 sm:px-6">
        <Brand />
        <div className="flex items-center gap-3 text-sm">
          {offline && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-sev-medium ring-1 ring-amber-200">
              <WifiOff size={14} /> Offline mode (cached key)
            </span>
          )}
          <Link to="/login" className="text-teal underline">Sign in</Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
        <h1 className="text-2xl font-semibold text-navy">Verify an enrolment credential</h1>
        <p className="mt-1 text-sm text-slate-600">
          The signature is checked in your browser with the published Ed25519 key, so it works without a connection.
        </p>
        <Card className="mt-6">
          <label className="block text-sm font-medium text-slate-700" htmlFor="token">Credential token or verification link</label>
          <textarea id="token" className={`${inputClass} mt-1 font-mono text-xs`} rows={4} value={input} onChange={(e) => { setInput(e.target.value); setOutcome(null); setRevocation(null); }} placeholder="Paste a token (payload.signature) or scan the QR code" />
          {samples.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="text-slate-500">Demo tokens:</span>
              {samples.map((s) => (
                <button key={s.token} className="rounded-full border px-2 py-0.5 hover:border-navy" onClick={() => { setInput(s.token); setOutcome(null); setRevocation(null); }}>
                  {s.label}
                </button>
              ))}
            </div>
          )}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button onClick={verify} disabled={!key || !token}>
              <ShieldCheck size={16} /> Verify signature
            </Button>
            {key && <span className="text-xs text-slate-500">Key {key.kid} · {key.algorithm}</span>}
          </div>
          {keyError && <p className="mt-3 text-sm text-sev-high">{keyError}</p>}
        </Card>

        {outcome && (
          <Card className={`mt-6 ${outcome.valid ? "border-teal/50" : "border-red-300"}`}>
            {outcome.valid && p ? (
              <>
                <div className="flex items-center gap-2 text-lg font-semibold text-teal">
                  <CheckCircle2 /> Signature valid
                </div>
                <dl className="mt-4 grid grid-cols-3 gap-y-2 text-sm">
                  {([
                    ["Institution", `${p.inst_name} (${p.inst})`],
                    ["Programme", p.prog],
                    ["Academic year", String(p.yr)],
                    ["Student code", p.sid],
                    ["APAAR", p.apaar || "not recorded"],
                    ["Status at issue", p.status],
                    ["Issued", fmtDate(new Date(p.iat * 1000).toISOString(), true)],
                    ["Credential ID", p.cid],
                  ] as [string, string][]).map(([k, v]) => (
                    <div key={k} className="contents">
                      <dt className="text-slate-500">{k}</dt>
                      <dd className="col-span-2 break-all font-medium">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-5 border-t pt-4">
                  <Button variant="secondary" onClick={checkRevocation} loading={checking}>
                    Check revocation (needs connection)
                  </Button>
                  {revocation === "error" && (
                    <p className="mt-3 flex items-center gap-2 text-sm text-sev-medium"><CloudOff size={16} /> Could not check revocation. You may be offline.</p>
                  )}
                  {revocation && revocation !== "error" && (
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                      <StatusChip status={revocation.status} />
                      {revocation.status === "valid" && <span>Not revoked.</span>}
                      {revocation.status === "revoked" && (
                        <span className="font-medium text-sev-high">Revoked on {fmtDate(revocation.revoked_at)}: {revocation.reason}</span>
                      )}
                      {revocation.status === "unknown" && <span>The issuer has no record of this credential.</span>}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div>
                <div className="flex items-center gap-2 text-lg font-semibold text-sev-high">
                  <ShieldX /> Signature invalid, record may be tampered
                </div>
                {outcome.reason && <p className="mt-1 text-sm text-slate-600">{outcome.reason}</p>}
              </div>
            )}
          </Card>
        )}
        <p className="mt-6 flex items-start gap-2 text-xs text-slate-500">
          <HelpCircle size={14} className="mt-0.5 shrink-0" />
          A valid signature proves the issuer created this exact record. Revocation is separate: a credential can be validly signed and later revoked
          (for example when a student withdraws), which only the issuer's server can tell you.
        </p>
      </main>
      <Footer />
    </div>
  );
}
