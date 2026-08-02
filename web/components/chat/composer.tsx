"use client";

import { useEffect, useRef, useState } from "react";
import { Globe, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SLASH_CMDS = [{ cmd: "/doc", label: "Générer un document Word" }];

export function Composer({
  onSend,
  disabled,
}: {
  onSend: (question: string, web: boolean) => void;
  disabled?: boolean;
}) {
  const [input, setInput] = useState("");
  const [web, setWeb] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const slashOpen = input.startsWith("/") && !input.includes(" ");
  const slashMatches = slashOpen
    ? SLASH_CMDS.filter((c) => c.cmd.startsWith(input.toLowerCase()))
    : [];

  const submit = () => {
    if (!input.trim() || disabled) return;
    onSend(input, web);
    setInput("");
  };

  return (
    <div className="border-t border-[var(--border)] bg-[var(--bg)] p-4">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-2 focus-within:border-[var(--accent-blue)]/40">
          <div className="flex flex-wrap items-center gap-2 px-1 pb-1">
            <button
              type="button"
              onClick={() => setWeb((w) => !w)}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2 py-1 text-xs transition-colors",
                web
                  ? "text-[var(--web)]"
                  : "text-[var(--text-muted)] hover:bg-[var(--wash)]",
              )}
              title="Recherche web"
              aria-pressed={web}
            >
              <Globe className="h-3.5 w-3.5" />
              {web ? "Web actif" : "Web"}
            </button>
            {web && (
              <span className="text-xs text-[var(--web)]">
                Web actif · votre question quitte l&apos;entreprise
              </span>
            )}
          </div>

          {slashMatches.length > 0 && (
            <div className="mx-1 mb-1 rounded-md border border-[var(--border)] bg-[var(--bg)] py-1 text-xs">
              {slashMatches.map((c) => (
                <button
                  key={c.cmd}
                  type="button"
                  className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left text-[var(--text)] hover:bg-[var(--wash)]"
                  onClick={() => setInput(`${c.cmd} `)}
                >
                  <span className="font-mono font-medium">{c.cmd}</span>
                  <span className="text-[var(--text-muted)]">{c.label}</span>
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={1}
              placeholder="Écrivez votre question… (ou /doc pour générer un document)"
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-[var(--text)] outline-none placeholder:text-[var(--text-muted)]"
            />
            <Button
              size="icon"
              onClick={submit}
              disabled={!input.trim() || disabled}
              className="rounded-md bg-[var(--accent-blue)] text-white hover:bg-[var(--accent-hover)]"
            >
              {disabled ? (
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
