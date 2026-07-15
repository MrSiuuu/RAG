"use client";

import { DEMO_USERS, type DemoUser } from "@/lib/types";
import { Button } from "@/components/ui/button";

export function UserSelector({
  value,
  onChange,
}: {
  value: DemoUser;
  onChange: (u: DemoUser) => void;
}) {
  return (
    <div className="flex items-center gap-0.5 rounded-md border border-[var(--line)] bg-[var(--surface)] p-0.5">
      {DEMO_USERS.map((u) => {
        const active = u.id === value.id;
        return (
          <Button
            key={u.id}
            variant={active ? "default" : "ghost"}
            size="sm"
            onClick={() => onChange(u)}
            className={
              active
                ? "gap-1.5 bg-[var(--ink)] text-[var(--paper)] hover:bg-[var(--ink)]/90"
                : "gap-1.5 text-[var(--muted)] hover:text-[var(--ink)]"
            }
          >
            <span className="font-medium">{u.label}</span>
            <span className={active ? "opacity-70" : "opacity-60"}>{u.role}</span>
          </Button>
        );
      })}
    </div>
  );
}
