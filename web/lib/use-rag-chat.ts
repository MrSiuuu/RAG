"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message, Source } from "./types";
import { authHeaders, useAuth } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Options = {
  onConversationChange?: (id: number | null) => void;
};

/**
 * Client SSE — aligné sur app/api/chat.py.
 * Identité via JWT ; conversation_id pour la persistance sidebar.
 */
export function useRagChat(options?: Options) {
  const { getToken } = useAuth();
  const onChangeRef = useRef(options?.onConversationChange);
  onChangeRef.current = options?.onConversationChange;

  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [statusSteps, setStatusSteps] = useState<string[]>([]);
  const [statusCollapsed, setStatusCollapsed] = useState(false);
  const [statusSummary, setStatusSummary] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const notifyConversation = useCallback((id: number | null) => {
    setConversationId(id);
    onChangeRef.current?.(id);
  }, []);

  const send = useCallback(
    async (question: string, web: boolean = false) => {
      const q = question.trim();
      if (!q || isStreaming) return;

      const token = getToken();
      if (!token) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "Session expirée. Reconnectez-vous.",
          },
        ]);
        return;
      }

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: q,
      };
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        sources: [],
        sourceQuestion: q,
      };

      try {
        sessionStorage.setItem("dyneff_last_question", q);
      } catch {
        /* ignore */
      }

      const historique = messages.slice(-6).map((m) => ({
        role: m.role,
        contenu: m.content,
      }));

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setStatusSteps([]);
      setStatusCollapsed(false);
      setStatusSummary(null);

      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (fn: (m: Message) => Message) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? fn(m) : m)),
        );

      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...authHeaders(token),
          },
          body: JSON.stringify({
            question: q,
            web_active: Boolean(web),
            historique,
            conversation_id: conversationId,
          }),
          signal: controller.signal,
        });

        if (res.status === 401) {
          patch((m) => ({
            ...m,
            content: "Non authentifié (401). Reconnectez-vous.",
          }));
          return;
        }
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let nbSources = 0;

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const { event, data } = parseSseBlock(part);
            if (!event) continue;

            if (event === "status") {
              const label = safeJson<{ label: string }>(data)?.label ?? "";
              if (label) {
                setStatusSteps((prev) =>
                  prev[prev.length - 1] === label ? prev : [...prev, label],
                );
              }
            } else if (event === "sources") {
              const src = safeJson<Source[]>(data) ?? [];
              nbSources = src.length;
              patch((m) => ({ ...m, sources: src }));
            } else if (event === "token") {
              setStatusCollapsed(true);
              setStatusSummary(
                nbSources > 0
                  ? `Recherche effectuée dans ${nbSources} passages`
                  : "Recherche effectuée",
              );
              const payload = safeJson<{ texte?: string } | string>(data);
              let text = "";
              if (typeof payload === "string") text = payload;
              else if (payload && typeof payload.texte === "string")
                text = payload.texte;
              else text = data;
              patch((m) => ({ ...m, content: m.content + text }));
            } else if (event === "file") {
              const f = safeJson<{ id: string; filename: string }>(data);
              if (f?.id) patch((m) => ({ ...m, file: f }));
            } else if (event === "done") {
              const info = safeJson<{
                latence_ms?: number;
                a_repondu?: boolean;
                nb_sources?: number;
                bavardage?: boolean;
                conversation_id?: number;
              }>(data);
              if (info?.conversation_id != null) {
                notifyConversation(info.conversation_id);
              }
              if (info?.bavardage) {
                setStatusCollapsed(true);
                setStatusSummary(null);
                setStatusSteps([]);
              } else if (info?.nb_sources != null) {
                setStatusSummary(
                  `Recherche effectuée dans ${info.nb_sources} passages`,
                );
              }
              patch((m) => ({
                ...m,
                latencyMs: info?.latence_ms,
                aRepondu: info?.a_repondu,
              }));
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          patch((m) => ({
            ...m,
            content:
              m.content ||
              "Erreur de connexion à l'API. Vérifiez `docker compose up` et le CORS.",
          }));
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [getToken, isStreaming, messages, conversationId, notifyConversation],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    setMessages([]);
    setStatusSteps([]);
    setStatusCollapsed(false);
    setStatusSummary(null);
  }, []);

  const newConversation = useCallback(() => {
    abortRef.current?.abort();
    reset();
    notifyConversation(null);
  }, [reset, notifyConversation]);

  const loadConversation = useCallback(
    async (id: number) => {
      const token = getToken();
      if (!token) return;
      abortRef.current?.abort();
      setIsStreaming(false);
      setStatusSteps([]);
      setStatusCollapsed(false);
      setStatusSummary(null);

      const res = await fetch(`${API_URL}/api/conversations/${id}/messages`, {
        headers: { ...authHeaders(token) },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const rows = (await res.json()) as Array<{
        role: string;
        contenu: string;
        sources?: Source[] | null;
        a_repondu?: boolean | null;
        latence_ms?: number | null;
      }>;

      let lastUserQ = "";
      const mapped: Message[] = rows.map((r) => {
        if (r.role === "user") lastUserQ = r.contenu;
        return {
          id: crypto.randomUUID(),
          role: r.role === "user" ? "user" : "assistant",
          content: r.contenu,
          sources: (r.sources as Source[]) ?? undefined,
          aRepondu: r.a_repondu ?? undefined,
          latencyMs: r.latence_ms ?? undefined,
          sourceQuestion: r.role === "assistant" ? lastUserQ : undefined,
        };
      });

      setMessages(mapped);
      notifyConversation(id);
    },
    [getToken, notifyConversation],
  );

  return {
    messages,
    conversationId,
    statusSteps,
    statusCollapsed,
    statusSummary,
    isStreaming,
    send,
    stop,
    reset,
    newConversation,
    loadConversation,
  };
}

export type ConversationListItem = {
  id: number;
  titre: string | null;
  cree_le: string | null;
};

export function useConversationsList(enabled: boolean) {
  const { getToken } = useAuth();
  const [items, setItems] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setItems([]);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/conversations`, {
        headers: { ...authHeaders(token) },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setItems((await res.json()) as ConversationListItem[]);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    if (enabled) void refresh();
  }, [enabled, refresh]);

  const remove = useCallback(
    async (id: number) => {
      const token = getToken();
      if (!token) return;
      const res = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: "DELETE",
        headers: { ...authHeaders(token) },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setItems((prev) => prev.filter((c) => c.id !== id));
    },
    [getToken],
  );

  return { items, loading, refresh, remove };
}

function parseSseBlock(block: string): { event?: string; data: string } {
  let event: string | undefined;
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  return { event, data: dataLines.join("\n") };
}

function safeJson<T>(raw: string): T | null {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}
