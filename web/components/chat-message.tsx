"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, ThumbsUp, ThumbsDown } from "lucide-react";
import type { Message } from "@/lib/types";
import { Sources } from "./sources";
import { FileDownload } from "./file-download";
import { cn } from "@/lib/utils";

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
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-[var(--ink)] px-4 py-2.5 text-[15px] leading-relaxed text-[var(--paper)]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="prose prose-sm max-w-none prose-headings:font-[family-name:var(--font-display)] prose-headings:text-[var(--ink)] prose-p:leading-relaxed prose-p:text-[var(--ink)]/90 prose-strong:text-[var(--ink)] prose-table:text-sm prose-th:border-b prose-th:border-[var(--line)] prose-td:border-b prose-td:border-[var(--line)] prose-pre:bg-[var(--wash)]">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
        {streaming && (
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-[var(--ember)] align-middle" />
        )}
      </div>
      <Sources sources={message.sources ?? []} />
      {message.file && (
        <FileDownload id={message.file.id} filename={message.file.filename} />
      )}
      {!streaming && message.content && <MessageActions message={message} />}
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
    <div className="mt-1 flex items-center gap-0.5 text-[var(--muted)]">
      <button
        type="button"
        onClick={copy}
        className="rounded-md p-1.5 transition-colors hover:bg-[var(--wash)] hover:text-[var(--ink)]"
        title="Copier"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-[var(--ember)]" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
      <button
        type="button"
        onClick={() => setVote(vote === "up" ? null : "up")}
        className={cn(
          "rounded-md p-1.5 transition-colors hover:bg-[var(--wash)]",
          vote === "up" && "text-[var(--ember)]",
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
        <span className="ml-1.5 font-[family-name:var(--font-display)] text-xs tabular-nums tracking-wide">
          {(message.latencyMs / 1000).toFixed(1)} s
        </span>
      )}
    </div>
  );
}
