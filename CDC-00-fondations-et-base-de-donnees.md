# CDC 0 — Fondations et base de données

> **Projet RAG Dyneff — POC service RH**
> Premier cahier des charges. Rien n'existe avant celui-ci.
> Généré le 14 juillet 2026.

---

## SOMMAIRE

**PARTIE A — POUR ISSA** *(comprendre — ne pas coller dans Cursor)*
1. [L'objectif en une phrase](#1--lobjectif-en-une-phrase)
2. [Pourquoi c'est important](#2--pourquoi-cest-important)
3. [Les concepts à comprendre](#3--les-concepts-à-comprendre)
4. [Où ça s'insère](#4--où-ça-sinsère)
5. [Les pièges de ce CDC](#5--les-pièges-de-ce-cdc)
6. [Trois corrections à la stack](#6--trois-corrections-à-la-stack)
7. [Les noms de modèles — vérifiés aujourd'hui](#7--les-noms-de-modèles--vérifiés-aujourdhui)
8. [Ce que je pourrai dire en réunion](#8--ce-que-je-pourrai-dire-en-réunion)

**PARTIE B — POUR CURSOR** *(copier-coller intégralement)*
- [Contexte du projet](#contexte-du-projet)
- [État actuel du code](#état-actuel-du-code)
- [Ce qu'il faut construire](#ce-quil-faut-construire)
- [Fichiers à créer](#fichiers-à-créer)
- [Spécifications techniques](#spécifications-techniques)
- [Contraintes impératives](#contraintes-impératives)
- [Definition of Done](#definition-of-done)

**[ANNEXE — Le mode d'emploi après Cursor](#annexe--le-mode-demploi-après-cursor)**

---
---

```
═══════════════════════════════════════════════════════════════
                     PARTIE A — POUR ISSA
          (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════════
```

## 1 — 🎯 L'objectif en une phrase

Poser le squelette du projet et **créer la base de données complète, une fois pour toutes**, pour ne plus jamais avoir à y revenir.

---

## 2 — 💡 Pourquoi c'est important

Une décision figée du projet : **PAS d'Alembic.**

Alembic, c'est l'outil qui fait évoluer un schéma de base sans perdre les données (« ajoute une colonne `cout_eur` à la table `messages` »). Il est exclu — à raison, c'est de l'overkill pour un POC.

**Mais ça a une conséquence directe, à comprendre maintenant :**

> **Chaque fois que le schéma changera, il faudra détruire la base et ré-ingérer tout le corpus.**

Ré-ingérer = re-payer les embeddings, re-attendre, et surtout **casser le rythme** au pire moment (mardi soir, la veille de la démo).

**Donc la règle du CDC 0 :** on crée **TOUTES** les tables tout de suite. Y compris celles qui ne serviront qu'au CDC 9 (les fichiers `.docx`) et au CDC 12 (le dashboard).

> **Une table vide ne coûte rien. Une migration à 23h la veille de la démo, si.**

---

## 3 — 📚 Les concepts à comprendre

### 3.1 — `init.sql` et le volume Docker

L'image `pgvector/pgvector:pg16` a une convention : tout fichier `.sql` posé dans le dossier `/docker-entrypoint-initdb.d/` est **exécuté automatiquement au tout premier démarrage**.

**Au tout premier démarrage. Une seule fois. Jamais plus.**

```
docker compose up    (1ère fois)  →  volume vide     →  init.sql S'EXÉCUTE  ✅
docker compose down
docker compose up    (2ème fois)  →  volume existant →  init.sql IGNORÉ     ❌
```

Tu vas modifier `init.sql`, relancer, et te demander pendant 40 minutes pourquoi ta nouvelle colonne n'apparaît pas.

**La commande à graver :**

```bash
docker compose down -v      # le -v DÉTRUIT le volume → init.sql se rejouera
```

Le `-v`, c'est tout. Sans lui : tu gardes les données. Avec lui : tu repars propre.

---

### 3.2 — L'index HNSW : le raccourci du sens

**Le problème.** Tu as 2 000 chunks, donc 2 000 vecteurs. Tu poses une question → 1 vecteur. Pour trouver les 5 plus proches, la méthode bête compare ton vecteur avec **les 2 000**. À 2 000, c'est instantané. À 2 millions, c'est mort.

**L'image.** Tu cherches le café le plus proche dans Paris.

| | Comment | Résultat |
|---|---|---|
| **Sans index** | Tu mesures la distance jusqu'à **chacun** des 4 000 cafés | Exact, mais long |
| **Avec HNSW** | Tu as un *plan de métro du sens*. Tu sautes de station en station en te rapprochant à chaque fois. Tu arrives en 6 sauts. | **Approximatif** (~99 % identique), **~100× plus rapide** |

**HNSW** = *Hierarchical Navigable Small World*. C'est ce plan de métro.

> ⚠️ **Contrainte dure : pgvector ne sait indexer que jusqu'à 2 000 dimensions.**
> C'est le **Piège n°1** du projet. `text-embedding-3-large` sort du **3072** par défaut → le `CREATE INDEX` explose.
> D'où `dimensions=1536` partout. Voir §5.1.

---

### 3.3 — L'index GIN : l'index d'un livre

À la fin d'un livre technique, il y a un index : *« congés → p. 8, 12, 47 »*. Tu ne relis pas les 500 pages : tu vas directement à l'entrée.

**GIN** (*Generalized Inverted Index*) fait exactement ça, et il sert **deux fois** chez nous :

| Sur quelle colonne | Pour répondre à quelle question |
|---|---|
| `tsv` (le texte français préparé) | *« Quels chunks contiennent le mot **congé** ? »* |
| `allowed_groups` (le tableau des droits) | *« Quels chunks sont visibles par **grp-rh** ? »* |

---

### 3.4 — La colonne `tsv` **générée** : celle qu'on ne touchera jamais

Un `tsvector`, c'est la forme « préparée pour la recherche » d'un texte. Postgres découpe en mots, ramène chaque mot à sa racine française (*congés → cong*), et jette les mots vides (*le, de, un*).

**Normalement**, il faut penser à la recalculer à chaque insertion. Un oubli = **un chunk invisible en recherche plein texte**, sans aucune erreur.

**Chez nous, non.** On la déclare en colonne **générée** :

```sql
tsv tsvector GENERATED ALWAYS AS (
    to_tsvector('french', coalesce(breadcrumb,'') || ' ' || coalesce(contenu,''))
) STORED
```

Postgres la calcule **tout seul**, à chaque `INSERT` et à chaque `UPDATE`.

> **Une classe entière de bug supprimée dès le CDC 0.**

**Et remarque bien : on indexe le breadcrumb ET le contenu.** C'est délibéré. « Article 12 » et « IDCC 1388 » sont dans le **breadcrumb**, pas dans le texte. C'est ce qui fera marcher la recherche par référence légale au CDC 3.

---

### 3.5 — L'opérateur `&&` : le cœur des ACL

Sur deux tableaux Postgres, `&&` répond à une seule question :

> **« Ces deux listes ont-elles au moins un élément en commun ? »**

```sql
ARRAY['grp-tous','grp-rh']  &&  ARRAY['grp-rh']    -- TRUE   ✅
ARRAY['grp-tous']           &&  ARRAY['grp-rh']    -- FALSE  ❌
```

C'est **toute la sécurité du projet**, en un opérateur :

```sql
WHERE allowed_groups && :groupes_de_l_utilisateur
```

Le chunk de la grille des salaires porte `{grp-rh}`. Paul (commercial) a `{grp-tous}`. Intersection vide → **le chunk n'existe pas pour lui.**

> Le LLM ne le verra jamais.
> **Pas parce qu'on lui a demandé de ne pas regarder.**
> **Parce que la requête SQL ne l'a pas ramené.**

C'est exactement la phrase à sortir devant le RSSI.

---

### 3.6 — Pydantic Settings : la config typée

Au lieu de `os.getenv("TOP_K")` — qui te rend la **chaîne** `"25"` et te fait planter trois fichiers plus loin — tu déclares une classe :

```python
class Settings(BaseSettings):
    top_k: int = 25
```

Pydantic :
- lit le `.env`
- **convertit** `"25"` → `25`
- **refuse de démarrer** si `OPENAI_API_KEY` manque

Erreur immédiate et claire, au lieu d'un bug silencieux à 2h du matin.

---

## 4 — 🧩 Où ça s'insère

**Ce qui existe avant ce CDC : rien.** Un dossier vide.

**Ce que ce CDC ajoute :**

| Brique | Contenu |
|---|---|
| 🗂️ **L'arborescence** | Tous les dossiers, y compris ceux des CDC futurs (vides mais présents) |
| 🐳 **`docker-compose.yml`** | 2 services : `db` (Postgres + pgvector) et `api` (FastAPI) |
| 🗄️ **`db/init.sql`** | **8 tables + tous les index + 3 utilisateurs de test** |
| ⚙️ **`app/config.py`** | La config Pydantic, lue depuis `.env` |
| 🔌 **`app/db.py`** | La connexion SQLAlchemy |
| 🚀 **`app/main.py`** | FastAPI + `GET /health` + `GET /health/db` |
| 🔒 **`.gitignore`** | **Avant le premier commit. Règle de sécurité n°4.** |

**Le front (`web/`) n'existe pas encore.** C'est le **Piège n°7** : le cerveau d'abord, le front ensuite.

**Les 8 tables créées :**

| Table | Utilisée à partir de | Rôle |
|---|---|---|
| `documents` | CDC 2 | Les fichiers du corpus |
| `chunks` | CDC 2 | **Le cœur** — texte + vecteur + ACL + full-text |
| `users` | CDC 6 | Les 3 utilisateurs de démo (créés dès maintenant) |
| `conversations` | CDC 7 | L'historique |
| `messages` | CDC 4 | **Alimente le dashboard du CDC 12** |
| `feedback` | CDC 7 | 👍 / 👎 |
| `fichiers` | CDC 9 | Les `.docx` générés |
| `audit_log` | CDC 6 | **La table qu'on montre au RSSI** |

---

## 5 — ⚠️ Les pièges de ce CDC

### 5.1 — 🔴 Piège n°1 du projet : les 1536 dimensions

Trois endroits doivent dire **exactement la même chose** :

| Où | Quoi |
|---|---|
| `db/init.sql` | `embedding vector(1536)` |
| `.env` | `EMBEDDING_DIM=1536` |
| CDC 2 (code Python) | `dimensions=1536` dans l'appel OpenAI |

**Ce qui se passe si tu te trompes :** le stockage passe sans erreur. Le `CREATE INDEX` explose. Tu cherches 3 heures.

**Deux garde-fous ajoutés dans ce CDC :**

1. **L'endpoint `/health/db`** compare la dimension **réellement en base** avec celle de ta config et renvoie `"coherence_dim": true`. Si c'est `false`, tu le sais en 2 secondes.
2. **Une contrainte SQL** (`chk_embedding_coherent`) refuse d'insérer un vecteur sans son nom de modèle et avec une dimension ≠ 1536. **Postgres lui-même bloque le Piège n°2** (le mélange de modèles d'embedding, celui qui renvoie du bruit pur sans jamais planter).

---

### 5.2 — 🔴 Le driver Postgres : `postgresql://` ne suffit PAS

Les instructions du projet donnent :

```bash
DATABASE_URL=postgresql://rag:rag@localhost:5432/ragdb   # ❌
```

Avec cette URL, SQLAlchemy cherche **psycopg2**. Or on installe **psycopg 3**. Résultat :

```
ModuleNotFoundError: No module named 'psycopg2'
```

**Correct :**

```bash
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/ragdb   # ✅
```

Le `+psycopg` dit explicitement : *« utilise psycopg 3 »*.

---

### 5.3 — 🔴 `localhost` vs `db` : l'adresse change selon d'où tu appelles

```
Depuis TA machine (DBeaver, uvicorn local)  →  localhost:5432
Depuis le conteneur api                     →  db:5432   ← le nom du service Docker
```

**Pourquoi ?** Dans un conteneur, `localhost` désigne **le conteneur lui-même**, pas ta machine. Il n'y a pas de Postgres dedans → `connection refused`.

**Comment c'est réglé ici :**
- Le `.env` contient `localhost` → pour DBeaver et pour lancer `uvicorn` à la main.
- `docker-compose.yml` **écrase** cette variable avec `db:5432` pour le conteneur `api`.
- Docker Compose donne priorité au bloc `environment:` sur `env_file:`.

**Les deux mondes marchent en même temps.** Tu n'as rien à changer.

---

### 5.4 — 🔴 `.env` dans `.gitignore` — **avant le premier commit**

**Règle de sécurité n°4.** Une clé OpenAI poussée sur un dépôt GitHub est scannée et cramée en minutes.

Dans la Partie B, le `.gitignore` est le **tout premier fichier créé**. Avant tout le reste.

**Vérification obligatoire avant le premier `git commit` :**

```bash
git status | grep .env      # ne doit RIEN renvoyer
```

---

### 5.5 — 🔴 Rappel : Règle de sécurité n°1

**Corpus public et synthétique UNIQUEMENT.** Aucun document RH réel de Dyneff sur cette machine, sur le VPS Hostinger, ou dans le compte OpenAI personnel.

Le `README.md` généré par ce CDC le rappelle en dur, en tête de fichier. C'est volontaire : le jour où quelqu'un d'autre ouvre le dépôt, c'est la première chose qu'il lit.

---

## 6 — 🔧 Trois corrections à la stack

Mon rôle est de te dire quand tu te trompes. **Trois paquets de ta liste sont des pièges connus.**

| Ta stack | Le problème | Ce qu'on fait |
|---|---|---|
| **`passlib[bcrypt]`** | **Combo cassé.** passlib 1.7.4 plante avec bcrypt ≥ 4.1 (`AttributeError: module 'bcrypt' has no attribute '__about__'`). passlib n'est plus maintenu. | On installe **`bcrypt`** tout court. Hasher = 1 ligne, vérifier = 1 ligne. **Une dépendance en moins.** |
| **`python-jose`** | Peu maintenu, historique de CVE. | On installe **`pyjwt`**. C'est le standard, et c'est ce que la doc officielle de FastAPI utilise. |
| **`postgresql://`** | Pointe sur psycopg2, qu'on n'installe pas. | **`postgresql+psycopg://`** |

**Aucune de ces trois n'est dans les « décisions figées » du projet** (section 7 des instructions). Ce sont des choix de librairie, pas d'architecture. Je les corrige.

Si tu veux garder passlib malgré tout, il faut épingler `bcrypt<4.1` — et tu traîneras une dette pour rien.

---

## 7 — 🤖 Les noms de modèles — vérifiés aujourd'hui

Les instructions du projet disent : *« les noms changent souvent, vérifier sur platform.openai.com »*.

**Je viens de le faire. La famille GPT-4.1 / GPT-4o est dépassée.** La génération actuelle est **GPT-5.6**, déclinée en trois tailles :

| Modèle | Prix (entrée / sortie, par 1M tokens) | Chez nous |
|---|---|---|
| `gpt-5.6-sol` | 5 $ / 30 $ | ❌ Overkill pour un RAG |
| `gpt-5.6-terra` | 2,50 $ / 15 $ | ✅ **`LLM_MODEL`** — la génération sourcée |
| `gpt-5.6-luna` | 1 $ / 6 $ | ✅ **`LLM_MODEL_FAST`** — rerank + query rewriting |
| `text-embedding-3-large` | négligeable | ✅ **`EMBEDDING_MODEL`** (avec `dimensions=1536`) |

### Deux points d'attention pour les CDC suivants

**1. Ces modèles ont un paramètre `reasoning`** (`none` / `low` / `medium` / `high` / …).

Pour un RAG, on veut **`none`** ou **`low`**. On ne veut pas qu'il *réfléchisse* — on veut qu'il **recopie le document en citant sa source**. Réfléchir = latence + coût, pour zéro gain.

**2. `temperature` n'est pas toujours accepté sur les modèles à raisonnement.**

Si l'API le refuse au CDC 4, on retire `temperature` et on met `reasoning: "none"`. Même effet : zéro créativité.

### Vérifie ce qui est réellement disponible sur TON compte

Les accès varient d'un compte à l'autre.

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  | grep -o '"id": *"[^"]*"' | sort
```

Si `gpt-5.6-terra` n'apparaît pas, prends ce qui s'en rapproche et mets-le dans le `.env`.

> **Rien n'est en dur dans le code. Tout passe par `settings`.**

---

## 8 — 🗣️ Ce que je pourrai dire en réunion

> *« Le filtrage par droits n'est pas une consigne donnée au modèle — c'est une clause SQL. Le passage interdit n'est pas ramené par la requête. Le LLM ne peut pas voir ce qui ne lui a jamais été envoyé. »*

Et si le RSSI creuse :

> *« Chaque requête est tracée dans une table d'audit qui conserve l'utilisateur, ses groupes **au moment de la requête**, la question posée, et la liste exacte des passages retournés. Je peux rejouer n'importe quel accès a posteriori. »*

C'est cette table `audit_log` — **créée aujourd'hui**, remplie au CDC 6 — qui fait la différence entre un prototype et une brique d'entreprise.

Et si on te demande *« et si vous changez de fournisseur d'IA ? »* :

> *« Le nom du modèle est une variable d'environnement. Le nom du modèle d'embedding est stocké dans chaque ligne de la base, avec sa dimension. Changer de fournisseur, c'est éditer un fichier et relancer l'indexation. L'architecture ne bouge pas. »*

---
---

```
═══════════════════════════════════════════════════════════════
                    PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT — à partir d'ici)
═══════════════════════════════════════════════════════════════
```

# MISSION — CDC 0 : Fondations et base de données

## Contexte du projet

On construit un **RAG** (Retrieval-Augmented Generation) pour le service RH d'une entreprise française d'environ 1 500 personnes.

**Stack :** FastAPI (Python 3.12) + Postgres 16 avec l'extension pgvector + (plus tard) Next.js.
**Une seule clé API :** OpenAI (génération, embeddings et rerank).
**Tout tourne en Docker.**

Ce CDC est le **socle**. Il ne fait rien d'intelligent : il crée la structure du dépôt, lance la base de données avec son schéma complet, et expose un endpoint de santé. Tout le reste (ingestion, retrieval, chat, front) viendra ensuite et s'appuiera dessus.

**Le code, les commentaires et les noms de colonnes sont en français.** Le développeur doit pouvoir expliquer chaque ligne en réunion devant un DSI.

---

## État actuel du code

**Le dossier est vide. Rien n'existe. Tu pars de zéro.**

---

## Ce qu'il faut construire

1. L'arborescence complète du dépôt (y compris les dossiers vides des étapes futures)
2. `.gitignore` — **EN TOUT PREMIER, avant tout autre fichier**
3. `pyproject.toml` avec les dépendances (gérées par `uv`)
4. `.env.example` (committé) — l'utilisateur en fera une copie en `.env` (jamais committé)
5. `docker-compose.yml` : 2 services — `db` et `api`
6. `Dockerfile` pour l'API
7. `db/init.sql` : **le schéma complet — 8 tables, tous les index, 3 utilisateurs de seed**
8. `app/config.py` : la configuration Pydantic Settings
9. `app/db.py` : le moteur SQLAlchemy
10. `app/main.py` : FastAPI + `GET /health` + `GET /health/db`
11. `README.md`

---

## Fichiers à créer

```
rag-dyneff/
├── .gitignore                      ← LE PREMIER FICHIER CRÉÉ
├── .env.example                    ← committé
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
│
├── db/
│   └── init.sql                    ← le schéma complet
│
├── corpus/
│   └── .gitkeep                    ← rempli au CDC 1
│
├── eval/
│   └── __init__.py                 ← rempli au CDC 5
│
├── web/
│   └── .gitkeep                    ← Next.js, CDC 8 — NE RIEN Y METTRE MAINTENANT
│
└── app/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── db.py
    ├── ingest/
    │   └── __init__.py             ← CDC 2
    ├── retrieval/
    │   └── __init__.py             ← CDC 3
    ├── llm/
    │   └── __init__.py             ← CDC 4
    ├── api/
    │   └── __init__.py             ← CDC 4
    ├── security/
    │   └── __init__.py             ← CDC 6
    ├── chat/
    │   └── __init__.py             ← CDC 7
    ├── files/
    │   └── __init__.py             ← CDC 9
    └── tools/
        └── __init__.py             ← CDC 10
```

Les sous-packages de `app/` ne contiennent qu'un `__init__.py` **vide** pour l'instant.

---

## Spécifications techniques

### 1. `.gitignore` — À CRÉER EN TOUT PREMIER

```gitignore
# ═══ SECRETS — NON NÉGOCIABLE ═══
.env
.env.local
.env.*.local
!.env.example

# ═══ Python ═══
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/

# ═══ Node / Next.js ═══
node_modules/
.next/
out/

# ═══ Fichiers générés par l'application ═══
generated/
*.docx

# ═══ OS / IDE ═══
.DS_Store
.idea/
.vscode/
```

---

### 2. `pyproject.toml`

```toml
[project]
name = "rag-dyneff"
version = "0.1.0"
description = "POC RAG RH — Dyneff"
requires-python = ">=3.12,<3.13"

dependencies = [
    # API
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "python-dotenv>=1.0",

    # Base de données
    "psycopg[binary]>=3.2",
    "sqlalchemy>=2.0",
    "pgvector>=0.3",

    # IA — une seule clé
    "openai>=1.60",
    "tiktoken>=0.8",

    # Ingestion (CDC 2)
    "pymupdf4llm>=0.0.17",

    # Génération de fichiers (CDC 9)
    "python-docx>=1.1",

    # Recherche web (CDC 10)
    "httpx>=0.27",

    # Auth (CDC 6)
    "bcrypt>=4.2",
    "pyjwt>=2.9",
]

# On n'installe QUE les dépendances, jamais le projet lui-même comme package.
[tool.uv]
package = false
```

> **⚠️ CORRECTIONS DÉLIBÉRÉES — NE PAS REVENIR DESSUS :**
> - On utilise **`bcrypt`** directement, **PAS `passlib`**.
>   *(passlib 1.7.4 est cassé avec bcrypt ≥ 4.1 : `AttributeError: module 'bcrypt' has no attribute '__about__'`. Et passlib n'est plus maintenu.)*
> - On utilise **`pyjwt`**, **PAS `python-jose`**.
>   *(python-jose est peu maintenu et a un historique de CVE. PyJWT est le standard, et c'est ce que la doc FastAPI utilise.)*

---

### 3. `.env.example`

L'utilisateur en fera une copie nommée `.env` et remplira les deux secrets.

```bash
# ═══════════════════════════════════════════════════════════
#  IA — UNE SEULE CLÉ
# ═══════════════════════════════════════════════════════════
OPENAI_API_KEY=sk-remplace-moi

# Noms de modèles — vérifiés en juillet 2026.
# Vérifier ce qui est réellement disponible sur le compte :
#   curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
LLM_MODEL=gpt-5.6-terra
LLM_MODEL_FAST=gpt-5.6-luna
EMBEDDING_MODEL=text-embedding-3-large

# ⚠️ DOIT être identique à vector(1536) dans db/init.sql.
#    pgvector ne sait indexer que jusqu'à 2000 dimensions.
#    text-embedding-3-large sort du 3072 par défaut → on force 1536.
EMBEDDING_DIM=1536

# ═══════════════════════════════════════════════════════════
#  BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════
# ⚠️ Le préfixe "+psycopg" est OBLIGATOIRE (psycopg 3, pas psycopg2).
#    "localhost" = depuis la machine hôte (DBeaver, uvicorn en local).
#    Dans le conteneur api, docker-compose écrase cette valeur par db:5432.
DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/ragdb

# ═══════════════════════════════════════════════════════════
#  RETRIEVAL — ne pas toucher avant l'éval (CDC 5)
# ═══════════════════════════════════════════════════════════
CHUNK_SIZE=800
CHUNK_OVERLAP=100
TOP_K=25          # candidats ramenés par la recherche hybride
TOP_N=5           # chunks gardés après reranking
TEMPERATURE=0     # aucune créativité — on veut le document

# ═══════════════════════════════════════════════════════════
#  AUTH (CDC 6)
# ═══════════════════════════════════════════════════════════
# Générer :  python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=remplace-moi-par-une-chaine-aleatoire
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# ═══════════════════════════════════════════════════════════
#  DIVERS
# ═══════════════════════════════════════════════════════════
APP_ENV=dev
```

---

### 4. `docker-compose.yml`

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: rag-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: rag
      POSTGRES_PASSWORD: rag
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      # ⚠️ Ce fichier n'est exécuté QU'AU PREMIER démarrage (volume vide).
      #    Après toute modification du schéma : docker compose down -v
      - ./db/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag -d ragdb"]
      interval: 5s
      timeout: 3s
      retries: 12

  api:
    build: .
    container_name: rag-api
    restart: unless-stopped
    env_file: .env
    environment:
      # ⚠️ Écrase le DATABASE_URL du .env.
      #    Dans le conteneur, la base s'appelle "db" (le nom du service),
      #    pas "localhost" (qui désignerait le conteneur api lui-même).
      #    Docker Compose donne priorité à "environment" sur "env_file".
      DATABASE_URL: postgresql+psycopg://rag:rag@db:5432/ragdb
    ports:
      - "8000:8000"
    volumes:
      - ./app:/srv/app
      - ./corpus:/srv/corpus
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  pgdata:
```

---

### 5. `Dockerfile`

```dockerfile
FROM python:3.12-slim

# uv : gestionnaire de paquets Python (~10x plus rapide que pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Couche de cache : les dépendances changent rarement, le code souvent.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY app ./app

ENV PATH="/srv/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 6. `db/init.sql` — LE SCHÉMA COMPLET

```sql
-- ═══════════════════════════════════════════════════════════════════
--  RAG DYNEFF — SCHÉMA COMPLET DE LA BASE
--
--  ⚠️ Ce fichier n'est exécuté QU'UNE SEULE FOIS : à la création du
--     volume Postgres. Pour le rejouer :   docker compose down -v
--
--  ⚠️ Il n'y a PAS d'outil de migration (pas d'Alembic — décision figée).
--     C'est pourquoi TOUTES les tables sont créées ici, y compris celles
--     qui ne seront utilisées que plus tard (fichiers, feedback, audit).
--     Une table vide ne coûte rien. Une migration la veille de la démo, si.
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════════════════════════
--  LES GROUPES — convention (pas de table, c'est du text[])
--
--    grp-tous    : tout le monde
--    grp-rh      : le service RH → accède aux documents confidentiels RH
--    grp-admin   : administration technique
-- ═══════════════════════════════════════════════════════════════════


-- ───────────────────────────────────────────────────────────────────
--  1. DOCUMENTS — un fichier du corpus
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE documents (
    id          SERIAL      PRIMARY KEY,
    titre       TEXT        NOT NULL,
    chemin      TEXT        NOT NULL UNIQUE,
    type        TEXT        NOT NULL CHECK (type IN ('pdf', 'md')),
    source      TEXT        NOT NULL CHECK (source IN ('public', 'synthetique', 'fictif')),
    service     TEXT        NOT NULL DEFAULT 'rh',
    sensibilite TEXT        NOT NULL DEFAULT 'interne'
                            CHECK (sensibilite IN ('public', 'interne', 'confidentiel')),
    nb_pages    INTEGER,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  documents        IS 'Un fichier du corpus RH.';
COMMENT ON COLUMN documents.source IS 'public = Légifrance | synthetique = rédigé par nous | fictif = inventé pour la démo ACL. AUCUN document réel de l''entreprise.';


-- ───────────────────────────────────────────────────────────────────
--  2. CHUNKS — le cœur du RAG
--
--     Un chunk "enfant" est cherchable : il porte un embedding.
--     Un chunk "parent" sert de contexte élargi envoyé au LLM
--     (technique small-to-big : on cherche petit, on donne grand).
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE chunks (
    id              SERIAL      PRIMARY KEY,
    document_id     INTEGER     NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    parent_id       INTEGER     REFERENCES chunks(id) ON DELETE CASCADE,

    contenu         TEXT        NOT NULL,
    breadcrumb      TEXT        NOT NULL DEFAULT '',
    texte_embedde   TEXT        NOT NULL,

    page            INTEGER,
    ordre           INTEGER     NOT NULL DEFAULT 0,
    nb_tokens       INTEGER,
    est_tableau     BOOLEAN     NOT NULL DEFAULT FALSE,

    embedding       vector(1536),
    embedding_model TEXT,
    embedding_dim   INTEGER,

    allowed_groups  TEXT[]      NOT NULL DEFAULT '{}',

    -- Colonne GÉNÉRÉE : Postgres la recalcule seul à chaque insert/update.
    -- On indexe breadcrumb + contenu : c'est ce qui permet de retrouver
    -- "Article 12" ou "IDCC 1388", qui figurent dans le breadcrumb et non
    -- dans le corps du texte.
    tsv             tsvector GENERATED ALWAYS AS (
                        to_tsvector('french',
                            coalesce(breadcrumb, '') || ' ' || coalesce(contenu, ''))
                    ) STORED,

    cree_le         TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- GARDE-FOU contre le mélange de modèles d'embedding (le bug le plus
    -- vicieux du RAG : il ne plante pas, il renvoie du bruit).
    -- Impossible d'insérer un vecteur sans dire avec quel modèle il a été
    -- produit, ni avec une dimension autre que 1536.
    CONSTRAINT chk_embedding_coherent CHECK (
        (embedding IS NULL AND embedding_model IS NULL)
        OR
        (embedding IS NOT NULL AND embedding_model IS NOT NULL AND embedding_dim = 1536)
    )
);

COMMENT ON COLUMN chunks.breadcrumb     IS 'Fil d''Ariane : "Document : ... / Section : Titre III > Article 12". Préfixé au contenu AVANT vectorisation.';
COMMENT ON COLUMN chunks.texte_embedde  IS 'Le texte EXACT envoyé au modèle d''embedding (breadcrumb + contenu). Indispensable pour débugger le retrieval.';
COMMENT ON COLUMN chunks.parent_id      IS 'Small-to-big : on CHERCHE sur l''enfant (précis), on DONNE le parent au LLM (contexte).';
COMMENT ON COLUMN chunks.allowed_groups IS 'ACL. Filtré en SQL AVANT la recherche, avec l''opérateur &&. JAMAIS de post-filtrage.';


-- ───────────────────────────────────────────────────────────────────
--  3. USERS
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id           SERIAL      PRIMARY KEY,
    email        TEXT        NOT NULL UNIQUE,
    nom          TEXT        NOT NULL,
    mot_de_passe TEXT        NOT NULL,   -- hash bcrypt. JAMAIS de clair.
    groupes      TEXT[]      NOT NULL DEFAULT '{grp-tous}',
    role         TEXT        NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    cree_le      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  4. CONVERSATIONS (CDC 7)
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE conversations (
    id      SERIAL      PRIMARY KEY,
    user_id INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titre   TEXT        NOT NULL DEFAULT 'Nouvelle conversation',
    resume  TEXT,                      -- mémoire glissante (CDC 7)
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    maj_le  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  5. MESSAGES
--     C'est CETTE table qui alimentera le dashboard du CDC 12.
--     Tout ce qui s'y trouve sera un SELECT COUNT(*).
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE messages (
    id                SERIAL        PRIMARY KEY,
    conversation_id   INTEGER       NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    role              TEXT          NOT NULL CHECK (role IN ('user', 'assistant')),
    contenu           TEXT          NOT NULL,
    question_reecrite TEXT,                            -- query rewriting (CDC 7)

    chunk_ids         INTEGER[]     NOT NULL DEFAULT '{}',
    sources           JSONB,                           -- citations structurées
    a_repondu         BOOLEAN,                         -- FALSE = "je ne sais pas"
    web_active        BOOLEAN       NOT NULL DEFAULT FALSE,

    modele            TEXT,
    tokens_in         INTEGER,
    tokens_out        INTEGER,
    latence_ms        INTEGER,
    cout_eur          NUMERIC(12, 6),

    cree_le           TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMENT ON COLUMN messages.a_repondu IS 'FALSE = le RAG a répondu "je ne sais pas". C''est ce champ qui produit les "trous du corpus" du dashboard (CDC 12).';


-- ───────────────────────────────────────────────────────────────────
--  6. FEEDBACK (CDC 7) — 👍 / 👎
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE feedback (
    id          SERIAL      PRIMARY KEY,
    message_id  INTEGER     NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    valeur      SMALLINT    NOT NULL CHECK (valeur IN (-1, 1)),   -- -1 = 👎, 1 = 👍
    commentaire TEXT,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  7. FICHIERS (CDC 9) — les .docx générés
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE fichiers (
    id         SERIAL      PRIMARY KEY,
    message_id INTEGER     REFERENCES messages(id) ON DELETE CASCADE,
    nom        TEXT        NOT NULL,
    chemin     TEXT        NOT NULL,
    type_mime  TEXT        NOT NULL DEFAULT
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    taille     INTEGER,
    cree_le    TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  8. AUDIT_LOG (CDC 6) — la table qu'on montre au RSSI
--
--     user_email et user_groups sont DÉNORMALISÉS À DESSEIN :
--     un journal d'audit doit rester vrai même si l'utilisateur change
--     de groupe ou est supprimé. On fige l'état AU MOMENT de la requête.
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    user_email  TEXT,
    user_groups TEXT[],
    question    TEXT        NOT NULL,
    chunk_ids   INTEGER[]   NOT NULL DEFAULT '{}',
    nb_chunks   INTEGER     NOT NULL DEFAULT 0,
    a_repondu   BOOLEAN,
    latence_ms  INTEGER,
    cout_eur    NUMERIC(12, 6),
    ip          INET,
    horodatage  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════
--  LES INDEX
-- ═══════════════════════════════════════════════════════════════════

-- Recherche VECTORIELLE (le sens). Distance cosinus, opérateur <=>.
-- ⚠️ HNSW ne supporte QUE jusqu'à 2000 dimensions → d'où vector(1536).
--    C'est le piège n°1 du projet.
CREATE INDEX idx_chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Recherche PLEIN TEXTE française (les mots exacts : "Article 12", "IDCC 1388").
CREATE INDEX idx_chunks_tsv
    ON chunks USING gin (tsv);

-- Filtre ACL : accélère l'opérateur && sur text[].
CREATE INDEX idx_chunks_allowed_groups
    ON chunks USING gin (allowed_groups);

-- Index de service
CREATE INDEX idx_chunks_document_id       ON chunks (document_id);
CREATE INDEX idx_chunks_parent_id         ON chunks (parent_id);
CREATE INDEX idx_conversations_user_id    ON conversations (user_id);
CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX idx_messages_cree_le         ON messages (cree_le DESC);
CREATE INDEX idx_messages_a_repondu       ON messages (a_repondu);
CREATE INDEX idx_feedback_message_id      ON feedback (message_id);
CREATE INDEX idx_fichiers_message_id      ON fichiers (message_id);
CREATE INDEX idx_audit_horodatage         ON audit_log (horodatage DESC);
CREATE INDEX idx_audit_user_id            ON audit_log (user_id);


-- ═══════════════════════════════════════════════════════════════════
--  SEED — 3 utilisateurs de démonstration
--
--  Mot de passe pour les trois : demo1234
--  Hash bcrypt (cost 12) déjà calculés — NE PAS les régénérer.
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO users (email, nom, mot_de_passe, groupes, role) VALUES
    ('marie@dyneff.fr', 'Marie Lefèvre',
     '$2b$12$XdOu722hLDAz0pKh9CAavuwVASM5ZfNJbbufoXwZq01cjWod7CqTW',
     ARRAY['grp-tous', 'grp-rh'], 'user'),

    ('paul@dyneff.fr', 'Paul Marchand',
     '$2b$12$dHvJAyaZUMJauviv.G0wTur27Slsf0xdaxBJw7iAmLumXu2cnphZi',
     ARRAY['grp-tous'], 'user'),

    ('admin@dyneff.fr', 'Administrateur',
     '$2b$12$2/A8UFzonF91IPaRkiEbvuVkZ8cKIrR4CUDIgdEfPmE8zpdTajB4y',
     ARRAY['grp-tous', 'grp-rh', 'grp-admin'], 'admin');

-- Marie  = RH         → verra la grille des salaires
-- Paul   = commercial → ne la verra JAMAIS
-- C'est le moment n°2 de la démo.
```

---

### 7. `app/config.py`

```python
"""Configuration de l'application, lue depuis le fichier .env.

Pydantic Settings valide et TYPE chaque variable : TOP_K devient un int,
pas la chaîne "25". Et si OPENAI_API_KEY manque, l'application refuse de
démarrer avec un message clair, au lieu de planter vingt minutes plus tard.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── IA ──────────────────────────────────────────────────
    openai_api_key: str

    # Pas de valeur par défaut : les noms de modèles changent trop vite.
    # Ils DOIVENT venir du .env. Jamais en dur dans le code.
    llm_model: str
    llm_model_fast: str
    embedding_model: str

    # Doit matcher vector(1536) dans db/init.sql.
    embedding_dim: int = 1536

    # ─── Base de données ─────────────────────────────────────
    database_url: str

    # ─── Retrieval ───────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 25       # candidats ramenés par la recherche hybride
    top_n: int = 5        # chunks gardés après reranking
    temperature: float = 0.0

    # ─── Auth (CDC 6) ────────────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # ─── Divers ──────────────────────────────────────────────
    app_env: str = "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

### 8. `app/db.py`

```python
"""Connexion à Postgres via SQLAlchemy 2.

⚠️ DATABASE_URL doit commencer par postgresql+psycopg:// (psycopg 3).
   Sans le "+psycopg", SQLAlchemy cherche psycopg2, qui n'est pas installé,
   et lève un ModuleNotFoundError incompréhensible.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # teste la connexion avant de s'en servir
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session, la ferme quoi qu'il arrive."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_est_joignable() -> bool:
    """Renvoie True si la base répond."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
```

---

### 9. `app/main.py`

```python
"""API RAG Dyneff — point d'entrée FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import db_est_joignable, engine

app = FastAPI(
    title="RAG Dyneff — API",
    description="POC RAG pour le service RH. Deux portes, un seul cerveau.",
    version="0.1.0",
)

# Le front Next.js arrivera sur le port 3000 (CDC 8).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Definition of Done du CDC 0.

    Doit renvoyer EXACTEMENT : {"status": "ok", "db": "connected"}
    """
    return {
        "status": "ok",
        "db": "connected" if db_est_joignable() else "disconnected",
    }


@app.get("/health/db")
def health_db() -> dict:
    """Endpoint de debug : prouve que pgvector et le schéma sont en place.

    Le champ "coherence_dim" est un garde-fou contre le piège n°1 du projet.
    Si la dimension déclarée en base et celle de la config divergent, le
    retrieval renverra du bruit pur SANS jamais planter. On veut le savoir
    maintenant, pas dans trois heures.
    """
    with engine.connect() as conn:
        version_pgvector = conn.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ).scalar()

        tables = [
            ligne[0]
            for ligne in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                )
            )
        ]

        # Pour une colonne pgvector, atttypmod contient directement le
        # nombre de dimensions déclaré à la création.
        dim_en_base = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
            )
        ).scalar()

        nb_users = conn.execute(text("SELECT count(*) FROM users")).scalar()
        nb_documents = conn.execute(text("SELECT count(*) FROM documents")).scalar()
        nb_chunks = conn.execute(text("SELECT count(*) FROM chunks")).scalar()

    return {
        "pgvector": version_pgvector,
        "nb_tables": len(tables),
        "tables": tables,
        "embedding_dim_en_base": dim_en_base,
        "embedding_dim_en_config": settings.embedding_dim,
        "coherence_dim": dim_en_base == settings.embedding_dim,
        "utilisateurs": nb_users,
        "documents": nb_documents,
        "chunks": nb_chunks,
        "modeles": {
            "generation": settings.llm_model,
            "rapide": settings.llm_model_fast,
            "embedding": settings.embedding_model,
        },
    }
```

---

### 10. `README.md`

````markdown
# RAG Dyneff — POC RH

RAG sur le corpus RH. FastAPI + Postgres/pgvector + (bientôt) Next.js.

> ⚠️ **CORPUS PUBLIC ET SYNTHÉTIQUE UNIQUEMENT.**
> Aucun document RH réel de l'entreprise ne doit se trouver dans ce dépôt,
> ni sur cette infrastructure, ni dans le compte OpenAI utilisé.

## Démarrer

```bash
cp .env.example .env
# → renseigner OPENAI_API_KEY
# → générer JWT_SECRET : python -c "import secrets; print(secrets.token_hex(32))"

docker compose up -d --build
curl localhost:8000/health
# → {"status":"ok","db":"connected"}
```

## Réinitialiser la base

`db/init.sql` n'est exécuté qu'à la **création du volume**.
Après toute modification du schéma :

```bash
docker compose down -v      # le -v détruit le volume
docker compose up -d --build
```

## DBeaver

| | |
|---|---|
| Hôte | `localhost` |
| Port | `5432` |
| Base | `ragdb` |
| Utilisateur | `rag` |
| Mot de passe | `rag` |

## Utilisateurs de démonstration

Mot de passe pour tous : `demo1234`

| Email | Groupes | Voit la grille des salaires ? |
|---|---|---|
| `marie@dyneff.fr` | `grp-tous`, `grp-rh` | ✅ |
| `paul@dyneff.fr` | `grp-tous` | ❌ |
| `admin@dyneff.fr` | tous | ✅ |
````

---

## Contraintes impératives

### ❌ INTERDIT — ne jamais introduire, même en suggestion

| Interdit | Pourquoi |
|---|---|
| **LangChain**, **LlamaIndex** | 300 dépendances, breaking changes, et ça cache exactement ce qu'il faut savoir expliquer en réunion |
| **Qdrant**, **Pinecone**, **Weaviate**, **Chroma** | pgvector suffit. Une seule base pour tout. |
| **Redis**, **Celery**, **Kubernetes** | Overkill total |
| **Alembic** | Décision figée. Toute migration = `docker compose down -v` |
| **Azure**, **LibreChat**, **Open WebUI** | Décisions figées |
| **passlib**, **python-jose** | Cassés / non maintenus (voir §2) |

### 🔴 RÈGLES ABSOLUES

1. Le `.gitignore` contenant `.env` est le **premier fichier créé**. Aucune exception.
2. `DATABASE_URL` commence par **`postgresql+psycopg://`**. Jamais `postgresql://` seul.
3. **`vector(1536)`** dans `init.sql` et **`EMBEDDING_DIM=1536`** dans `.env`. Les deux doivent être identiques.
4. **Aucun nom de modèle OpenAI en dur** dans le code Python. Tout passe par `settings`.
5. **Aucun mot de passe en clair** en base. Uniquement des hash bcrypt.
6. Code, commentaires et noms de colonnes **en français**.
7. **Pas de `web/`, pas de code front** dans ce CDC. Le front viendra au CDC 8.

### ✍️ STYLE DE CODE ATTENDU

- Python typé (`-> dict`, `: str`).
- Des docstrings **courtes** qui expliquent le **POURQUOI**, pas le QUOI.
- **Pas d'abstraction prématurée.** Pas de classe si une fonction suffit.
- Pas de `try/except` qui avale les erreurs en silence.

---

## Definition of Done

### Étape 1 — Préparer

```bash
cp .env.example .env

# Renseigner dans .env :
#   OPENAI_API_KEY = ta clé
#   JWT_SECRET     = python -c "import secrets; print(secrets.token_hex(32))"
```

### Étape 2 — Lancer

```bash
docker compose up -d --build
```

### Étape 3 — Le test qui compte

```bash
curl -s localhost:8000/health
```

**Résultat attendu EXACTEMENT :**

```json
{"status":"ok","db":"connected"}
```

### Étape 4 — Vérifier le schéma

```bash
curl -s localhost:8000/health/db
```

**Résultat attendu :**

```json
{
  "pgvector": "0.8.0",
  "nb_tables": 8,
  "tables": ["audit_log", "chunks", "conversations", "documents",
             "feedback", "fichiers", "messages", "users"],
  "embedding_dim_en_base": 1536,
  "embedding_dim_en_config": 1536,
  "coherence_dim": true,
  "utilisateurs": 3,
  "documents": 0,
  "chunks": 0,
  "modeles": {
    "generation": "gpt-5.6-terra",
    "rapide": "gpt-5.6-luna",
    "embedding": "text-embedding-3-large"
  }
}
```

### ✅ Les 4 points qui DOIVENT être vrais — sinon le CDC n'est pas fini

| # | Vérification | Attendu |
|---|---|---|
| 1 | `nb_tables` | **8** |
| 2 | `coherence_dim` | **true** |
| 3 | `utilisateurs` | **3** |
| 4 | `git status` ne montre PAS `.env` | **rien** |

### Étape 5 — Vérifier que les index existent

```bash
docker exec -it rag-db psql -U rag -d ragdb -c "\di"
```

**Doit contenir au minimum :**
- `idx_chunks_embedding_hnsw`
- `idx_chunks_tsv`
- `idx_chunks_allowed_groups`

### Étape 6 — Prouver l'ACL avant même d'avoir des données

```bash
docker exec -it rag-db psql -U rag -d ragdb -c \
  "SELECT email, groupes, ARRAY['grp-rh'] && groupes AS voit_les_salaires FROM users;"
```

**Résultat attendu :**

```
      email       |            groupes             | voit_les_salaires
------------------+--------------------------------+-------------------
 marie@dyneff.fr  | {grp-tous,grp-rh}              | t
 paul@dyneff.fr   | {grp-tous}                     | f
 admin@dyneff.fr  | {grp-tous,grp-rh,grp-admin}    | t
```

> **Marie voit. Paul ne voit pas.**
> **La sécurité est prouvée avant même d'avoir indexé un seul document.**

```
═══════════════════════════════════════════════════════════════
                   FIN DE LA PARTIE B
═══════════════════════════════════════════════════════════════
```

---
---

# ANNEXE — Le mode d'emploi après Cursor

## Avant de coller la Partie B

```bash
mkdir rag-dyneff && cd rag-dyneff
git init
```

Puis ouvre Cursor sur ce dossier et colle la **PARTIE B** intégralement.

## Après que Cursor a généré les fichiers

```bash
# 1. Configurer
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"    # → JWT_SECRET
# → éditer .env : OPENAI_API_KEY + JWT_SECRET

# 2. VÉRIFIER QUE .env EST IGNORÉ — avant de committer quoi que ce soit
git status | grep .env
# ↑ ne doit RIEN renvoyer. Si ça renvoie ".env", NE COMMITTE PAS.

# 3. Premier commit
git add -A
git commit -m "CDC 0 — fondations et schéma de base de données"

# 4. Lancer
docker compose up -d --build

# 5. Tester
curl -s localhost:8000/health
curl -s localhost:8000/health/db
```

## Si quelque chose casse

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'psycopg2'` | `DATABASE_URL` sans `+psycopg` | Corriger le `.env` |
| `connection refused` depuis le conteneur api | `localhost` au lieu de `db` | Vérifier le bloc `environment:` du service `api` |
| `nb_tables` < 8 | `init.sql` n'a pas été rejoué | `docker compose down -v && docker compose up -d --build` |
| `coherence_dim: false` | Piège n°1 | Vérifier que `.env` dit `1536` ET que `init.sql` dit `vector(1536)` |
| `CREATE INDEX` explose sur l'embedding | Dimension > 2000 | Idem — pgvector plafonne à 2000 |
| Pydantic refuse de démarrer | Une variable manque dans `.env` | Lire le message d'erreur, il dit laquelle |

## Une fois la DoD validée

Reviens avec la sortie de :

```bash
curl -s localhost:8000/health/db
```

Si `nb_tables: 8` et `coherence_dim: true` → **on passe au CDC 1 : le corpus.**

---

## Rappel des règles de sécurité du projet

| # | Règle |
|---|---|
| 🔴 **1** | **Corpus public et synthétique UNIQUEMENT.** Aucun document RH réel de Dyneff sur l'infra perso. |
| 🔴 **2** | **Le dire avant qu'on me le dise.** En réunion, poser le sujet de l'infra perso en premier. |
| 🔴 **3** | **Le VPS n'est pas ouvert au monde.** Mot de passe / restriction IP. |
| 🔴 **4** | **`.env` dans `.gitignore` dès le premier commit.** Sans exception. |
