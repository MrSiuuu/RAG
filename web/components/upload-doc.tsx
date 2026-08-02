"use client";

import { useEffect, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { authHeaders, useAuth } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ServiceOpt = { id: string; label: string; groups: string[] };

export function UploadDoc() {
  const { getToken } = useAuth();
  const [services, setServices] = useState<ServiceOpt[]>([]);
  const [service, setService] = useState("cse");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    document: string;
    nb_enfants: number;
    label: string;
  } | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    void fetch(`${API_URL}/api/admin/services`, {
      headers: authHeaders(token),
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: ServiceOpt[]) => setServices(data))
      .catch(() => undefined);
  }, [getToken]);

  const submit = async () => {
    if (!file) return;
    const token = getToken();
    if (!token) {
      setError("Session expirée — reconnectez-vous");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("service", service);
      fd.append("sensibilite", "interne");
      const res = await fetch(`${API_URL}/api/admin/ingest`, {
        method: "POST",
        headers: authHeaders(token),
        body: fd,
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult({
        document: data.document,
        nb_enfants: data.nb_enfants,
        label: data.label,
      });
      setFile(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'indexation");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl">
      <h2 className="text-xl font-semibold text-[var(--text)]">
        Ajouter un document
      </h2>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        Déposez un fichier .md ou .pdf. Il sera découpé, vectorisé et indexé
        pour le service choisi.
      </p>

      <div className="mt-6 space-y-4 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
        <label className="block text-xs font-medium text-[var(--muted)]">
          Service
          <select
            value={service}
            onChange={(e) => setService(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--paper)] px-3 py-2 text-sm text-[var(--ink)]"
          >
            {(services.length
              ? services
              : [{ id: "cse", label: "CSE", groups: [] }]
            ).map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--line)] bg-[var(--paper)] px-4 py-10 text-sm text-[var(--muted)] transition-colors hover:border-[var(--ember)]/50 hover:bg-[var(--wash)]">
          <FileUp className="h-6 w-6 text-[var(--ember)]" />
          <span>
            {file ? file.name : "Glisser un fichier ou cliquer pour choisir"}
          </span>
          <input
            type="file"
            accept=".md,.pdf,text/markdown,application/pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <button
          type="button"
          disabled={!file || loading}
          onClick={() => void submit()}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--ink)] px-4 py-2.5 text-sm font-medium text-[var(--paper)] disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Découpage et vectorisation…
            </>
          ) : (
            "Indexer"
          )}
        </button>

        {error && <p className="text-sm text-red-700">{error}</p>}
        {result && (
          <div className="rounded-lg border border-[var(--line)] bg-[var(--wash)] px-4 py-3 text-sm text-[var(--ink)]">
            <strong>{result.document}</strong> indexé — {result.nb_enfants}{" "}
            passages — visible par : {result.label}
          </div>
        )}
      </div>
    </div>
  );
}
