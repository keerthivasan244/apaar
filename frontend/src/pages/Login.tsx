import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Building2, GraduationCap, Landmark, SearchCheck, ShieldCheck } from "lucide-react";
import { ROLE_HOME, useAuth } from "../auth/AuthContext";
import { Button, ErrorBanner, Field, inputClass } from "../components/ui";
import { Footer } from "../components/Layout";

const DEMO_ACCOUNTS = [
  { username: "inst_a", label: "Institution (Greenfield)", icon: <Building2 size={16} /> },
  { username: "inst_b", label: "Institution (Lakeview)", icon: <Building2 size={16} /> },
  { username: "officer", label: "AICTE officer", icon: <Landmark size={16} /> },
  { username: "student", label: "Student (Ananya Rao)", icon: <GraduationCap size={16} /> },
  { username: "verifier", label: "Verifier (Acme Hiring)", icon: <SearchCheck size={16} /> },
];

export default function Login() {
  const { user, login, config } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await login(username.trim(), password);
      navigate(ROLE_HOME[u.role], { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-lg md:grid-cols-2">
          <div className="hidden flex-col justify-between bg-navy p-8 text-white md:flex">
            <div className="flex items-center gap-2 text-xl font-semibold">
              <ShieldCheck /> APAAR Verify
            </div>
            <div>
              <p className="text-lg font-medium">Trusted enrolment data for AICTE-approved institutions.</p>
              <ul className="mt-4 space-y-2 text-sm text-slate-200">
                <li>• Fuzzy duplicate detection with explanations</li>
                <li>• Explainable institution risk scores</li>
                <li>• Ed25519-signed credentials, verifiable offline</li>
                <li>• Tamper-evident audit chain and consent</li>
              </ul>
            </div>
            <p className="text-xs text-slate-300">SIH 2026 · PS SIH26263 · Demo build</p>
          </div>
          <div className="p-8">
            <h1 className="text-2xl font-semibold text-navy">Sign in</h1>
            <p className="mt-1 text-sm text-slate-600">Use your username, not an email address.</p>
            <form className="mt-6 space-y-4" onSubmit={submit}>
              <ErrorBanner message={error} />
              <Field label="Username">
                <input className={inputClass} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
              </Field>
              <Field label="Password">
                <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              </Field>
              <Button type="submit" loading={busy} className="w-full">
                Sign in
              </Button>
            </form>
            {config?.demo_mode && (
              <div className="mt-6">
                <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Demo accounts (password demo123)</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {DEMO_ACCOUNTS.map((a) => (
                    <button
                      key={a.username}
                      type="button"
                      onClick={() => {
                        setUsername(a.username);
                        setPassword("demo123");
                      }}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:border-navy hover:text-navy"
                    >
                      {a.icon}
                      {a.label}
                    </button>
                  ))}
                </div>
                <a href="/verify" className="mt-4 inline-block text-sm text-teal underline">
                  Public credential verification page →
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
