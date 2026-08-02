"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, ThumbsUp, ThumbsDown, SendHorizontal } from "lucide-react";
import type { Message } from "@/lib/types";
import { authHeaders, useAuth } from "@/lib/auth";
import { Sources } from "./sources";
import { FileDownload } from "./file-download";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ChatMessage({
  message,
  streaming,
}: {
  message: Message;
  streaming?: boolean;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-lg border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-[15px] leading-relaxed text-[var(--text)]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="prose prose-sm max-w-none prose-headings:text-[var(--text)] prose-p:leading-relaxed prose-p:text-[var(--text)]/90 prose-strong:text-[var(--text)] prose-table:text-sm prose-th:border-b prose-th:border-[var(--border)] prose-td:border-b prose-td:border-[var(--border)] prose-pre:bg-[var(--wash)]">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
        {streaming && (
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-[var(--accent-blue)] align-middle" />
        )}
      </div>
      <Sources sources={message.sources ?? []} />
      {message.file && (
        <FileDownload id={message.file.id} filename={message.file.filename} />
      )}
      {!streaming && message.content && <MessageActions message={message} />}
      {!streaming && message.aRepondu === false && (
        <TransmitButton
          question={
            message.sourceQuestion ||
            (typeof window !== "undefined"
              ? sessionStorage.getItem("dyneff_last_question")
              : null) ||
            "Question hors corpus"
          }
        />
      )}
    </div>
  );
}

function TransmitButton({ question }: { question: string }) {
  const { getToken } = useAuth();
  const [done, setDone] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const transmit = async () => {
    const token = getToken();
    if (!token || busy) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/demandes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({ question, service: "rh" }),
      });
      if (!res.ok) throw new Error("fail");
      setDone(true);
      setToast("Demande transmise au service concerné");
      setTimeout(() => setToast(null), 3000);
    } catch {
      setToast("Échec de la transmission");
      setTimeout(() => setToast(null), 3000);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2">
      {!done && (
        <button
          type="button"
          onClick={() => void transmit()}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text)] transition-colors hover:border-[var(--accent-blue)]/40 hover:bg-[var(--wash)] disabled:opacity-50"
        >
          <SendHorizontal className="h-3.5 w-3.5 text-[var(--accent-blue)]" />
          Transmettre au service concerné
        </button>
      )}
      {toast && (
        <p className="mt-2 rounded-md border border-[var(--border)] bg-[var(--wash)] px-3 py-2 text-xs text-[var(--text)]">
          {toast}
        </p>
      )}
    </div>
  );
}

function MessageActions({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<"up" | "down" | null>(null);

  const copy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="mt-1 flex items-center gap-0.5 text-[var(--text-muted)]">
      <button
        type="button"
        onClick={copy}
        className="rounded-md p-1.5 transition-colors hover:bg-[var(--wash)] hover:text-[var(--text)]"
        title="Copier"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-[var(--accent-blue)]" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
      <button
        type="button"
        onClick={() => setVote(vote === "up" ? null : "up")}
        className={cn(
          "rounded-md p-1.5 transition-colors hover:bg-[var(--wash)]",
          vote === "up" && "text-[var(--accent-blue)]",
        )}
        title="Utile"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => setVote(vote === "down" ? null : "down")}
        className={cn(
          "rounded-md p-1.5 transition-colors hover:bg-[var(--wash)]",
          vote === "down" && "text-red-700",
        )}
        title="Pas utile"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
      {message.latencyMs != null && (
        <span className="ml-1.5 text-xs tabular-nums tracking-wide">
          {(message.latencyMs / 1000).toFixed(1)} s
        </span>
      )}
    </div>
  );
}
