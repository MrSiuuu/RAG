"use client";

import { useState } from "react";
import { Check, ChevronDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatusSteps({
  steps,
  collapsed,
  summary,
}: {
  steps: string[];
  collapsed?: boolean;
  summary?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!steps.length && !summary) return null;

  if (collapsed && !expanded) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="mb-2 flex items-center gap-2 text-xs text-[var(--text-muted)] hover:text-[var(--text)]"
      >
        <Check className="h-3.5 w-3.5 text-[var(--accent-blue)]" />
        <span>{summary || "Recherche effectuée"}</span>
        <ChevronDown className="h-3 w-3 opacity-50" />
      </button>
    );
  }

  return (
    <div className="mb-3">
      {collapsed && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="mb-1.5 flex items-center gap-2 text-xs text-[var(--text-muted)]"
        >
          <Check className="h-3.5 w-3.5 text-[var(--accent-blue)]" />
          <span>{summary || "Recherche effectuée"}</span>
          <ChevronDown className="h-3 w-3 rotate-180 opacity-50" />
        </button>
      )}
      <ul className="space-y-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2.5">
        {steps.map((label, i) => {
          const last = i === steps.length - 1 && !collapsed;
          return (
            <li
              key={`${i}-${label}`}
              className={cn(
                "flex items-center gap-2 text-xs",
                last ? "text-[var(--text)]" : "text-[var(--text-muted)]",
              )}
            >
              {last ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent-blue)]" />
              ) : (
                <Check className="h-3.5 w-3.5 text-[var(--accent-blue)]" />
              )}
              <span>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
