"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useConversationsList, useRagChat } from "@/lib/use-rag-chat";
import { Sidebar } from "@/components/sidebar/sidebar";
import { Composer } from "@/components/chat/composer";
import { ChatMessage } from "@/components/chat-message";
import { StatusSteps } from "@/components/status-steps";

const SUGGESTED = [
  "Combien de jours de congés par an ?",
  "Comment poser une note de frais ?",
  "Quel est le budget du CSE pour 2026 ?",
];

export function Chat() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { items, refresh, remove } = useConversationsList(
    Boolean(ready && user),
  );

  const onConversationChange = useCallback(
    (_id: number | null) => {
      void refresh();
    },
    [refresh],
  );

  const {
    messages,
    conversationId,
    statusSteps,
    statusCollapsed,
    statusSummary,
    isStreaming,
    send,
    newConversation,
    loadConversation,
  } = useRagChat({ onConversationChange });

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, statusSteps, isStreaming]);

  if (!ready || !user) {
    return (
      <div className="flex h-dvh items-center justify-center text-sm text-[var(--text-muted)]">
        Chargement…
      </div>
    );
  }

  const empty = messages.length === 0;

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--bg)]">
      <Sidebar
        collapsed={collapsed}
        onToggle={() => setCollapsed((c) => !c)}
        conversations={items}
        activeId={conversationId}
        onNew={() => {
          newConversation();
          void refresh();
        }}
        onSelect={(id) => {
          void loadConversation(id).catch(() => undefined);
        }}
        onDelete={(id) => {
          void remove(id).then(() => {
            if (conversationId === id) newConversation();
          });
        }}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-3xl">
            {empty ? (
              <EmptyState
                onPick={(q) => void send(q, false)}
                disabled={isStreaming}
              />
            ) : (
              <div className="flex flex-col gap-6">
                {messages.map((m, i) => {
                  const isLastAssistant =
                    isStreaming &&
                    i === messages.length - 1 &&
                    m.role === "assistant";
                  const showCollapsedStatus =
                    !isStreaming &&
                    i === messages.length - 1 &&
                    m.role === "assistant" &&
                    Boolean(statusSummary);

                  return (
                    <div key={m.id}>
                      {isLastAssistant && (
                        <StatusSteps
                          steps={statusSteps}
                          collapsed={statusCollapsed}
                          summary={statusSummary ?? undefined}
                        />
                      )}
                      {showCollapsedStatus && (
                        <StatusSteps
                          steps={statusSteps}
                          collapsed
                          summary={statusSummary ?? undefined}
                        />
                      )}
                      <ChatMessage message={m} streaming={isLastAssistant} />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <Composer onSend={(q, web) => void send(q, web)} disabled={isStreaming} />
      </main>
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
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-8 px-2 text-center">
      <div className="max-w-md">
        <p className="text-3xl font-semibold tracking-tight text-[var(--text)] sm:text-4xl">
          Dyneff
        </p>
        <h1 className="mt-2 text-lg font-medium text-[var(--text)]">
          Assistant Dyneff
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-[var(--text-muted)]">
          Posez une question sur vos procédures internes. Chaque réponse cite
          ses sources.
        </p>
      </div>
      <div className="flex w-full max-w-md flex-col gap-2">
        {SUGGESTED.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            disabled={disabled}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left text-sm text-[var(--text)] transition-colors hover:border-[var(--accent-blue)]/40 hover:bg-[var(--wash)] disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
