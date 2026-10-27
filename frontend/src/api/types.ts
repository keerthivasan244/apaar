export type Role = "institution_admin" | "aicte_officer" | "student" | "verifier";

export interface User {
  id: number;
  username: string;
  role: Role;
  display_name: string;
  college_id: number | null;
  student_id: number | null;
  organisation?: string | null;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Policy {
  academic_year: number;
  apaar_regex: string;
  intake_categories: string[];
  supernumerary_cap_pct: Record<string, number>;
  levels: string[];
  shifts: string[];
  genders: string[];
  social_categories: string[];
}

export interface AppConfig {
  demo_mode: boolean;
  demo_otp_hint: string | null;
  academic_year: number;
  policy: Policy;
}

export interface SupernumeraryUse {
  count: number;
  cap: number;
  over_by: number;
}

export interface ProgrammeLedger {
  id: number;
  college_id: number;
  name: string;
  level: string;
  shift: string;
  approved_intake: number;
  admitted: number;
  over_by: number;
  supernumerary: Record<string, SupernumeraryUse>;
  total_enrolled: number;
}

export interface CodeCount {
  code: string;
  count: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface CollegeAnalytics {
  programmes: ProgrammeLedger[];
  category_breakdown: CategoryCount[];
  flags_by_code: CodeCount[];
  totals: {
    students: number;
    open_flags: number;
    programmes: number;
    programmes_over_intake: number;
    approved_intake: number;
    admitted: number;
  };
}

export interface Issue {
  code: string;
  field: string;
  message: string;
  hint: string;
  severity: string;
}

export interface UploadRow {
  row: number;
  status: "ok" | "warning" | "error";
  issues: Issue[];
  data: { student_code: string; name: string };
}

export interface UploadResult {
  dry_run: boolean;
  summary: { total: number; ok: number; warnings: number; errors: number };
  rows: UploadRow[];
  batch_id: number | null;
  new_flags: number | null;
  new_matches: number | null;
  rows_saved?: number;
  rows_skipped?: number;
}

export interface StudentRow {
  id: number;
  student_code: string;
  name: string;
  apaar_id: string | null;
  college_id: number;
  college_name: string;
  programme: string;
  programme_id: number | null;
  level: string;
  year: number;
  status: string;
  gender: string;
  admission_category: string;
  social_category: string;
  open_flags: string[];
}

export interface Counterpart {
  student_id: number;
  name: string;
  student_code: string;
  college_id: number;
  college_name: string;
}

export interface FlagRow {
  id: number;
  code: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  status: string;
  evidence: Record<string, unknown>;
  counterpart: Counterpart | string | null;
  student: { id: number; name: string; student_code: string } | null;
  college_id: number;
  college_name: string;
  programme: string | null;
  match_id: number | null;
  created_at: string;
  age_days: number;
  reviewed_by: string | null;
  reviewed_at: string | null;
  note: string | null;
}

export interface MatchSide {
  id: number;
  name: string;
  student_code: string;
  college_id: number;
  college_name: string;
  father_name?: string;
  dob?: string;
  gender?: string;
  apaar_id?: string | null;
  phone_last4?: string | null;
  programme?: string;
  college_aicte_id?: string;
}

export interface MatchComponent {
  value_a: string | null;
  value_b: string | null;
  similarity: number | null;
  base_weight: number;
  weight: number;
  contribution: number;
  excluded: boolean;
}

export interface MatchRow {
  id: number;
  score: number;
  band: "probable" | "review";
  status: "pending" | "confirmed" | "dismissed";
  student_a: MatchSide;
  student_b: MatchSide;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  note: string | null;
  top_explanation?: string | null;
  components?: Record<string, MatchComponent>;
  explanations?: string[];
}

export interface CollegeRow {
  id: number;
  aicte_id: string;
  name: string;
  city: string;
  state: string;
  type: string;
  prev_year_enrolment: number;
  students?: number;
  open_flags?: number;
  risk_score?: number;
  risk_band?: Band;
  top_reason?: string | null;
}

export type Band = "low" | "medium" | "high";

export interface RiskComponent {
  value: number;
  weight: number;
  contribution: number;
}

export interface RiskRow {
  college_id: number;
  aicte_id: string;
  name: string;
  state: string;
  score: number;
  band: Band;
  components: Record<string, RiskComponent>;
  reasons: string[];
  facts: Record<string, number>;
  disclaimer?: string;
}

export interface AuditRow {
  id: number;
  ts: string;
  actor: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  hash: string;
  prev_hash?: string;
  payload?: Record<string, unknown>;
}

export interface Overview {
  totals: {
    colleges: number;
    students: number;
    open_flags: number;
    pending_matches: number;
    high_risk_colleges: number;
  };
  flags_by_code: CodeCount[];
  category_breakdown: CategoryCount[];
  top_over_intake: { college_id: number; college: string; approved: number; admitted: number; excess: number }[];
  top_risk: { college_id: number; name: string; score: number; band: Band; top_reason: string | null }[];
  recent_audit: AuditRow[];
}

export interface CredentialRow {
  id: string;
  student_id: number;
  student_name: string;
  student_code: string;
  token: string;
  kid: string;
  issued_at: string;
  cid: string;
  status: "valid" | "revoked" | "unknown";
  revoked_at: string | null;
  reason: string | null;
}

export interface CredentialPayload {
  v: number;
  cid: string;
  sid: string;
  apaar: string | null;
  inst: string;
  inst_name: string;
  prog: string;
  yr: number;
  status: string;
  iat: number;
  kid: string;
}

export interface PublicKeyInfo {
  kid: string;
  algorithm: string;
  public_key_b64: string;
}

export interface CredentialStatus {
  cid: string;
  status: "valid" | "revoked" | "unknown";
  revoked_at: string | null;
  reason: string | null;
}

export type ConsentField = "name" | "dob" | "programme" | "admission_category" | "student_code";

export interface ConsentRow {
  id: number;
  purpose: string;
  fields: ConsentField[];
  status: "requested" | "approved" | "denied" | "revoked" | "expired";
  created_at: string;
  approved_at: string | null;
  expires_at: string | null;
  verifier_organisation: string | null;
  verifier_name: string;
  apaar_id?: string;
  institution_name?: string;
}

export interface LookupResult {
  found: boolean;
  enrolment_status: string | null;
  institution_name: string | null;
  programme: string | null;
  year: number | null;
}

export interface ChainResult {
  intact: boolean;
  entries_checked: number;
  first_broken_id: number | null;
}

export interface StudentProfile {
  id: number;
  name: string;
  student_code: string;
  apaar_id: string | null;
  institution_name: string;
  aicte_id: string;
  programme: string;
  year: number;
  status: string;
}
