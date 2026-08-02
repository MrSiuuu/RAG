"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Upload,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  if (!user) return null;

  const initial = (user.nom?.trim()?.[0] || "?").toUpperCase();

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-[var(--sidebar-hover)]"
        aria-expanded={open}
      >
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
          style={{ backgroundColor: "var(--accent-blue)" }}
        >
          {initial}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-[var(--sidebar-text)]">
          {user.nom}
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-[var(--sidebar-muted)] transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 z-20 mb-1 overflow-hidden rounded-md border border-[var(--sidebar-hover)] bg-[var(--sidebar-bg)] py-1 shadow-none">
          {user.role === "admin" && (
            <Link
              href="/admin"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)]"
            >
              <LayoutDashboard className="h-4 w-4 text-[var(--sidebar-muted)]" />
              Tableau de bord
            </Link>
          )}
          <Link
            href="/upload"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)]"
          >
            <Upload className="h-4 w-4 text-[var(--sidebar-muted)]" />
            Importer un document
          </Link>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              logout();
              router.replace("/login");
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)]"
          >
            <LogOut className="h-4 w-4 text-[var(--sidebar-muted)]" />
            Se déconnecter
          </button>
        </div>
      )}
    </div>
  );
}
