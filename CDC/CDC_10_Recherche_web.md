# CDC 10 — La recherche web

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Ajouter un **interrupteur « Web »** dans l'interface : quand l'utilisateur l'active, l'assistant complète sa réponse avec des résultats du web **en plus** du corpus interne — et affiche ces sources en **orange**, nettement distinctes des sources internes bleues.

---

## 💡 Pourquoi c'est important

C'est **l'autre manque de Datasulting** — leur portail était figé sur les connaissances d'entraînement du modèle. C'est le **moment n°4** de ta démo :

> *« La réglementation sur le congé paternité a changé en 2026 ? »*
> → toggle éteint : *« je n'ai pas cette information »* (ce n'est pas dans le corpus interne)
> → toggle allumé : va chercher sur Légifrance / service-public.fr → **réponse à jour, sources orange**

---

## 📚 Les concepts à comprendre

### 1. ⚠️ Toggle manuel, JAMAIS automatique — le point de sécurité

**Le scénario catastrophe** (Piège n°6 du projet) : si le modèle décide **tout seul** d'aller sur le web, un jour il enverra *« quel est le salaire d'un cadre chez Dyneff »* à un moteur de recherche externe. **C'est une fuite de données. Et c'est toi qui l'auras codée.**

**La règle :** la recherche web ne se déclenche **QUE** si l'utilisateur a coché l'interrupteur. Le modèle ne décide **jamais**. Techniquement : le front envoie un champ `web: true/false`, et le backend n'appelle le moteur que si `web === true`.

**Le corollaire honnête :** quand le web est activé, **ta question sort de l'entreprise** (elle part chez le fournisseur de recherche). L'utilisateur doit le **voir** — d'où un petit avertissement à côté de l'interrupteur quand il est allumé. C'est ça qui transforme un risque en **choix conscient**.

### 2. Le web est ADDITIF, l'ACL interne reste intacte

Quand le toggle est allumé, il se passe **deux choses en parallèle** :
- le retrieval interne tourne **comme d'habitude** (toujours **filtré par ACL**),
- **en plus**, on interroge le web.

Les deux jeux de résultats sont donnés au modèle, et les deux types de sources s'affichent. **Le web n'affaiblit jamais l'ACL interne** — ce sont deux tuyaux séparés.

### 3. La distinction visuelle : bleu vs orange

**L'image :** deux tampons différents. `📄 Interne` en **bleu** (ton corpus, fiable, sourcé). `🌐 Web` en **orange** (l'extérieur, à jour mais à vérifier). L'utilisateur sait **toujours** d'où vient chaque information. C'est une question de confiance — et ça prépare la question du RSSI.

### 4. Le moteur : Tavily

Un moteur de recherche **taillé pour les LLM** : tu lui envoies une question, il te renvoie des extraits propres (titre + URL + contenu), prêts à injecter. Clé gratuite sur tavily.com, appel en 3 lignes via `httpx` (déjà dans ta stack). Isolé dans un seul fichier `app/tools/web.py` — si tu veux en changer un jour, tu remplaces une fonction.

> **La nuance « une seule clé » :** oui, ça ajoute `TAVILY_API_KEY`. Mais la recherche web est une capacité **différente** de la génération/embeddings/rerank (qui restent 100 % OpenAI). Ta règle visait à ne pas jongler entre fournisseurs de LLM — elle tient. Un moteur de recherche, c'est une autre catégorie.

---

## 🧩 Où ça s'insère

**Ce qui existe déjà (on réutilise) :**
- `app/api/chat.py` — le streaming SSE. On y ajoute une **branche web** (après le retrieval interne).
- Le retrieval interne **filtré ACL** — inchangé.
- Le front (CDC 8/9) — on ajoute l'interrupteur + la couleur orange sur les cartes.

**Ce que ce CDC ajoute :**
```
app/tools/web.py          ← appel Tavily (httpx)
app/config.py             ← + TAVILY_API_KEY
.env                      ← + TAVILY_API_KEY (gitignore, règle 4)
web/components/chat.tsx    ← l'interrupteur Web
web/components/sources.tsx ← couleur orange pour type "web"
web/lib/use-rag-chat.ts    ← envoie le champ web
web/lib/types.ts           ← Source gagne un champ type
```

---

## ⚠️ Les pièges de ce CDC

| Piège | Conséquence | Solution |
|---|---|---|
| **Recherche web automatique** | Fuite : une question interne part sur un moteur externe | Le backend n'appelle Tavily **QUE si `web === true`** dans la requête. Jamais le modèle qui décide. |
| **Oublier que la question sort de l'entreprise** | L'utilisateur ne sait pas qu'il fuite | Avertissement visible à côté de l'interrupteur quand il est allumé. |
| **`TAVILY_API_KEY` absente** | Le toggle ne fait rien | La fonction renvoie `[]` proprement (dégradation douce). Ajoute la clé dans `.env`. |
| **async vs sync** | Le générateur SSE plante | Si le générateur de `chat.py` est `async`, utilise `httpx.AsyncClient` ; sinon `httpx.post`. Les deux versions sont fournies. |
| **Le web pollue l'ACL interne** | Confusion des couches | Retrieval interne = ACL, inchangé. Web = tuyau séparé, clairement labellisé `[WEB]`. |

---

## 🗣️ Ce que je pourrai dire en réunion grâce à ça

> *« La recherche web n'est jamais automatique. Sinon, un jour, le système enverrait "salaire d'un cadre chez Dyneff" à un moteur externe — une fuite. C'est un interrupteur que l'utilisateur active consciemment, et quand il est allumé, l'interface le prévient que sa question quitte l'entreprise. Et regardez : les sources web sont en orange, les sources internes en bleu. On sait toujours d'où vient l'information. »*

C'est une démo de **maturité sécurité**, pas juste une feature.

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

RAG RH Dyneff. On ajoute une **recherche web optionnelle**, déclenchée par un **toggle manuel** dans l'UI (JAMAIS automatique — c'est une exigence de sécurité). Quand le toggle est actif, on interroge **Tavily** (via `httpx`, déjà installé) et on injecte les résultats dans le contexte du LLM **en plus** des chunks internes (qui restent **filtrés par ACL**). Les sources web sont marquées `type: "web"` pour un rendu **orange** distinct du bleu interne. **Interdit** : recherche web automatique/décidée par le LLM, LangChain.

## État actuel du code

```
app/
├── api/chat.py         ← POST /api/chat en SSE. Requête actuelle : {question, user_groups}.
│                          Émet status/sources/token/done. Token = {"texte": ...}. Sources en clé "document".
├── retrieval/pipeline.py ← retrieval filtré ACL (inchangé)
└── config.py           ← pydantic-settings
web/
├── lib/use-rag-chat.ts ← client SSE ; send(question) POST {question, user_groups}
├── lib/types.ts        ← type Source (clé document/section/page/extrait/url)
├── components/chat.tsx    ← page de chat + input
└── components/sources.tsx ← cartes de sources (bleu, FileText)
```

> **⚠️ AVANT DE CODER :** ouvre `app/api/chat.py`, repère le helper `sse`, l'appel retrieval interne, la variable `sources` (internes) et le `contexte` assemblé. Tu **ajoutes** une branche web ; tu ne réécris rien. Repère aussi si le générateur SSE est `async` (→ httpx async) ou non.

---

## Ce qu'il faut construire

1. `app/config.py` — ajouter `TAVILY_API_KEY`.
2. `.env` — ajouter `TAVILY_API_KEY=tvly-...`.
3. `app/tools/web.py` — appel Tavily + formatage.
4. **Branche web** dans `app/api/chat.py` (déclenchée uniquement si `web === true`).
5. Front : champ `web` dans la requête, interrupteur dans `chat.tsx`, couleur orange dans `sources.tsx`, champ `type` sur `Source`.

---

## Spécifications techniques

### 1. `app/config.py` — ajouter le réglage

```python
TAVILY_API_KEY: str = ""   # vide = recherche web désactivée (dégradation douce)
```

### 2. `.env`

```bash
# Recherche web (clé gratuite sur tavily.com) — vide = désactivé
TAVILY_API_KEY=tvly-...
```

### 3. `app/tools/web.py`

**Version async** (si le générateur SSE de `chat.py` est `async`) :

```python
import httpx

from app.config import settings

TAVILY_URL = "https://api.tavily.com/search"


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Recherche web via Tavily. Renvoie [{title, url, content}].
    Ne DOIT être appelée QUE lorsque l'utilisateur a activé le toggle (jamais automatique)."""
    if not settings.TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                TAVILY_URL,
                headers={"Authorization": f"Bearer {settings.TAVILY_API_KEY}"},
                json={
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
            for r in data.get("results", [])
        ]
    except Exception:
        return []


def format_web_context(results: list[dict]) -> str:
    if not results:
        return ""
    blocs = [
        f"[WEB {i}] {r['title']}\nURL : {r['url']}\n{r['content']}"
        for i, r in enumerate(results, 1)
    ]
    return "=== RÉSULTATS WEB (source externe, à vérifier) ===\n" + "\n\n".join(blocs)
```

> **Variante sync** (si le générateur n'est pas async) : remplace le corps par
> ```python
> resp = httpx.post(TAVILY_URL, headers={"Authorization": f"Bearer {settings.TAVILY_API_KEY}"},
>                   json={...}, timeout=15.0)
> resp.raise_for_status()
> data = resp.json()
> ```
> et retire `async`/`await`.

### 4. Branche web dans `app/api/chat.py`

- La requête accepte désormais un champ **`web: bool = False`** (l'ajouter au modèle Pydantic de la requête).
- Dans le générateur SSE, **après** le retrieval interne (variables `chunks`, `sources`, `contexte` existantes) et **avant** la génération :

```python
from app.tools.web import web_search, format_web_context

# `web` = valeur du champ de la requête (False par défaut).
web_results = []
if web:                                            # ⚠️ UNIQUEMENT si l'utilisateur a activé le toggle
    yield sse("status", {"label": "Recherche sur le web…"})
    web_results = await web_search(question)        # ou version sync selon chat.py
    if web_results:
        web_ctx = format_web_context(web_results)
        contexte = (contexte + "\n\n" + web_ctx) if contexte else web_ctx
        for r in web_results:
            sources.append({
                "type": "web",                      # ← déclenche le rendu orange
                "document": r["title"],
                "url": r["url"],
                "extrait": (r["content"] or "")[:300],
            })

# Refus si AUCUN contexte (ni interne ni web)
if not chunks and not web_results:
    # → chemin "je ne sais pas" habituel (réutiliser le bloc existant)
    ...
```

- Ajouter à la fin du prompt utilisateur (ou en note) que le modèle peut s'appuyer sur les blocs `[WEB]` en plus du corpus interne, et **signaler quand une information provient du web**.
- L'événement `sources` émis contient donc **internes (sans type) + web (type "web")**. Ne pas modifier le sérialiseur des sources internes.

### 5. Front

**`web/lib/types.ts`** — ajouter le champ sur `Source` :
```typescript
type?: "interne" | "web";   // absent/interne → bleu ; "web" → orange
```

**`web/lib/use-rag-chat.ts`** — `send` prend l'état du toggle et l'envoie :
```typescript
const send = useCallback(
  async (question: string, web: boolean = false) => {
    // …
    body: JSON.stringify({ question: q, user_groups: userGroups, web }),
    // …
  },
  [userGroups, isStreaming]
);
```

**`web/components/sources.tsx`** — colorer selon `type` :
```tsx
"use client";

import { useState } from "react";
import { FileText, Globe, ChevronDown } from "lucide-react";
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
  const isWeb = source.type === "web";

  const label = [
    (source as { document?: string }).document ?? (source as { doc?: string }).doc,
    source.section,
    source.page ? `p.${source.page}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const accent = isWeb ? "text-orange-600" : "text-blue-600";
  const num = isWeb ? "text-orange-700" : "text-blue-700";
  const Icon = isWeb ? Globe : FileText;

  // Web : le clic ouvre l'URL. Interne : le clic déplie l'extrait.
  if (isWeb && source.url) {
    return (
      <a
        href={source.url}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-1.5 rounded-lg border border-orange-200 bg-orange-50 px-2.5 py-1.5 text-xs hover:bg-orange-100"
      >
        <Icon className={`h-3.5 w-3.5 shrink-0 ${accent}`} />
        <span className={`font-semibold ${num}`}>{index}.</span>
        <span className="text-foreground/80">{label || source.url}</span>
        <span className="text-orange-500">↗</span>
      </a>
    );
  }

  return (
    <div className="rounded-lg border bg-card text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 text-left hover:bg-accent"
      >
        <Icon className={`h-3.5 w-3.5 shrink-0 ${accent}`} />
        <span className={`font-semibold ${num}`}>{index}.</span>
        <span className="text-foreground/80">{label}</span>
        <ChevronDown className={`h-3 w-3 shrink-0 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="max-w-md border-t px-2.5 py-2 leading-relaxed text-muted-foreground">
          {source.extrait}
        </div>
      )}
    </div>
  );
}
```

**`web/components/chat.tsx`** — l'interrupteur Web + passage à `send` :
```tsx
// imports
import { Globe } from "lucide-react";
import { cn } from "@/lib/utils";

// dans le composant Chat, à côté des autres états :
const [web, setWeb] = useState(false);

// submit envoie l'état du toggle :
const submit = () => {
  if (!input.trim() || isStreaming) return;
  send(input, web);
  setInput("");
};

// EmptyState : passer aussi web
// <EmptyState onPick={(q) => send(q, web)} disabled={isStreaming} />

// Zone d'input : ajouter l'interrupteur au-dessus du textarea
<div className="border-t p-4">
  <div className="flex flex-col gap-2 rounded-xl border bg-background p-2 focus-within:ring-2 focus-within:ring-ring">
    <div className="flex items-center gap-2 px-1">
      <button
        type="button"
        onClick={() => setWeb((w) => !w)}
        className={cn(
          "flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors",
          web
            ? "border-orange-300 bg-orange-50 text-orange-700"
            : "border-transparent text-muted-foreground hover:bg-accent"
        )}
        title="Recherche web"
      >
        <Globe className="h-3.5 w-3.5" />
        Web
      </button>
      {web && (
        <span className="text-xs text-orange-600">
          Résultats web ajoutés · votre question quitte l'entreprise
        </span>
      )}
    </div>
    <div className="flex items-end gap-2">
      {/* … textarea existant … */}
      {/* … bouton Send existant … */}
    </div>
  </div>
</div>
```

---

## Contraintes impératives

- **INTERDIT** : recherche web automatique. Le backend n'appelle Tavily **QUE si `web === true`** dans la requête. Le LLM ne déclenche jamais la recherche.
- Le retrieval interne reste **filtré par ACL**, inchangé. Le web est un tuyau **séparé**.
- Les sources web portent `type: "web"` → rendu **orange**. Ne pas modifier le sérialiseur des sources internes.
- L'interrupteur affiche un **avertissement** quand il est allumé (la question sort de l'entreprise).
- `TAVILY_API_KEY` dans `.env` (gitignore). Absente → `web_search` renvoie `[]` proprement.
- Ne pas installer de SDK Tavily : appel REST direct via `httpx`.

---

## Definition of Done

```bash
cd c:\Users\ISSA\Desktop\RAG
docker compose up -d
cd web && npm run dev
# → http://localhost:3000
```

**Résultat attendu exactement :**

1. **Toggle éteint** — taper « La réglementation sur le congé paternité a changé en 2026 ? »
   → réponse « je n'ai pas cette information » (hors corpus), **aucune source web**.
2. **Toggle allumé** — activer l'interrupteur **Web** (il devient orange, l'avertissement apparaît), reposer la même question
   → un statut « Recherche sur le web… », puis une réponse **à jour**, avec des **cartes de sources orange** (Légifrance / service-public.fr) **cliquables** vers l'URL.
3. **Distinction visuelle** — sur une question interne avec le toggle allumé : les sources **internes restent bleues**, les éventuelles sources **web sont orange** — nettement séparées.
4. **Sécurité** — toggle éteint = **aucun appel réseau externe** (le web ne part jamais tout seul).

**Si la recherche web se déclenche sans que l'utilisateur ait activé le toggle → NON conforme (faille de sécurité).**
