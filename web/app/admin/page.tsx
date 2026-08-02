"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, MessageSquare, Upload } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { DashboardAnalytics } from "@/components/dashboard/analytics";

export default function AdminPage() {
  const { user, ready, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.role !== "admin") {
      router.replace("/");
    }
  }, [ready, user, router]);

  if (!ready || !user || user.role !== "admin") {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-[var(--muted)]">
        Chargement…
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-5xl flex-col px-4 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] pb-4">
        <div>
          <p className="text-2xl font-semibold text-[var(--text)]">
            Administration
          </p>
          <p className="text-sm text-[var(--text-muted)]">{user.nom}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/upload"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--ink)] hover:bg-[var(--wash)]"
          >
            <Upload className="h-3.5 w-3.5" />
            Upload
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--ink)] hover:bg-[var(--wash)]"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Chat
          </Link>
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:bg-[var(--wash)]"
          >
            <LogOut className="h-3.5 w-3.5" />
            Quitter
          </button>
        </div>
      </header>

      <DashboardAnalytics />
    </div>
  );
}
