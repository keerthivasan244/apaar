import { ButtonHTMLAttributes, ReactNode, useEffect } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, Inbox, Loader2, X } from "lucide-react";
import type { Band } from "../api/types";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold text-navy">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, children, className, actions }: { title?: ReactNode; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5", className)}>
      {(title || actions) && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-base font-semibold text-slate-800">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

type Variant = "primary" | "secondary" | "danger" | "ghost" | "accent";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-navy text-white hover:bg-navy-light",
  accent: "bg-teal text-white hover:bg-teal-light",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50",
  danger: "bg-sev-high text-white hover:opacity-90",
  ghost: "text-navy hover:bg-slate-100",
};

export function Button({
  variant = "primary", loading, className, children, disabled, ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
    >
      {loading && <Loader2 size={16} className="animate-spin" />}
      {children}
    </button>
  );
}

const SEVERITY_STYLE: Record<string, string> = {
  low: "bg-slate-100 text-slate-700",
  medium: "bg-amber-50 text-sev-medium ring-1 ring-amber-200",
  high: "bg-red-50 text-sev-high ring-1 ring-red-200",
  critical: "bg-sev-critical text-white",
  error: "bg-red-50 text-sev-high ring-1 ring-red-200",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={cx("inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize", SEVERITY_STYLE[severity] || SEVERITY_STYLE.low)}>{severity}</span>;
}

const STATUS_STYLE: Record<string, string> = {
  open: "bg-amber-50 text-sev-medium",
  pending: "bg-amber-50 text-sev-medium",
  requested: "bg-amber-50 text-sev-medium",
  confirmed: "bg-red-50 text-sev-high",
  dismissed: "bg-slate-100 text-slate-600",
  resolved_auto: "bg-slate-100 text-slate-600",
  approved: "bg-emerald-50 text-teal",
  valid: "bg-emerald-50 text-teal",
  ok: "bg-emerald-50 text-teal",
  active: "bg-emerald-50 text-teal",
  warning: "bg-amber-50 text-sev-medium",
  error: "bg-red-50 text-sev-high",
  denied: "bg-red-50 text-sev-high",
  revoked: "bg-red-50 text-sev-high",
  expired: "bg-slate-100 text-slate-600",
  unknown: "bg-slate-100 text-slate-600",
};

export function StatusChip({ status }: { status: string }) {
  return (
    <span className={cx("inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize", STATUS_STYLE[status] || "bg-slate-100 text-slate-700")}>
      {status.replace("_", " ")}
    </span>
  );
}

export const BAND_COLOR: Record<Band, string> = { low: "#15803D", medium: "#B7791F", high: "#C0392B" };

export function RiskChip({ score, band }: { score: number; band: Band }) {
  const style = { low: "bg-emerald-50 text-emerald-700 ring-emerald-200", medium: "bg-amber-50 text-sev-medium ring-amber-200", high: "bg-red-50 text-sev-high ring-red-200" }[band];
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ring-1", style)}>
      {score}
      <span className="font-normal capitalize">{band}</span>
    </span>
  );
}

export function KpiTile({ label, value, to, tone = "navy", icon }: { label: string; value: ReactNode; to?: string; tone?: "navy" | "red" | "amber" | "teal"; icon?: ReactNode }) {
  const toneClass = { navy: "text-navy", red: "text-sev-high", amber: "text-sev-medium", teal: "text-teal" }[tone];
  const body = (
    <div className="flex h-full items-start justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-navy/40 hover:shadow">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
        <div className={cx("mt-1 text-3xl font-semibold", toneClass)}>{value}</div>
      </div>
      {icon && <div className="text-slate-300">{icon}</div>}
    </div>
  );
  return to ? <Link to={to} className="block">{body}</Link> : body;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded bg-slate-200", className)} />;
}

export function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-slate-500">
      <Inbox size={32} className="text-slate-300" />
      <div className="font-medium text-slate-700">{title}</div>
      {children && <div className="max-w-md text-sm">{children}</div>}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }: { message: string | null; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div className="mb-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-sev-high" role="alert">
      <AlertCircle size={18} className="mt-0.5 shrink-0" />
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button className="font-medium underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function ProgressBar({ value, max = 1, color = "#1F3A5F", className }: { value: number; max?: number; color?: string; className?: string }) {
  const pct = Math.max(0, Math.min(100, (value / (max || 1)) * 100));
  return (
    <div className={cx("h-2 w-full overflow-hidden rounded-full bg-slate-100", className)}>
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function Modal({ open, title, onClose, children, footer }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className="w-full max-w-lg rounded-xl bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h3 className="font-semibold text-slate-800">{title}</h3>
          <button onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/20";

export function Select({ value, onChange, options, label }: { value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; label: string }) {
  return (
    <select aria-label={label} className={cx(inputClass, "w-auto")} value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export function fmtDate(iso: string | null | undefined, withTime = false) {
  if (!iso) return "–";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return withTime ? d.toLocaleString() : d.toLocaleDateString();
}

export const CODE_LABEL: Record<string, string> = {
  MISSING_APAAR: "Missing APAAR",
  INVALID_APAAR_FORMAT: "Invalid APAAR",
  DUP_SAME_COLLEGE: "Duplicate (same college)",
  DUP_CROSS_COLLEGE: "Duplicate (cross college)",
  PROBABLE_DUP: "Probable duplicate",
  INTAKE_EXCEEDED: "Intake exceeded",
  SUPERNUMERARY_EXCEEDED: "Supernumerary exceeded",
  UNAPPROVED_PROGRAMME: "Unapproved programme",
  CATEGORY_INCONSISTENT: "Category inconsistent",
  DOB_IMPLAUSIBLE: "Implausible DOB",
};
