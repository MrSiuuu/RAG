# CDC 3 — Le retrieval (trouver les bons morceaux)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Quand quelqu'un pose une question, **trouver les 5 morceaux les plus pertinents** dans la base — en cherchant par sens ET par mots exacts, en filtrant les droits d'accès, et en reclassant les résultats avec GPT.

---

## 💡 Pourquoi c'est important

Le CDC 2 a rempli ta base. Mais pour l'instant, personne ne peut l'interroger.

Le CDC 3, c'est **le bibliothécaire**. Rappelle-toi l'image du début :

> L'assistant est un stagiaire brillant. Mais avant qu'il réponde, le bibliothécaire fouille les étagères et revient avec les 5 passages les plus pertinents.

**C'est exactement ce CDC.** Le stagiaire (le LLM qui répond) arrive au CDC 4. Ici on construit le bibliothécaire.

À la fin, tu pourras taper une question dans le terminal et **voir arriver les bons morceaux**. Avant même qu'il y ait un front. C'est le test le plus important du projet.

---

## 📚 Les concepts — en français

### 1. Pourquoi chercher de deux façons

Imagine que tu cherches *« Article 402 »* dans ta base.

**Recherche par sens :** elle transforme *« Article 402 »* en liste de nombres, et cherche les morceaux dont les nombres sont proches. Problème : *« Article 402 »* n'a pas vraiment de sens — c'est un code. La recherche par sens va ramener des trucs vaguement liés aux articles, mais pas forcément *l'Article 402*.

**Recherche par mots exacts :** elle cherche littéralement le texte *« Article 402 »* dans les morceaux. Elle le trouve.

| | Ce qu'elle trouve bien | Ce qu'elle rate |
|---|---|---|
| **Par sens** | « vacances » → « congés payés » | « Article 402 », « IDCC 1388 » |
| **Par mots exacts** | « Article 402 » exactement | les synonymes |

**Il faut les deux.** On les lance en parallèle, et on fusionne les deux listes.

### 2. La fusion — comment on mélange deux listes

Chaque recherche renvoie ses résultats classés par pertinence.

```
Recherche par sens :        Recherche par mots exacts :
  1. morceau A                1. morceau C
  2. morceau B                2. morceau A
  3. morceau C                3. morceau D
  4. morceau D                4. morceau B
```

On fusionne avec une formule simple : **plus un morceau est bien classé dans les DEUX listes, plus il monte**. Un morceau qui est n°1 dans les deux listes écrase tout.

Ça s'appelle RRF. C'est ~15 lignes de Python. Pas de librairie.

### 3. Le reclassement — pourquoi la recherche rapide ne suffit pas

La fusion rapide ramène **25 candidats**. Mais elle n'est pas parfaite — elle est rapide, pas fine.

Alors on envoie ces 25 candidats au **petit modèle GPT** et on lui dit :
> *« Voilà la question. Voilà 25 morceaux. Dis-moi les 5 qui répondent vraiment à la question, en JSON. »*

GPT relit, réfléchit, renvoie les 5 meilleurs IDs.

**C'est le meilleur rapport qualité/effort de tout le projet.** ~25 lignes de code, et la qualité des résultats monte drastiquement.

### 4. Le filtre des droits — LA règle absolue

**Avant de chercher quoi que ce soit, on filtre.**

```sql
-- On ne cherche QUE dans les morceaux que l'utilisateur a le droit de voir
WHERE allowed_groups && user_groups
```

Paul (commercial) pose une question → on exclut d'emblée tous les morceaux `grp-rh` → la grille des salaires n'existe pas pour lui → **il ne peut pas la voir même en cherchant activement**.

> ⚠️ **RÈGLE ABSOLUE : le filtre est en SQL, AVANT la recherche.**
> Pas après. Jamais après. Si on filtre après, GPT a déjà vu les données interdites.

### 5. L'endpoint de debug — `/search`

Ce CDC crée un endpoint **uniquement pour toi**, pour tester le retrieval en `curl` sans avoir de front.

Il n'est **pas destiné aux utilisateurs finaux**. C'est ton outil de debug.

---

## 🧩 Où ça s'insère

### Ce qui existe après le CDC 2

```
rag-dyneff/
├── app/
│   ├── config.py          Settings (pydantic-settings)
│   ├── db.py              connexion Postgres
│   ├── main.py            GET /health, GET /health/db
│   └── ingest/            pipeline d'ingestion ✅
├── corpus/                10 documents + manifest.json ✅
└── db/init.sql            8 tables + index HNSW + GIN ✅
```

**186 chunks enfants vectorisés sont en base. 75 parents aussi.**

### Ce que le CDC 3 ajoute

```
app/
└── retrieval/
    ├── __init__.py
    ├── acl.py          le filtre des droits
    ├── vector.py       recherche par sens
    ├── fulltext.py     recherche par mots exacts
    ├── fusion.py       fusionner les deux listes (RRF)
    ├── rerank.py       reclasser avec GPT
    └── pipeline.py     orchestrer tout ça

app/api/
└── search.py           POST /search (endpoint de debug)
```

Et dans `app/main.py` : on branche le nouveau router.

---

## ⚠️ Les pièges de ce CDC

### 🔴 Piège n°1 — Post-filtrage des droits

```sql
-- ✅ BON : on filtre AVANT de chercher
SELECT ... FROM chunks
WHERE allowed_groups && :user_groups        -- ← EN PREMIER
ORDER BY embedding <=> :query_vector
LIMIT 25;

-- ❌ MAUVAIS : on récupère 25 résultats, PUIS on jette les interdits
-- → GPT a déjà vu les données confidentielles
-- → et on se retrouve avec 3 résultats au lieu de 25
```

### 🔴 Piège n°2 — Le reranker qui hallucine des IDs

GPT peut renvoyer des IDs qui n'existent pas dans les 25 candidats.

Par exemple tu lui envoies les IDs `[12, 45, 67, 89, 102, ...]` et il renvoie `[12, 45, 999, 89, 102]`.

**Le 999 n'existe pas.** Si tu ne vérifies pas, ton code plante ou renvoie des résultats fantômes.

→ **Garde-fou obligatoire :** après le reranking, on vérifie que chaque ID renvoyé par GPT est bien dans la liste des 25 candidats. Sinon on l'ignore.

### 🔴 Piège n°3 — Vectoriser la question avec un modèle différent

Les morceaux ont été vectorisés avec `text-embedding-3-large`, dimension 1536.

Si tu vectorises la question avec un autre modèle → les nombres ne sont pas comparables → la recherche renvoie du bruit pur → **et rien ne plante**.

→ **Le modèle et la dimension viennent du `.env`. Toujours.**

### 🔴 Piège n°4 — La recherche full-text qui ignore les accents

Postgres a un dictionnaire français intégré (`french`). Il sait que :
- `congés` = `conge` (même racine)
- `payés` = `paye`

Donc `plainto_tsquery('french', 'congés payés')` trouve les morceaux qui contiennent `congé` ou `payé`, avec ou sans accent, au singulier ou au pluriel.

Si tu oublies le `'french'` → le dictionnaire par défaut est `simple` → les accents ne sont pas gérés → la recherche rate la moitié des résultats.

---

## 🗣️ Ce que je pourrai dire en réunion

> *« La recherche n'est pas un simple Ctrl+F. On cherche simultanément par sens — pour trouver les synonymes — et par mots exacts — pour ne pas rater les références légales. On fusionne les deux, et on demande au modèle de relire les 25 candidats pour ne garder que les 5 vraiment pertinents. »*

Et devant le RSSI :

> *« Le filtre des droits d'accès s'applique en SQL, avant la recherche. Le modèle ne reçoit jamais un passage qu'il n'a pas le droit de voir. Ce n'est pas une vérification après coup — c'est une exclusion structurelle. »*

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
LangChain · LlamaIndex · Qdrant · Pinecone · Weaviate · Chroma · Ragas · Redis · Celery · Alembic · Azure · LibreChat · Open WebUI · sentence-transformers · unstructured.

---

## État actuel du code

```
rag-dyneff/
├── docker-compose.yml
├── db/init.sql                  # 8 tables : documents, chunks (parent/child),
│                                #   users, conversations, messages,
│                                #   feedback, fichiers, audit_log
│                                # Index : HNSW sur embedding, GIN sur tsv, GIN sur allowed_groups
├── app/
│   ├── __init__.py
│   ├── config.py                # Settings (pydantic-settings) — variables ci-dessous
│   ├── db.py                    # connexion psycopg 3
│   ├── main.py                  # FastAPI : GET /health, GET /health/db
│   └── ingest/                  # pipeline ingestion — NE PAS MODIFIER
│       ├── __init__.py
│       ├── __main__.py
│       ├── modeles.py
│       ├── manifest.py
│       ├── load.py
│       ├── chunk.py
│       ├── embed.py
│       └── index.py
├── corpus/                      # 10 documents indexés
└── .env
```

**Variables disponibles dans `app/config.py` (Settings) :**
```python
openai_api_key: str
database_url: str
embedding_model: str      # "text-embedding-3-large"
embedding_dim: int        # 1536
llm_model: str            # le modèle fort — génération
llm_model_fast: str       # le modèle mini — reranking
top_k: int                # 25 — candidats ramenés par la recherche
top_n: int                # 5  — chunks gardés après reranking
temperature: float        # 0
```

**État de la base après CDC 2 :**
- `chunks` : 186 enfants vectorisés (embedding vector(1536)) + 75 parents (embedding NULL)
- `documents` : 10 lignes
- `users` : 3 utilisateurs seedés (marie grp-rh+grp-tous, paul grp-tous, admin tous)
- Colonnes clés de `chunks` :
  - `id`, `type` ('child'|'parent'), `parent_id`, `document_id`
  - `breadcrumb`, `contenu`, `contenu_indexe`
  - `embedding vector(1536)`, `embedding_model`, `embedding_dim`
  - `allowed_groups text[]`
  - `tsv tsvector` (GENERATED ALWAYS — Postgres la calcule seul)
  - `page`, `nb_tokens`, `ordre`

---

## Ce qu'il faut construire

```
app/retrieval/
├── __init__.py
├── acl.py          validation des groupes utilisateur
├── vector.py       recherche par proximité de sens
├── fulltext.py     recherche par mots exacts (français)
├── fusion.py       RRF — fusionner les deux listes
├── rerank.py       reclassement par le petit modèle GPT
└── pipeline.py     orchestration complète

app/api/
├── __init__.py
└── search.py       POST /search — endpoint de debug
```

Et modifier `app/main.py` pour brancher le router `/search`.

---

## Spécifications techniques

### `app/retrieval/acl.py`

```python
def valider_groupes(groupes: list[str]) -> list[str]:
    """Valide et normalise la liste des groupes d'un utilisateur.

    Règles :
    - Chaque groupe doit commencer par 'grp-'
    - Liste vide → lever une ValueError (pas de groupes = pas d'accès)
    - Doublons supprimés
    - Ordre trié (pour la cohérence des logs)
    """
```

---

### `app/retrieval/vector.py`

```python
def recherche_vectorielle(
    conn,                          # connexion psycopg 3
    vecteur_question: list[float],
    groupes_utilisateur: list[str],
    top_k: int,
) -> list[dict]:
    """Cherche les top_k chunks enfants les plus proches du vecteur_question.

    RÈGLE ABSOLUE : le filtre ACL est dans la clause WHERE,
    AVANT le ORDER BY. Jamais après.

    Renvoie une liste de dicts :
    {
      "id": int,
      "document_id": int,
      "breadcrumb": str,
      "contenu": str,
      "contenu_indexe": str,
      "parent_id": int | None,
      "page": int | None,
      "allowed_groups": list[str],
      "score_vecteur": float,   # distance cosinus [0, 2] — plus petit = plus proche
    }
    """
```

**Requête SQL exacte à utiliser :**

```sql
SELECT
    c.id,
    c.document_id,
    c.breadcrumb,
    c.contenu,
    c.contenu_indexe,
    c.parent_id,
    c.page,
    c.allowed_groups,
    (c.embedding <=> %s::vector)  AS score_vecteur
FROM chunks c
WHERE c.type = 'child'
  AND c.embedding IS NOT NULL
  AND c.allowed_groups && %s                    -- ACL : AVANT la recherche
ORDER BY c.embedding <=> %s::vector             -- le plus proche en premier
LIMIT %s;
```

**Comment passer le vecteur :**
```python
vecteur_str = "[" + ",".join(f"{x:.7f}" for x in vecteur_question) + "]"
# Puis utiliser vecteur_str dans les paramètres (%s)
# Passer 4 paramètres : (vecteur_str, groupes_en_array, vecteur_str, top_k)
# Pour l'array Postgres : list(groupes_utilisateur)
```

---

### `app/retrieval/fulltext.py`

```python
def recherche_plein_texte(
    conn,
    question: str,
    groupes_utilisateur: list[str],
    top_k: int,
) -> list[dict]:
    """Cherche par mots exacts, avec le dictionnaire français de Postgres.

    Renvoie le même format que recherche_vectorielle,
    avec "score_texte" à la place de "score_vecteur".
    score_texte = ts_rank (plus grand = plus pertinent).
    """
```

**Requête SQL exacte :**

```sql
SELECT
    c.id,
    c.document_id,
    c.breadcrumb,
    c.contenu,
    c.contenu_indexe,
    c.parent_id,
    c.page,
    c.allowed_groups,
    ts_rank(c.tsv, plainto_tsquery('french', %s))  AS score_texte
FROM chunks c
WHERE c.type = 'child'
  AND c.allowed_groups && %s                        -- ACL : AVANT la recherche
  AND c.tsv @@ plainto_tsquery('french', %s)        -- filtre : seulement les pertinents
ORDER BY score_texte DESC
LIMIT %s;
```

**Note sur `plainto_tsquery` :** cette fonction gère automatiquement les accents,
les majuscules, et la conjugaison française. Elle ne plante pas sur une
question en langage naturel (contrairement à `to_tsquery`).

---

### `app/retrieval/fusion.py`

```python
def rrf(
    liste_vecteur: list[dict],
    liste_texte: list[dict],
    k: int = 60,
) -> list[dict]:
    """Reciprocal Rank Fusion — fusionne deux listes classées en une seule.

    Formule pour chaque chunk :
        score_rrf = 1/(k + rang_dans_liste_vecteur)
                  + 1/(k + rang_dans_liste_texte)

    Si un chunk n'apparaît que dans une seule liste :
        son rang dans l'autre est considéré comme (longueur_de_liste + 1).

    Renvoie la liste fusionnée, triée par score_rrf décroissant.
    Chaque dict conserve tous les champs originaux + "score_rrf".
    """
```

Implémentation attendue (~20 lignes) :

```python
def rrf(liste_vecteur, liste_texte, k=60):
    scores: dict[int, float] = {}
    meta: dict[int, dict] = {}

    for rang, chunk in enumerate(liste_vecteur, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rang)
        meta[chunk["id"]] = chunk

    n = len(liste_vecteur)
    for rang, chunk in enumerate(liste_texte, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rang)
        if chunk["id"] not in meta:
            meta[chunk["id"]] = chunk

    fusionnes = sorted(meta.values(), key=lambda c: scores[c["id"]], reverse=True)
    for chunk in fusionnes:
        chunk["score_rrf"] = scores[chunk["id"]]

    return fusionnes
```

---

### `app/retrieval/rerank.py`

```python
def reranker(
    question: str,
    candidats: list[dict],
    top_n: int,
    modele: str,
) -> list[dict]:
    """Reclasse les candidats avec le petit modèle GPT.

    Envoie la question + les candidats tronqués (300 premiers caractères du
    contenu_indexe pour limiter le coût) et demande les top_n meilleurs IDs.

    GARDE-FOU OBLIGATOIRE : vérifier que chaque ID renvoyé par GPT
    existe bien dans la liste des candidats. Ignorer les autres.

    Renvoie les top_n chunks dans l'ordre donné par GPT.
    """
```

**Prompt exact pour le reranker :**

```python
PROMPT_RERANK = """Tu es un moteur de recherche documentaire.
On te donne une question et une liste de passages numérotés.
Réponds UNIQUEMENT avec un objet JSON : {{"ids": [id1, id2, ...]}}
Donne les {top_n} IDs des passages qui répondent le mieux à la question.
Du plus pertinent au moins pertinent.
Si aucun passage ne répond à la question, renvoie {{"ids": []}}.
PAS d'explication. PAS de markdown. JUSTE le JSON."""
```

**Construction du message utilisateur :**

```python
lignes = [f"Question : {question}\n\nPassages :"]
for c in candidats:
    extrait = c["contenu_indexe"][:300].replace("\n", " ")
    lignes.append(f"[{c['id']}] {extrait}")
message_user = "\n".join(lignes)
```

**Appel OpenAI :**

```python
from openai import OpenAI
import json

client = OpenAI()
reponse = client.chat.completions.create(
    model=modele,
    temperature=0,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": PROMPT_RERANK.format(top_n=top_n)},
        {"role": "user", "content": message_user},
    ],
)
resultat = json.loads(reponse.choices[0].message.content)
ids_gpt = resultat.get("ids", [])
```

**Garde-fou — OBLIGATOIRE :**

```python
ids_valides = {c["id"] for c in candidats}
ids_filtres = [i for i in ids_gpt if i in ids_valides]

if not ids_filtres:
    # GPT n'a rien trouvé de pertinent → on garde le top_n de la fusion RRF
    return candidats[:top_n]

index_par_id = {c["id"]: c for c in candidats}
return [index_par_id[i] for i in ids_filtres[:top_n]]
```

---

### `app/retrieval/pipeline.py`

```python
from dataclasses import dataclass


@dataclass
class ResultatRecherche:
    chunks_enfants: list[dict]    # les top_n chunks trouvés
    chunks_parents: list[dict]    # les sections complètes (pour la génération)
    question_recrite: str         # la question telle qu'elle a été cherchée
    nb_candidats_avant_rerank: int
    duree_ms: int


def rechercher(
    conn,
    question: str,
    groupes_utilisateur: list[str],
    settings,
) -> ResultatRecherche:
    """Pipeline complet de retrieval.

    Ordre des opérations — NE PAS CHANGER :
    1. Valider les groupes (acl.py)
    2. Vectoriser la question (embed.py — même modèle qu'à l'ingestion)
    3. Recherche vectorielle (vector.py) — ACL dans le WHERE
    4. Recherche plein texte (fulltext.py) — ACL dans le WHERE
    5. Fusion RRF (fusion.py)
    6. Reranking GPT (rerank.py) → top_n chunks enfants
    7. Charger les parents correspondants
    8. Renvoyer ResultatRecherche
    """
```

**Étape 7 — charger les parents :**

```python
def charger_parents(conn, chunks_enfants: list[dict]) -> list[dict]:
    """Pour chaque chunk enfant qui a un parent_id,
    charge le chunk parent (contenu complet de la section).

    C'est le parent qu'on donnera à lire au LLM (CDC 4).
    L'enfant a servi à TROUVER. Le parent sert à RÉPONDRE.
    """
    parent_ids = list({
        c["parent_id"]
        for c in chunks_enfants
        if c.get("parent_id") is not None
    })
    if not parent_ids:
        return []

    # IN avec psycopg 3 : passer une liste Python, ça marche
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT * FROM chunks WHERE id = ANY(%s)",
            (parent_ids,)
        )
        return cur.fetchall()
```

---

### `app/api/search.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RequeteRecherche(BaseModel):
    question: str
    user_groups: list[str]    # ex: ["grp-tous"] ou ["grp-rh", "grp-tous"]


class ChunkResultat(BaseModel):
    id: int
    breadcrumb: str
    extrait: str              # les 300 premiers caractères du contenu
    page: int | None
    score_rrf: float | None = None


class ReponseRecherche(BaseModel):
    question: str
    chunks: list[ChunkResultat]
    nb_candidats_avant_rerank: int
    duree_ms: int


@router.post("/search", response_model=ReponseRecherche)
async def chercher(requete: RequeteRecherche):
    """Endpoint de DEBUG — pas destiné au front final.
    Permet de tester le retrieval en curl avant le CDC 4.
    """
```

**Dans `app/main.py`, ajouter :**

```python
from app.api.search import router as search_router
app.include_router(search_router)
```

---

## Contraintes impératives

### ❌ INTERDIT

| Interdit | Pourquoi |
|---|---|
| **Post-filtrage des ACL** | Le LLM ne doit JAMAIS voir un chunk interdit |
| **LangChain, LlamaIndex** | Décision figée |
| **Un modèle d'embedding différent de celui du .env** | Piège n°3 — résultats absurdes sans erreur |
| **`to_tsquery`** à la place de `plainto_tsquery` | `to_tsquery` plante sur une question en langage naturel |
| **Ignorer le garde-fou du reranker** | GPT hallucine des IDs — sans vérification, le code plante |
| **`encoding_for_model`** dans tiktoken | Utiliser `get_encoding("cl100k_base")` |

### ✅ OBLIGATOIRE

1. **Le filtre ACL dans le WHERE SQL, avant le ORDER BY.** Dans les deux requêtes.
2. **Même modèle et même dimension qu'à l'ingestion** — lus depuis `settings`.
3. **Garde-fou reranker** — vérifier chaque ID renvoyé par GPT.
4. **Tout en français** : noms de fonctions, variables, messages, commentaires.
5. **Type hints Python 3.12 partout.**
6. **Aucune valeur en dur** — tout vient de `settings`.

---

## Definition of Done

### Test 1 — Question normale (grp-tous)

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "combien de jours de congés payés", "user_groups": ["grp-tous"]}' \
  | python -m json.tool
```

**Attendu :**
```json
{
  "question": "combien de jours de congés payés",
  "chunks": [
    {
      "id": ...,
      "breadcrumb": "Document : Procédure congés payés\nSection : ...",
      "extrait": "...",
      "page": null,
      "score_rrf": ...
    }
  ],
  "nb_candidats_avant_rerank": 25,
  "duree_ms": ...
}
```

**Critères :**
- exactement **5 chunks** dans la liste (ou moins si le corpus est petit)
- les breadcrumbs mentionnent **« congés »**
- `duree_ms` < 5000 (5 secondes)

---

### Test 2 — 🔒 La grille des salaires est invisible pour Paul

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "grille des salaires", "user_groups": ["grp-tous"]}' \
  | python -m json.tool
```

**Attendu : `"chunks": []`**

Si ce n'est pas une liste vide → **STOP. Ne pas continuer.**
La démo ACL du moment n°2 est morte.

---

### Test 3 — 🔒 Marie (RH) voit la grille

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "grille des salaires", "user_groups": ["grp-rh", "grp-tous"]}' \
  | python -m json.tool
```

**Attendu :** au moins 1 chunk dont le breadcrumb contient **« rémunération »** ou **« salaire »**.

---

### Test 4 — Référence légale exacte (teste le full-text)

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "IDCC 1388", "user_groups": ["grp-tous"]}' \
  | python -m json.tool
```

**Attendu :** au moins 1 résultat (si IDCC 1388 apparaît dans un document).
Ce test valide que la recherche par mots exacts fonctionne bien en complément du vectoriel.

---

### Test 5 — Question hors corpus

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"question": "politique RSE de TotalEnergies", "user_groups": ["grp-tous"]}' \
  | python -m json.tool
```

**Attendu :** `"chunks": []` ou chunks avec des scores très bas.
Pas de résultat inventé.

---

**Les 5 tests doivent passer. Le test 2 est non négociable.**

```
═══════════════════════════════════════════════════════════════
                   FIN DE LA PARTIE B
═══════════════════════════════════════════════════════════════
```
