import { ReactNode, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  BarChart3, CheckSquare, FileDown, Flag, GitCompare, Home, KeyRound, LogOut, Menu, MessageSquareText, School,
  ScrollText, ShieldCheck, Upload, Users, Wallet, X,
} from "lucide-react";
import type { Role } from "../api/types";
import { ROLE_LABEL, useAuth } from "../auth/AuthContext";
import { cx } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
}

const NAV: Record<Role, NavItem[]> = {
  institution_admin: [
    { to: "/institution", label: "Dashboard", icon: <Home size={18} />, end: true },
    { to: "/institution/upload", label: "Upload students", icon: <Upload size={18} /> },
    { to: "/institution/students", label: "Students", icon: <Users size={18} /> },
    { to: "/institution/flags", label: "Flags", icon: <Flag size={18} /> },
    { to: "/institution/credentials", label: "Credentials", icon: <KeyRound size={18} /> },
  ],
  aicte_officer: [
    { to: "/aicte", label: "Dashboard", icon: <Home size={18} />, end: true },
    { to: "/aicte/colleges", label: "Institutions", icon: <School size={18} /> },
    { to: "/aicte/flags", label: "Flag queue", icon: <Flag size={18} /> },
    { to: "/aicte/matches", label: "Duplicate review", icon: <GitCompare size={18} /> },
    { to: "/aicte/risk", label: "Risk scores", icon: <BarChart3 size={18} /> },
    { to: "/aicte/audit", label: "Audit chain", icon: <ScrollText size={18} /> },
    { to: "/aicte/reports", label: "Reports", icon: <FileDown size={18} /> },
    { to: "/aicte/ask", label: "Ask (beta)", icon: <MessageSquareText size={18} /> },
  ],
  student: [{ to: "/student", label: "My wallet", icon: <Wallet size={18} />, end: true }],
  verifier: [{ to: "/verifier", label: "Verify a student", icon: <CheckSquare size={18} />, end: true }],
};

export function Footer() {
  return (
    <footer className="border-t border-slate-200 px-4 py-3 text-center text-xs text-slate-500 sm:px-6">
      Synthetic demo data. External registries are simulated. Policy values illustrative.
    </footer>
  );
}

export function Brand({ light }: { light?: boolean }) {
  return (
    <div className={cx("flex items-center gap-2 font-semibold", light ? "text-white" : "text-navy")}>
      <ShieldCheck size={22} />
      <span>APAAR Verify</span>
    </div>
  );
}

export default function Layout() {
  const { user, logout, config } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  if (!user) return null;
  const items = NAV[user.role];

  const sidebar = (
    <nav className="flex flex-col gap-1 p-3">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            cx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition", isActive ? "bg-white/15 text-white" : "text-slate-200 hover:bg-white/10")
          }
        >
          {item.icon}
          {item.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-60 shrink-0 flex-col bg-navy lg:flex">
        <div className="px-5 py-4">
          <Brand light />
        </div>
        {sidebar}
      </aside>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setOpen(false)}>
          <aside className="h-full w-64 bg-navy" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4">
              <Brand light />
              <button className="text-white" onClick={() => setOpen(false)} aria-label="Close menu">
                <X size={20} />
              </button>
            </div>
            {sidebar}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <Menu size={22} />
            </button>
            <div className="lg:hidden">
              <Brand />
            </div>
            {config?.demo_mode && (
              <span className="hidden rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-sev-medium ring-1 ring-amber-200 md:inline">
                Demo mode: external registries are simulated
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <div className="hidden text-right sm:block">
              <div className="font-medium text-slate-800">{user.display_name}</div>
            </div>
            <span className="rounded-full bg-navy/10 px-2 py-0.5 text-xs font-medium text-navy">{ROLE_LABEL[user.role]}</span>
            <button
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-slate-600 hover:bg-slate-100"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <Footer />
      </div>
    </div>
  );
}
