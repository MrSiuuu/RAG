# CDC 4 — La génération et le streaming (l'assistant parle)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Prendre les 5 morceaux trouvés au CDC 3, les donner à lire à GPT, et lui faire **rédiger une réponse en français, avec ses sources citées** — les mots arrivant **au fil de l'eau**, comme dans ChatGPT.

Et s'il ne trouve pas la réponse dans les morceaux : **il dit « je ne sais pas »**. Il n'invente pas.

---

## 💡 Pourquoi c'est important

Reprends l'image du début :

| | Qui | Fait |
|---|---|---|
| 🔍 **Le bibliothécaire** | CDC 3 ✅ | fouille les étagères, ramène 5 passages |
| ✍️ **Le stagiaire** | **CDC 4 — ici** | lit les 5 passages, rédige la réponse, cite ses sources |

**C'est le CDC où le projet devient visible.** Jusqu'ici tu avais des chunks et des scores. À la fin de celui-ci, tu as **une réponse**.

Et c'est le CDC qui tue **l'objection n°1** :

> ❌ *« Ça hallucine, on ne peut pas faire confiance »*
>
> ✅ **Citations obligatoires** (document + section + page) + **« je ne sais pas »** quand le corpus ne couvre pas.

---

## 📚 Les concepts — en français

### 1. Le prompt système : les règles du jeu

GPT n'est pas obéissant par défaut. Si tu lui donnes 5 paragraphes et une question, il va **compléter avec ce qu'il croit savoir**. C'est exactement ce qu'on ne veut pas.

Alors on lui écrit **des règles très strictes**, en français, qu'il lit avant chaque question :

```
Tu réponds UNIQUEMENT à partir des passages fournis.
Si l'information n'y est pas, tu dis : "Je n'ai pas trouvé cette
information dans les documents auxquels vous avez accès."
Tu cites TOUJOURS ta source : [Document, Section, page].
Tu n'inventes RIEN. Tu ne complètes RIEN avec tes connaissances générales.
```

**Ce texte, c'est le prompt système.** C'est le levier de qualité le plus sous-estimé du projet.

### 2. Température 0 : pas de créativité

La « température », c'est le curseur de créativité de GPT.

| Température | Comportement |
|---|---|
| **1** (par défaut) | il varie, il reformule, il improvise |
| **0** | il donne toujours la réponse la plus probable |

**Nous, on veut le document, pas de la poésie.** Température 0.

> ⚠️ **Attention :** certains modèles récents **refusent** `temperature=0` (tu l'as déjà vu au CDC 3 avec le reranker). Le code doit gérer ce cas : essayer avec 0, et si le modèle refuse, réessayer sans le paramètre.

### 3. Le streaming : pourquoi c'est vital

Sans streaming :

```
[l'utilisateur pose sa question]
[écran figé... 1s... 2s... 3s... 4s...]
[BOUM — la réponse complète apparaît d'un coup]
```

**Ça a l'air cassé.** Pendant 4 secondes, l'utilisateur croit que le truc est planté.

Avec streaming :

```
[l'utilisateur pose sa question]
Le
Le salarié
Le salarié bénéficie
Le salarié bénéficie de 25
Le salarié bénéficie de 25 jours...
```

**Les mots arrivent un par un.** Comme ChatGPT. **C'est ce qui transforme un script en produit.**

### 4. SSE : la technique du streaming

**SSE = Server-Sent Events.** C'est une vieille technique web, très simple : au lieu de renvoyer une réponse d'un coup, le serveur garde la connexion ouverte et **envoie des petits messages au fur et à mesure**.

Chaque message ressemble à ça :

```
event: token
data: {"texte": "Le"}

event: token
data: {"texte": " salarié"}
```

C'est du texte brut. Pas de WebSocket, pas de magie. FastAPI le fait nativement.

### 5. Les événements de statut — LE plus gros effet visuel du projet

On n'envoie pas que les mots de la réponse. On envoie aussi **ce que le système est en train de faire** :

```
event: status    {"label": "Recherche dans 10 documents RH…"}
event: status    {"label": "Sélection des 5 passages les plus pertinents…"}
event: sources   [{doc, section, page, extrait}, ...]
event: token     {"texte": "Le"}
event: token     {"texte": " salarié"}
event: done      {"latence_ms": 2300, "cout": 0.0004}
```

**En démo, c'est ça qui fait "waouh".** L'utilisateur voit le système travailler. Il ne regarde pas un écran figé — il regarde un moteur tourner.

C'est ta **feature 1.3**. Coût de développement : quasi nul. Impact visuel : maximal.

### 6. La citation : format et pourquoi

Chaque affirmation doit pouvoir être vérifiée. Donc GPT doit citer :

```
Le salarié bénéficie de 25 jours ouvrés de congés payés par an.
[Procédure congés payés · 1.1 Le droit annuel · p.—]
```

Et on renvoie **en parallèle** un événement `sources` structuré, pour que le front (CDC 8) puisse afficher des **cartes cliquables** sous la réponse.

> **Le texte cite. Les cartes prouvent.**

### 7. « Je ne sais pas » — ce n'est pas un échec, c'est la feature

Contre-intuitif, mais c'est **le point le plus fort de ta démo** :

> *« Le taux de "je ne sais pas" n'est pas un bug. C'est le taux d'honnêteté du système. Un assistant qui répond toujours, c'est un assistant qui invente. »*

Et au CDC 12, ces « je ne sais pas » deviennent **la liste des documents qui manquent aux RH**. C'est un livrable, pas un défaut.

---

## 🧩 Où ça s'insère

### Ce qui existe après le CDC 3

```
app/
├── config.py            Settings
├── db.py                connexion Postgres
├── main.py              GET /health, POST /search
├── ingest/              ✅ pipeline d'ingestion
├── retrieval/           ✅ acl, vector, fulltext, fusion, rerank, pipeline
└── api/
    └── search.py        ✅ POST /search (debug)
```

**`rechercher()` dans `app/retrieval/pipeline.py` renvoie déjà :**
- les 5 chunks enfants
- leurs chunks parents (les sections complètes)

### Ce que le CDC 4 ajoute

```
app/
├── llm/
│   ├── __init__.py
│   ├── prompts.py       le prompt système français ⭐
│   ├── contexte.py      assembler les chunks en contexte lisible
│   ├── citations.py     extraire les sources structurées
│   └── generate.py      appel OpenAI en streaming
└── api/
    └── chat.py          POST /api/chat (SSE)
```

---

## ⚠️ Les pièges de ce CDC

### 🔴 Piège n°1 — Le modèle qui refuse `temperature=0`

Tu l'as déjà rencontré au CDC 3 :

```
openai.BadRequestError: 'temperature' does not support 0 with this model.
```

→ **Le code doit essayer avec `temperature=0`, et si le modèle refuse, réessayer sans le paramètre.** Un helper unique, réutilisé partout.

### 🔴 Piège n°2 — Le streaming qui ne stream pas

Si tu construis la réponse complète et que tu l'envoies d'un coup, ce n'est **pas** du streaming — même si tu utilises SSE.

Il faut :
1. `stream=True` dans l'appel OpenAI
2. Boucler sur les morceaux reçus
3. Les renvoyer **immédiatement** avec `yield`

→ Test : `curl -N` doit afficher les mots **progressivement**. Si tout arrive d'un coup, c'est cassé.

### 🔴 Piège n°3 — Les accents cassés en SSE

SSE est un format texte. Si l'encodage n'est pas explicite, les accents français partent en `Ã©`.

→ `media_type="text/event-stream; charset=utf-8"` et `json.dumps(..., ensure_ascii=False)`.

### 🔴 Piège n°4 — Le buffering du proxy

Si tu déploies derrière un reverse proxy (CDC 13), il peut **accumuler** les messages et les envoyer d'un coup → le streaming meurt.

→ On ajoute dès maintenant l'en-tête `X-Accel-Buffering: no`. Ça coûte une ligne, ça évite un debug de 2 heures dans 3 semaines.

### 🔴 Piège n°5 — Donner l'enfant au lieu du parent

Rappel du CDC 2 :
- l'**enfant** (le petit morceau) sert à **TROUVER**
- le **parent** (la section complète) sert à **RÉPONDRE**

→ Le contexte qu'on donne à GPT doit contenir **les parents**, pas les enfants. Sinon il lit une phrase hors contexte et répond mal.

**Mais la citation, elle, porte sur l'enfant** (c'est lui qui est précis : section + page).

### 🔴 Piège n°6 — Zéro chunk → ne pas appeler GPT du tout

Si le CDC 3 renvoie `chunks: []` (Paul sur la grille des salaires), **on n'appelle même pas GPT**.

On renvoie directement le message *« je n'ai pas d'information accessible »*.

**Pourquoi c'est important :**
- ça coûte 0 €
- c'est instantané
- et surtout : **GPT ne voit rien**. Il ne peut rien inventer sur des données qu'il n'a jamais reçues.

---

## 🗣️ Ce que je pourrai dire en réunion

> *« Le modèle ne répond qu'à partir des passages qu'on lui fournit, à température zéro, avec citation obligatoire. Quand le corpus ne couvre pas la question, il le dit — il ne complète pas avec ses connaissances générales. Ce n'est pas une limite du système : c'est sa garantie. »*

Et sur les statuts en direct :

> *« Ce que vous voyez défiler, ce ne sont pas des animations. C'est le pipeline réel : reformulation, recherche, sélection, génération. Chaque étape est traçable dans l'audit log. »*

---
---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

Je construis **RAG Dyneff** : un assistant qui répond aux questions RH des collaborateurs en s'appuyant **uniquement** sur un corpus de documents internes, avec citations obligatoires et filtrage par droits d'accès.

**Stack (verrouillée) :** Python 3.12 · uv · FastAPI · Postgres 16 + pgvector · SDK OpenAI (une seule clé) · Next.js 15 (plus tard).

**Interdits absolus :**
LangChain · LlamaIndex · Qdrant · Pinecone · Weaviate · Chroma · Ragas · Redis · Celery · Alembic · Azure · LibreChat · Open WebUI.

---

## État actuel du code

```
rag-dyneff/
├── db/init.sql
├── app/
│   ├── config.py          # Settings (pydantic-settings)
│   ├── db.py              # connexion psycopg 3
│   ├── main.py            # GET /health, GET /health/db, POST /search
│   ├── ingest/            # ✅ ingestion — NE PAS MODIFIER
│   ├── retrieval/         # ✅ retrieval — NE PAS MODIFIER
│   │   ├── acl.py
│   │   ├── vector.py
│   │   ├── fulltext.py
│   │   ├── fusion.py
│   │   ├── rerank.py
│   │   └── pipeline.py    # rechercher() → ResultatRecherche
│   └── api/
│       ├── __init__.py
│       └── search.py      # ✅ POST /search
└── corpus/                # 10 documents, 186 chunks enfants + 75 parents
```

**Ce que `app/retrieval/pipeline.py::rechercher()` renvoie déjà :**

```python
@dataclass
class ResultatRecherche:
    chunks_enfants: list[dict]     # les top_n chunks (5) — servent à CITER
    chunks_parents: list[dict]     # les sections complètes — servent à RÉPONDRE
    question_recrite: str
    nb_candidats_avant_rerank: int
    duree_ms: int
```

**Champs d'un chunk (dict) :**
`id`, `document_id`, `type`, `parent_id`, `breadcrumb`, `contenu`, `contenu_indexe`, `page`, `allowed_groups`, `nb_tokens`, `ordre`, et selon la source : `score_vecteur`, `score_texte`, `score_rrf`.

**Variables disponibles dans `settings` :**
```python
openai_api_key: str
llm_model: str            # le modèle fort — génération
llm_model_fast: str       # le modèle mini
temperature: float        # 0
top_n: int                # 5
```

**⚠️ Fait connu du CDC 3 :** le modèle configuré **refuse `temperature=0`**
(`BadRequestError: 'temperature' does not support 0 with this model`).
Le code doit gérer ce cas proprement (voir spécification ci-dessous).

---

## Ce qu'il faut construire

```
app/llm/
├── __init__.py
├── prompts.py        # le prompt système français ⭐
├── contexte.py       # assembler les chunks parents en contexte
├── citations.py      # extraire les sources structurées
└── generate.py       # appel OpenAI en STREAMING + helper température

app/api/
└── chat.py           # POST /api/chat — réponse SSE
```

Et brancher le router dans `app/main.py`.

---

## Spécifications techniques

### `app/llm/prompts.py`

```python
PROMPT_SYSTEME = """Tu es l'assistant RH de Dyneff, distributeur multi-énergies français.

RÈGLES ABSOLUES — tu ne les enfreins JAMAIS :

1. Tu réponds UNIQUEMENT à partir des PASSAGES fournis ci-dessous.
   Tu n'utilises AUCUNE connaissance générale. Aucune.

2. Si l'information demandée n'est PAS dans les passages, tu réponds
   EXACTEMENT ceci, sans rien ajouter :
   "Je n'ai pas trouvé cette information dans les documents auxquels vous avez accès."

3. Tu cites TOUJOURS ta source, juste après l'affirmation concernée,
   au format : [Nom du document · Section]
   Exemple : Le salarié bénéficie de 25 jours ouvrés de congés payés par an.
             [Procédure congés payés · 1.1 Le droit annuel à congés payés]

4. Tu n'inventes AUCUN chiffre, AUCUNE date, AUCUN nom, AUCUNE procédure.
   Si un chiffre n'est pas écrit dans les passages, tu ne le donnes pas.

5. Tu réponds en français, de façon claire et concise.
   Tu utilises du markdown (gras, listes, tableaux) quand c'est utile.

6. Si les passages se contredisent, tu le SIGNALES explicitement
   au lieu de choisir arbitrairement.

7. Tu ne dis jamais "selon les passages fournis" ni "d'après le contexte".
   Tu réponds directement, et tu cites.

PASSAGES DISPONIBLES :
{contexte}
"""

MESSAGE_AUCUN_ACCES = (
    "Je n'ai pas trouvé cette information dans les documents "
    "auxquels vous avez accès."
)
```

---

### `app/llm/contexte.py`

```python
def assembler_contexte(
    chunks_parents: list[dict],
    chunks_enfants: list[dict],
) -> str:
    """Assemble les passages en un bloc de texte lisible par le LLM.

    RÈGLE (Piège n°5) :
    - On donne les PARENTS (les sections complètes) — c'est ça qu'on lit.
    - Si un chunk enfant n'a pas de parent, on donne l'enfant.
    - On dédoublonne : un parent ne doit apparaître qu'UNE fois,
      même si plusieurs de ses enfants ont été retenus.

    Format de sortie :

    ─── PASSAGE 1 ───
    Document : Procédure congés payés
    Section  : 1. L'acquisition des congés

    Chaque salarié acquiert un droit à congés payés de 25 jours ouvrés...

    ─── PASSAGE 2 ───
    ...
    """
```

**Implémentation attendue :**

```python
def assembler_contexte(chunks_parents, chunks_enfants):
    # 1. Les parents à utiliser, dédoublonnés, dans l'ordre de pertinence des enfants
    parents_par_id = {p["id"]: p for p in chunks_parents}
    passages: list[dict] = []
    vus: set[int] = set()

    for enfant in chunks_enfants:
        pid = enfant.get("parent_id")
        if pid is not None and pid in parents_par_id:
            if pid not in vus:
                vus.add(pid)
                passages.append(parents_par_id[pid])
        else:
            # pas de parent → on utilise l'enfant lui-même
            if enfant["id"] not in vus:
                vus.add(enfant["id"])
                passages.append(enfant)

    # 2. Formatage
    blocs = []
    for i, p in enumerate(passages, start=1):
        blocs.append(
            f"─── PASSAGE {i} ───\n"
            f"{p['breadcrumb']}\n"
            f"{p['contenu']}"
        )
    return "\n\n".join(blocs)
```

---

### `app/llm/citations.py`

```python
from pydantic import BaseModel


class Citation(BaseModel):
    chunk_id: int
    document: str          # "Procédure congés payés"
    section: str           # "1. L'acquisition des congés > 1.1 Le droit annuel"
    page: int | None
    extrait: str           # 200 premiers caractères du contenu de l'ENFANT


def extraire_citations(chunks_enfants: list[dict]) -> list[Citation]:
    """Construit les citations structurées à partir des chunks ENFANTS.

    Piège n°5 : c'est l'ENFANT qui cite (il est précis : section + page),
    pas le parent (trop large).

    Le breadcrumb a ce format exact :
        "Document : Procédure congés payés\\nSection  : 1. Acquisition > 1.1 Droit\\n---"

    → parser sur les préfixes "Document : " et "Section  : "
      (attention : DEUX espaces après "Section")
    """
```

**Parsing du breadcrumb — robuste :**

```python
def _parser_breadcrumb(breadcrumb: str) -> tuple[str, str]:
    document = ""
    section = ""
    for ligne in breadcrumb.split("\n"):
        ligne = ligne.strip()
        if ligne.startswith("Document :"):
            document = ligne.removeprefix("Document :").strip()
        elif ligne.startswith("Section"):
            # "Section  :" avec un ou deux espaces
            _, _, reste = ligne.partition(":")
            section = reste.strip()
    return document, section
```

---

### `app/llm/generate.py`

#### Le helper température — OBLIGATOIRE (Piège n°1)

```python
from openai import OpenAI, BadRequestError


def _appel_avec_temperature(client: OpenAI, **kwargs):
    """Appelle l'API en essayant temperature=0.

    Certains modèles récents REFUSENT temperature=0 et n'acceptent
    que la valeur par défaut (1). Constaté au CDC 3 sur le reranker.
    → On essaie avec, et si le modèle refuse, on réessaie sans.
    """
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise
```

#### La génération en streaming

```python
from collections.abc import Iterator


def generer_streaming(
    question: str,
    contexte: str,
    modele: str,
    temperature: float,
) -> Iterator[str]:
    """Génère la réponse en STREAMING. Yield chaque morceau de texte
    dès qu'il arrive. NE PAS accumuler puis tout renvoyer (Piège n°2).
    """
    client = OpenAI()

    flux = _appel_avec_temperature(
        client,
        model=modele,
        temperature=temperature,
        stream=True,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEME.format(contexte=contexte)},
            {"role": "user", "content": question},
        ],
    )

    for morceau in flux:
        if not morceau.choices:
            continue
        texte = morceau.choices[0].delta.content
        if texte:
            yield texte          # ⭐ yield IMMÉDIAT — c'est ça, le streaming
```

---

### `app/api/chat.py` — L'endpoint SSE

```python
import json
import time
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class RequeteChat(BaseModel):
    question: str
    user_groups: list[str] = ["grp-tous"]
```

#### Le format SSE — helper

```python
def sse(evenement: str, donnees: dict | list) -> str:
    """Formate un événement SSE.

    ⚠️ ensure_ascii=False — sinon les accents français partent en \\u00e9
    """
    charge = json.dumps(donnees, ensure_ascii=False)
    return f"event: {evenement}\ndata: {charge}\n\n"
```

#### Le générateur d'événements

```python
def flux_evenements(requete: RequeteChat) -> Iterator[str]:
    debut = time.perf_counter()

    # ── 1. Statut : recherche ────────────────────────────────────
    yield sse("status", {"label": "Recherche dans les documents RH…"})

    with get_connection() as conn:
        resultat = rechercher(
            conn,
            question=requete.question,
            groupes_utilisateur=requete.user_groups,
            settings=settings,
        )

    # ── 2. AUCUN CHUNK → on n'appelle PAS le LLM (Piège n°6) ────
    if not resultat.chunks_enfants:
        yield sse("sources", [])
        yield sse("token", {"texte": MESSAGE_AUCUN_ACCES})
        yield sse("done", {
            "latence_ms": int((time.perf_counter() - debut) * 1000),
            "a_repondu": False,
            "nb_sources": 0,
        })
        return

    # ── 3. Statut : sélection ────────────────────────────────────
    yield sse("status", {
        "label": f"Sélection des {len(resultat.chunks_enfants)} passages les plus pertinents…"
    })

    # ── 4. Les sources, AVANT la réponse ─────────────────────────
    citations = extraire_citations(resultat.chunks_enfants)
    yield sse("sources", [c.model_dump() for c in citations])

    # ── 5. Statut : rédaction ────────────────────────────────────
    yield sse("status", {"label": "Rédaction de la réponse…"})

    # ── 6. Les tokens, au fil de l'eau ───────────────────────────
    contexte = assembler_contexte(resultat.chunks_parents, resultat.chunks_enfants)
    reponse_complete = []

    for texte in generer_streaming(
        question=requete.question,
        contexte=contexte,
        modele=settings.llm_model,
        temperature=settings.temperature,
    ):
        reponse_complete.append(texte)
        yield sse("token", {"texte": texte})

    # ── 7. Fin ───────────────────────────────────────────────────
    texte_final = "".join(reponse_complete)
    a_repondu = MESSAGE_AUCUN_ACCES not in texte_final

    yield sse("done", {
        "latence_ms": int((time.perf_counter() - debut) * 1000),
        "a_repondu": a_repondu,
        "nb_sources": len(citations),
    })
```

#### L'endpoint

```python
@router.post("/api/chat")
async def chat(requete: RequeteChat):
    return StreamingResponse(
        flux_evenements(requete),
        media_type="text/event-stream; charset=utf-8",   # ⚠️ charset — Piège n°3
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",                    # ⚠️ anti-buffering — Piège n°4
        },
    )
```

**Dans `app/main.py` :**
```python
from app.api.chat import router as chat_router
app.include_router(chat_router)
```

---

## Récapitulatif des événements SSE

| Événement | Charge utile | Quand |
|---|---|---|
| `status` | `{"label": "..."}` | 3 fois : recherche, sélection, rédaction |
| `sources` | `[{chunk_id, document, section, page, extrait}, ...]` | **1 fois, AVANT les tokens** |
| `token` | `{"texte": "..."}` | N fois, au fil de l'eau |
| `done` | `{"latence_ms": int, "a_repondu": bool, "nb_sources": int}` | 1 fois, à la fin |

**L'ordre est imposé.** Le front (CDC 8) en dépend.

---

## Contraintes impératives

### ❌ INTERDIT

| Interdit | Pourquoi |
|---|---|
| **Accumuler la réponse puis l'envoyer d'un coup** | Ce n'est pas du streaming (Piège n°2) |
| **Appeler le LLM quand `chunks_enfants` est vide** | Piège n°6 — coût inutile + risque d'invention |
| **Donner les chunks ENFANTS au LLM** | Il faut les PARENTS (Piège n°5) |
| **Citer les chunks PARENTS** | La citation doit être précise → l'ENFANT |
| **`ensure_ascii=True`** (défaut de `json.dumps`) | Les accents cassent (Piège n°3) |
| **Laisser planter sur `temperature=0`** | Piège n°1 — helper obligatoire |
| **LangChain, LlamaIndex** | Décision figée |
| **Modifier `app/retrieval/` ou `app/ingest/`** | Ils fonctionnent. On ne touche pas. |

### ✅ OBLIGATOIRE

1. **Le prompt système en français**, avec les 7 règles, tel qu'écrit ci-dessus.
2. **Le helper `_appel_avec_temperature`** — réutilisable.
3. **`yield` immédiat** dans la boucle de streaming.
4. **`ensure_ascii=False`** partout dans les `json.dumps`.
5. **Les 4 en-têtes HTTP** (`Cache-Control`, `Connection`, `X-Accel-Buffering`, `charset`).
6. **Tout en français** : fonctions, variables, commentaires, messages.
7. **Type hints Python 3.12 partout.**
8. **Aucune valeur en dur** — tout vient de `settings`.

---

## Definition of Done

### Test 1 — 🔴 LE STREAMING STREAME VRAIMENT

Crée `test-chat.json` :
```json
{"question": "Combien de jours de congés payés par an ?", "user_groups": ["grp-tous"]}
```

Puis :
```bash
curl -N -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  --data-binary "@test-chat.json"
```

**Attendu — les événements arrivent DANS CET ORDRE, PROGRESSIVEMENT :**

```
event: status
data: {"label": "Recherche dans les documents RH…"}

event: status
data: {"label": "Sélection des 5 passages les plus pertinents…"}

event: sources
data: [{"chunk_id": 39, "document": "Procedure Conges payes et RTT", "section": "1. L'acquisition des congés > 1.1 Le droit annuel à congés payés", "page": null, "extrait": "Chaque salarié acquiert..."}, ...]

event: status
data: {"label": "Rédaction de la réponse…"}

event: token
data: {"texte": "Le"}

event: token
data: {"texte": " salarié"}

...

event: done
data: {"latence_ms": 2847, "a_repondu": true, "nb_sources": 5}
```

**🔴 CRITÈRE ÉLIMINATOIRE :** les `event: token` doivent apparaître **un par un**, sur plusieurs secondes.
**S'ils arrivent tous d'un coup à la fin → LE STREAMING NE MARCHE PAS. Ce n'est pas fini.**

**Vérifie aussi :**
- ✅ les accents s'affichent bien (`congés`, pas `congÃ©s`)
- ✅ la réponse contient **25 jours ouvrés**
- ✅ la réponse contient au moins une citation `[... · ...]`

---

### Test 2 — 🔒 Paul ne voit rien, et le LLM n'est PAS appelé

`test-acl.json` :
```json
{"question": "Quelle est la grille des salaires ?", "user_groups": ["grp-tous"]}
```

```bash
curl -N -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  --data-binary "@test-acl.json"
```

**Attendu :**
```
event: status
data: {"label": "Recherche dans les documents RH…"}

event: sources
data: []

event: token
data: {"texte": "Je n'ai pas trouvé cette information dans les documents auxquels vous avez accès."}

event: done
data: {"latence_ms": ..., "a_repondu": false, "nb_sources": 0}
```

**Critères :**
- ✅ `"sources": []`
- ✅ `"a_repondu": false`
- ✅ **AUCUN** `event: status` "Rédaction de la réponse…" → **preuve que le LLM n'a pas été appelé**
- ✅ latence < 3000 ms (pas d'appel à GPT = rapide)

---

### Test 3 — 🔒 Marie (RH) obtient la réponse

`test-marie.json` :
```json
{"question": "Quelle est la grille des salaires ?", "user_groups": ["grp-rh", "grp-tous"]}
```

**Attendu :** une vraie réponse, avec des sources pointant vers **« Grille de remuneration 2026 »**.

---

### Test 4 — « Je ne sais pas » sur une question hors corpus

`test-horscorpus.json` :
```json
{"question": "Quelle est la politique RSE de TotalEnergies ?", "user_groups": ["grp-tous"]}
```

**Attendu :** *« Je n'ai pas trouvé cette information dans les documents auxquels vous avez accès. »*

**Critère :** le modèle **n'invente RIEN** sur TotalEnergies, alors qu'il en sait forcément quelque chose.
**C'est le test qui prouve que le prompt système tient.**

---

### Test 5 — Question piège : chiffre absent du corpus

`test-piege.json` :
```json
{"question": "Combien de jours de congé paternité en 2026 ?", "user_groups": ["grp-tous"]}
```

*(Le congé paternité est un des 7 « trous connus » du manifest — il n'est PAS dans le corpus.)*

**Attendu :** *« Je n'ai pas trouvé cette information… »*

**🔴 Si le modèle donne un chiffre (25 jours, 28 jours…), il a halluciné.**
→ Renforcer la règle n°4 du prompt système et retester.

---

**Les 5 tests doivent passer. Les tests 1 (streaming), 2 (ACL) et 5 (hallucination) sont non négociables.**

```
═══════════════════════════════════════════════════════════════
                   FIN DE LA PARTIE B
═══════════════════════════════════════════════════════════════
```
