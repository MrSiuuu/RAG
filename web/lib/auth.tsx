"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "dyneff_token";
const USER_KEY = "dyneff_user";

export type AuthUser = {
  id: number;
  email: string;
  nom: string;
  groupes: string[];
  role: string;
};

type AuthContextValue = {
  token: string | null;
  user: AuthUser | null;
  ready: boolean;
  login: (email: string, motDePasse: string) => Promise<AuthUser>;
  logout: () => void;
  getToken: () => string | null;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem(TOKEN_KEY);
    const uRaw = localStorage.getItem(USER_KEY);
    if (t && uRaw) {
      try {
        setToken(t);
        setUser(JSON.parse(uRaw) as AuthUser);
      } catch {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
    }
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, motDePasse: string) => {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, mot_de_passe: motDePasse }),
    });
    if (!res.ok) {
      throw new Error("Identifiants incorrects");
    }
    const data = (await res.json()) as {
      access_token: string;
      user: AuthUser;
    };
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const getToken = useCallback(() => token ?? localStorage.getItem(TOKEN_KEY), [token]);

  const value = useMemo(
    () => ({ token, user, ready, login, logout, getToken }),
    [token, user, ready, login, logout, getToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans AuthProvider");
  return ctx;
}

export function authHeaders(token: string | null | undefined): HeadersInit {
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}
