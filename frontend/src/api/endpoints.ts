import { api, qs } from "./client";
import type {
  AppConfig, AuditRow, ChainResult, CollegeAnalytics, CollegeRow, ConsentField, ConsentRow, CredentialPayload,
  CredentialRow, CredentialStatus, FlagRow, LookupResult, MatchRow, Overview, Paged, ProgrammeLedger,
  PublicKeyInfo, RiskRow, StudentProfile, StudentRow, UploadResult, User,
} from "./types";

type Params = Record<string, string | number | boolean | null | undefined>;

export const Api = {
  config: () => api<AppConfig>("/config"),
  login: (username: string, password: string) =>
    api<{ access_token: string; user: User }>("/auth/login", { method: "POST", json: { username, password } }),
  me: () => api<User>("/auth/me"),

  colleges: () => api<CollegeRow[]>("/colleges"),
  college: (id: number) => api<CollegeRow>(`/colleges/${id}`),
  programmes: (id: number) => api<ProgrammeLedger[]>(`/colleges/${id}/programmes`),
  collegeAnalytics: (id: number) => api<CollegeAnalytics>(`/analytics/colleges/${id}`),
  overview: () => api<Overview>("/analytics/overview"),

  uploadStudents: (file: File, dryRun: boolean) => {
    const body = new FormData();
    body.append("file", file);
    return api<UploadResult>(`/students/bulk?dry_run=${dryRun}`, { method: "POST", body });
  },
  myProfile: () => api<StudentProfile>("/students/me"),
  students: (p: Params) => api<Paged<StudentRow>>(`/students${qs(p)}`),

  flags: (p: Params) => api<Paged<FlagRow>>(`/flags${qs(p)}`),
  reviewFlag: (id: number, status: "confirmed" | "dismissed", note: string) =>
    api<FlagRow>(`/flags/${id}`, { method: "PATCH", json: { status, note } }),

  matches: (p: Params) => api<Paged<MatchRow>>(`/matches${qs(p)}`),
  match: (id: number) => api<MatchRow>(`/matches/${id}`),
  reviewMatch: (id: number, status: "confirmed" | "dismissed", note: string) =>
    api<MatchRow>(`/matches/${id}`, { method: "PATCH", json: { status, note } }),

  risk: () => api<RiskRow[]>("/risk/colleges"),
  riskFor: (id: number) => api<RiskRow>(`/risk/colleges/${id}`),

  audit: (p: Params) => api<Paged<AuditRow>>(`/audit${qs(p)}`),
  verifyChain: () => api<ChainResult>("/audit/verify"),
  tamper: () => api<{ entry_id: number }>("/admin/demo/tamper-audit", { method: "POST", json: {} }),
  resetDemo: () => api<{ status: string }>("/admin/demo/reset", { method: "POST" }),
  demoTokens: () => api<{ label: string; token: string }[]>("/admin/demo/tokens"),

  publicKey: () => api<PublicKeyInfo>("/keys/public"),
  credentials: (p: Params) => api<Paged<CredentialRow>>(`/credentials${qs(p)}`),
  myCredentials: () => api<CredentialRow[]>("/credentials/mine"),
  issueCredential: (studentId: number) => api<CredentialRow>(`/credentials/issue/${studentId}`, { method: "POST" }),
  revokeCredential: (cid: string, reason: string) =>
    api<CredentialRow>(`/credentials/${cid}/revoke`, { method: "POST", json: { reason } }),
  credentialStatus: (cid: string) => api<CredentialStatus>(`/credentials/status/${encodeURIComponent(cid)}`),
  verifyCredential: (token: string) =>
    api<{ signature_valid: boolean; status: string | null; payload: CredentialPayload | null }>(
      "/credentials/verify", { method: "POST", json: { token } }),

  lookup: (apaar: string) => api<LookupResult>(`/verify/apaar/${encodeURIComponent(apaar)}`),
  requestConsent: (apaar_id: string, fields: ConsentField[], purpose: string) =>
    api<ConsentRow>("/consents", { method: "POST", json: { apaar_id, fields, purpose } }),
  myConsents: () => api<ConsentRow[]>("/consents/mine"),
  approveConsent: (id: number, otp: string) => api<ConsentRow>(`/consents/${id}/approve`, { method: "POST", json: { otp } }),
  denyConsent: (id: number) => api<ConsentRow>(`/consents/${id}/deny`, { method: "POST" }),
  revokeConsent: (id: number) => api<ConsentRow>(`/consents/${id}/revoke`, { method: "POST" }),
  consentResult: (id: number) =>
    api<{ consent_id: number; expires_at: string; data: Partial<Record<ConsentField, string>> }>(`/consents/${id}/result`),
};
