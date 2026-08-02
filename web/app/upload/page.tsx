"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutDashboard, LogOut, MessageSquare } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { UploadDoc } from "@/components/upload-doc";

export default function UploadPage() {
  const { user, ready, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-sm text-[var(--muted)]">
        Chargement…
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col px-4 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] pb-4">
        <div>
          <p className="text-2xl font-semibold text-[var(--text)]">
            Déposer un document
          </p>
          <p className="text-sm text-[var(--text-muted)]">
            Self-service — indexation automatique par service
          </p>
        </div>
        <div className="flex items-center gap-2">
          {user.role === "admin" && (
            <Link
              href="/admin"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--ink)] hover:bg-[var(--wash)]"
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              Admin
            </Link>
          )}
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

      <UploadDoc />
    </div>
  );
}
