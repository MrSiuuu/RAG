"use client";

import { useState } from "react";
import { FileText, ChevronDown } from "lucide-react";
import type { Source } from "@/lib/types";

export function Sources({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {sources.map((s, i) => (
        <SourceCard key={s.chunk_id ?? i} source={s} index={i + 1} />
      ))}
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [open, setOpen] = useState(false);
  const label = [
    source.document,
    source.section,
    source.page != null && source.page !== "" ? `p.${source.page}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="max-w-full rounded-md border border-[var(--line)] bg-[var(--surface)] text-xs shadow-[0_1px_0_rgba(11,45,42,0.04)]">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex max-w-full items-center gap-1.5 px-2.5 py-1.5 text-left transition-colors hover:bg-[var(--wash)]"
      >
        <FileText className="h-3.5 w-3.5 shrink-0 text-[var(--ember)]" />
        <span className="font-semibold tabular-nums text-[var(--ink)]">{index}.</span>
        <span className="truncate text-[var(--ink)]/80">{label}</span>
        <ChevronDown
          className={`h-3 w-3 shrink-0 text-[var(--muted)] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="max-w-md border-t border-[var(--line)] px-2.5 py-2 leading-relaxed text-[var(--muted)]">
          {source.extrait}
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block text-[var(--ember)] underline underline-offset-2"
            >
              Ouvrir la source
            </a>
          )}
        </div>
      )}
    </div>
  );
}
