# CDC 8 — Le front (Next.js)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Construire **une seule page** de chat qui parle à ton API (`/api/chat`), qui **stream** les tokens comme ChatGPT, affiche les **statuts en direct**, les **cartes de sources cliquables**, et un **sélecteur d'utilisateur Marie/Paul** — pour que la démo ACL se fasse en un clic.

---

## 💡 Pourquoi c'est important

Le cerveau (CDC 0→4) répond déjà parfaitement… **dans un terminal**. Tu ne peux pas montrer un `curl` à Rémi.

Ce CDC transforme le `curl` en produit. Sur tes 5 moments de démo :

| Moment | Ce que le front rend possible |
|---|---|
| 1. Question RH + citations | Streaming + cartes de sources cliquables |
| 2. Changement d'utilisateur → sécurité | **Le sélecteur Marie/Paul.** Même question, deux réponses. |
| 3. `.docx` (CDC 9) | Se branchera sur ce front |
| 5. Dashboard (CDC 12) | Réutilisera ces composants |

**Sans ce CDC, il n'y a pas de démo.** C'est le passage de « il a bricolé une API » à « il a un produit ».

---

## 📚 Les concepts à comprendre

### 1. Lire du streaming SSE dans le navigateur (sans `useChat`)

**L'image :** ton backend est un fax qui envoie une réponse **page par page** : d'abord un statut (« je cherche… »), puis les sources, puis les mots un par un, puis « fini ».

Le hook `useChat` de Vercel sait lire un fax **uniquement s'il est écrit sur le papier à en-tête de Vercel**. Ton backend écrit sur son propre papier à en-tête (`event: status`, `event: token`…). Donc on lit le fax nous-mêmes, ligne par ligne.

Techniquement : on fait un `fetch`, on récupère `response.body` (un flux), et on lit les morceaux au fur et à mesure avec un `ReadableStream`. On découpe sur les lignes vides (`\n\n`), on regarde le `event:` et le `data:`, et on met à jour l'écran. **~90 lignes, entièrement sous ton contrôle.**

> **Pourquoi pas `useChat` alors que le doc le prévoyait ?** Parce que brancher `useChat` obligerait à **réécrire le format de streaming de ton backend** (le CDC 4, déjà codé et testé). On ne casse pas ce qui marche la veille d'une démo. Le client custom lit exactement ce que ton API envoie déjà.

### 2. CORS — le bouncer paranoïaque du navigateur

**L'image :** le navigateur est un videur. Une page servie depuis `localhost:3000` qui tente d'appeler une API sur `localhost:8000`, c'est deux adresses différentes. Le videur bloque **par défaut**, sauf si l'API affiche explicitement : « j'autorise les pages venant de `:3000` ».

- En `curl` : pas de videur. Tout marche. (C'est pour ça que tes tests CDC 0→4 passaient.)
- Dans le navigateur : sans autorisation CORS, **chaque requête échoue**, avec une erreur du genre *« blocked by CORS policy »* dans la console (F12).

→ On ajoute **6 lignes** au backend (`CORSMiddleware`). Ça ne touche aucune logique du RAG.

### 3. Markdown propre (la classe `prose`)

Le LLM répond en markdown (titres, **gras**, tableaux — la grille des salaires est un tableau). `react-markdown` + `remark-gfm` transforment ce markdown en vrai HTML, et `@tailwindcss/typography` (la classe `prose`) le rend joli sans qu'on écrive une ligne de CSS.

### 4. `"use client"`

Next.js 15 rend les composants côté serveur par défaut. Mais tout ce qui utilise l'interactivité (état, clics, streaming) doit tourner **côté navigateur**. On met `"use client"` en haut de ces fichiers. Sans ça → erreur.

---

## 🧩 Où ça s'insère

**Ce qui existe déjà (on n'y touche pas, sauf CORS) :**
```
app/                     ← le backend Python, terminé
├── main.py              ← ⚠️ SEUL fichier backend modifié (ajout CORS)
├── api/chat.py          ← POST /api/chat (SSE) — déjà testé
├── llm/…                ← génération, citations, prompts
├── retrieval/…          ← hybride + rerank + ACL
└── ingest/…             ← ingestion
docker-compose.yml       ← rag-db + rag-api
```

**Ce que ce CDC ajoute :** un dossier `web/` complètement neuf, à côté de `app/`. Une app Next.js indépendante.

```
web/                     ← NOUVEAU
├── app/                 (page, layout, styles)
├── components/          (chat, message, sources, sélecteur)
└── lib/                 (le client SSE custom, les types)
```

---

## ⚠️ Les pièges de ce CDC

| Piège | Symptôme | Solution |
|---|---|---|
| **CORS non configuré** | Écran vide, F12 montre « blocked by CORS ». Tout marchait en curl. | Le patch `CORSMiddleware` dans `main.py` (PARTIE B, étape 1). **À faire en premier.** |
| **Format SSE différent de ce que je suppose** | Les tokens ne s'affichent pas, ou avec des guillemets. | Cursor doit **lire `app/api/chat.py` d'abord** et aligner le parseur sur le vrai format émis (event names + encodage des `data:`). Instruction donnée en PARTIE B. |
| **Streaming coupé au milieu** | Des caractères manquants ou dédoublés. | Le parseur **bufferise** et ne traite que les événements complets (séparés par `\n\n`). Code fourni, ne pas simplifier. |
| **Le kill switch** | Le texte arrive **d'un seul bloc** au lieu de mot par mot. | Rappel du doc : *si ça ne stream pas, on jette.* On debug CORS/parseur AVANT d'ajouter quoi que ce soit d'autre. |
| **Follow-up qui ne marche pas** | « et pour les cadres ? » renvoie n'importe quoi. | **Normal.** Le mono-tour est volontaire ici. La mémoire = CDC 7. |

---

## 🗣️ Ce que je pourrai dire en réunion grâce à ça

> *« Regardez : je pose la question, la réponse arrive en direct, sourcée. Maintenant je change d'utilisateur — Paul, commercial — je pose exactement la même question sur la grille des salaires… »* **[clic] [rien n'apparaît]** *« …et il n'a rien. Le filtrage par droits se fait avant même que le modèle ne voie le document. »*

C'est le moment n°2, le plus fort. Il se joue **entièrement** sur le sélecteur d'utilisateur de ce front.

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

On construit le front d'un RAG RH. Le backend Python (FastAPI + Postgres/pgvector + OpenAI) est **déjà terminé et testé** : il expose `POST /api/chat` qui répond en **Server-Sent Events** avec un format maison. Ta mission est de construire une app **Next.js 15 + TypeScript + Tailwind + shadcn/ui** qui consomme ce flux. **Interdiction absolue** d'installer LangChain, ni le Vercel AI SDK / `useChat` : on lit le SSE avec un client custom (raison : le backend émet un format SSE maison que `useChat` ne sait pas parser, et on ne modifie pas le backend).

## État actuel du code

Le repo contient déjà (ne pas modifier, sauf `app/main.py`) :

```
app/
├── main.py            ← FastAPI, monte le router chat. À PATCHER (CORS uniquement).
├── config.py          ← Pydantic settings (.env)
├── api/chat.py        ← POST /api/chat, streaming SSE. Format d'événements ci-dessous.
├── llm/               ← génération, citations, prompts (terminé)
├── retrieval/         ← hybride + RRF + rerank + ACL (terminé)
└── ingest/            ← ingestion (terminé)
docker-compose.yml     ← services: rag-db (postgres+pgvector), rag-api (uvicorn :8000)
```

**Contrat de l'endpoint `POST /api/chat` :**

- **Requête** (JSON) :
  ```json
  { "question": "Combien de jours de congés payés ?", "user_groups": ["grp-tous"] }
  ```
- **Réponse** : `text/event-stream` (SSE). Séquence d'événements attendue :
  ```
  event: status
  data: {"label": "Reformulation de la question…"}

  event: status
  data: {"label": "Recherche dans 47 documents RH…"}

  event: sources
  data: [{"doc":"Convention collective","section":"Titre III > Art. 12","page":8,"extrait":"…","url":null}]

  event: token
  data: "Le"

  event: token
  data: " salarié"

  event: done
  data: {"latency_ms": 2300, "a_repondu": true}
  ```
- Quand aucun chunk n'est accessible (ACL) : `event: sources` renvoie `[]`, puis un texte du type « je n'ai pas d'information accessible », puis `done` avec `a_repondu: false`.

> **⚠️ AVANT DE CODER LE PARSEUR : ouvre `app/api/chat.py` et vérifie les noms exacts des événements (`status`/`sources`/`token`/`done`) et l'encodage des lignes `data:` (JSON ou brut). Aligne le parseur `parseSseBlock`/`safeJson` du fichier `lib/use-rag-chat.ts` sur le format réel. Le code fourni suppose des `data:` encodés en JSON.**

---

## Ce qu'il faut construire

Une app Next.js dans un nouveau dossier `web/`, à la racine du repo (à côté de `app/`).

**Fonctionnalités (scope verrouillé) :**
1. **UNE page** de chat.
2. **Streaming** des tokens, un par un.
3. **Ligne de statut en direct** pendant la recherche (spinner + label), qui disparaît quand le premier token arrive.
4. **Cartes de sources** sous la réponse, cliquables (déplient l'extrait).
5. **Sélecteur d'utilisateur** en haut à droite (Marie RH / Paul Commercial) qui change les `user_groups` envoyés.
6. **Markdown propre** (tableaux, gras, listes).
7. **Bouton copier** + **👍/👎** (état local) + **latence** affichée sous chaque réponse.
8. **Écran d'accueil** avec 3 questions suggérées.

**Hors scope (NE PAS faire) :** dark mode, animations, page settings, sélecteur de modèle, logo custom, sidebar/historique persisté, multi-tour/mémoire, authentification. La requête envoyée contient **uniquement** `{ question, user_groups }` (mono-tour).

---

## Fichiers à créer / modifier

```
app/main.py                          ← MODIFIER (ajout CORS)

web/
├── .env.local                       ← CRÉER
├── app/
│   ├── layout.tsx                   ← CRÉER
│   ├── page.tsx                     ← CRÉER
│   └── globals.css                  ← MODIFIER (ajout plugin typography)
├── components/
│   ├── chat.tsx                     ← CRÉER
│   ├── chat-message.tsx             ← CRÉER
│   ├── sources.tsx                  ← CRÉER
│   ├── user-selector.tsx            ← CRÉER
│   └── ui/                          ← généré par shadcn (button)
└── lib/
    ├── types.ts                     ← CRÉER
    ├── use-rag-chat.ts              ← CRÉER (le client SSE custom)
    └── utils.ts                     ← généré par shadcn (cn) — NE PAS recréer
```

---

## Spécifications techniques

### Étape 1 — Patcher le backend (CORS)

Dans `app/main.py`, ajouter le middleware CORS **sans rien toucher d'autre**. Après la création de l'app FastAPI (`app = FastAPI(...)`), insérer :

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Étape 2 — Scaffold le front

Depuis la **racine du repo**, exécuter :

```bash
# Créer l'app Next.js dans web/ (App Router, TS, Tailwind, alias @/)
pnpm create next-app@latest web --typescript --tailwind --app --src-dir=false --import-alias "@/*" --eslint --no-turbopack

cd web

# Initialiser shadcn/ui (accepter les valeurs par défaut / base color: neutral)
pnpm dlx shadcn@latest init -d

# Ajouter le composant Button
pnpm dlx shadcn@latest add button

# Markdown
pnpm add react-markdown remark-gfm
pnpm add -D @tailwindcss/typography
```

**Enregistrer le plugin typography** dans `web/app/globals.css` selon la version de Tailwind installée :
- **Tailwind v4** (Next 15 par défaut) : ajouter en haut du fichier, sous les imports existants :
  ```css
  @plugin "@tailwindcss/typography";
  ```
- **Tailwind v3** : ajouter `require("@tailwindcss/typography")` dans le tableau `plugins` de `tailwind.config.ts`.

### Étape 3 — `web/.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Étape 4 — `web/lib/types.ts`

```typescript
export type Source = {
  doc: string;
  section: string;
  page: number | string | null;
  extrait: string;
  url?: string | null;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  latencyMs?: number;
  aRepondu?: boolean;
};

export type DemoUser = {
  id: string;
  label: string;
  role: string;
  groups: string[];
};

export const DEMO_USERS: DemoUser[] = [
  { id: "marie", label: "Marie", role: "RH", groups: ["grp-rh", "grp-tous"] },
  { id: "paul", label: "Paul", role: "Commercial", groups: ["grp-tous"] },
];
```

### Étape 5 — `web/lib/use-rag-chat.ts` (le cœur — le client SSE custom)

```typescript
"use client";

import { useCallback, useRef, useState } from "react";
import type { Message, Source } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useRagChat(userGroups: string[]) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || isStreaming) return;

      const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: q };
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

      // helper: modifier UNIQUEMENT le message assistant en cours
      const patch = (fn: (m: Message) => Message) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)));

      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, user_groups: userGroups }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          // normaliser CRLF -> LF puis accumuler
          buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

          // les événements SSE sont séparés par une ligne vide
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? ""; // garder le morceau incomplet pour le prochain tour

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
              // les tokens sont des chaînes encodées en JSON -> préserve les espaces
              const tok = safeJson<string>(data);
              const text = typeof tok === "string" ? tok : data;
              patch((m) => ({ ...m, content: m.content + text }));
              setStatus(null); // premier token: on efface la ligne de statut
            } else if (event === "done") {
              const info = safeJson<{ latency_ms?: number; a_repondu?: boolean }>(data);
              patch((m) => ({ ...m, latencyMs: info?.latency_ms, aRepondu: info?.a_repondu }));
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          patch((m) => ({
            ...m,
            content: m.content || "⚠️ Erreur de connexion à l'API. Le backend est-il lancé (docker compose up) et le CORS configuré ?",
          }));
        }
      } finally {
        setIsStreaming(false);
        setStatus(null);
        abortRef.current = null;
      }
    },
    [userGroups, isStreaming]
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
```

### Étape 6 — `web/components/user-selector.tsx`

```tsx
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
    <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1">
      {DEMO_USERS.map((u) => {
        const active = u.id === value.id;
        return (
          <Button
            key={u.id}
            variant={active ? "default" : "ghost"}
            size="sm"
            onClick={() => onChange(u)}
            className="gap-1.5"
          >
            <span className="font-medium">{u.label}</span>
            <span
              className={
                active ? "text-primary-foreground/80" : "text-muted-foreground"
              }
            >
              {u.role}
            </span>
          </Button>
        );
      })}
    </div>
  );
}
```

### Étape 7 — `web/components/sources.tsx`

```tsx
"use client";

import { useState } from "react";
import { FileText, ChevronDown } from "lucide-react";
import type { Source } from "@/lib/types";

export function Sources({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {sources.map((s, i) => (
        <SourceCard key={i} source={s} index={i + 1} />
      ))}
    </div>
  );
}

function SourceCard({ source, index }: { source: Source; index: number }) {
  const [open, setOpen] = useState(false);
  const label = [
    source.doc,
    source.section,
    source.page ? `p.${source.page}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="rounded-lg border bg-card text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-left hover:bg-accent"
      >
        <FileText className="h-3.5 w-3.5 shrink-0 text-blue-600" />
        <span className="font-semibold text-blue-700">{index}.</span>
        <span className="text-foreground/80">{label}</span>
        <ChevronDown
          className={`h-3 w-3 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="max-w-md border-t px-2.5 py-2 leading-relaxed text-muted-foreground">
          {source.extrait}
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 block text-blue-600 underline"
            >
              Ouvrir la source
            </a>
          )}
        </div>
      )}
    </div>
  );
}
```

### Étape 8 — `web/components/chat-message.tsx`

```tsx
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, ThumbsUp, ThumbsDown } from "lucide-react";
import type { Message } from "@/lib/types";
import { Sources } from "./sources";
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
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2.5 text-primary-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-muted prose-table:text-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        {streaming && (
          <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-foreground/60 align-middle" />
        )}
      </div>
      <Sources sources={message.sources ?? []} />
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
    <div className="flex items-center gap-1 text-muted-foreground">
      <button onClick={copy} className="rounded p-1.5 hover:bg-accent" title="Copier">
        {copied ? (
          <Check className="h-3.5 w-3.5 text-green-600" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </button>
      <button
        onClick={() => setVote(vote === "up" ? null : "up")}
        className={cn("rounded p-1.5 hover:bg-accent", vote === "up" && "text-green-600")}
        title="Utile"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => setVote(vote === "down" ? null : "down")}
        className={cn("rounded p-1.5 hover:bg-accent", vote === "down" && "text-red-600")}
        title="Pas utile"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
      {message.latencyMs != null && (
        <span className="ml-1 text-xs">{(message.latencyMs / 1000).toFixed(1)} s</span>
      )}
    </div>
  );
}
```

### Étape 9 — `web/components/chat.tsx`

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { DEMO_USERS, type DemoUser } from "@/lib/types";
import { useRagChat } from "@/lib/use-rag-chat";
import { ChatMessage } from "./chat-message";
import { UserSelector } from "./user-selector";
import { Button } from "@/components/ui/button";

const SUGGESTED = [
  "Combien de jours de congés payés par an ?",
  "Quelle est la procédure de télétravail ?",
  "Quel est le plafond des notes de frais repas ?",
];

export function Chat() {
  const [user, setUser] = useState<DemoUser>(DEMO_USERS[0]);
  const { messages, status, isStreaming, send } = useRagChat(user.groups);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, status]);

  const submit = () => {
    if (!input.trim() || isStreaming) return;
    send(input);
    setInput("");
  };

  const empty = messages.length === 0;

  return (
    <div className="mx-auto flex h-dvh max-w-3xl flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
            RH
          </div>
          <div>
            <div className="text-sm font-semibold">Assistant RH Dyneff</div>
            <div className="text-xs text-muted-foreground">RAG · sources citées</div>
          </div>
        </div>
        {/* on ne reset pas au changement d'user : reposer la MÊME question montre la différence ACL */}
        <UserSelector value={user} onChange={setUser} />
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
        {empty ? (
          <EmptyState onPick={(q) => send(q)} disabled={isStreaming} />
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
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{status}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex items-end gap-2 rounded-xl border bg-background p-2 focus-within:ring-2 focus-within:ring-ring">
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
            className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm outline-none"
          />
          <Button
            size="icon"
            onClick={submit}
            disabled={!input.trim() || isStreaming}
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
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
      <div>
        <h1 className="text-2xl font-semibold">Assistant RH Dyneff</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Posez une question sur les procédures RH. Chaque réponse cite ses sources.
        </p>
      </div>
      <div className="flex w-full max-w-md flex-col gap-2">
        {SUGGESTED.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            disabled={disabled}
            className="rounded-xl border bg-card px-4 py-3 text-left text-sm hover:bg-accent disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
```

### Étape 10 — `web/app/page.tsx`

```tsx
import { Chat } from "@/components/chat";

export default function Home() {
  return <Chat />;
}
```

### Étape 11 — `web/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Assistant RH Dyneff",
  description: "RAG RH — sources citées",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
```

---

## Contraintes impératives

- **INTERDIT** : LangChain, LlamaIndex, Vercel AI SDK (`ai`, `@ai-sdk/react`, `useChat`), Redux, Zustand, framer-motion, toute autre lib UI que shadcn.
- **Ne modifier aucun fichier de `app/`** sauf `app/main.py` (ajout CORS uniquement).
- **Lire `app/api/chat.py` avant d'écrire le parseur SSE** et aligner `parseSseBlock`/`safeJson` sur le format réel des événements.
- **Ne pas simplifier le buffering du parseur** (`buffer.split("\n\n")` + garder le morceau incomplet) : c'est ce qui évite les tokens coupés.
- La requête envoyée est **strictement** `{ question, user_groups }`. Pas d'historique, pas de `messages[]`.
- Tout composant interactif commence par `"use client"`.
- Pas de dark mode, pas d'animations superflues, pas de page settings, pas de logo custom.

---

## Definition of Done

```bash
# Terminal 1 — le backend (déjà construit), à la racine du repo
docker compose up

# Terminal 2 — le front
cd web
pnpm install
pnpm dev
# → ouvrir http://localhost:3000
```

**Résultat attendu exactement :**

1. **Accueil** : titre « Assistant RH Dyneff », 3 questions suggérées, sélecteur en haut à droite sur **Marie (RH)**.
2. **Streaming** : cliquer « Combien de jours de congés payés ? » →
   - une **ligne de statut** apparaît (spinner + « Recherche… »),
   - puis les **tokens s'affichent un par un** (PAS d'un seul bloc — c'est le kill switch),
   - la réponse mentionne **25 jours ouvrés**,
   - des **cartes de sources bleues** apparaissent dessous ; cliquer dessus déplie l'extrait.
3. **Démo ACL** : passer sur **Paul (Commercial)**, taper « grille des salaires » →
   - réponse du type « je n'ai pas d'information accessible »,
   - **aucune carte de source**.
4. **Inverse** : repasser sur **Marie**, même question → la **grille apparaît** (tableau markdown) avec la source « Grille de rémunération 2026 ».
5. **Actions** : le bouton **copier** fonctionne, les **👍/👎** changent d'état, la **latence** s'affiche sous la réponse (ex. « 2.3 s »).

**Si les tokens arrivent d'un seul bloc au lieu de mot par mot → NON conforme.** Debugger dans l'ordre : (a) CORS dans `main.py`, (b) le format SSE réel vs le parseur, (c) la console navigateur (F12). Ne rien ajouter d'autre tant que le streaming n'est pas visible.
