# CDC 1 — Le corpus de test

> **Projet RAG Dyneff — POC service RH**
> Deuxième cahier des charges. Le CDC 0 (fondations + base de données) est fait et validé.
> Généré le 14 juillet 2026.

> 🔑 **Aucune clé OpenAI nécessaire pour ce CDC.** On n'appelle aucune API. On écrit des fichiers.

---

## SOMMAIRE

**PARTIE A — POUR ISSA** *(comprendre — ne pas coller dans Cursor)*
1. [L'objectif en une phrase](#1--lobjectif-en-une-phrase)
2. [Pourquoi c'est le CDC le plus sous-estimé du projet](#2--pourquoi-cest-le-cdc-le-plus-sous-estimé-du-projet)
3. [L'idée centrale : on écrit le corpus À L'ENVERS](#3--lidée-centrale--on-écrit-le-corpus-à-lenvers)
4. [Les concepts à comprendre](#4--les-concepts-à-comprendre)
5. [Le mapping corpus → les 5 moments de la démo](#5--le-mapping-corpus--les-5-moments-de-la-démo)
6. [Les trous volontaires](#6--les-trous-volontaires)
7. [Les pièges de ce CDC](#7--les-pièges-de-ce-cdc)
8. [L'étape manuelle : la convention collective](#8--létape-manuelle--la-convention-collective)
9. [Ce que je pourrai dire en réunion](#9--ce-que-je-pourrai-dire-en-réunion)

**PARTIE B — POUR CURSOR** *(copier-coller intégralement)*

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

Écrire les **11 documents** sur lesquels le RAG sera bâti — un vrai document public, huit procédures synthétiques, deux documents confidentiels fictifs — et le `manifest.json` qui déclare, pour chacun, **qui a le droit de le voir**.

---

## 2 — 💡 Pourquoi c'est le CDC le plus sous-estimé du projet

Tu vas être tenté de bâcler celui-là. *« C'est juste du contenu, le vrai boulot c'est le retrieval. »*

**Non.** Voilà pourquoi.

### 2.1 — Le corpus, c'est l'éval

Au **CDC 5**, on génère 40 questions/réponses **depuis le corpus**. C'est ton contrôle. C'est ton chiffre. C'est ta phrase en réunion :

> *« Testé sur 40 questions réelles : 87 % de réponses justes, 0 % d'hallucination. »*

**Si le corpus est plat, l'éval est vide de sens.**

Un corpus sans chiffres précis → aucune question ne peut avoir de bonne réponse vérifiable.
Un corpus sans tableaux → on ne teste jamais le pire cas du chunking.
Un corpus sans références d'articles → on ne teste jamais la moitié « mots exacts » de la recherche hybride.

> **Le corpus n'est pas du remplissage. C'est le sujet du contrôle.**

### 2.2 — Le corpus, c'est la démo

Les 5 moments de mercredi **dépendent chacun d'un document précis, avec un chiffre précis dedans.**

Exemple, le moment n°3 — celui qui tue Datasulting :

> *« Rédige le courrier de refus de télétravail **3 jours/semaine** pour M. Dupont »*

Pour que le RAG produise un refus **fondé**, il faut que la procédure télétravail dise noir sur blanc :
- **le plafond est de 2 jours par semaine**
- **voici les motifs de refus recevables**
- **voici la procédure de notification (écrit motivé, délai, voie de recours)**

**Si ces trois éléments ne sont pas dans le document, le `.docx` généré sera du vent.** Et le moment n°3 tombe à plat.

### 2.3 — Le corpus, c'est le seul endroit où tu décides de la vérité

Après le CDC 1, tu ne discutes plus de ce que le système « devrait » répondre. **Tu compares à ce qui est écrit.** Le corpus devient le référentiel. C'est ça qui rend l'éval possible.

---

## 3 — 🔄 L'idée centrale : on écrit le corpus À L'ENVERS

**La méthode naïve :**

```
J'écris 8 procédures RH plausibles
     ↓
J'espère que la démo marchera avec
```

**La méthode qu'on applique :**

```
Je liste les 5 moments de la démo
     ↓
Pour chaque moment, je liste la question exacte
     ↓
Pour chaque question, j'écris le document qui contient la réponse
     ↓
ET je m'assure qu'il contient LE chiffre précis qui rend la réponse vérifiable
```

> **Le corpus est la conséquence de la démo, pas l'inverse.**

C'est exactement ce qu'un consultant ne fait pas. Il livre un corpus « représentatif » et découvre en réunion que la démo ne tient pas.

---

## 4 — 📚 Les concepts à comprendre

### 4.1 — Le `manifest.json` : le contrat entre le CDC 1 et le CDC 2

Le manifest est un fichier JSON qui déclare, **pour chaque document du corpus** :

| Champ | Exemple | À quoi ça sert |
|---|---|---|
| `chemin` | `corpus/procedure-teletravail.md` | Où est le fichier |
| `titre` | `Procédure Télétravail` | **Ce qui s'affichera dans la citation** |
| `type` | `md` ou `pdf` | Quel parseur utiliser (CDC 2) |
| `source` | `public` / `synthetique` / `fictif` | Traçabilité — la preuve que rien n'est réel |
| `sensibilite` | `public` / `interne` / `confidentiel` | Lisibilité humaine |
| **`allowed_groups`** | `["grp-rh"]` | 🔒 **LA SÉCURITÉ. Recopié dans chaque chunk en base.** |

**Au CDC 2, l'ingestion lira le manifest et rien d'autre.**

> ⚠️ **Point capital : l'ingestion ne fera JAMAIS un `glob("corpus/*.md")`.**
>
> Si elle le faisait, n'importe quel fichier posé dans le dossier (un README, une note, un brouillon) serait indexé — **sans ACL, donc visible par tout le monde par défaut.**
>
> **Le manifest est la porte d'entrée. Un fichier qui n'y est pas n'existe pas pour le RAG.**

---

### 4.2 — La structure markdown **pilote** le découpage

Souviens-toi du **Piège n°3** : *« JAMAIS de découpage tous les N caractères. On découpe sur les TITRES. »*

Concrètement, au CDC 2, le chunker va faire ça :

```
# Procédure Télétravail                    ← Titre du document
## 3. Le refus d'une demande               ← Section
### 3.2 Les motifs de refus recevables     ← Sous-section  →  UN CHUNK
```

Et il fabrique le breadcrumb :

```
Document : Procédure Télétravail
Section  : 3. Le refus d'une demande > 3.2 Les motifs de refus recevables
---
Le responsable hiérarchique peut refuser une demande de télétravail
pour l'un des motifs suivants...
```

**Conséquence directe :**

| Si le document est… | Alors… |
|---|---|
| **Plat** (que du texte, pas de titres) | Le chunker n'a rien pour découper → il coupe au caractère → **breadcrumbs vides → retrieval nul** |
| **Bien structuré** (`#` > `##` > `###`) | Chaque sous-section devient un chunk propre, avec son fil d'Ariane → **retrieval précis** |

> **La qualité du markdown que Cursor écrit aujourd'hui détermine la qualité du RAG mercredi.**
>
> C'est un des **3 leviers de qualité** du projet (avec les ACL et l'éval).

**Donc la contrainte imposée à Cursor :** chaque document a un `#`, au moins 4 `##`, et chaque `##` contient 2 à 4 `###` de 150 à 400 mots. **Un `###` ≈ un chunk.**

---

### 4.3 — Les tableaux : le pire cas du chunker

**Piège n°3, deuxième partie :** *« Les tableaux : on les extrait à part et on ne les coupe JAMAIS. »*

Un tableau coupé en deux, c'est ça :

```
| Niveau | Coefficient | Minimum |
|--------|-------------|---------|
| 5      | 320         | 44 000
```
→ **inexploitable.** Le modèle ne sait plus quelle colonne il lit.

**On met donc 5 tableaux dans le corpus, exprès :**

| Document | Le tableau |
|---|---|
| Guide Mutuelle | **Comparatif des 3 régimes** — c'est la démo *« compare les 3 régimes en tableau »* |
| Grille de rémunération | **8 niveaux × 4 colonnes** — c'est la démo ACL |
| Notes de frais | Les plafonds par type de dépense |
| Arrêt maladie | Le barème de maintien de salaire par ancienneté |
| Procédure disciplinaire | L'échelle des sanctions |

**Si le CDC 2 casse un de ces cinq tableaux, on le verra immédiatement.** C'est fait exprès.

---

### 4.4 — Le nom du fichier ne fait **PAS** la sécurité

Deux fichiers du corpus s'appellent `CONFIDENTIEL-grille-remuneration-2026.md` et `CONFIDENTIEL-procedure-disciplinaire.md`.

Le préfixe `CONFIDENTIEL-` est **un confort visuel pour toi.** C'est tout.

> 🔴 **La sécurité, c'est `allowed_groups: ["grp-rh"]` dans le manifest.**
> **Recopié dans la colonne `allowed_groups` de chaque chunk.**
> **Filtré en SQL, avant la recherche.**

C'est exactement le **Piège n°5** transposé : ne jamais confondre la couche « confort » et la couche « sécurité ». Si demain tu renommes le fichier `notes.md`, la protection ne bouge pas d'un millimètre.

---

### 4.5 — Les « trous volontaires »

Un RAG qui répond toujours quelque chose est un RAG qui hallucine.

**Il faut donc des questions dont on SAIT que la réponse n'est pas dans le corpus.** On les déclare, dans le manifest, sous la clé `trous_connus`.

Elles serviront **trois fois** :

| CDC | Usage |
|---|---|
| **CDC 5 — l'éval** | Les questions « il DOIT dire je ne sais pas ». C'est la métrique **taux de refus**. |
| **CDC 10 — la recherche web** | *« Le congé paternité a changé en 2026 ? »* → pas dans le corpus → **toggle web** → démo moment n°4 |
| **CDC 12 — le dashboard** | Le bloc **« les trous du corpus »** → *« voici les 3 documents qui manquent dans votre base »* → **c'est ça, le livrable pour les RH** |

> **Les trous ne sont pas un défaut du corpus. Ce sont des fonctionnalités.**

---

## 5 — 🎬 Le mapping corpus → les 5 moments de la démo

**C'est le tableau qui justifie tout ce CDC.**

| # | Moment de la démo | La question exacte | Le document qui porte la réponse | Le chiffre clé |
|---|---|---|---|---|
| **1** | Question RH réelle + citations | *« Combien de jours de congés payés par an ? »* | Convention collective **+** Procédure Congés payés *(deux sources → bon test du reranker)* | **25 jours ouvrés** |
| **2** | 🔒 Changement d'utilisateur | *« Quel est le salaire d'un cadre confirmé ? »* | **CONFIDENTIEL — Grille de rémunération** *(`grp-rh` uniquement)* | **54 000 – 71 000 €** |
| **3** | 💥 Génération de `.docx` | *« Rédige le courrier de refus de télétravail 3 jours/semaine pour M. Dupont »* | Procédure Télétravail — **plafond + motifs de refus + procédure de notification** | **2 jours/semaine max** |
| **4** | 🌐 Toggle recherche web | *« La réglementation sur le congé paternité a changé en 2026 ? »* | **AUCUN — trou volontaire** | — |
| **5** | 📊 Dashboard | *« Quels documents manquent dans votre base ? »* | `manifest.json` → `trous_connus` | **7 trous déclarés** |

### Pourquoi le moment n°2 marche

| Utilisateur | Groupes | Réponse attendue |
|---|---|---|
| **Marie** (RH) | `grp-tous`, `grp-rh` | *« Niveau 6, coefficient 380 : entre 54 000 € et 71 000 € bruts annuels, médiane 62 000 €. [Grille de rémunération 2026 · §2]* » |
| **Paul** (commercial) | `grp-tous` | *« Je n'ai pas d'information accessible sur ce sujet dans les documents auxquels vous avez accès. »* |

**Même question. Même système. Deux réponses.** Et pas parce qu'on a demandé au modèle d'être discret — **parce que la requête SQL n'a rien ramené.**

### Pourquoi le moment n°3 marche

La Procédure Télétravail **doit** contenir, explicitement :

1. **« Le télétravail est limité à 2 jours par semaine. »** → M. Dupont demande 3 jours → **hors plafond** → motif de refus n°4
2. **Une liste numérotée de 6 motifs de refus recevables** → le courrier peut en citer un
3. **La procédure de notification** : réponse écrite motivée sous 1 mois, voie de recours DRH sous 15 jours → le courrier reprend ces mentions

**Résultat :** le `.docx` généré n'est pas une lettre inventée. C'est une lettre **conforme à la procédure, sourcée, prête à signer.**

> ### *« Un RAG qui répond, ça informe. Un RAG qui produit le document, ça remplace du travail. »*

---

## 6 — 🕳️ Les trous volontaires

Sept sujets **délibérément absents** du corpus :

| # | Le trou | Pourquoi celui-là |
|---|---|---|
| 1 | **Congé proche aidant** | Sujet RH réel et fréquent → question naturelle |
| 2 | **Mobilité internationale / expatriation** | Le doc mobilité dit explicitement « France métropolitaine » → **le RAG doit voir la limite** |
| 3 | **Réforme du congé paternité 2026** | 🌐 **La question de la démo web (moment 4)** |
| 4 | **Télétravail depuis l'étranger** | Piège classique post-COVID |
| 5 | **Compte épargne temps (CET)** | Sujet RH courant, non couvert |
| 6 | **Congé sabbatique** | Idem |
| 7 | **Participation / intéressement** | Sujet salarial hors grille |

**Ces sept-là finiront dans le dashboard, sous le bloc :**

```
🕳️  LES TROUS DU CORPUS
    • Congé proche aidant
    • Mobilité internationale
    • Compte épargne temps
```

> *« Voici les documents qui manquent dans votre base. »*
>
> **C'est un livrable. Pas une démo.**

---

## 7 — ⚠️ Les pièges de ce CDC

### 7.1 — 🔴 Le piège de l'incohérence entre documents

Si la Procédure Congés dit **25 jours** et que la Procédure Onboarding dit **30 jours**, alors :
- le retrieval remonte les deux
- le LLM se contredit ou choisit au hasard
- **l'éval devient du bruit** — impossible de savoir si l'erreur vient du système ou du corpus

**La parade :** la Partie B impose un **référentiel de constantes**. Un tableau unique de tous les chiffres. **Tous les documents doivent le respecter à la lettre.** Aucune improvisation.

---

### 7.2 — 🔴 Le piège du document plat

Cursor, laissé libre, écrit volontiers de longs paragraphes sans structure.

**Un document plat = un chunking raté = un RAG médiocre.** Voir §4.2.

**La parade :** la Partie B impose la structure (`#` > `##` > `###`), et le **script de validation refuse** un document qui a moins de 4 `##`.

---

### 7.3 — 🔴 Le piège du fichier oublié dans le dossier

Un `README.md`, un `notes.md`, un brouillon posé dans `/corpus` → indexé sans ACL → **visible par tout le monde**.

**La parade :** l'ingestion lit **uniquement** le `manifest.json`. Jamais un glob. C'est écrit noir sur blanc dans les contraintes de la Partie B, et ce sera re-vérifié au CDC 2.

---

### 7.4 — 🔴 Le piège de la sensibilité incohérente

Un document marqué `"sensibilite": "confidentiel"` mais avec `"allowed_groups": ["grp-tous"]` → **la grille des salaires est publique.** La démo meurt. Le projet aussi.

**La parade :** le script de validation **bloque** cette combinaison. Erreur fatale, exit code 1.

```python
if doc["sensibilite"] == "confidentiel" and "grp-tous" in doc["allowed_groups"]:
    → ERREUR BLOQUANTE
```

---

### 7.5 — 🔴 RAPPEL — Règle de sécurité n°1

> **AUCUN document RH réel de Dyneff.**
> Pas sur cette machine. Pas sur le VPS. Pas dans le compte OpenAI.

**Le corpus est composé exclusivement de :**
1. La convention collective de l'industrie du pétrole — **source publique, Légifrance**
2. Huit procédures **écrites de toutes pièces** par Cursor
3. Deux documents confidentiels **entièrement inventés**

> *Le jour où un vrai document RH Dyneff se retrouve sur mon infra perso, je ne suis plus candidat au poste de Responsable IA — je suis un incident de sécurité.*

**Chaque document synthétique porte, en pied de page, la mention :**

```
> Document synthétique — rédigé pour la démonstration technique du POC RAG.
> Ne constitue en aucun cas un document RH réel de l'entreprise.
```

C'est ta protection. Si quelqu'un ouvre un fichier par hasard, il le lit en première ligne.

---

## 8 — 📥 L'étape manuelle : la convention collective

**C'est la seule chose que Cursor ne peut pas faire à ta place.** Il n'a pas accès au web.

### Ce qu'il faut télécharger

| | |
|---|---|
| **Document** | Convention collective nationale de l'**industrie du pétrole** du 3 septembre 1985 |
| **IDCC** | **1388** |
| **Brochure JO** | **3001** |
| **Étendue par** | arrêté du 31 juillet 1986 (JORF du 9 août 1986) |
| **Volume** | ~220–231 pages (texte consolidé) |
| **Source** | Légifrance — https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635267 |
| **Alternative** | Code du travail numérique — https://code.travail.gouv.fr/convention-collective/1388-industrie-du-petrole |

### Où le mettre

```
corpus/convention-collective-petrole-1388.pdf
```

**Le nom exact compte** — c'est celui déclaré dans le `manifest.json`.

### Pourquoi ce document précisément

| Raison | Détail |
|---|---|
| **C'est public** | Légifrance. Zéro risque juridique, zéro risque de sécurité. |
| **C'est la bonne branche** | Dyneff est un distributeur multi-énergies → l'industrie du pétrole, c'est sa convention. **En réunion, ça fait vrai.** |
| **C'est numéroté** | Les articles sont référencés `Article 101`, `Article 405`, `Article 855`… → **c'est exactement ce qui teste la moitié « mots exacts » de la recherche hybride.** Un RAG purement vectoriel rate « Article 405 ». Le nôtre non. |
| **C'est dense et long** | ~220 pages → ~200 chunks → un vrai test du chunking, pas un jouet. |

> ⚠️ **Attention à la numérotation réelle.** Les articles de l'IDCC 1388 sont numérotés **à trois chiffres** (101, 102… 201… 405…), **pas** « Article 12 ». Les exemples du glossaire du projet utilisaient « Article 12 » à titre d'illustration. Pour l'éval du CDC 5, on utilisera **les vrais numéros**, lus dans le PDF.

### ⚠️ Le contrôle qualité vient au CDC 2, pas maintenant

Un PDF juridique de 220 pages peut mal se parser. **Ce n'est pas un problème du CDC 1** — le CDC 1 se contente de poser le fichier.

**Mais retiens ça pour le CDC 2 :** la première chose qu'on fera, c'est **regarder le markdown produit par `pymupdf4llm`**. S'il est illisible (titres perdus, colonnes mélangées, sommaire éclaté), le plan B est de **ne garder que 3 ou 4 Titres** (durée du travail, congés, maladie, classification).

> **30 pages propres valent mieux que 220 pages en bouillie.**
> **La qualité du découpage prime sur le volume du corpus.**

---

## 9 — 🗣️ Ce que je pourrai dire en réunion

Sur le corpus :

> *« La démo tourne sur la vraie convention collective de la branche — l'IDCC 1388, publique, sur Légifrance — et sur des procédures internes que j'ai écrites moi-même. **Aucun document RH réel de Dyneff n'a quitté l'infrastructure de l'entreprise.** Ce que je démontre, c'est le moteur. Le brancher sur vos vrais documents, c'est un déploiement. »*

**Cette phrase, tu la dis en premier. Avant qu'on te la pose.** *(Règle de sécurité n°2.)*

Sur les trous :

> *« Le système sait dire "je ne sais pas". Et quand il le dit, il le compte. À la fin du mois, je peux vous sortir la liste des sujets sur lesquels vos collaborateurs posent des questions **et sur lesquels votre documentation est muette**. Ce n'est plus un chatbot. C'est un audit de votre base documentaire. »*

**Ça, personne d'autre ne l'apportera à la réunion.**

---
---

```
═══════════════════════════════════════════════════════════════
                    PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT — à partir d'ici)
═══════════════════════════════════════════════════════════════
```

# MISSION — CDC 1 : Le corpus de test

## Contexte du projet

On construit un **RAG** (Retrieval-Augmented Generation) pour le service RH d'une entreprise française de distribution multi-énergies (~1 500 salariés).

**Stack déjà en place :** FastAPI (Python 3.12) + Postgres 16 + pgvector, le tout en Docker.

Ce CDC ne produit **aucun code applicatif**. Il produit **du contenu** : les documents sur lesquels le RAG sera bâti, plus le fichier de métadonnées qui déclare les droits d'accès, plus un script de validation.

**C'est le socle de tout le reste.** La qualité de ce corpus détermine directement la qualité du retrieval (CDC 3), de la génération (CDC 4) et de l'évaluation (CDC 5).

---

## État actuel du code

Le **CDC 0** est terminé et validé. Existent déjà :

```
rag-dyneff/
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── db/init.sql              ← 8 tables créées
├── corpus/                  ← VIDE (c'est l'objet de ce CDC)
├── eval/
├── web/
└── app/
    ├── main.py              ← GET /health, GET /health/db
    ├── config.py
    ├── db.py
    └── ingest|retrieval|llm|api|security|chat|files|tools/  (vides)
```

**Les tables existantes qui concernent ce CDC** (dans `db/init.sql`) :

```sql
CREATE TABLE documents (
    id          SERIAL PRIMARY KEY,
    titre       TEXT NOT NULL,
    chemin      TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL CHECK (type IN ('pdf', 'md')),
    source      TEXT NOT NULL CHECK (source IN ('public', 'synthetique', 'fictif')),
    service     TEXT NOT NULL DEFAULT 'rh',
    sensibilite TEXT NOT NULL DEFAULT 'interne'
                CHECK (sensibilite IN ('public', 'interne', 'confidentiel')),
    nb_pages    INTEGER,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- chunks.allowed_groups TEXT[] NOT NULL DEFAULT '{}'
```

> ⚠️ **Le `manifest.json` que tu vas produire DOIT respecter ces contraintes `CHECK` à la lettre.**
> Sinon l'insertion du CDC 2 sera rejetée par Postgres.

**Les groupes existants** (utilisateurs déjà seedés en base) :

| Groupe | Qui |
|---|---|
| `grp-tous` | Tout le monde |
| `grp-rh` | Le service RH (Marie) — accède aux documents confidentiels |
| `grp-admin` | Administration technique |

---

## ⚠️ ÉTAPE MANUELLE PRÉALABLE (faite par l'utilisateur, PAS par toi)

L'utilisateur télécharge la **Convention collective nationale de l'industrie du pétrole (IDCC 1388)** depuis Légifrance et la dépose ici :

```
corpus/convention-collective-petrole-1388.pdf
```

**Tu ne peux pas la télécharger** (pas d'accès réseau). **Tu la déclares quand même dans le `manifest.json`.**

Le script de validation signalera son absence en **AVERTISSEMENT** (pas en erreur) si le fichier n'est pas encore là.

---

## Ce qu'il faut construire

| # | Livrable |
|---|---|
| 1 | **8 procédures internes synthétiques** en markdown |
| 2 | **2 documents confidentiels fictifs** en markdown |
| 3 | **`corpus/manifest.json`** — le contrat de métadonnées + droits d'accès |
| 4 | **`scripts/valider_corpus.py`** — le script de validation (bibliothèque standard uniquement) |

---

## Fichiers à créer

```
rag-dyneff/
├── corpus/
│   ├── manifest.json                              ← LE CONTRAT
│   ├── convention-collective-petrole-1388.pdf     ← posé manuellement par l'utilisateur
│   │
│   ├── procedure-teletravail.md                   ← ⭐ CRITIQUE (démo moment 3)
│   ├── procedure-conges-payes.md                  ← ⭐ CRITIQUE (démo moment 1)
│   ├── procedure-notes-de-frais.md
│   ├── procedure-arret-maladie.md
│   ├── procedure-onboarding.md
│   ├── guide-mutuelle.md                          ← ⭐ contient LE grand tableau
│   ├── procedure-entretien-annuel.md
│   ├── procedure-mobilite-interne.md
│   │
│   ├── CONFIDENTIEL-grille-remuneration-2026.md   ← 🔒 grp-rh (démo moment 2)
│   └── CONFIDENTIEL-procedure-disciplinaire.md    ← 🔒 grp-rh
│
└── scripts/
    └── valider_corpus.py
```

**Noms de fichiers : ASCII strict, sans accent, sans espace.** (Compatibilité Windows / Docker / URL.)

---

## 🔢 LE RÉFÉRENTIEL DE CONSTANTES — À RESPECTER À LA LETTRE

> **RÈGLE ABSOLUE : tous les documents doivent être cohérents entre eux.**
> Si deux documents se contredisent, l'évaluation du CDC 5 devient impossible à interpréter.
> **N'invente AUCUN chiffre. Utilise EXACTEMENT ceux-ci.**

### Entreprise (fictive, pour le décor)

| Élément | Valeur |
|---|---|
| Nom | **Dyneff** (distributeur multi-énergies) |
| Effectif | ~1 700 salariés |
| Convention collective | **Industrie du pétrole — IDCC 1388** |
| Version des procédures | **2026.1 — en vigueur au 1er janvier 2026** |

### Congés payés

| Élément | Valeur |
|---|---|
| **Droit annuel** | **25 jours ouvrés** (5 semaines) — **2,08 jours acquis par mois** |
| Période de référence | 1er juin → 31 mai |
| Congé principal | minimum **12 jours ouvrés consécutifs**, maximum **20 jours** |
| Délai de prévenance | **1 mois** pour une absence ≥ 5 jours · **15 jours** en dessous |
| Report | maximum **5 jours**, jusqu'au **31 décembre**, sur validation du manager |
| Jours de fractionnement | **+1 jour** si 3 ou 4 jours pris hors période · **+2 jours** si ≥ 5 jours |
| Congé sans solde | possible, **accord écrit du manager + DRH**, **3 mois maximum** |
| RTT (cadres au forfait 218 jours) | **12 jours/an** — 6 au choix du salarié, 6 imposés par l'entreprise |

### Télétravail ⭐ (document le plus critique du corpus)

| Élément | Valeur |
|---|---|
| **PLAFOND** | **2 jours par semaine — MAXIMUM** ← *le chiffre qui fait toute la démo* |
| Ancienneté minimale | **6 mois** |
| Postes exclus | exploitation de dépôt, logistique terrain, accueil, maintenance sur site |
| Jours | **fixes**, définis dans l'avenant au contrat |
| Demande | écrite, au manager, **1 mois avant** la date souhaitée |
| **Réponse de l'employeur** | **écrite et motivée, sous 1 mois** |
| **Recours** | auprès de la DRH, **sous 15 jours** après notification du refus |
| Indemnité | **2,70 € par jour télétravaillé**, plafonnée à **21,60 € / mois** |
| Réversibilité | préavis de **1 mois**, des deux côtés |
| Période d'adaptation | **3 mois** |

**Les 6 motifs de refus recevables — à écrire sous forme de liste NUMÉROTÉE :**

1. **Poste non éligible** — la fonction exige une présence physique permanente
2. **Ancienneté insuffisante** — moins de 6 mois dans l'entreprise
3. **Nécessités de service** — continuité d'activité, présence d'équipe requise
4. **Demande excédant le plafond** — au-delà de **2 jours par semaine** ⭐
5. **Conditions matérielles non réunies** — connexion, espace de travail, conformité électrique
6. **Autonomie insuffisante** — constatée lors de l'entretien avec le manager

### Notes de frais

| Dépense | Plafond |
|---|---|
| Repas (midi ou soir), en déplacement | **19,40 €** |
| Nuitée — province | **75 €** |
| Nuitée — grandes métropoles | **110 €** |
| Nuitée — Paris / Île-de-France | **150 €** |
| Kilométrique | **barème fiscal en vigueur** |
| Justificatif obligatoire | **au-delà de 10 €** |

| Règle | Valeur |
|---|---|
| Dépôt des notes | **avant le 5 du mois suivant** |
| Remboursement | avec la paie du mois suivant |
| Validation | manager N+1 · **contrôle DRH au-delà de 500 €** |
| Taxi / VTC | **uniquement** si aucune alternative — justificatif + motif obligatoires |
| **Alcool** | **jamais remboursé**, sans exception |
| Invitation client | plafond **60 € par convive**, nom des convives obligatoire |

### Arrêt maladie

| Élément | Valeur |
|---|---|
| Prévenir le manager | **sous 24 heures** |
| Transmettre l'arrêt | **sous 48 heures** |
| Carence Sécurité sociale | **3 jours** |
| Maintien de salaire employeur | **à partir de 1 an d'ancienneté** |
| Visite de reprise | **obligatoire après 30 jours d'arrêt** |
| Subrogation | **oui** (l'entreprise perçoit les IJSS et maintient le salaire) |

**Barème de maintien de salaire (tableau à reproduire) :**

| Ancienneté | 100 % du salaire | puis 75 % du salaire |
|---|---|---|
| < 1 an | — | — |
| 1 à 5 ans | 30 jours | 30 jours |
| 6 à 10 ans | 40 jours | 40 jours |
| 11 à 15 ans | 50 jours | 50 jours |
| 16 à 20 ans | 60 jours | 60 jours |
| > 20 ans | 90 jours | 90 jours |

### Onboarding

| Jalon | Contenu |
|---|---|
| **J-7** | Kit d'accueil envoyé · création des comptes (Microsoft Entra ID) · commande du matériel |
| **J0** | Accueil à **9h00** · remise du poste et du badge · tour des équipes · signature des documents |
| **J+7** | Point d'étape avec le manager |
| **J+30** | **Entretien d'étonnement** avec la DRH |
| **J+90** | Bilan de fin de période d'essai |

| Élément | Valeur |
|---|---|
| Période d'essai — cadres | **3 mois**, renouvelable **1 fois** |
| Période d'essai — non-cadres | **2 mois**, renouvelable **1 fois** |
| Parrain / marraine | désigné dès J-7 |
| Adhésion mutuelle | **dans les 15 jours** suivant l'embauche |

### Mutuelle ⭐ (le grand tableau)

**Trois régimes : Base / Confort / Famille+**

| Garantie | **Base** | **Confort** | **Famille+** |
|---|---|---|---|
| Cotisation mensuelle salarié | **18 €** | **34 €** | **52 €** |
| Part employeur | 60 % | 60 % | 55 % |
| Consultation généraliste | 100 % BR | 150 % BR | 200 % BR |
| Consultation spécialiste | 100 % BR | 200 % BR | 250 % BR |
| Optique — verres + monture / 2 ans | 150 € | 300 € | 450 € |
| Dentaire — prothèses | 125 % BR | 250 % BR | 400 % BR |
| Orthodontie | **non couvert** | 150 % BR | 300 % BR |
| Hospitalisation — chambre particulière | 50 € / nuit | 80 € / nuit | 110 € / nuit |
| Médecine douce (ostéopathie, chiropraxie) | **non couvert** | 4 séances × 30 € | 6 séances × 40 € |
| Ayants droit (conjoint, enfants) | **non** | option payante | **inclus** |

*(BR = Base de Remboursement de la Sécurité sociale.)*

| Règle | Valeur |
|---|---|
| Adhésion | **obligatoire**, sauf cas de dispense |
| Cas de dispense | CDD < 12 mois · couverture par le conjoint · apprenti · temps très partiel |
| Changement de régime | **une fois par an**, au 1er janvier — **demande avant le 30 novembre** |
| Changement hors période | uniquement sur **événement familial** (mariage, naissance, divorce) |

### Entretien annuel

| Élément | Valeur |
|---|---|
| Campagne | **1er février → 31 mars** |
| Auto-évaluation du salarié | à remplir **au moins 7 jours avant** l'entretien |
| Durée recommandée | **1h30** |
| Compte rendu | signé par les deux parties · **contestation possible sous 15 jours** auprès du N+2 |
| Entretien professionnel (formation, évolution) | **tous les 2 ans** — distinct de l'entretien annuel |
| Bilan à 6 ans | **obligatoire** (état des lieux du parcours) |

### Mobilité interne

| Élément | Valeur |
|---|---|
| Ancienneté minimale | **18 mois dans le poste actuel** |
| Publication | bourse à l'emploi interne · **priorité interne pendant 15 jours** avant toute publication externe |
| Le manager actuel est informé | **après le premier entretien**, jamais avant |
| Préavis de transfert | **2 mois maximum** |
| Prime de mobilité géographique | **3 000 €** |
| Déménagement | pris en charge sur présentation de **3 devis** |
| **Périmètre** | ⚠️ **France métropolitaine uniquement** — la mobilité internationale N'EST PAS traitée dans ce document *(trou volontaire)* |

### 🔒 CONFIDENTIEL — Grille de rémunération 2026

| Niveau | Coef. | Intitulé | Minimum brut annuel | Médian | Maximum |
|---|---|---|---|---|---|
| **1** | 190 | Employé / Opérateur débutant | 24 600 € | 26 000 € | 27 500 € |
| **2** | 215 | Employé confirmé | 27 000 € | 29 500 € | 32 000 € |
| **3** | 240 | Technicien | 31 000 € | 34 500 € | 38 000 € |
| **4** | 275 | Technicien supérieur / Agent de maîtrise | 36 000 € | 41 000 € | 46 000 € |
| **5** | 320 | Cadre débutant | 44 000 € | 49 000 € | 55 000 € |
| **6** | 380 | **Cadre confirmé** ⭐ | **54 000 €** | **62 000 €** | **71 000 €** |
| **7** | 450 | Cadre supérieur / Responsable de service | 70 000 € | 82 000 € | 95 000 € |
| **8** | 550 | Directeur | 95 000 € | 115 000 € | 140 000 € |

| Élément | Valeur |
|---|---|
| Budget d'augmentation 2026 | **2,3 % de la masse salariale** — dont **0,6 %** réservé aux mesures individuelles |
| Part variable — cadres (niveaux 5-6) | **jusqu'à 10 %** du fixe |
| Part variable — cadres supérieurs (7-8) | **jusqu'à 20 %** du fixe |
| Prime d'ancienneté | **+3 %** à 3 ans, **+6 %** à 6 ans, **+9 %** à 9 ans, **+12 %** à 12 ans |
| Fourchette d'embauche | entre le **minimum** et le **médian** du niveau — au-delà : **validation DRH obligatoire** |
| Révision de la grille | annuelle, au **1er janvier** |

> ⭐ **Le niveau 6 « Cadre confirmé » est LE chiffre de la démonstration ACL.**
> La question posée sera : *« Quel est le salaire d'un cadre confirmé ? »*
> Marie (RH) doit obtenir : **54 000 € – 71 000 €, médiane 62 000 €**.
> Paul (commercial) doit obtenir : **« je n'ai pas d'information accessible »**.

### 🔒 CONFIDENTIEL — Procédure disciplinaire

**Échelle des sanctions (tableau à reproduire) :**

| Niveau | Sanction | Effet | Inscrite au dossier |
|---|---|---|---|
| 1 | **Avertissement** | Rappel écrit à l'ordre | 3 ans |
| 2 | **Blâme** | Reproche écrit formalisé | 3 ans |
| 3 | **Mise à pied disciplinaire** | **5 jours ouvrés maximum**, non rémunérés | 5 ans |
| 4 | **Mutation disciplinaire** | Changement de poste ou de site | 5 ans |
| 5 | **Rétrogradation** | Changement de niveau — nécessite l'accord du salarié | 5 ans |
| 6 | **Licenciement pour cause réelle et sérieuse** | Rupture avec préavis | — |
| 7 | **Licenciement pour faute grave / lourde** | Rupture immédiate, sans préavis ni indemnité | — |

| Règle de procédure | Valeur |
|---|---|
| **Prescription des faits** | **2 mois** à compter de la connaissance des faits par l'employeur |
| Convocation à l'entretien préalable | **LRAR ou remise en main propre contre décharge** — **5 jours ouvrables minimum** avant l'entretien |
| Assistance du salarié | par un membre du personnel ou un conseiller extérieur |
| Notification de la sanction | **entre 2 jours ouvrables et 1 mois** après l'entretien |
| Mise à pied conservatoire | possible, **effet immédiat**, distincte de la sanction |
| Recours | conseil de prud'hommes |

**Barème indicatif par type de faute (tableau à reproduire) :**

| Faute | Sanction de 1re occurrence | Récidive |
|---|---|---|
| Retards répétés non justifiés | Avertissement | Blâme |
| Absence injustifiée (1 journée) | Avertissement | Mise à pied 1 jour |
| **Non-respect des consignes de sécurité sur site pétrolier** | **Mise à pied 3 jours** | **Licenciement pour faute grave** |
| **Conduite d'un véhicule-citerne sous emprise d'alcool** | **Licenciement pour faute grave** | — |
| Usage abusif des ressources informatiques | Avertissement | Blâme |
| Divulgation d'informations confidentielles | Mise à pied 5 jours | Licenciement pour faute grave |

---

## 📐 LA STRUCTURE MARKDOWN OBLIGATOIRE

> **Le découpage en chunks (CDC 2) se fera SUR LES TITRES.**
> Un document mal structuré = un chunking raté = un RAG médiocre.
> **Cette contrainte n'est pas cosmétique. Elle est fonctionnelle.**

### Le gabarit imposé pour chaque document synthétique

```markdown
# [Titre du document]

**Version 2026.1 — en vigueur au 1er janvier 2026**
**Service émetteur : Direction des Ressources Humaines**
**Convention collective applicable : Industrie du pétrole (IDCC 1388)**

[Un paragraphe d'introduction : objet du document, à qui il s'applique. 3-5 lignes.]

---

## 1. [Première grande section]

### 1.1 [Sous-section]

[150 à 400 mots. → CE BLOC DEVIENDRA UN CHUNK.]

### 1.2 [Sous-section]

[150 à 400 mots.]

---

## 2. [Deuxième grande section]

### 2.1 [Sous-section]

...

---

## 6. Questions fréquentes

### 6.1 [Question posée telle qu'un salarié la poserait]

[Réponse courte et factuelle.]

---

## 7. Contacts et documents liés

- **Contact :** [service RH / adresse générique fictive]
- **Voir aussi :** [renvoi vers un ou deux AUTRES documents du corpus]

---

> Document synthétique — rédigé pour la démonstration technique du POC RAG.
> Ne constitue en aucun cas un document RH réel de l'entreprise.
```

### Les règles non négociables

| # | Règle |
|---|---|
| 1 | **Exactement UN titre `#`** par document, en première ligne |
| 2 | **Au minimum 4 titres `##`**, numérotés (`## 1.`, `## 2.`…) |
| 3 | **2 à 4 titres `###` par `##`**, numérotés (`### 1.1`, `### 1.2`…) |
| 4 | **Chaque `###` fait 150 à 400 mots.** C'est la taille d'un chunk. |
| 5 | **Chaque document fait au minimum 900 mots** (hors tableaux) |
| 6 | **Tous les chiffres viennent du référentiel ci-dessus.** Aucune invention. |
| 7 | Chaque document a une section **« Questions fréquentes »** — 3 à 5 questions posées **comme un salarié les poserait vraiment** |
| 8 | Chaque document a une section **« Contacts et documents liés »** avec **au moins un renvoi vers un autre document du corpus** |
| 9 | Chaque document se termine par la **mention « Document synthétique »** |
| 10 | **Tout en français.** Pas d'anglicisme inutile. |

### Les renvois croisés imposés

| Document | Doit renvoyer vers |
|---|---|
| Congés payés | Convention collective · Arrêt maladie |
| Télétravail | Congés payés · Entretien annuel |
| Notes de frais | Mobilité interne |
| Arrêt maladie | Mutuelle · Congés payés |
| Onboarding | Mutuelle · Entretien annuel · Télétravail |
| Mutuelle | Onboarding · Arrêt maladie |
| Entretien annuel | Mobilité interne |
| Mobilité interne | Entretien annuel · Notes de frais |

*(Ces renvois créent des questions qui traversent plusieurs documents — c'est ce qui fera travailler le reranker au CDC 3.)*

---

## 📄 SPÉCIFICATION DES 10 DOCUMENTS

### 1. `corpus/procedure-teletravail.md` ⭐ LE PLUS IMPORTANT

**Titre :** `# Procédure Télétravail`

**Sections obligatoires :**

| Section | Contenu |
|---|---|
| `## 1. Champ d'application` | 1.1 Qui est éligible · 1.2 Les postes exclus · 1.3 L'ancienneté minimale (6 mois) |
| `## 2. Les modalités` | 2.1 **Le plafond : 2 jours par semaine maximum** ⭐ · 2.2 Les jours fixes et l'avenant au contrat · 2.3 L'indemnité (2,70 €/jour, 21,60 €/mois) · 2.4 L'équipement fourni |
| `## 3. La demande` | 3.1 La forme (écrite, au manager, 1 mois avant) · 3.2 L'instruction de la demande · 3.3 La période d'adaptation (3 mois) |
| `## 4. Le refus` ⭐⭐ | 4.1 **Les 6 motifs de refus recevables** (liste NUMÉROTÉE, reprise à l'identique du référentiel) · 4.2 **La forme du refus** : réponse **écrite et motivée**, sous **1 mois** · 4.3 **La voie de recours** : DRH, sous **15 jours** |
| `## 5. La réversibilité` | 5.1 À l'initiative du salarié · 5.2 À l'initiative de l'employeur · 5.3 Le préavis (1 mois) |
| `## 6. Questions fréquentes` | *« Puis-je télétravailler 3 jours par semaine ? »* → **NON, le plafond est de 2 jours** ⭐ · *« Puis-je poser un jour de congé un jour de télétravail ? »* · *« Que se passe-t-il si mon manager refuse ? »* |
| `## 7. Contacts et documents liés` | Renvois vers Congés payés et Entretien annuel |

> 🔴 **La section `## 4. Le refus` est la plus importante de tout le corpus.**
> C'est elle qui alimente la génération du `.docx` au CDC 9 :
> *« Rédige le courrier de refus de télétravail 3 jours/semaine pour M. Dupont. »*
>
> Le courrier devra **citer un motif** (le n°4 : demande excédant le plafond), **respecter la forme** (écrit motivé), et **mentionner la voie de recours** (DRH, 15 jours).
>
> **Écris cette section comme si un juriste allait la relire.**

**Longueur cible : 1 400 – 1 800 mots.**

---

### 2. `corpus/procedure-conges-payes.md` ⭐

**Titre :** `# Procédure Congés payés et RTT`

| Section | Contenu |
|---|---|
| `## 1. L'acquisition des congés` | 1.1 **25 jours ouvrés par an** ⭐ · 1.2 L'acquisition mensuelle (2,08 j/mois) · 1.3 La période de référence (1er juin → 31 mai) |
| `## 2. La pose des congés` | 2.1 Le délai de prévenance (1 mois / 15 jours) · 2.2 Le congé principal (12 à 20 jours consécutifs) · 2.3 La validation par le manager |
| `## 3. Le report et le fractionnement` | 3.1 Le report (5 jours max, jusqu'au 31 décembre) · 3.2 Les jours de fractionnement (+1 / +2) |
| `## 4. Les RTT` | 4.1 Qui y a droit (cadres au forfait 218 jours) · 4.2 **12 jours par an** · 4.3 La répartition (6 salarié / 6 employeur) |
| `## 5. Les congés exceptionnels` | 5.1 Les événements familiaux (mariage, naissance, décès — donne un barème court en jours) · 5.2 **Le congé sans solde** (3 mois max, accord écrit manager + DRH) |
| `## 6. Questions fréquentes` | *« Combien de jours de congés ai-je par an ? »* → **25 jours ouvrés** ⭐ · *« Puis-je reporter mes congés ? »* · *« Combien de RTT pour un cadre ? »* |
| `## 7. Contacts et documents liés` | Convention collective · Arrêt maladie |

**Longueur cible : 1 200 – 1 500 mots.**

---

### 3. `corpus/procedure-notes-de-frais.md`

**Titre :** `# Procédure Notes de frais et déplacements professionnels`

| Section | Contenu |
|---|---|
| `## 1. Les principes` | 1.1 Ce qui est remboursable · 1.2 Ce qui ne l'est jamais (**l'alcool**) · 1.3 L'autorisation préalable de déplacement |
| `## 2. Les plafonds` | 2.1 **Le tableau des plafonds** (repas 19,40 € · nuitées 75/110/150 €) 📊 · 2.2 Les frais kilométriques · 2.3 Les invitations client (60 €/convive) |
| `## 3. Les justificatifs` | 3.1 L'obligation au-delà de 10 € · 3.2 La conservation · 3.3 Le cas du taxi / VTC |
| `## 4. La soumission et le remboursement` | 4.1 **Le délai : avant le 5 du mois suivant** · 4.2 La validation (manager N+1, DRH au-delà de 500 €) · 4.3 Le remboursement (paie du mois suivant) |
| `## 5. Questions fréquentes` | *« Quel est le plafond pour un repas ? »* → **19,40 €** · *« Mon repas d'affaires avec du vin est-il remboursé ? »* → **l'alcool jamais** · *« Que se passe-t-il si je dépasse le délai ? »* |
| `## 6. Contacts et documents liés` | Mobilité interne |

📊 **Le tableau des plafonds est obligatoire.**

**Longueur cible : 1 100 – 1 400 mots.**

---

### 4. `corpus/procedure-arret-maladie.md`

**Titre :** `# Procédure Arrêt maladie et absence pour raison de santé`

| Section | Contenu |
|---|---|
| `## 1. Les obligations du salarié` | 1.1 Prévenir le manager **sous 24 h** · 1.2 Transmettre l'arrêt **sous 48 h** · 1.3 La prolongation |
| `## 2. L'indemnisation` | 2.1 Le délai de carence Sécurité sociale (**3 jours**) · 2.2 **Le barème de maintien de salaire** 📊 (le tableau du référentiel) · 2.3 La subrogation |
| `## 3. Le retour` | 3.1 **La visite de reprise (obligatoire après 30 jours)** · 3.2 Le retour progressif / mi-temps thérapeutique · 3.3 L'aménagement de poste |
| `## 4. Les cas particuliers` | 4.1 L'accident du travail · 4.2 L'arrêt pendant les congés payés · 4.3 L'arrêt de longue durée (> 90 jours) et la prévoyance |
| `## 5. Questions fréquentes` | *« Sous combien de temps dois-je envoyer mon arrêt ? »* → **48 h** · *« Mon salaire est-il maintenu ? »* → dépend de l'ancienneté · *« Suis-je obligé de passer une visite de reprise ? »* |
| `## 6. Contacts et documents liés` | Mutuelle · Congés payés |

📊 **Le barème de maintien de salaire est obligatoire, sous forme de tableau.**

**Longueur cible : 1 100 – 1 400 mots.**

---

### 5. `corpus/procedure-onboarding.md`

**Titre :** `# Parcours d'intégration d'un nouveau collaborateur`

| Section | Contenu |
|---|---|
| `## 1. Avant l'arrivée (J-7)` | 1.1 Le kit d'accueil · 1.2 La création des comptes (Microsoft Entra ID) · 1.3 La commande du matériel · 1.4 La désignation du parrain / de la marraine |
| `## 2. Le jour J` | 2.1 L'accueil (9h00) · 2.2 La remise du matériel et du badge · 2.3 Les documents à signer · 2.4 La visite du site |
| `## 3. Les 90 premiers jours` | 3.1 **J+7** : point manager · 3.2 **J+30** : entretien d'étonnement avec la DRH · 3.3 **J+90** : bilan de fin de période d'essai |
| `## 4. La période d'essai` | 4.1 **Cadres : 3 mois, renouvelable 1 fois** · 4.2 **Non-cadres : 2 mois, renouvelable 1 fois** · 4.3 La rupture de la période d'essai |
| `## 5. Les démarches du nouveau collaborateur` | 5.1 **L'adhésion à la mutuelle (sous 15 jours)** · 5.2 L'accès au télétravail (rappel : **6 mois d'ancienneté minimum**) · 5.3 La formation obligatoire sécurité (site pétrolier) |
| `## 6. Questions fréquentes` | *« Quand puis-je commencer à télétravailler ? »* → **après 6 mois** · *« Quelle est la durée de ma période d'essai ? »* · *« Quand dois-je choisir ma mutuelle ? »* |
| `## 7. Contacts et documents liés` | Mutuelle · Entretien annuel · Télétravail |

**Longueur cible : 1 200 – 1 500 mots.**

---

### 6. `corpus/guide-mutuelle.md` ⭐ LE GRAND TABLEAU

**Titre :** `# Guide de la complémentaire santé (mutuelle d'entreprise)`

| Section | Contenu |
|---|---|
| `## 1. Le principe` | 1.1 L'adhésion obligatoire · 1.2 Les cas de dispense · 1.3 La part employeur |
| `## 2. Les trois régimes` | 2.1 Le régime **Base** · 2.2 Le régime **Confort** · 2.3 Le régime **Famille+** |
| `## 3. Le comparatif détaillé` ⭐ | 3.1 **LE TABLEAU COMPLET des 10 garanties × 3 régimes** 📊 (reprendre EXACTEMENT le référentiel) · 3.2 Comment lire les pourcentages (BR = Base de Remboursement) |
| `## 4. Changer de régime` | 4.1 La période annuelle (**avant le 30 novembre**, effet au 1er janvier) · 4.2 Les changements hors période (événement familial) |
| `## 5. La prévoyance` | 5.1 Ce que couvre la prévoyance (invalidité, incapacité, décès) · 5.2 La différence avec la mutuelle |
| `## 6. Questions fréquentes` | *« Quel régime choisir si j'ai deux enfants ? »* · *« La médecine douce est-elle remboursée ? »* → **seulement en Confort et Famille+** · *« Puis-je refuser la mutuelle ? »* |
| `## 7. Contacts et documents liés` | Onboarding · Arrêt maladie |

📊 **La section 3.1 doit contenir le tableau COMPLET, à 4 colonnes et 10 lignes.**
C'est ce tableau qui alimentera la démo *« Compare les 3 régimes de mutuelle en tableau »* (CDC 9).
**Il ne doit JAMAIS être coupé par le chunker.**

**Longueur cible : 1 300 – 1 600 mots.**

---

### 7. `corpus/procedure-entretien-annuel.md`

**Titre :** `# Procédure Entretien annuel d'évaluation`

| Section | Contenu |
|---|---|
| `## 1. Le calendrier` | 1.1 **La campagne : 1er février → 31 mars** · 1.2 La convocation · 1.3 La préparation (auto-évaluation **7 jours avant**) |
| `## 2. Le déroulé` | 2.1 Le bilan de l'année écoulée · 2.2 La fixation des objectifs · 2.3 Les besoins de formation · 2.4 Les souhaits d'évolution |
| `## 3. Le compte rendu` | 3.1 La signature des deux parties · 3.2 **La contestation (sous 15 jours, auprès du N+2)** · 3.3 La conservation au dossier |
| `## 4. L'entretien professionnel` | 4.1 La différence avec l'entretien annuel · 4.2 **Tous les 2 ans** · 4.3 **Le bilan obligatoire à 6 ans** |
| `## 5. Questions fréquentes` | *« Quand a lieu mon entretien annuel ? »* → **entre février et mars** · *« Puis-je contester mon évaluation ? »* → **oui, sous 15 jours** · *« Quelle différence entre entretien annuel et entretien professionnel ? »* |
| `## 6. Contacts et documents liés` | Mobilité interne |

**Longueur cible : 1 000 – 1 300 mots.**

---

### 8. `corpus/procedure-mobilite-interne.md`

**Titre :** `# Procédure Mobilité interne`

| Section | Contenu |
|---|---|
| `## 1. Les conditions d'éligibilité` | 1.1 **18 mois d'ancienneté minimum dans le poste** · 1.2 L'évaluation annuelle satisfaisante · 1.3 ⚠️ **Le périmètre : France métropolitaine uniquement** *(dire explicitement que la mobilité internationale n'est pas traitée ici)* |
| `## 2. La bourse à l'emploi interne` | 2.1 La publication des postes · 2.2 **La priorité interne (15 jours)** · 2.3 La candidature |
| `## 3. Le processus de sélection` | 3.1 L'entretien avec le manager d'accueil · 3.2 **L'information du manager actuel (après le 1er entretien, jamais avant)** · 3.3 La décision |
| `## 4. Le transfert` | 4.1 **Le préavis (2 mois maximum)** · 4.2 La passation · 4.3 L'intégration dans la nouvelle équipe |
| `## 5. La mobilité géographique` | 5.1 **La prime de 3 000 €** · 5.2 **La prise en charge du déménagement (3 devis)** · 5.3 L'aide au logement |
| `## 6. Questions fréquentes` | *« Depuis combien de temps dois-je être en poste pour candidater ? »* → **18 mois** · *« Mon manager sera-t-il prévenu ? »* → **après le premier entretien** · *« Y a-t-il une prime si je déménage ? »* → **3 000 €** |
| `## 7. Contacts et documents liés` | Entretien annuel · Notes de frais |

**Longueur cible : 1 100 – 1 400 mots.**

---

### 9. `corpus/CONFIDENTIEL-grille-remuneration-2026.md` 🔒

**Titre :** `# Grille de rémunération 2026 — Document confidentiel`

**En première ligne du corps, un bandeau :**

```markdown
> 🔒 **DOCUMENT CONFIDENTIEL — DIFFUSION RESTREINTE**
> Accès réservé au service Ressources Humaines et à la Direction.
> Toute diffusion non autorisée constitue une faute disciplinaire.
```

| Section | Contenu |
|---|---|
| `## 1. Le principe de la grille` | 1.1 Les niveaux et coefficients · 1.2 L'articulation avec les minima conventionnels (IDCC 1388) · 1.3 La révision annuelle (1er janvier) |
| `## 2. La grille par niveau` ⭐ | 2.1 **LE TABLEAU des 8 niveaux** 📊 (minimum / médian / maximum — reprendre EXACTEMENT le référentiel) · 2.2 Commentaire par famille de métiers |
| `## 3. La part variable` | 3.1 Cadres niveaux 5-6 : **jusqu'à 10 %** · 3.2 Cadres supérieurs niveaux 7-8 : **jusqu'à 20 %** · 3.3 Les critères de déclenchement |
| `## 4. Les primes` | 4.1 **La prime d'ancienneté** (+3 % / +6 % / +9 % / +12 %) 📊 · 4.2 La prime d'astreinte · 4.3 La prime de sujétion (travail posté) |
| `## 5. La politique d'embauche` | 5.1 **La fourchette : entre le minimum et le médian** · 5.2 **Au-delà du médian : validation DRH obligatoire** · 5.3 Le budget d'augmentation 2026 (**2,3 %**, dont **0,6 %** individuel) |
| `## 6. Contacts` | DRH uniquement |

> ⭐ **Le niveau 6 « Cadre confirmé » (54 000 / 62 000 / 71 000 €) est LE chiffre de la démonstration ACL.**

**Longueur cible : 900 – 1 200 mots.**

---

### 10. `corpus/CONFIDENTIEL-procedure-disciplinaire.md` 🔒

**Titre :** `# Procédure disciplinaire — Document confidentiel`

**Même bandeau confidentiel en première ligne.**

| Section | Contenu |
|---|---|
| `## 1. Les principes` | 1.1 La proportionnalité · 1.2 **La prescription des faits (2 mois)** · 1.3 Le principe du contradictoire |
| `## 2. L'échelle des sanctions` ⭐ | 2.1 **LE TABLEAU des 7 niveaux de sanction** 📊 (reprendre EXACTEMENT le référentiel) · 2.2 La mise à pied conservatoire (distincte de la sanction) |
| `## 3. La procédure` | 3.1 **La convocation (LRAR, 5 jours ouvrables minimum)** · 3.2 L'entretien préalable et l'assistance du salarié · 3.3 **La notification (entre 2 jours ouvrables et 1 mois)** |
| `## 4. Le barème indicatif par type de faute` ⭐ | 4.1 **LE TABLEAU des fautes et sanctions** 📊 (reprendre EXACTEMENT le référentiel, **y compris les fautes liées à la sécurité sur site pétrolier et à la conduite de véhicule-citerne**) |
| `## 5. Les recours` | 5.1 Le recours interne · 5.2 Le conseil de prud'hommes · 5.3 La conservation au dossier |
| `## 6. Contacts` | DRH uniquement |

**Longueur cible : 900 – 1 200 mots.**

---

## 📋 `corpus/manifest.json` — LE CONTRAT

> ⚠️ **`type`, `source` et `sensibilite` DOIVENT respecter les contraintes `CHECK` de `db/init.sql`.**
> Toute autre valeur sera rejetée par Postgres au CDC 2.

```json
{
  "version": 1,
  "genere_le": "2026-07-14",
  "description": "Corpus de test du POC RAG RH. Corpus PUBLIC et SYNTHETIQUE uniquement. Aucun document reel de l'entreprise.",

  "groupes": {
    "grp-tous": "Tous les collaborateurs",
    "grp-rh": "Service Ressources Humaines - acces aux documents confidentiels",
    "grp-admin": "Administration technique"
  },

  "documents": [
    {
      "chemin": "corpus/convention-collective-petrole-1388.pdf",
      "titre": "Convention collective nationale de l'industrie du petrole (IDCC 1388)",
      "type": "pdf",
      "source": "public",
      "service": "rh",
      "sensibilite": "public",
      "allowed_groups": ["grp-tous"],
      "url": "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635267",
      "description": "Texte de base du 3 septembre 1985, etendu par arrete du 31 juillet 1986. Brochure JO 3001."
    },
    {
      "chemin": "corpus/procedure-teletravail.md",
      "titre": "Procedure Teletravail",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "Plafond de 2 jours par semaine, motifs de refus, voie de recours."
    },
    {
      "chemin": "corpus/procedure-conges-payes.md",
      "titre": "Procedure Conges payes et RTT",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "25 jours ouvres, RTT, report, fractionnement, conges exceptionnels."
    },
    {
      "chemin": "corpus/procedure-notes-de-frais.md",
      "titre": "Procedure Notes de frais et deplacements professionnels",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "Plafonds, justificatifs, delais de soumission, validation."
    },
    {
      "chemin": "corpus/procedure-arret-maladie.md",
      "titre": "Procedure Arret maladie et absence pour raison de sante",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "Delais de declaration, bareme de maintien de salaire, visite de reprise."
    },
    {
      "chemin": "corpus/procedure-onboarding.md",
      "titre": "Parcours d'integration d'un nouveau collaborateur",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "J-7, J0, J+7, J+30, J+90. Periode d'essai."
    },
    {
      "chemin": "corpus/guide-mutuelle.md",
      "titre": "Guide de la complementaire sante (mutuelle d'entreprise)",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "Trois regimes Base / Confort / Famille+. Tableau comparatif complet."
    },
    {
      "chemin": "corpus/procedure-entretien-annuel.md",
      "titre": "Procedure Entretien annuel d'evaluation",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "Campagne fevrier-mars, compte rendu, contestation, entretien professionnel."
    },
    {
      "chemin": "corpus/procedure-mobilite-interne.md",
      "titre": "Procedure Mobilite interne",
      "type": "md",
      "source": "synthetique",
      "service": "rh",
      "sensibilite": "interne",
      "allowed_groups": ["grp-tous"],
      "description": "18 mois d'anciennete, bourse a l'emploi, prime de mobilite. France metropolitaine uniquement."
    },
    {
      "chemin": "corpus/CONFIDENTIEL-grille-remuneration-2026.md",
      "titre": "Grille de remuneration 2026",
      "type": "md",
      "source": "fictif",
      "service": "rh",
      "sensibilite": "confidentiel",
      "allowed_groups": ["grp-rh"],
      "description": "DOCUMENT FICTIF. 8 niveaux, part variable, primes. Sert a demontrer le filtrage par droits."
    },
    {
      "chemin": "corpus/CONFIDENTIEL-procedure-disciplinaire.md",
      "titre": "Procedure disciplinaire",
      "type": "md",
      "source": "fictif",
      "service": "rh",
      "sensibilite": "confidentiel",
      "allowed_groups": ["grp-rh"],
      "description": "DOCUMENT FICTIF. Echelle des sanctions, procedure, bareme par faute. Sert a demontrer le filtrage par droits."
    }
  ],

  "trous_connus": [
    "Conge proche aidant",
    "Mobilite internationale et expatriation",
    "Reforme du conge paternite 2026",
    "Teletravail depuis l'etranger",
    "Compte epargne temps (CET)",
    "Conge sabbatique",
    "Participation et interessement"
  ]
}
```

> **Note :** le JSON est volontairement **sans accents** (ASCII) pour éviter tout problème d'encodage sous Windows.
> Les **fichiers markdown**, eux, sont en **français normal avec accents**, encodés en **UTF-8**.

---

## 🔍 `scripts/valider_corpus.py`

**Contrainte forte : ce script n'utilise QUE la bibliothèque standard Python.**
Pas de pydantic, pas de dépendance. Il doit tourner sur la machine de l'utilisateur, sous Windows, sans venv ni Docker :

```powershell
python scripts\valider_corpus.py
```

### Ce qu'il doit vérifier

| # | Contrôle | Gravité |
|---|---|---|
| 1 | `corpus/manifest.json` existe et est un JSON valide | **ERREUR** |
| 2 | Les clés `version`, `documents`, `trous_connus` sont présentes | **ERREUR** |
| 3 | Chaque `chemin` déclaré existe sur le disque | **ERREUR** *(sauf le PDF → AVERTISSEMENT)* |
| 4 | `type` ∈ `{pdf, md}` **et** cohérent avec l'extension du fichier | **ERREUR** |
| 5 | `source` ∈ `{public, synthetique, fictif}` | **ERREUR** |
| 6 | `sensibilite` ∈ `{public, interne, confidentiel}` | **ERREUR** |
| 7 | `allowed_groups` non vide et ⊆ `{grp-tous, grp-rh, grp-admin}` | **ERREUR** |
| 8 | 🔒 **`sensibilite == "confidentiel"` ET `grp-tous` dans `allowed_groups`** | **ERREUR FATALE** |
| 9 | Chaque `.md` commence par **exactement un** titre `#` | **ERREUR** |
| 10 | Chaque `.md` a **au moins 4** titres `##` | **ERREUR** |
| 11 | Chaque `.md` fait **au moins 900 mots** | **ERREUR** |
| 12 | Chaque `.md` contient la mention **« Document synthétique »** ou le bandeau **« DOCUMENT CONFIDENTIEL »** | AVERTISSEMENT |
| 13 | Il y a **exactement 2** documents `confidentiel`, et **tous deux** en `["grp-rh"]` | **ERREUR** |
| 14 | Aucun fichier `.md` présent dans `corpus/` **sans être déclaré** au manifest | AVERTISSEMENT |

### Ce qu'il doit afficher

Un tableau récapitulatif, puis un verdict.

```
=============================================================================
  VALIDATION DU CORPUS - RAG DYNEFF
=============================================================================

  FICHIER                                  TYPE  SENSIBILITE   GROUPES     MOTS   ##  ~CHUNKS
  ---------------------------------------------------------------------------------------------
  convention-collective-petrole-1388.pdf   pdf   public        grp-tous       -    -     ~200
  procedure-teletravail.md                 md    interne       grp-tous    1612    7       11
  procedure-conges-payes.md                md    interne       grp-tous    1344    7        9
  procedure-notes-de-frais.md              md    interne       grp-tous    1208    6        8
  procedure-arret-maladie.md               md    interne       grp-tous    1255    6        8
  procedure-onboarding.md                  md    interne       grp-tous    1390    7        9
  guide-mutuelle.md                        md    interne       grp-tous    1470    7       10
  procedure-entretien-annuel.md            md    interne       grp-tous    1102    6        7
  procedure-mobilite-interne.md            md    interne       grp-tous    1233    7        8
  CONFIDENTIEL-grille-remuneration-2026.md md    confidentiel  grp-rh      1024    6        7
  CONFIDENTIEL-procedure-disciplinaire.md  md    confidentiel  grp-rh       987    6        7

  ---------------------------------------------------------------------------------------------
  11 documents declares
   9 accessibles a tous (grp-tous)
   2 CONFIDENTIELS (grp-rh uniquement)
  ~284 chunks estimes
   7 trous connus declares

  CONTROLE DE SECURITE
  --------------------
  [OK] Aucun document confidentiel accessible a grp-tous
  [OK] Les 2 documents confidentiels sont bien restreints a grp-rh

  =============================================================================
  [OK] CORPUS VALIDE
  =============================================================================
```

En cas de problème :

```
  [ERREUR] corpus/guide-mutuelle.md : 640 mots (minimum 900)
  [ERREUR] CONFIDENTIEL-grille-remuneration-2026.md : accessible a grp-tous !

  =============================================================================
  [ECHEC] CORPUS INVALIDE - 2 erreur(s)
  =============================================================================
```

### Détails d'implémentation

```python
#!/usr/bin/env python3
"""Valide le corpus et son manifest AVANT l'ingestion (CDC 2).

Bibliotheque standard UNIQUEMENT : ce script doit pouvoir tourner
sur n'importe quelle machine, sans venv, sans Docker, sans dependance.

Usage :
    python scripts/valider_corpus.py

Codes de sortie :
    0 = corpus valide
    1 = corpus invalide
"""

import json
import re
import sys
from pathlib import Path

# Compatibilite console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent
MANIFEST = RACINE / "corpus" / "manifest.json"

TYPES_VALIDES        = {"pdf", "md"}
SOURCES_VALIDES      = {"public", "synthetique", "fictif"}
SENSIBILITES_VALIDES = {"public", "interne", "confidentiel"}
GROUPES_VALIDES      = {"grp-tous", "grp-rh", "grp-admin"}

MOTS_MINIMUM   = 900
TITRES_H2_MIN  = 4
MOTS_PAR_CHUNK = 150      # estimation grossiere : ~1 chunk par ### de 150 mots

# ... (implementation)
```

**Fonctions attendues :**

| Fonction | Rôle |
|---|---|
| `charger_manifest() -> dict` | Lit et parse le JSON. Erreur claire si absent ou malformé. |
| `compter_mots(texte: str) -> int` | Compte les mots hors blocs de code et hors tableaux |
| `compter_titres(texte: str, niveau: int) -> int` | Compte les `#`, `##` ou `###` en début de ligne |
| `valider_document(doc: dict, erreurs: list, avertissements: list) -> dict` | Valide un document, renvoie ses statistiques |
| `controle_securite(documents: list, erreurs: list) -> None` | **Le contrôle ACL — le plus important** |
| `fichiers_orphelins(documents: list) -> list[str]` | Les `.md` de `corpus/` non déclarés au manifest |
| `afficher_rapport(...) -> None` | Le tableau + le verdict |
| `main() -> int` | Orchestration, renvoie le code de sortie |

**Le contrôle de sécurité est le cœur du script. Écris-le explicitement :**

```python
def controle_securite(documents: list, erreurs: list) -> None:
    """Le controle qui compte : aucun document confidentiel ne doit
    etre accessible a grp-tous.

    Si ce controle passe, la demo ACL du CDC 6 fonctionnera.
    S'il echoue, la grille des salaires est publique. Le projet meurt.
    """
    confidentiels = [d for d in documents if d.get("sensibilite") == "confidentiel"]

    for doc in confidentiels:
        groupes = doc.get("allowed_groups", [])
        if "grp-tous" in groupes:
            erreurs.append(
                f"FATAL - {doc['chemin']} est CONFIDENTIEL mais accessible a grp-tous !"
            )
        if groupes != ["grp-rh"]:
            erreurs.append(
                f"{doc['chemin']} : un document confidentiel doit etre restreint "
                f"a ['grp-rh'], trouve {groupes}"
            )

    if len(confidentiels) != 2:
        erreurs.append(
            f"Attendu : 2 documents confidentiels. Trouve : {len(confidentiels)}"
        )
```

---

## Contraintes impératives

### ❌ INTERDIT

| Interdit | Pourquoi |
|---|---|
| **Inventer un chiffre** qui n'est pas dans le référentiel | Deux documents incohérents = éval impossible à interpréter |
| **Écrire un document plat** (sans `##` / `###`) | Le chunking découpe sur les titres. Pas de titres = pas de chunks. |
| **Utiliser un vrai document RH d'entreprise** | Règle de sécurité n°1 du projet. Non négociable. |
| **Mettre `grp-tous` sur un document confidentiel** | La démo ACL meurt. Le script de validation le bloque. |
| **Ajouter des dépendances au script de validation** | Bibliothèque standard uniquement. Il doit tourner partout. |
| **Ajouter un README ou des notes dans `corpus/`** | Tout `.md` non déclaré au manifest est un fichier orphelin |
| **Écrire du code applicatif** | Ce CDC ne produit que du contenu + un script de validation |

### ✅ OBLIGATOIRE

1. **Tous les chiffres viennent du référentiel.** Relis-le avant d'écrire chaque document.
2. **Structure : `#` > `##` (≥4) > `###` (2 à 4 par `##`, 150–400 mots chacun).**
3. **Les 5 tableaux imposés** : mutuelle, grille de rémunération, notes de frais, maintien de salaire, sanctions.
4. **Une section « Questions fréquentes »** dans chaque document — les questions posées **comme un salarié les poserait**.
5. **Les renvois croisés** entre documents (voir le tableau plus haut).
6. **La mention « Document synthétique »** en pied de chaque procédure.
7. **Le bandeau « DOCUMENT CONFIDENTIEL »** en tête des deux documents restreints.
8. **UTF-8** pour les `.md` (avec accents). **ASCII** pour le `manifest.json`.
9. **Français** partout.

---

## Definition of Done

### Étape 1 — L'utilisateur dépose le PDF

```
corpus/convention-collective-petrole-1388.pdf
```
*(Téléchargé depuis Légifrance — https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635267)*

### Étape 2 — La commande

```bash
python scripts/valider_corpus.py
```

*(Sous Windows : `python scripts\valider_corpus.py`)*

### Étape 3 — Le résultat attendu EXACTEMENT

```
  =============================================================================
  [OK] CORPUS VALIDE
  =============================================================================
```

**Avec, dans le tableau :**

| # | Vérification | Attendu |
|---|---|---|
| 1 | Nombre de documents déclarés | **11** |
| 2 | Documents accessibles à `grp-tous` | **9** |
| 3 | Documents **confidentiels** (`grp-rh` seul) | **2** |
| 4 | Trous connus déclarés | **7** |
| 5 | Chaque `.md` | **≥ 900 mots, ≥ 4 titres `##`** |
| 6 | Contrôle de sécurité | **[OK] Aucun document confidentiel accessible à grp-tous** |
| 7 | Code de sortie | **0** |

### Étape 4 — La vérification manuelle (2 minutes, indispensable)

Ouvre `corpus/procedure-teletravail.md` et vérifie que la section `## 4. Le refus` contient :

- [ ] **« 2 jours par semaine »** comme plafond explicite
- [ ] **Les 6 motifs de refus**, en liste numérotée
- [ ] **« réponse écrite et motivée sous 1 mois »**
- [ ] **« recours auprès de la DRH sous 15 jours »**

> **Si ces 4 éléments ne sont pas là, le moment n°3 de la démo ne tiendra pas.**
> **Ce document est le plus important du corpus. Relis-le.**

### Étape 5 — Le contrôle de sécurité manuel

```bash
python -c "import json; m=json.load(open('corpus/manifest.json')); print([d['chemin'] for d in m['documents'] if 'grp-tous' in d['allowed_groups'] and d['sensibilite']=='confidentiel'])"
```

**Résultat attendu : `[]` (liste vide).**

**Si cette commande renvoie quoi que ce soit, la grille des salaires est publique. On s'arrête tout.**

```
═══════════════════════════════════════════════════════════════
                   FIN DE LA PARTIE B
═══════════════════════════════════════════════════════════════
```

---
---

# ANNEXE — Le mode d'emploi après Cursor

## Ce que tu fais, toi

### 1. Télécharger la convention collective

| | |
|---|---|
| **Où** | https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635267 |
| **Quoi** | Convention collective nationale de l'industrie du pétrole — **IDCC 1388** — Brochure **3001** |
| **Où la mettre** | `corpus/convention-collective-petrole-1388.pdf` |

*Alternative si Légifrance est capricieux : https://code.travail.gouv.fr/convention-collective/1388-industrie-du-petrole*

### 2. Lancer Cursor sur la Partie B

Il va écrire 10 fichiers markdown + le manifest + le script.

### 3. Valider

```powershell
python scripts\valider_corpus.py
```

Tu dois voir `[OK] CORPUS VALIDE`.

### 4. LIRE `procedure-teletravail.md` 🔴

**Ne saute pas cette étape.** C'est le document qui porte le moment n°3 de la démo.

Vérifie de tes yeux, dans la section `## 4. Le refus` :

| ✅ | À vérifier |
|---|---|
| ☐ | Le plafond de **2 jours/semaine** est écrit explicitement |
| ☐ | Les **6 motifs de refus** sont là, numérotés |
| ☐ | La **réponse écrite motivée sous 1 mois** est mentionnée |
| ☐ | La **voie de recours (DRH, 15 jours)** est mentionnée |

Si un seul manque → tu le rajoutes à la main. **Ça vaut le coup.**

### 5. Committer

```bash
git add -A
git commit -m "CDC 1 — corpus de test (11 documents + manifest + validateur)"
```

Le corpus est **public et synthétique** : il peut aller sur GitHub sans aucun problème.
**C'est même une preuve** — n'importe qui peut vérifier qu'aucun document Dyneff n'y figure.

---

## Si ça casse

| Symptôme | Cause | Solution |
|---|---|---|
| `[ERREUR] ... : 640 mots (minimum 900)` | Cursor a été paresseux | Redemande-lui d'étoffer ce document précis |
| `[ERREUR] ... : moins de 4 titres ##` | Document plat | Redemande la structure `##` / `###` |
| `[AVERTISSEMENT] fichier orphelin : corpus/notes.md` | Un fichier traîne | Supprime-le ou déclare-le au manifest |
| `[FATAL] ... CONFIDENTIEL mais accessible a grp-tous` | 🔴 **Le manifest est faux** | **Corrige immédiatement.** `allowed_groups: ["grp-rh"]` |
| Le PDF n'est pas trouvé | Pas encore téléchargé | C'est un **avertissement**, pas une erreur. Le reste du corpus est valide. |
| `UnicodeEncodeError` sous Windows | Encodage console | Le script fait déjà `sys.stdout.reconfigure(encoding="utf-8")` |

---

## Récapitulatif — ce que le CDC 1 met en place

| Élément | Ce que ça débloque |
|---|---|
| **11 documents** | Le CDC 2 (ingestion) a de quoi manger |
| **La structure `#` / `##` / `###`** | Le chunking sur les titres (Piège n°3) |
| **Les 5 tableaux** | Le test du pire cas du chunker |
| **La numérotation des articles (IDCC 1388)** | Le test de la moitié « mots exacts » de la recherche hybride (CDC 3) |
| **2 documents `grp-rh`** | 🔒 **La démo ACL** (moment n°2) |
| **La section « Le refus » du télétravail** | 💥 **La génération du `.docx`** (moment n°3) |
| **Les 7 trous connus** | 🌐 **La recherche web** (moment n°4) + 📊 **le dashboard** (moment n°5) + le **« je ne sais pas »** de l'éval |
| **Le référentiel de constantes** | **L'éval du CDC 5 est interprétable** — pas de contradiction interne |
| **Le script de validation** | Un contrôle ACL **avant** que le premier chunk n'existe |

---

## Prochaine étape

**CDC 2 — L'ingestion** (parsing + chunking + embeddings).

> 🔑 **C'est là qu'il te faudra ta clé OpenAI.** C'est le premier appel à l'API.
> Budget de l'ingestion complète : **moins de 0,50 €.**

Reviens avec la sortie de `python scripts/valider_corpus.py`.
