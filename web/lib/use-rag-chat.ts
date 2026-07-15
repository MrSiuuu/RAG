"use client";

import { useCallback, useRef, useState } from "react";
import type { Message, Source } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Client SSE custom — aligné sur app/api/chat.py :
 * - event: status  → {"label": "..."}
 * - event: sources → [{chunk_id, document, section, page, extrait}]
 * - event: token   → {"texte": "..."}
 * - event: done    → {latence_ms, a_repondu, nb_sources}
 */
export function useRagChat(userGroups: string[]) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (question: string, web: boolean = false) => {
      const q = question.trim();
      if (!q || isStreaming) return;

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
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setStatus(null);

      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (fn: (m: Message) => Message) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? fn(m) : m)),
        );

      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: q,
            user_groups: userGroups,
            web: Boolean(web),
          }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

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
              if (label) setStatus(label);
            } else if (event === "sources") {
              const src = safeJson<Source[]>(data) ?? [];
              patch((m) => ({ ...m, sources: src }));
            } else if (event === "token") {
              // Format réel CDC 4 : {"texte": "..."}
              const payload = safeJson<{ texte?: string } | string>(data);
              let text = "";
              if (typeof payload === "string") {
                text = payload;
              } else if (payload && typeof payload.texte === "string") {
                text = payload.texte;
              } else {
                text = data;
              }
              patch((m) => ({ ...m, content: m.content + text }));
              setStatus(null);
            } else if (event === "file") {
              const f = safeJson<{ id: string; filename: string }>(data);
              if (f?.id) patch((m) => ({ ...m, file: f }));
            } else if (event === "done") {
              const info = safeJson<{
                latence_ms?: number;
                a_repondu?: boolean;
              }>(data);
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
        setStatus(null);
        abortRef.current = null;
      }
    },
    [userGroups, isStreaming],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);
  const reset = useCallback(() => {
    setMessages([]);
    setStatus(null);
  }, []);

  return { messages, status, isStreaming, send, stop, reset };
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
