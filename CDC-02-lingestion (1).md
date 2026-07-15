# CDC 2 — L'ingestion (lire, découper, vectoriser, ranger)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Prendre les 10 documents du dossier `corpus/`, les **découper en petits morceaux**, transformer chaque morceau en **liste de nombres**, et **tout ranger dans Postgres** — avec, collée sur chaque morceau, l'étiquette « qui a le droit de lire ça ».

---

## 💡 Pourquoi c'est important

Aujourd'hui tu as :
- une base de données **vide** (CDC 0)
- des documents qui dorment **sur ton disque** (CDC 1)

Les deux ne se parlent pas. **Ton assistant ne peut répondre à rien.**

Le CDC 2, c'est **le pont**. À la fin, ta base contient de la matière. Et à partir de là, tout le reste devient possible : chercher (CDC 3), répondre (CDC 4), noter (CDC 5).

> **C'est le premier CDC qui coûte de l'argent.** Il faut ta clé OpenAI.
> **Budget : moins de 5 centimes.** Sérieusement. On y reviendra.

---

## 📚 Les concepts — en français, sans jargon

### 1. Découper : pourquoi on ne peut pas donner le document entier

Ton assistant, c'est un lecteur. Tu lui poses une question, il lit, il répond.

**Mais il ne peut pas lire 50 pages à chaque question.** C'est trop long, trop cher, et il se perd.

Alors on découpe chaque document en **morceaux d'environ 800 mots**. Quand quelqu'un pose une question, on va chercher **les 5 morceaux les plus pertinents**, et on donne **seulement ceux-là** à lire.

```
Procédure télétravail (12 pages)
        ↓  DÉCOUPAGE
morceau 1 : "Qui peut télétravailler — conditions d'éligibilité..."
morceau 2 : "Le nombre de jours — plafond de 2 jours par semaine..."
morceau 3 : "Le refus — les 6 motifs recevables..."
morceau 4 : "Le recours — saisine du DRH sous 15 jours..."
```

### 2. Découper **BÊTEMENT** : la faute qui tue

La façon naïve, c'est de couper tous les 3 000 caractères. **Ne fais jamais ça.**

```
❌ CE QU'ON OBTIENT

morceau 7 : "...effectif. Les congés doivent être posés avec un préavis
             minimum de 15 jou"
             
→ coupé au milieu d'un mot
→ on ne sait même pas de quel document ça vient
→ inexploitable
```

**Nous, on découpe sur les TITRES.** Tes documents ont une structure (`#`, `##`, `###`) — c'est exactement pour ça que le CDC 1 l'a imposée.

Un morceau = **une sous-section entière**. Jamais coupée au milieu.

**Et les tableaux ne sont JAMAIS coupés.** Un tableau coupé en deux, c'est un tableau mort.

### 3. Le fil d'Ariane : l'astuce gratuite qui change tout

Prends ce morceau, tout seul :

```
"Il est de 25 jours ouvrés."
```

**Il est de 25 jours ouvrés… quoi ?** On ne sait pas. Ce morceau est inutilisable.

Alors avant de le ranger, on lui **colle son adresse en haut** :

```
Document : Procédure congés payés
Section  : 2. Le calcul du droit > 2.1 Le droit de base
---
Il est de 25 jours ouvrés.
```

**Maintenant il se suffit à lui-même.** Le lecteur sait de quoi on parle.

Ça s'appelle un **fil d'Ariane** (en anglais : *breadcrumb*). Ça coûte zéro. Ça double la qualité.

> ⭐ **C'est un des 3 leviers de qualité de tout le projet.** Les deux autres : les droits, et l'éval.

### 4. Le petit morceau et le gros morceau

Petit problème : pour **trouver**, on veut des morceaux **précis** (courts). Pour **répondre**, on veut du **contexte** (long).

Les deux besoins se contredisent.

**La solution :** on stocke les deux.

| | Ce que c'est | À quoi ça sert |
|---|---|---|
| **Le petit morceau** (§ 4.2) | une sous-section | on **CHERCHE** dedans |
| **Le gros morceau** (§ 4 entier) | la section complète autour | on **DONNE À LIRE** ça |

**L'image :** tu cherches avec une **loupe**, mais tu lis la **page entière**.

Tu trouves le paragraphe exact, puis tu remontes d'un cran pour donner tout le contexte au lecteur.

*(Dans le code, on appelle le gros morceau le « parent », et le petit le « child ». C'est du vocabulaire, pas de la magie.)*

### 5. Le vecteur : l'adresse GPS du sens

Rappel, parce que c'est le cœur.

Quelqu'un demande : *« j'ai droit à combien de **vacances** ? »*
Le document dit : *« Le salarié bénéficie de 25 jours de **congés payés** »*

👉 **Zéro mot en commun.** Un `Ctrl+F` échoue.

Alors on ne cherche pas les **mots**. On cherche le **sens**.

Imagine une carte géante où chaque phrase a une position. Les phrases qui veulent dire la même chose sont **voisines** :

```
    "vacances" ●
               ● "congés payés"       ← même quartier
               ● "25 jours ouvrés"

                        "note de frais" ●
                                        ● "remboursement"    ← autre quartier
```

Cette position, c'est une **liste de 1 536 nombres**. C'est ça, un vecteur.

```
"congés payés"  →  [0.23, -0.11, 0.87, 0.04, ... ]     (1 536 nombres)
"vacances"      →  [0.25, -0.09, 0.85, 0.06, ... ]     ← quasi identique
"note de frais" →  [-0.71, 0.44, 0.02, -0.33, ... ]    ← très loin
```

C'est un service d'OpenAI qui calcule ça. **C'est le seul truc payant de ce CDC.** Et c'est ridiculement peu cher : **0,13 $ pour un million de mots**. Ton corpus entier fait ~150 000 mots. **Fais le calcul : 2 centimes.**

### 6. La recherche par mots exacts : Postgres la fait tout seul

Le vecteur trouve le **sens**. Mais il rate les **codes** :

| | Trouve | Rate |
|---|---|---|
| **Vecteur** | « vacances » → « congés payés » ✅ | « Article 402 », « IDCC 1388 » ❌ |
| **Mots exacts** | « Article 402 » ✅ | les synonymes ❌ |

**Il faut les deux.** Un assistant qui ne fait que du vectoriel rate toutes les références légales.

Bonne nouvelle : **Postgres sait déjà chercher par mots exacts, en français, tout seul.** Il découpe le texte, enlève les accents, ramène « congés » et « congé » à la même racine. C'est intégré. Zéro dépendance.

Dans ce CDC, on lui prépare juste le terrain : une colonne `tsv` qui se remplit **toute seule**. On s'en servira au CDC 3.

### 7. Les gommettes (les droits)

Rappel du CDC 1 : le `manifest.json` porte, pour chaque document, **qui a le droit de le lire**.

```json
"CONFIDENTIEL-grille-remuneration-2026.md"  →  ["grp-rh"]
"procedure-teletravail.md"                  →  ["grp-tous"]
```

**Au moment du découpage, on recopie la gommette sur CHAQUE morceau.**

Pourquoi sur chaque morceau et pas juste sur le document ? Parce qu'au CDC 3, la recherche se fera **directement sur les morceaux**. Le filtre doit être **là**, sur la ligne qu'on interroge. Pas ailleurs.

---

## 🧩 Où ça s'insère

### Ce qui existe déjà

**Après le CDC 0 :**
```
rag-dyneff/
├── docker-compose.yml         Postgres 16 + pgvector, tourne
├── db/init.sql                8 tables créées
├── app/
│   ├── config.py              lit le .env (Pydantic)
│   ├── db.py                  la connexion
│   └── main.py                FastAPI : GET /health, GET /health/db
├── .env                       OPENAI_API_KEY, DATABASE_URL, ...
└── .gitignore                 .env dedans ✅
```

**Après le CDC 1 :**
```
├── corpus/
│   ├── manifest.json                              les gommettes
│   ├── procedure-teletravail.md
│   ├── procedure-conges-payes.md
│   ├── ... (8 procédures)
│   ├── CONFIDENTIEL-grille-remuneration-2026.md   grp-rh
│   └── CONFIDENTIEL-procedure-disciplinaire.md    grp-rh
└── scripts/valider_corpus.py                      → [OK] CORPUS VALIDE
```

### Ce que le CDC 2 ajoute

```
├── app/ingest/          ← NOUVEAU : le découpeur
└── db/init.sql          ← MODIFIÉ : la table chunks s'enrichit
```

Et une commande :

```bash
python -m app.ingest
```

### ⚠️ Une modification de la base est nécessaire

Le CDC 0 avait prévu la table `chunks`, mais il lui manque **3 colonnes** dont on a besoin maintenant. Il faut donc :

1. Mettre à jour `db/init.sql`
2. **Effacer et recréer la base** : `docker compose down -v && docker compose up -d`

**Tu ne perds rien.** La base ne contient que 3 utilisateurs de test, et `init.sql` les recrée.

> 💡 **Pourquoi `-v` ?** Parce que Postgres ne joue `init.sql` **qu'une seule fois**, à la toute première création. Tant que le volume Docker existe, le fichier est ignoré. Le `-v` supprime le volume. C'est LA commande à connaître.

---

## ⚠️ Les pièges de ce CDC

### 🔴 Piège n°1 — La dimension du vecteur (celui qui te fait perdre 3 heures)

Le modèle `text-embedding-3-large` sort, **par défaut**, des vecteurs de **3 072 nombres**.

**Mais pgvector ne sait indexer que jusqu'à 2 000.**

Ce qui se passe alors :
- l'insertion en base : ✅ ça passe
- la création de l'index : 💥 **ça explose**

Et le message d'erreur ne t'aide pas.

**La solution — trois endroits, une seule valeur :**

```python
client.embeddings.create(model=..., input=..., dimensions=1536)   # ← le paramètre
```
```sql
embedding vector(1536)      -- dans init.sql
```
```bash
EMBEDDING_DIM=1536          # dans .env
```

**Les trois doivent dire 1536.** Le script vérifiera lui-même et refusera de continuer si ce n'est pas le cas.

### 🔴 Piège n°2 — Mélanger deux modèles (le bug le plus vicieux du projet)

Tu ranges tes documents avec le modèle A.
Plus tard, tu poses une question avec le modèle B.

**Résultat :** les vecteurs ne sont pas comparables. La recherche ramène **du bruit pur**.

**Et rien ne plante.** Aucune erreur. Ça retourne juste des réponses absurdes, et tu cherches pendant des heures.

**Le garde-fou :** on **écrit le nom du modèle dans chaque ligne de la base**.

```sql
embedding_model TEXT     -- 'text-embedding-3-large'
embedding_dim   INTEGER  -- 1536
```

Si tu changes de modèle un jour → **tu réindexes tout**. Pas de mélange. Jamais.

### 🔴 Piège n°3 — Le tableau coupé en deux

Ta grille de rémunération, c'est un tableau.

Si le découpeur le coupe :

```
morceau 12 :
| Poste             | Min    | Max    |
|-------------------|--------|--------|
| Cadre confirmé    | 54 000 |

morceau 13 :
| 71 000 |
| Cadre supérieur   | 72 000 | 95 000 |
```

**Les deux morceaux sont morts.** Et la démo du moment n°2 avec.

→ **Un tableau est atomique.** Le code doit le traiter comme un bloc insécable, même s'il dépasse la taille cible.

### 🔴 Piège n°4 — Se ruiner en itérant

Tu vas vouloir ajuster le découpage. Le relancer. L'ajuster encore.

Si chaque essai appelle OpenAI, tu paies à chaque fois (peu, mais quand même) et tu attends.

→ **On code un mode `--dry-run` :** il découpe, il t'affiche le résultat, et il **n'appelle rien, n'écrit rien**.

Tu peux itérer 50 fois pour zéro centime.

### 🔴 Piège n°5 — Le PDF de la convention collective

Il n'est pas là. **Ce n'est pas grave.**

Le code sait lire les PDF (il faut ce code, car chez Dyneff le corpus sera 100 % PDF). Mais tant qu'aucun PDF n'est dans `corpus/`, ce chemin de code affiche juste un avertissement.

**Une annexe à la fin de ce document te donne un script pour aller le chercher sur Légifrance.** Elle est marquée **OPTIONNELLE**. Fais-la **après** que le CDC 2 passe sa Definition of Done. Pas avant.

---

## 🗣️ Ce que je pourrai dire en réunion grâce à ça

> *« Le découpage n'est pas mécanique. On ne coupe pas tous les N caractères — on découpe sur la structure du document, on préserve les tableaux, et on préfixe chaque passage de son chemin dans le document. C'est ce qui fait qu'une citation est vérifiable : je sais toujours de quelle section et de quelle page vient chaque phrase. »*

Et devant le RSSI :

> *« Les droits d'accès ne sont pas posés à la lecture. Ils sont posés à l'écriture, sur chaque passage, au moment de l'indexation. Le filtre est ensuite appliqué en SQL, avant la recherche. Le modèle ne voit jamais un passage qu'il n'a pas le droit de voir. »*

---
---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

Je construis **RAG Dyneff** : un assistant qui répond aux questions RH des collaborateurs en s'appuyant **uniquement** sur un corpus de documents internes, avec citations obligatoires et filtrage par droits d'accès.

**Stack (verrouillée) :** Python 3.12 · uv · FastAPI · Postgres 16 + pgvector · SDK OpenAI (une seule clé, pour les embeddings ET la génération) · Next.js 15 (plus tard).

**Interdits absolus — ne propose JAMAIS ces alternatives :**
LangChain · LlamaIndex · Qdrant · Pinecone · Weaviate · Chroma · Ragas · Redis · Celery · Alembic · Azure · LibreChat · Open WebUI · sentence-transformers · unstructured.

Le pipeline RAG complet doit tenir en ~300 lignes de Python nu, que je dois pouvoir expliquer ligne par ligne devant un DSI.

---

## État actuel du code

```
rag-dyneff/
├── docker-compose.yml          # service "db" : image pgvector/pgvector:pg16
├── db/
│   └── init.sql                # 8 tables : documents, chunks, users, conversations,
│                               #            messages, feedback, fichiers, audit_log
├── app/
│   ├── __init__.py
│   ├── config.py               # Settings (pydantic-settings) — lit le .env
│   ├── db.py                   # connexion Postgres (psycopg 3)
│   └── main.py                 # FastAPI : GET /health, GET /health/db
├── corpus/
│   ├── manifest.json
│   ├── procedure-teletravail.md
│   ├── procedure-conges-payes.md
│   ├── procedure-notes-de-frais.md
│   ├── procedure-arret-maladie.md
│   ├── procedure-onboarding.md
│   ├── procedure-mutuelle.md
│   ├── procedure-entretien-annuel.md
│   ├── procedure-mobilite-interne.md
│   ├── CONFIDENTIEL-grille-remuneration-2026.md
│   └── CONFIDENTIEL-procedure-disciplinaire.md
├── scripts/
│   └── valider_corpus.py       # → [OK] CORPUS VALIDE
├── .env                        # (dans .gitignore)
└── pyproject.toml
```

**Structure du `manifest.json` (déjà en place) :**

```json
{
  "version": "1.0",
  "documents": [
    {
      "chemin": "corpus/procedure-teletravail.md",
      "titre": "Procédure télétravail",
      "type": "md",
      "source": "synthetique",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"]
    },
    {
      "chemin": "corpus/CONFIDENTIEL-grille-remuneration-2026.md",
      "titre": "Grille de rémunération 2026",
      "type": "md",
      "source": "fictif",
      "sensibilite": "confidentiel",
      "allowed_groups": ["grp-rh"]
    }
  ],
  "trous_connus": ["congé paternité 2026", "..."]
}
```

**Structure des documents markdown (imposée au CDC 1) :**
- `#` = titre du document (exactement 1)
- `##` = sections majeures (au moins 4)
- `###` = sous-sections (2 à 4 par `##`, 150 à 400 mots chacune)
- 5 documents contiennent des **tableaux markdown**

---

## Ce qu'il faut construire

Une commande `python -m app.ingest` qui, pour chacun des documents du `manifest.json` :

1. **Charge** le fichier → markdown (avec les numéros de page pour les PDF)
2. **Découpe** sur les titres → sections
3. **Fabrique les chunks** : un « parent » par `##`, un « enfant » par `###`, chacun préfixé de son fil d'Ariane
4. **Vectorise** les enfants uniquement (OpenAI, `dimensions=1536`, par lots)
5. **Insère** en base, avec `allowed_groups` recopiés depuis le manifest

Plus un mode `--dry-run` qui fait 1→3, affiche les statistiques, et **n'appelle pas OpenAI et n'écrit pas en base**.

---

## ÉTAPE 0 — Mettre à jour le schéma de la base

Ouvre `db/init.sql`. **Remplace les définitions de `documents` et `chunks`** par exactement ceci (garde les 6 autres tables telles quelles) :

```sql
-- ─────────────────────────────────────────────────────────────
--  DOCUMENTS
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    chemin          TEXT        NOT NULL UNIQUE,   -- 'corpus/procedure-teletravail.md'
    titre           TEXT        NOT NULL,
    type            TEXT        NOT NULL,          -- 'md' | 'pdf'
    source          TEXT        NOT NULL,          -- 'public' | 'synthetique' | 'fictif'
    sensibilite     TEXT        NOT NULL,          -- 'public' | 'interne' | 'confidentiel'
    allowed_groups  TEXT[]      NOT NULL,
    nb_chunks       INTEGER     NOT NULL DEFAULT 0,
    indexe_le       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
--  CHUNKS
--  type = 'child'  → petit morceau, VECTORISÉ, c'est lui qu'on cherche
--  type = 'parent' → section complète, PAS vectorisé, c'est lui qu'on lit
-- ─────────────────────────────────────────────────────────────
CREATE TABLE chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    type            TEXT    NOT NULL DEFAULT 'child'
                            CHECK (type IN ('child', 'parent')),
    parent_id       INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
    ordre           INTEGER NOT NULL,          -- position dans le document

    breadcrumb      TEXT    NOT NULL,          -- "Document : X\nSection : A > B\n---"
    contenu         TEXT    NOT NULL,          -- le texte SEUL (sans le fil d'Ariane)
    contenu_indexe  TEXT    NOT NULL,          -- fil d'Ariane + contenu → c'est CE texte
                                               -- qu'on vectorise ET qu'on met en full-text
    page            INTEGER,                   -- NULL pour les .md
    nb_tokens       INTEGER NOT NULL,

    -- garde-fou du Piège n°2 : on SAIT avec quoi chaque ligne a été vectorisée
    embedding       vector(1536),              -- NULL pour les 'parent'
    embedding_model TEXT,                      -- NULL pour les 'parent'
    embedding_dim   INTEGER,                   -- NULL pour les 'parent'

    allowed_groups  TEXT[]  NOT NULL,          -- recopié du manifest

    -- Postgres calcule cette colonne TOUT SEUL, à chaque écriture. On ne l'alimente jamais.
    tsv             tsvector GENERATED ALWAYS AS
                        (to_tsvector('french', contenu_indexe)) STORED
);

-- Recherche par proximité de sens (CDC 3)
CREATE INDEX idx_chunks_embedding
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Recherche par mots exacts, en français (CDC 3)
CREATE INDEX idx_chunks_tsv
    ON chunks USING gin (tsv);

-- Filtrage par droits — DOIT être rapide, il s'applique AVANT tout le reste (CDC 3)
CREATE INDEX idx_chunks_acl
    ON chunks USING gin (allowed_groups);

CREATE INDEX idx_chunks_type      ON chunks (type);
CREATE INDEX idx_chunks_parent    ON chunks (parent_id);
CREATE INDEX idx_chunks_document  ON chunks (document_id);
```

Puis **rejoue le schéma** (le volume Docker doit être détruit, sinon `init.sql` est ignoré) :

```bash
docker compose down -v
docker compose up -d
```

---

## ÉTAPE 1 — Ajouter les variables au `.env`

Ajoute ces lignes au `.env` (et au `.env.example` s'il existe) :

```bash
# ─── Embeddings ───────────────────────────────────────────
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIM=1536            # ⚠️ DOIT valoir 1536 — cf. Piège n°1
EMBEDDING_BATCH=64            # nombre de textes envoyés par appel API
EMBEDDING_PRIX_MTOKEN=0.13    # $ par million de tokens — pour l'estimation de coût

# ─── Découpage ────────────────────────────────────────────
CHUNK_SIZE=800                # taille cible d'un chunk, en tokens
CHUNK_OVERLAP=100             # recouvrement quand on doit re-découper, en tokens
```

Étends `app/config.py` (la classe `Settings`) avec ces champs, typés.

---

## Fichiers à créer

```
app/ingest/
├── __init__.py
├── __main__.py       # point d'entrée : python -m app.ingest
├── modeles.py        # les dataclasses
├── manifest.py       # lire + re-valider le manifest
├── load.py           # fichier → markdown (+ pages pour les PDF)
├── chunk.py          # markdown → sections → chunks     ⭐ LE CŒUR
├── embed.py          # OpenAI, dimensions=1536, par lots
└── index.py          # écriture en base
```

---

## Spécifications techniques

### `app/ingest/modeles.py`

```python
from dataclasses import dataclass, field


@dataclass
class Section:
    """Une section de markdown, délimitée par un titre."""
    niveau: int                      # 1 pour '#', 2 pour '##', 3 pour '###'
    titre: str
    contenu: str                     # le texte SOUS ce titre, hors sous-sections
    chemin: list[str]                # ["4. Le refus", "4.2 Les motifs recevables"]
    page: int | None = None          # None pour un .md


@dataclass
class ChunkPret:
    """Un chunk prêt à être inséré. Pas encore d'id : on ne connaît pas
    l'id du parent avant de l'avoir inséré, donc on relie par une clé logique."""
    cle: str                         # "3::sec2::sub1"  — unique dans le document
    cle_parent: str | None           # la cle du parent, ou None si c'est un parent
    type: str                        # 'child' | 'parent'
    ordre: int
    breadcrumb: str
    contenu: str
    contenu_indexe: str              # breadcrumb + "\n" + contenu
    nb_tokens: int
    page: int | None
    embedding: list[float] | None = None
```

---

### `app/ingest/manifest.py`

```python
def charger_manifest(chemin: Path = Path("corpus/manifest.json")) -> list[dict]:
    """Lit le manifest et renvoie la liste des documents.

    GARDE-FOU DE SÉCURITÉ — refuse d'indexer si un document 'confidentiel'
    est accessible à 'grp-tous'. Lève une exception, n'écrit rien.
    Ce contrôle existe déjà dans scripts/valider_corpus.py. On le REFAIT ici.
    Défense en profondeur : le validateur peut ne pas avoir été lancé.
    """
```

Le garde-fou, explicitement :

```python
for doc in documents:
    if doc["sensibilite"] == "confidentiel" and "grp-tous" in doc["allowed_groups"]:
        raise ValueError(
            f"REFUS D'INDEXER — {doc['chemin']} est confidentiel "
            f"mais accessible a grp-tous. Corrige le manifest."
        )
```

---

### `app/ingest/load.py`

```python
def charger(chemin: Path, type_doc: str) -> tuple[str, dict[int, int]]:
    """Renvoie (markdown, offsets_pages).

    offsets_pages : {offset_caractere_de_debut: numero_de_page}
                    dictionnaire VIDE pour un .md (pas de pagination)
    """
```

**Pour un `.md`** :
```python
return chemin.read_text(encoding="utf-8"), {}
```

**Pour un `.pdf`** — `pymupdf4llm`, en mode page par page pour récupérer les numéros :
```python
import pymupdf4llm

pages = pymupdf4llm.to_markdown(str(chemin), page_chunks=True)
# pages = [{"text": "...", "metadata": {"page": 1, ...}}, ...]

morceaux: list[str] = []
offsets: dict[int, int] = {}
curseur = 0
for p in pages:
    texte = p["text"]
    offsets[curseur] = p["metadata"]["page"]      # page 1-based
    morceaux.append(texte)
    curseur += len(texte) + 2                     # +2 pour le "\n\n" de jointure
return "\n\n".join(morceaux), offsets
```

Une fonction utilitaire :
```python
def page_de(offset: int, offsets_pages: dict[int, int]) -> int | None:
    """Le numéro de page à un offset caractère donné. None si pas de pagination."""
    if not offsets_pages:
        return None
    page = None
    for debut in sorted(offsets_pages):
        if debut <= offset:
            page = offsets_pages[debut]
        else:
            break
    return page
```

---

### `app/ingest/chunk.py` ⭐ **LE CŒUR — lis les règles jusqu'au bout**

#### Compter les tokens

```python
import tiktoken

# get_encoding, PAS encoding_for_model : encoding_for_model lève une exception
# si le nom du modèle est inconnu de la version installée de tiktoken.
# Les modèles text-embedding-3-* utilisent cl100k_base.
ENCODEUR = tiktoken.get_encoding("cl100k_base")

def compter_tokens(texte: str) -> int:
    return len(ENCODEUR.encode(texte))
```

#### 1. Découper le markdown en sections

```python
def decouper_en_sections(
    markdown: str,
    offsets_pages: dict[int, int],
) -> list[Section]:
```

Règles :
- Une ligne titre = `^(#{1,6})\s+(.+)$`
- **Ignorer tout titre situé à l'intérieur d'un bloc de code** (entre deux lignes ` ``` `). Un `#` dans un bloc de code est un commentaire Python, pas un titre.
- Maintenir une **pile de titres**. `chemin` = les titres des niveaux **strictement inférieurs** au niveau courant, plus le titre courant — **en excluant le niveau 1** (c'est le titre du document, il va dans le fil d'Ariane à part).
- `contenu` = les lignes entre ce titre et le titre suivant (quel que soit son niveau). **Le contenu propre, sans les sous-sections.**
- `page` = `page_de(offset_du_titre, offsets_pages)`

#### 2. Fabriquer les chunks

```python
def construire_chunks(
    doc_id_logique: str,
    doc_titre: str,
    sections: list[Section],
    chunk_size: int,
    chunk_overlap: int,
) -> list[ChunkPret]:
```

**Les règles, dans cet ordre exact :**

| Règle | Détail |
|---|---|
| **R1** | Un **parent** est créé pour **chaque section de niveau 2** (`##`). Son `contenu` = son propre texte **+ le texte de toutes ses sous-sections `###`**, concaténé, titres inclus. Un parent n'est **jamais vectorisé** et **jamais re-découpé**, quelle que soit sa taille. |
| **R2** | Un **enfant** est créé pour **chaque section de niveau 3** (`###`), rattaché au parent de son `##`. |
| **R3** | Si un `##` **n'a aucun `###`**, on crée **un seul enfant** dont le contenu est celui du `##`, rattaché à ce même `##` en tant que parent. (Oui, le texte est dupliqué. C'est voulu, ça coûte quelques milliers de tokens, et ça garde le code uniforme.) |
| **R4** | Si du contenu existe **sous le `#` avant le premier `##`** (préambule), on crée un parent artificiel intitulé **« Préambule »**, et un enfant associé. |
| **R5** | Les titres de **niveau 4 et plus** (`####`) ne créent **pas** de nouveau niveau. Leur contenu est **absorbé** dans le `###` qui les contient (le titre `####` reste dans le texte). |
| **R6** | Si le `contenu_indexe` d'un **enfant** dépasse `CHUNK_SIZE` tokens → **on le re-découpe** (voir plus bas). Les sous-morceaux gardent le **même parent** et le **même fil d'Ariane**. |

#### 3. Le fil d'Ariane — format EXACT, pas de variante

```python
def fil_ariane(doc_titre: str, chemin: list[str]) -> str:
    return (
        f"Document : {doc_titre}\n"
        f"Section  : {' > '.join(chemin)}\n"
        f"---"
    )
```

Exemple concret produit :

```
Document : Procédure télétravail
Section  : 4. Le refus > 4.2 Les motifs recevables
---
```

Et :
```python
contenu_indexe = fil_ariane(...) + "\n" + contenu
```

⚠️ **`contenu_indexe` est ce qu'on vectorise ET ce que Postgres met en full-text.**
⚠️ **`contenu` (sans le fil d'Ariane) est ce qu'on affichera à l'utilisateur.**
Les deux sont stockés. Ne les confonds pas.

#### 4. Re-découper un enfant trop long — ⚠️ LES TABLEAUX SONT INSÉCABLES

```python
def decouper_en_blocs(contenu: str) -> list[str]:
    """Découpe un contenu en blocs INSÉCABLES.

    Un bloc est :
      - un tableau markdown ENTIER    (lignes consecutives commençant par '|')
      - un bloc de code ENTIER        (entre deux ```)
      - un paragraphe                 (texte entre deux lignes vides)

    Un bloc n'est JAMAIS coupé, même s'il dépasse à lui seul chunk_size.
    """
```

Puis :

```python
def regrouper_en_morceaux(
    blocs: list[str],
    breadcrumb: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Remplit gloutonnement des morceaux de <= chunk_size tokens.

    - Le fil d'Ariane est recollé sur CHAQUE morceau, et compté dans le budget.
    - Recouvrement : chaque nouveau morceau reprend les DERNIERS blocs du
      précédent, jusqu'à atteindre ~chunk_overlap tokens.
      → un paragraphe à cheval sur deux morceaux reste trouvable.
    - Un bloc qui, seul, dépasse chunk_size part dans son propre morceau,
      SANS être coupé. On émet un avertissement :
          [!] Bloc insécable de {n} tokens dans « {breadcrumb} »
    """
```

---

### `app/ingest/embed.py`

```python
import time
from openai import OpenAI


def vectoriser(
    textes: list[str],
    modele: str,
    dimension: int,
    taille_lot: int = 64,
) -> list[list[float]]:
    """Appelle l'API OpenAI par lots. Renvoie les vecteurs DANS L'ORDRE d'entrée."""
    client = OpenAI()          # lit OPENAI_API_KEY dans l'environnement
    vecteurs: list[list[float]] = []

    for debut in range(0, len(textes), taille_lot):
        lot = textes[debut : debut + taille_lot]

        for tentative in range(5):
            try:
                reponse = client.embeddings.create(
                    model=modele,
                    input=lot,
                    dimensions=dimension,   # ⭐ PIÈGE N°1 — sans ça : 3072, l'index explose
                )
                break
            except Exception as e:
                if tentative == 4:
                    raise
                time.sleep(2 ** tentative)   # 1s, 2s, 4s, 8s

        # L'API garantit l'ordre, mais on ne fait pas confiance : on retrie sur .index
        for item in sorted(reponse.data, key=lambda d: d.index):
            vecteurs.append(item.embedding)

    # ⭐ GARDE-FOU PIÈGE N°1 — on vérifie AVANT d'écrire en base
    for v in vecteurs:
        if len(v) != dimension:
            raise ValueError(
                f"Dimension recue : {len(v)}, attendue : {dimension}. "
                f"Le parametre dimensions= n'a pas ete pris en compte."
            )

    return vecteurs
```

---

### `app/ingest/index.py`

```python
def indexer(documents_et_chunks, settings) -> dict:
    """Écrit tout en base. Renvoie les statistiques.

    STRATÉGIE : reconstruction complète.
      TRUNCATE chunks, documents RESTART IDENTITY CASCADE;
    Puis tout réinsérer.

    Pourquoi TRUNCATE et pas un INSERT incrémental ?
      → l'ingestion devient IDEMPOTENTE : relancer 10 fois donne le même résultat
      → si on change de modèle d'embedding, on ne PEUT PAS mélanger (Piège n°2)
      → 400 lignes, ça prend 2 secondes. Pas de sur-ingénierie.
    """
```

**Ordre d'insertion — obligatoire :**

1. `TRUNCATE chunks, documents RESTART IDENTITY CASCADE;`
2. Insérer les `documents`, récupérer les `id` (via `RETURNING id`)
3. Insérer **les parents** (`type='parent'`, `embedding=NULL`), récupérer leurs `id` → construire une table de correspondance `{cle_logique: id_en_base}`
4. Insérer **les enfants** (`type='child'`), avec `parent_id` résolu depuis la table de correspondance
5. Mettre à jour `documents.nb_chunks`

**Écrire un vecteur avec psycopg 3 — méthode robuste, sans dépendre d'un adaptateur :**

```python
def vers_litteral_vecteur(v: list[float]) -> str:
    """pgvector accepte la forme textuelle '[0.1,0.2,...]'.
    On caste explicitement en SQL avec ::vector.
    Zéro dépendance à un adaptateur, marche dans toutes les versions."""
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"
```

```sql
INSERT INTO chunks (
    document_id, type, parent_id, ordre,
    breadcrumb, contenu, contenu_indexe, page, nb_tokens,
    embedding, embedding_model, embedding_dim, allowed_groups
) VALUES (
    %s, 'child', %s, %s,
    %s, %s, %s, %s, %s,
    %s::vector, %s, %s, %s
)
```

Utilise `cur.executemany(...)`. Pas de `COPY`, pas d'ORM. ~400 lignes, c'est instantané.

⚠️ **Ne touche JAMAIS à la colonne `tsv` en Python.** Elle est `GENERATED ALWAYS`. Postgres la remplit seul à partir de `contenu_indexe`. Si tu essaies de l'écrire, Postgres refusera l'INSERT.

---

### `app/ingest/__main__.py`

```bash
python -m app.ingest              # découpe + vectorise + écrit en base
python -m app.ingest --dry-run    # découpe + affiche — AUCUN appel API, AUCUNE écriture
python -m app.ingest --doc corpus/procedure-teletravail.md   # un seul document
```

**Contrôles à faire AVANT tout traitement (fail fast) :**

```python
# 1. La dimension déclarée doit valoir 1536 — sinon l'index HNSW explosera
if settings.embedding_dim != 1536:
    sys.exit("EMBEDDING_DIM doit valoir 1536 (limite d'indexation de pgvector).")

# 2. La clé API doit exister (sauf en dry-run)
if not dry_run and not settings.openai_api_key:
    sys.exit("OPENAI_API_KEY absente du .env")

# 3. Le manifest doit passer le garde-fou de sécurité
documents = charger_manifest()   # lève si un confidentiel est en grp-tous
```

**Sortie attendue en `--dry-run` :**

```
──────────────────────────────────────────────────────────────────────────────
  Document                                  enfants  parents   tok.moy   max
──────────────────────────────────────────────────────────────────────────────
  Procédure télétravail                          14        5       412   780
  Procédure congés payés                         12        4       389   654
  Procédure notes de frais                       15        5       401   823  [!]
  ...
  Grille de rémunération 2026        [grp-rh]     9        4       520  1240  [!]
──────────────────────────────────────────────────────────────────────────────
  TOTAL : 10 documents · 128 enfants · 44 parents
  Tokens à vectoriser : 52 480
  Coût estimé : 0,007 $

  [!] 2 blocs insécables dépassent CHUNK_SIZE (tableaux — c'est normal et voulu)

  [DRY-RUN] Aucun appel OpenAI. Aucune écriture en base.
──────────────────────────────────────────────────────────────────────────────
```

**Sortie attendue en mode réel :**

```
  Vectorisation : 128 textes en 2 lots... OK
──────────────────────────────────────────────────────────────────────────────
  128 chunks indexés depuis 10 documents (+ 44 parents)
  Modèle : text-embedding-3-large · dimension 1536
  Tokens : 52 480 · Coût : 0,007 $
  Durée : 8,2 s
──────────────────────────────────────────────────────────────────────────────
```

---

## Contraintes impératives

### ❌ INTERDIT

| Interdit | Pourquoi |
|---|---|
| **LangChain, LlamaIndex** | Décision figée. Le RAG entier = ~300 lignes de Python nu que je dois pouvoir expliquer. |
| **`RecursiveCharacterTextSplitter`** ou tout découpage **par nombre de caractères** | Piège n°3. On découpe sur la STRUCTURE. |
| **Couper un tableau markdown** | La grille de rémunération est un tableau. Un tableau coupé = la démo ACL morte. |
| **Appeler l'API OpenAI en mode `--dry-run`** | Le dry-run doit être 100 % gratuit et hors-ligne. |
| **Écrire dans la colonne `tsv`** | Elle est `GENERATED ALWAYS`. Postgres la calcule seul. |
| **Omettre `dimensions=1536`** | Piège n°1. L'index HNSW explosera plus tard, pas maintenant. |
| **Vectoriser les chunks `parent`** | Ils ne sont jamais cherchés, seulement lus. On paierait pour rien. |
| **`sentence-transformers`, `unstructured`, un modèle local** | Une seule clé API : OpenAI. Décision figée. |
| **`tiktoken.encoding_for_model(...)`** | Lève une exception sur un nom de modèle inconnu. Utilise `get_encoding("cl100k_base")`. |

### ✅ OBLIGATOIRE

1. **Tout en français** : noms de fonctions, variables, messages, commentaires, docstrings.
2. **Type hints partout.** Python 3.12 (`list[str]`, `int | None`).
3. **Zéro nouvelle dépendance.** Tout est déjà dans le `pyproject.toml` : `openai`, `pymupdf4llm`, `tiktoken`, `psycopg[binary]`, `pydantic-settings`.
4. **Aucune valeur en dur.** `CHUNK_SIZE`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` viennent **tous** de `app/config.py`, qui lit le `.env`.
5. **Le garde-fou de dimension** (`if len(v) != dimension: raise`) doit être présent **avant** toute écriture en base.
6. **Le garde-fou du manifest** (confidentiel + grp-tous → refus) doit être présent.
7. **Commente le POURQUOI, pas le QUOI.** Je dois pouvoir relire ce code dans 3 semaines et l'expliquer en réunion.
8. **Fail fast** : les contrôles d'abord, le traitement ensuite.

---

## Definition of Done

### 1. Le schéma est en place

```bash
docker compose down -v && docker compose up -d
sleep 5
curl -s localhost:8000/health
```
→ `{"status":"ok","db":"connected"}`

### 2. Le découpage est correct — sans dépenser un centime

```bash
python -m app.ingest --dry-run
```

**Attendu :**
- un tableau, une ligne par document, **10 documents**
- **aucun document à 0 enfant**
- les seuls `[!]` sont sur des **tableaux** (blocs insécables) — c'est voulu
- la ligne finale : `[DRY-RUN] Aucun appel OpenAI. Aucune écriture en base.`

### 3. L'ingestion réelle passe

```bash
python -m app.ingest
```

**Attendu :** `N chunks indexés depuis 10 documents (+ M parents)`, avec `N > 100`.

### 4. 🔴 LES 6 CONTRÔLES EN BASE — dans DBeaver

```sql
-- ① Chaque chunk enfant a bien un vecteur
SELECT count(*) FROM chunks WHERE type = 'child' AND embedding IS NULL;
-- ATTENDU : 0

-- ② La dimension est unique et vaut 1536      (Piège n°1)
SELECT DISTINCT embedding_dim, embedding_model FROM chunks WHERE type = 'child';
-- ATTENDU : une seule ligne → 1536 | text-embedding-3-large      (Piège n°2)

-- ③ Le fil d'Ariane est présent et lisible
SELECT breadcrumb, left(contenu, 60) FROM chunks WHERE type = 'child' LIMIT 5;
-- ATTENDU : "Document : ... / Section : ... > ..." sur chaque ligne

-- ④ Les droits sont posés sur chaque morceau
SELECT allowed_groups, count(*) FROM chunks GROUP BY 1;
-- ATTENDU : {grp-tous} → beaucoup   |   {grp-rh} → quelques dizaines

-- ⑤ 🔴 LE CONTRÔLE QUI DÉCIDE DE TOUT
SELECT count(*) FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE d.sensibilite = 'confidentiel'
  AND 'grp-tous' = ANY(c.allowed_groups);
-- ATTENDU : 0
-- Si ce n'est PAS 0 : la grille des salaires est publique. On s'arrête tout.

-- ⑥ La recherche par mots exacts en français fonctionne déjà
SELECT count(*) FROM chunks
WHERE tsv @@ plainto_tsquery('french', 'congés payés');
-- ATTENDU : > 0
```

### 5. L'ingestion est rejouable

```bash
python -m app.ingest
python -m app.ingest
```
→ **Le même nombre de chunks les deux fois.** Pas de doublons.

### 6. Le parent/enfant est correct

```sql
SELECT
  (SELECT count(*) FROM chunks WHERE type='child')                      AS enfants,
  (SELECT count(*) FROM chunks WHERE type='parent')                     AS parents,
  (SELECT count(*) FROM chunks WHERE type='child' AND parent_id IS NULL) AS orphelins;
-- ATTENDU : orphelins = 0
```

**Si un seul de ces 6 contrôles échoue, le CDC 2 n'est pas fini.**

```
═══════════════════════════════════════════════════════════════
                   FIN DE LA PARTIE B
═══════════════════════════════════════════════════════════════
```

---
---

# 🎁 ANNEXE — OPTIONNELLE — Le texte de la convention collective

> ⚠️ **NE FAIS CECI QU'APRÈS que le CDC 2 ait passé sa Definition of Done.**
> Ce n'est **pas** bloquant. Ton corpus de 10 documents suffit à tout construire.

## Le constat

Légifrance publie la convention collective **gratuitement**, mais **article par article**, sur des pages web séparées. Il n'existe **aucun bouton de téléchargement** du texte complet. Les sites qui vendent le PDF le vendent précisément pour cette raison.

**Donc : il faut du code.**

## Ce que ça t'apporte

| | |
|---|---|
| ✅ | Une **vraie source publique** dans tes citations, pas un document que tu as toi-même inventé |
| ✅ | De **vraies références légales** (`Article 402`, `IDCC 1388`) → parfait pour tester la moitié « mots exacts » de la recherche hybride du CDC 3 |

## ⚠️ Le piège à connaître AVANT de le faire

La convention contient **un titre entier sur les salaires** (coefficients, barèmes, minima conventionnels).

Si tu l'indexes avec `grp-tous` :

```
Paul (commercial) → « c'est quoi la grille des salaires ? »
→ le RAG remonte les minima conventionnels publics
→ IL RÉPOND
```

**Ta démo ACL du moment n°2 est morte.** Elle repose sur le fait que Paul obtienne *« je n'ai pas d'information accessible »*.

→ **Donc : n'importe QUOI sauf les chapitres salaires.** Récupère les titres sur les congés, la durée du travail, la maladie, la rupture du contrat. **Pas la rémunération.**

## Le script

Crée `scripts/telecharger_convention.py`.

**Ce qu'il fait :**
1. Charge la page sommaire : `https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635267`
2. Extrait tous les liens d'articles (motif : `/conv_coll/article_ka/KALIARTI...`)
3. **Filtre** : exclut les articles dont le titre de section contient `salaire`, `rémunération`, `coefficient`, `barème`, `appointement`
4. Pour chaque article restant : charge sa page, extrait le titre + le texte
5. Écrit `corpus/convention-collective-petrole-1388.md` avec la structure `#` / `##` / `###` attendue par le chunker

**Contraintes :**
- Bibliothèque standard + `httpx` (déjà installé). **Pas de BeautifulSoup**, pas de Selenium.
- **Un délai de 0,5 s entre deux requêtes.** C'est un site public de l'État — on ne le martèle pas.
- Si Légifrance change son HTML, le script casse. **C'est acceptable : on le lance une fois.**

**Ensuite :**
1. Ajouter l'entrée au `manifest.json` (`type: "md"`, `source: "public"`, `sensibilite: "public"`, `allowed_groups: ["grp-tous"]`)
2. `python scripts/valider_corpus.py`
3. `python -m app.ingest`
4. **Refaire le contrôle ⑤.** S'il ne renvoie plus 0, tu as ramené des articles salaires → retire-les.

## Et le PDF, alors ?

Le code de lecture des PDF (`pymupdf4llm`) **est écrit** dans ce CDC. Il tourne dès qu'un `.pdf` est déclaré au manifest. Il te servira le jour où tu brancheras SharePoint.

**Mais tu n'as pas besoin d'un PDF aujourd'hui.** Le markdown que produit ce script est même *meilleur* : la structure est propre, il n'y a rien à re-deviner.

> 🔴 **RAPPEL — RÈGLE DE SÉCURITÉ N°1 :** corpus **public et synthétique UNIQUEMENT**.
> La convention collective est publique (Légifrance) → ✅ OK.
> **Aucun document RH réel de Dyneff sur ta machine, ton VPS, ou ton compte OpenAI.** Jamais.
