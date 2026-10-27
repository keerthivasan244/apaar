import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getToken, onUnauthorized, setToken } from "../api/client";
import { Api } from "../api/endpoints";
import type { AppConfig, Role, User } from "../api/types";

const USER_KEY = "apaar.user";

interface AuthValue {
  user: User | null;
  config: AppConfig | null;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export const ROLE_HOME: Record<Role, string> = {
  institution_admin: "/institution",
  aicte_officer: "/aicte",
  student: "/student",
  verifier: "/verifier",
};

export const ROLE_LABEL: Record<Role, string> = {
  institution_admin: "Institution admin",
  aicte_officer: "AICTE officer",
  student: "Student",
  verifier: "Verifier",
};

function storedUser(): User | null {
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw && getToken() ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(storedUser);
  const [config, setConfig] = useState<AppConfig | null>(null);

  useEffect(() => {
    Api.config().then(setConfig).catch(() => setConfig(null));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    try {
      sessionStorage.removeItem(USER_KEY);
    } catch {
      /* ignore */
    }
    setUser(null);
  }, []);

  useEffect(() => onUnauthorized(logout), [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await Api.login(username, password);
    setToken(res.access_token);
    try {
      sessionStorage.setItem(USER_KEY, JSON.stringify(res.user));
    } catch {
      /* ignore */
    }
    setUser(res.user);
    return res.user;
  }, []);

  const value = useMemo(() => ({ user, config, login, logout }), [user, config, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
