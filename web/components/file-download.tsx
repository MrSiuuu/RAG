"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function FileDownload({
  id,
  filename,
}: {
  id: string;
  filename: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      // Cross-origin : l'attribut HTML `download` est ignoré par le navigateur.
      // On fetch le blob puis on déclenche le save côté client.
      const res = await fetch(`${API_URL}/api/files/${id}`);
      if (res.status === 404) {
        setError(
          "Fichier introuvable — regénérez le document (mémoire API vidée au reload).",
        );
        return;
      }
      if (!res.ok) {
        setError(`Téléchargement impossible (${res.status})`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "document.docx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("Erreur réseau — vérifiez que l'API tourne sur :8000");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => void download()}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--text)] transition-colors hover:border-[var(--accent-blue)]/40 hover:bg-[var(--wash)] disabled:opacity-50"
      >
        {busy ? (
          <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[var(--accent-blue)]" />
        ) : (
          <FileDown className="h-4 w-4 shrink-0 text-[var(--accent-blue)]" />
        )}
        <span className="font-medium">Télécharger le document</span>
        <span className="text-[var(--text-muted)]">· {filename}</span>
      </button>
      {error && (
        <p className="mt-2 text-xs text-red-700">{error}</p>
      )}
    </div>
  );
}
