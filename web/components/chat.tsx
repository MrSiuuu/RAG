"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, Globe } from "lucide-react";
import { DEMO_USERS, type DemoUser } from "@/lib/types";
import { useRagChat } from "@/lib/use-rag-chat";
import { cn } from "@/lib/utils";
import { ChatMessage } from "./chat-message";
import { UserSelector } from "./user-selector";
import { Button } from "@/components/ui/button";

const SUGGESTED = [
  "Combien de jours de congés payés par an ?",
  "Rédige le courrier de refus de télétravail 3 jours/semaine pour M. Dupont",
  "La réglementation sur le congé paternité a changé en 2026 ?",
];

export function Chat() {
  const [user, setUser] = useState<DemoUser>(DEMO_USERS[0]);
  const { messages, status, isStreaming, send } = useRagChat(user.groups);
  const [input, setInput] = useState("");
  const [web, setWeb] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, status]);

  const submit = () => {
    if (!input.trim() || isStreaming) return;
    send(input, web);
    setInput("");
  };

  const empty = messages.length === 0;

  return (
    <div className="relative mx-auto flex h-dvh max-w-3xl flex-col">
      <header className="relative z-10 flex items-center justify-between border-b border-[var(--line)] px-4 py-3 backdrop-blur-sm">
        <div className="min-w-0">
          <div className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-[var(--ink)]">
            Dyneff
          </div>
          <div className="text-xs text-[var(--muted)]">Assistant RH · sources citées</div>
        </div>
        <UserSelector value={user} onChange={setUser} />
      </header>

      <div ref={scrollRef} className="relative z-10 flex-1 overflow-y-auto px-4 py-6">
        {empty ? (
          <EmptyState onPick={(q) => send(q, web)} disabled={isStreaming} />
        ) : (
          <div className="flex flex-col gap-6">
            {messages.map((m, i) => (
              <ChatMessage
                key={m.id}
                message={m}
                streaming={
                  isStreaming &&
                  i === messages.length - 1 &&
                  m.role === "assistant"
                }
              />
            ))}
            {status && (
              <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--ember)]" />
                <span>{status}</span>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="relative z-10 border-t border-[var(--line)] bg-[var(--paper)]/80 p-4 backdrop-blur-sm">
        <div className="flex flex-col gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-2 shadow-[0_8px_24px_-16px_rgba(11,45,42,0.35)] focus-within:border-[var(--ink)]/30 focus-within:ring-2 focus-within:ring-[var(--ember)]/25">
          <div className="flex flex-wrap items-center gap-2 px-1">
            <button
              type="button"
              onClick={() => setWeb((w) => !w)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors",
                web
                  ? "border-orange-300 bg-orange-50 text-orange-700"
                  : "border-transparent text-[var(--muted)] hover:bg-[var(--wash)]",
              )}
              title="Recherche web"
              aria-pressed={web}
            >
              <Globe className="h-3.5 w-3.5" />
              Web
            </button>
            {web && (
              <span className="text-xs text-orange-600">
                Résultats web ajoutés · votre question quitte l&apos;entreprise
              </span>
            )}
          </div>
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={1}
              placeholder={`Posez une question RH (vous êtes ${user.label})…`}
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-[var(--ink)] outline-none placeholder:text-[var(--muted)]"
            />
            <Button
              size="icon"
              onClick={submit}
              disabled={!input.trim() || isStreaming}
              className="bg-[var(--ink)] text-[var(--paper)] hover:bg-[var(--ink)]/90"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-8 px-2 text-center">
      <div className="max-w-md">
        <p className="font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight text-[var(--ink)] sm:text-5xl">
          Dyneff
        </p>
        <h1 className="mt-3 text-lg font-medium text-[var(--ink)]/85 sm:text-xl">
          Assistant RH
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
          Posez une question sur les procédures internes. Chaque réponse cite
          ses sources — et reste silencieuse hors de votre périmètre.
        </p>
      </div>
      <div className="flex w-full max-w-md flex-col gap-2">
        {SUGGESTED.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            disabled={disabled}
            className="rounded-lg border border-[var(--line)] bg-[var(--surface)]/80 px-4 py-3 text-left text-sm text-[var(--ink)] transition-colors hover:border-[var(--ember)]/40 hover:bg-[var(--wash)] disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
