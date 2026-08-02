"use client";

import { useState } from "react";
import { FileText, Globe, ChevronDown } from "lucide-react";
import type { Source } from "@/lib/types";

export function Sources({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {sources.map((s, i) => (
        <SourceCard
          key={`${s.type ?? "interne"}-${s.chunk_id ?? i}`}
          source={s}
          index={i + 1}
        />
      ))}
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [open, setOpen] = useState(false);
  const isWeb = source.type === "web";

  const label = [
    source.document,
    !isWeb ? source.section : null,
    !isWeb && source.page != null && source.page !== ""
      ? `p.${source.page}`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  if (isWeb && source.url) {
    return (
      <a
        href={source.url}
        target="_blank"
        rel="noreferrer"
        className="flex max-w-full items-center gap-1.5 rounded-md border border-[color-mix(in_srgb,var(--web)_35%,transparent)] bg-[color-mix(in_srgb,var(--web)_8%,white)] px-2.5 py-1.5 text-xs text-[var(--text)] transition-colors hover:bg-[color-mix(in_srgb,var(--web)_14%,white)]"
      >
        <Globe className="h-3.5 w-3.5 shrink-0 text-[var(--web)]" />
        <span className="font-semibold tabular-nums text-[var(--web)]">
          {index}.
        </span>
        <span className="truncate text-[var(--text)]/80">
          {label || source.url}
        </span>
      </a>
    );
  }

  return (
    <div className="max-w-full rounded-md border border-[color-mix(in_srgb,var(--accent-blue)_25%,var(--border))] bg-[var(--surface)] text-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex max-w-full items-center gap-1.5 px-2.5 py-1.5 text-left transition-colors hover:bg-[var(--wash)]"
      >
        <FileText className="h-3.5 w-3.5 shrink-0 text-[var(--accent-blue)]" />
        <span className="font-semibold tabular-nums text-[var(--accent-blue)]">
          {index}.
        </span>
        <span className="truncate text-[var(--text)]/80">{label}</span>
        <ChevronDown
          className={`h-3 w-3 shrink-0 text-[var(--text-muted)] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="max-w-md border-t border-[var(--border)] px-2.5 py-2 leading-relaxed text-[var(--text-muted)]">
          {source.extrait}
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block text-[var(--accent-blue)] underline underline-offset-2"
            >
              Ouvrir la source
            </a>
          )}
        </div>
      )}
    </div>
  );
}
