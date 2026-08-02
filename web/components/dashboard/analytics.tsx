"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  BarChart3,
  Clock,
  Coins,
  FileCheck2,
  HelpCircle,
  Inbox,
  MessageSquareText,
  User,
  Building2,
} from "lucide-react";
import { authHeaders, useAuth } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Kpis = {
  nb_questions: number;
  taux_reponse: number;
  taux_je_ne_sais_pas: number;
  taux_succes_generation: number;
  latence_moyenne_ms: number;
  cout_moyen: number;
};

type TopQ = { question: string; count: number };
type TopUser = { nom: string; count: number };
type TopService = { service: string; count: number };
type Demande = {
  id: number;
  user_email: string | null;
  service: string;
  question: string;
  cree_le: string | null;
};

export function DashboardAnalytics() {
  const { getToken } = useAuth();
  const [tab, setTab] = useState<
    "overview" | "questions" | "services" | "demandes"
  >("overview");
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [top, setTop] = useState<TopQ[]>([]);
  const [topUser, setTopUser] = useState<TopUser | null>(null);
  const [topService, setTopService] = useState<TopService | null>(null);
  const [demandes, setDemandes] = useState<Demande[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const h = authHeaders(token);
    void Promise.all([
      fetch(`${API_URL}/api/admin/kpis`, { headers: h }).then(async (r) => {
        if (r.status === 403) throw new Error("403");
        return r.json();
      }),
      fetch(`${API_URL}/api/admin/top-questions`, { headers: h }).then((r) =>
        r.json(),
      ),
      fetch(`${API_URL}/api/admin/top-user`, { headers: h }).then((r) =>
        r.json(),
      ),
      fetch(`${API_URL}/api/admin/top-service`, { headers: h }).then((r) =>
        r.json(),
      ),
      fetch(`${API_URL}/api/demandes`, { headers: h }).then((r) =>
        r.ok ? r.json() : [],
      ),
    ])
      .then(([k, t, u, s, d]) => {
        setKpis(k);
        setTop(t);
        setTopUser(u);
        setTopService(s);
        setDemandes(d as Demande[]);
        setErr(null);
      })
      .catch(() =>
        setErr("Impossible de charger les analytics (droits admin)."),
      );
  }, [getToken]);

  if (err) {
    return <p className="text-sm text-red-700">{err}</p>;
  }
  if (!kpis) {
    return (
      <p className="text-sm text-[var(--muted)]">Chargement des indicateurs…</p>
    );
  }

  const maxTop = Math.max(...top.map((t) => t.count), 1);

  return (
    <div className="flex min-h-[70vh] gap-0 overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)]">
      <aside className="w-48 shrink-0 border-r border-[var(--border)] bg-[var(--sidebar-bg)] px-3 py-4 text-[var(--sidebar-text)]">
        <p className="mb-4 px-2 text-sm font-semibold tracking-wide">
          Analytics
        </p>
        <nav className="flex flex-col gap-1">
          {(
            [
              ["overview", "Vue d'ensemble", BarChart3],
              ["questions", "Questions", MessageSquareText],
              ["services", "Services", Building2],
              ["demandes", "Demandes", Inbox],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors ${
                tab === id
                  ? "bg-white/15 text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="flex-1 overflow-y-auto p-6">
        {tab === "overview" && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Kpi
              icon={<MessageSquareText className="h-4 w-4" />}
              label="Questions"
              value={String(kpis.nb_questions)}
            />
            <Kpi
              icon={<BarChart3 className="h-4 w-4" />}
              label="Taux de réponse"
              value={`${kpis.taux_reponse} %`}
            />
            <Kpi
              icon={<HelpCircle className="h-4 w-4" />}
              label="Je ne sais pas"
              value={`${kpis.taux_je_ne_sais_pas} %`}
            />
            <Kpi
              icon={<FileCheck2 className="h-4 w-4" />}
              label="Succès génération fichiers"
              value={`${kpis.taux_succes_generation} %`}
            />
            <Kpi
              icon={<Clock className="h-4 w-4" />}
              label="Latence moyenne"
              value={`${(kpis.latence_moyenne_ms / 1000).toFixed(1)} s`}
            />
            <Kpi
              icon={<Coins className="h-4 w-4" />}
              label="Coût moyen"
              value={`${kpis.cout_moyen.toFixed(4)} €`}
            />
            <Kpi
              icon={<Inbox className="h-4 w-4" />}
              label="Demandes transmises"
              value={String(demandes.length)}
            />
          </div>
        )}

        {tab === "questions" && (
          <section>
            <h3 className="mb-4 text-lg font-semibold text-[var(--ink)]">
              Top 10 des questions
            </h3>
            <ul className="space-y-2">
              {top.map((t) => (
                <li key={t.question} className="text-sm">
                  <div className="mb-0.5 flex justify-between gap-2 text-[var(--ink)]">
                    <span className="truncate">{t.question}</span>
                    <span className="tabular-nums text-[var(--muted)]">
                      {t.count}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[var(--wash)]">
                    <div
                      className="h-full rounded-full bg-[var(--ink)]"
                      style={{ width: `${(t.count / maxTop) * 100}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}

        {tab === "services" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-[var(--line)] bg-[var(--paper)] p-5">
              <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--muted)]">
                <Building2 className="h-3.5 w-3.5" />
                Service le plus consulté
              </div>
              <p className="text-2xl font-semibold text-[var(--ink)]">
                {topService?.service ?? "—"}
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {topService?.count ?? 0} questions
              </p>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-[var(--paper)] p-5">
              <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--muted)]">
                <User className="h-3.5 w-3.5" />
                Utilisateur le plus actif
              </div>
              <p className="text-2xl font-semibold text-[var(--ink)]">
                {topUser?.nom ?? "—"}
              </p>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {topUser?.count ?? 0} questions
              </p>
            </div>
          </div>
        )}

        {tab === "demandes" && (
          <section>
            <h3 className="mb-4 text-lg font-semibold text-[var(--ink)]">
              Demandes transmises
            </h3>
            {demandes.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                Aucune demande pour le moment.
              </p>
            ) : (
              <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="border-b border-[var(--border)] bg-[var(--wash)] text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    <tr>
                      <th className="px-3 py-2 font-medium">Date</th>
                      <th className="px-3 py-2 font-medium">Utilisateur</th>
                      <th className="px-3 py-2 font-medium">Service</th>
                      <th className="px-3 py-2 font-medium">Question</th>
                    </tr>
                  </thead>
                  <tbody>
                    {demandes.map((d) => (
                      <tr
                        key={d.id}
                        className="border-b border-[var(--border)] last:border-0"
                      >
                        <td className="whitespace-nowrap px-3 py-2 text-[var(--text-muted)]">
                          {d.cree_le
                            ? new Date(d.cree_le).toLocaleString("fr-FR", {
                                dateStyle: "short",
                                timeStyle: "short",
                              })
                            : "—"}
                        </td>
                        <td className="px-3 py-2 text-[var(--text)]">
                          {d.user_email ?? "—"}
                        </td>
                        <td className="px-3 py-2 uppercase text-[var(--text)]">
                          {d.service}
                        </td>
                        <td className="px-3 py-2 text-[var(--text)]">
                          {d.question}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

function Kpi({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--paper)] px-4 py-3">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--muted)]">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-[var(--ink)]">
        {value}
      </p>
    </div>
  );
}
