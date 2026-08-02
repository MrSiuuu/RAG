"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const DEMO = [
  { label: "Collaborateur", email: "paul@dyneff.fr", role: "Utilisateur" },
  { label: "Admin", email: "admin@dyneff.fr", role: "Administration" },
] as const;

const DEMO_PASSWORD = "demo1234";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const doLogin = async (e: string, p: string) => {
    setLoading(true);
    setError(null);
    try {
      const user = await login(e, p);
      router.replace(user.role === "admin" ? "/admin" : "/");
    } catch {
      setError("Identifiants incorrects");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (ev: FormEvent) => {
    ev.preventDefault();
    void doLogin(email.trim(), password);
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-[var(--bg)] px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <p className="text-4xl font-semibold tracking-tight text-[var(--text)]">
            Dyneff
          </p>
          <p className="mt-2 text-sm text-[var(--text-muted)]">
            Connexion à l&apos;assistant interne
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6"
        >
          <label className="block text-xs font-medium text-[var(--text-muted)]">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent-blue)]/50"
            />
          </label>
          <label className="mt-4 block text-xs font-medium text-[var(--text-muted)]">
            Mot de passe
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-[var(--accent-blue)]/50"
            />
          </label>

          {error && <p className="mt-3 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-5 w-full rounded-md bg-[var(--accent-blue)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            {loading ? "Connexion…" : "Se connecter"}
          </button>
        </form>

        <div className="mt-6">
          <p className="mb-2 text-center text-xs uppercase tracking-wide text-[var(--text-muted)]">
            Accès démo
          </p>
          <div className="grid gap-2">
            {DEMO.map((d) => (
              <button
                key={d.email}
                type="button"
                disabled={loading}
                onClick={() => void doLogin(d.email, DEMO_PASSWORD)}
                className="flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left text-sm transition-colors hover:border-[var(--accent-blue)]/40 hover:bg-[var(--wash)] disabled:opacity-50"
              >
                <span className="font-medium text-[var(--text)]">{d.label}</span>
                <span className="text-xs text-[var(--text-muted)]">{d.role}</span>
              </button>
            ))}
          </div>
          <p className="mt-3 text-center text-xs text-[var(--text-muted)]">
            Mot de passe démo : demo1234
          </p>
        </div>
      </div>
    </div>
  );
}
