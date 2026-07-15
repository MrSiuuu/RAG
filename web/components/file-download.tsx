"use client";

import { FileDown } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function FileDownload({
  id,
  filename,
}: {
  id: string;
  filename: string;
}) {
  return (
    <a
      href={`${API_URL}/api/files/${id}`}
      download={filename}
      className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] shadow-[0_1px_0_rgba(11,45,42,0.04)] transition-colors hover:border-[var(--ember)]/40 hover:bg-[var(--wash)]"
    >
      <FileDown className="h-4 w-4 shrink-0 text-[var(--ember)]" />
      <span className="font-medium">{filename}</span>
      <span className="text-[var(--muted)]">· Télécharger</span>
    </a>
  );
}
