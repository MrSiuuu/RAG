"use client";

import { PanelLeftClose, PanelLeftOpen, Plus, Trash2 } from "lucide-react";
import type { ConversationListItem } from "@/lib/use-rag-chat";
import { cn } from "@/lib/utils";
import { UserMenu } from "./user-menu";

export function Sidebar({
  collapsed,
  onToggle,
  conversations,
  activeId,
  onNew,
  onSelect,
  onDelete,
}: {
  collapsed: boolean;
  onToggle: () => void;
  conversations: ConversationListItem[];
  activeId: number | null;
  onNew: () => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  if (collapsed) {
    return (
      <aside className="flex h-dvh w-14 shrink-0 flex-col items-center border-r border-[var(--sidebar-hover)] bg-[var(--sidebar-bg)] py-3">
        <button
          type="button"
          onClick={onToggle}
          className="rounded-md p-2 text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)]"
          title="Ouvrir la sidebar"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onNew}
          className="mt-3 rounded-md p-2 text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)]"
          title="Nouvelle conversation"
        >
          <Plus className="h-4 w-4" />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-dvh w-[260px] shrink-0 flex-col bg-[var(--sidebar-bg)] text-[var(--sidebar-text)]">
      <div className="flex items-start justify-between gap-2 px-4 pb-3 pt-4">
        <div className="min-w-0">
          <p className="text-base font-semibold tracking-tight">Dyneff</p>
          <p className="text-xs text-[var(--sidebar-muted)]">Assistant Dyneff</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-md p-1.5 text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)]"
          title="Replier"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-md border border-[var(--sidebar-hover)] px-3 py-2 text-sm text-[var(--sidebar-text)] transition-colors hover:bg-[var(--sidebar-hover)]"
        >
          <Plus className="h-4 w-4" />
          Nouvelle conversation
        </button>
      </div>

      <div className="mx-3 border-t border-[var(--sidebar-hover)]" />

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <p className="mb-2 px-2 text-[10px] font-medium uppercase tracking-wide text-[var(--sidebar-muted)]">
          Historique
        </p>
        {conversations.length === 0 ? (
          <p className="px-2 text-xs text-[var(--sidebar-muted)]">
            Aucune conversation
          </p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((c) => {
              const active = c.id === activeId;
              const titre =
                c.titre?.trim() || "Nouvelle conversation";
              return (
                <li key={c.id} className="group relative">
                  <button
                    type="button"
                    onClick={() => onSelect(c.id)}
                    className={cn(
                      "w-full truncate rounded-md px-2.5 py-2 pr-8 text-left text-sm transition-colors",
                      active
                        ? "bg-[var(--sidebar-hover)] text-[var(--sidebar-text)]"
                        : "text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--sidebar-text)]",
                    )}
                    title={titre}
                  >
                    {titre}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(c.id);
                    }}
                    className="absolute right-1 top-1/2 -translate-y-1/2 rounded p-1 text-[var(--sidebar-muted)] opacity-0 transition-opacity hover:bg-[#3a4049] hover:text-[var(--sidebar-text)] group-hover:opacity-100"
                    title="Supprimer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>

      <div className="border-t border-[var(--sidebar-hover)] px-2 py-2">
        <UserMenu />
      </div>
    </aside>
  );
}
