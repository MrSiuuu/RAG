# CDC 6→12 — LA COUCHE ENTREPRISE (session finale avant la démo)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Transformer le moteur RAG déjà fini en un **produit démontrable** : un service dépose son doc et le chatbot est à jour tout seul, on se connecte avec un vrai login, chaque service a son corpus cloisonné, l'admin voit les stats, et quand l'IA ne sait pas elle renvoie vers le bon service.

## 💡 Pourquoi c'est important (lien direct avec Rémi)

Le call a produit **deux exigences** de Rémi que ton moteur ne couvre pas encore :

1. **« Les services déposent leurs fichiers, un robot vectorise tout seul, le chatbot est à jour sans qu'on y touche. »** → c'est le **Module 1** (self-service ingestion). Ton endpoint EST ce que le robot n8n appellera. Tu montres un fichier déposé → 30 s après il répond dessus. C'est le pilier n°2 de Rémi, en vrai.
2. **« Rien ne sort, même pas une partie. »** → tes ACL le prouvent déjà, mais il faut un **vrai login** pour que la démo Marie/Paul soit crédible (Module 2), et le **bouton contacter le service** (Module 4) répond à la peur RH « on va nous remplacer ».

## 📚 Les 3 concepts nouveaux

| Concept | L'image | Où |
|---|---|---|
| **Upload multipart** | Au lieu de lancer une commande dans le terminal, l'utilisateur glisse un fichier dans la page. Le serveur le reçoit, le découpe, le vectorise, l'insère. | Module 1 |
| **JWT (jeton)** | Un bracelet de festival. Tu te connectes une fois (email + mdp), on te donne un bracelet signé qui dit « je suis Marie, groupes RH ». À chaque question tu montres le bracelet, on lit tes groupes dessus. Impossible à falsifier (signé avec `JWT_SECRET`). | Module 2 |
| **Seed d'usage** | Ton dashboard serait **vide** : l'éval n'écrit pas dans la table `messages`. Le seed la remplit avec un mois d'usage réaliste pour que les graphes aient quelque chose à montrer. | Module 3 |

## 🧩 Où ça s'insère (état actuel réel, confirmé par Cursor)

- Backend **fini** : ingestion, retrieval hybride + ACL, génération streaming, .docx, recherche web. Routes : `/health`, `/search`, `/api/chat`, `/api/files/{id}`.
- Dossiers **vides à remplir** : `app/security/` (auth) et `app/chat/` (mémoire, pas dans ce CDC).
- La BDD a **déjà** toutes les tables : `users` (avec `role`, `groupes`, `mot_de_passe` bcrypt), `messages`, `conversations`, `audit_log`, `feedback`, `fichiers`. Users seedés : Marie (grp-rh + grp-tous), Paul (grp-tous), admin. Mdp `demo1234`.
- `.env` a déjà `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`.
- Front `web/` : chat qui stream, `user-selector` Marie/Paul, cartes sources, download .docx. Pas de page login ni admin.
- Ingestion = **CLI uniquement** (`python -m app.ingest`), et elle **TRUNCATE** toute la table (ré-indexe tout). Il faut une version **incrémentale** pour la self-service.

## ⚠️ Les pièges de ce CDC (lis ça deux fois)

1. 🔴 **INTERDIT de faire `docker compose down -v`.** Ça effacerait ton corpus indexé → tu devrais tout ré-ingérer (coût OpenAI + galère SSL). Donc **aucune modif de `init.sql`** ce soir. La seule table nouvelle (`demandes`) se crée via `CREATE TABLE IF NOT EXISTS` au démarrage de l'API. Aucun `ALTER` sur les tables existantes n'est nécessaire.
2. 🔴 **Le dashboard sera vide sans le seed.** Tu lances `scripts/seed_usage.py` sinon les cartes affichent 0. En démo tu dis : *« usage simulé pour l'illustration, la mécanique de calcul est réelle. »*
3. 🔴 **L'auth peut bloquer toute la démo.** Si le login foire à 23 h, tu ne rentres plus dans l'app. Garde-fou intégré : les **boutons démo** (Marie / Paul / Admin) sur la page login font un vrai `/auth/login` en un clic. Le sélecteur devient de la vraie auth, pas un mode bidon. Tu ne peux pas te retrouver bloqué dehors.
4. 🔴 **La recherche web contredit « rien ne sort ».** Elle n'est PAS dans ce CDC (déjà codée). Rappel pour demain : off par défaut, toggle manuel, **jamais** sur du confidentiel, tu la montres en dernier.
5. 🔴 **Ne casse pas `/api/chat`.** Il marche. On ajoute l'auth par-dessus sans réécrire le pipeline.

## 🗣️ Ce que tu pourras dire en réunion grâce à ça

> *« Un service dépose son document — ici, regardez — et 30 secondes après le chatbot répond dessus, cloisonné aux droits du service. C'est exactement le robot de mise à jour automatique que tu décrivais, Rémi. La brique difficile — droits, qualité, citations, mise à jour autonome — est résolue. »*

> *« Chaque service a son corpus : RH, CSE, HSE. Un utilisateur ne voit que le sien. Et quand l'IA ne sait pas, elle ne bricole pas : elle transmet la question au bon service. L'IA filtre, elle ne remplace pas. »*

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

RAG interne pour le service RH de Dyneff. Stack : FastAPI + Postgres 16/pgvector + OpenAI (SDK) + Next.js 15 (dossier `web/`). Le moteur RAG est terminé (ingestion, retrieval hybride + ACL en SQL, génération streaming SSE, génération .docx, recherche web). Cette session ajoute la couche entreprise : self-service ingestion multi-service, authentification complète, dashboard admin, bouton de transmission au service, et polish de l'interface.

## État actuel du code (ne pas casser)

```
app/
  main.py            # /health, /health/db
  config.py          # Settings (get_settings), a déjà JWT_SECRET/JWT_ALGORITHM/JWT_EXPIRE_MINUTES
  db.py              # get_db(), db_est_joignable()
  api/chat.py        # POST /api/chat (SSE : status, sources, token, done)
  api/search.py      # POST /search (debug)
  api/files.py       # GET /api/files/{file_id}
  ingest/            # load, chunk, embed, index (index.py TRUNCATE tout), __main__ (CLI)
  llm/               # generate (OpenAI streaming), prompts, contexte, citations
  retrieval/         # vector, fulltext, fusion (rrf), rerank, pipeline, acl
  files/             # intent, generate_doc, docx, store
  tools/web.py       # Tavily
  security/__init__.py   # VIDE — à remplir (Module 2)
  chat/__init__.py       # VIDE — hors scope
db/init.sql          # 8 tables déjà créées (NE PAS TOUCHER)
web/
  app/page.tsx, layout.tsx, globals.css
  components/chat.tsx, chat-message.tsx, sources.tsx, file-download.tsx, user-selector.tsx
  lib/use-rag-chat.ts, types.ts, utils.ts
```

Modèles (dans `.env`, ne pas changer) : `LLM_MODEL=gpt-5.6-terra`, `LLM_MODEL_FAST=gpt-5.6-luna`, `EMBEDDING_MODEL=text-embedding-3-large`, `EMBEDDING_DIM=1536`.

Tables existantes utiles :
- `users(id, email, nom, mot_de_passe, groupes TEXT[], role)` — seed Marie (`{grp-tous,grp-rh}`), Paul (`{grp-tous}`), admin ; mdp bcrypt de `demo1234`.
- `documents(id, chemin, titre, type, source, sensibilite, allowed_groups TEXT[], nb_chunks, indexe_le)`.
- `chunks(id, document_id, type, parent_id, ordre, breadcrumb, contenu, contenu_indexe, page, nb_tokens, embedding vector(1536), embedding_model, embedding_dim, allowed_groups TEXT[], tsv)`.
- `messages(id, conversation_id, role, contenu, question_reecrite, chunk_ids, sources JSONB, a_repondu BOOL, web_active, tokens_in, tokens_out, latence_ms, cout, modele, cree_le)`.
- `conversations(id, user_id, titre, resume, cree_le)`.
- `audit_log`, `feedback`, `fichiers`.

## CONTRAINTES IMPÉRATIVES GLOBALES

- 🔴 **NE JAMAIS proposer ni exécuter `docker compose down -v`.** Le volume `pgdata` contient le corpus indexé.
- 🔴 **NE PAS modifier `db/init.sql`.** Toute table nouvelle se crée via `CREATE TABLE IF NOT EXISTS` exécuté au démarrage de l'API (voir Module 4). Aucun `ALTER` sur les tables existantes.
- 🔴 **Garder OpenAI** partout tel quel. Ne pas introduire Nomic/Ollama dans ce CDC.
- 🔴 **INTERDIT** : LangChain, LlamaIndex, Ragas, Qdrant, `useChat` de Vercel, Alembic, Redis.
- 🔴 **Ne pas réécrire le pipeline RAG.** On ajoute l'auth par-dessus `/api/chat`.
- Le même modèle d'embedding et la même dimension (`text-embedding-3-large`, 1536) à l'indexation self-service qu'au reste. Stocker `embedding_model` et `embedding_dim` sur chaque chunk.
- Code commenté en français, style existant conservé.

---

## MODULE 1 — Self-service ingestion + multi-service (RH / CSE / HSE / …)

### But
Un utilisateur connecté dépose un fichier `.md` ou `.pdf` via l'UI, choisit son service, et le document est chuncké + vectorisé + indexé automatiquement, avec les ACL du service. Sans CLI. Ré-indexation incrémentale (ne truncate pas tout).

### Fichiers à créer / modifier
- **créer** `app/services.py` — la table des services → groupes.
- **modifier** `app/ingest/index.py` — ajouter `indexer_un_document(...)` (insert d'UN doc, sans TRUNCATE).
- **créer** `app/api/admin.py` — routers admin (ce module + Module 3). Ici : `POST /api/admin/ingest`.
- **modifier** `app/main.py` — inclure le router admin.
- **créer** `web/app/admin/page.tsx` — page admin avec un onglet « Ajouter un document » (le dashboard du Module 3 ira dans le second onglet).
- **créer** `web/components/upload-doc.tsx` — formulaire d'upload (fichier + sélecteur de service).

### Spécifications

**`app/services.py`**
```python
SERVICES = {
    "rh":        {"label": "Ressources Humaines", "groups": ["grp-rh"]},
    "cse":       {"label": "CSE",                 "groups": ["grp-cse"]},
    "hse":       {"label": "HSE",                 "groups": ["grp-hse"]},
    "juridique": {"label": "Juridique",           "groups": ["grp-juridique"]},
    "public":    {"label": "Public (tous)",       "groups": ["grp-tous"]},
}
def groupes_du_service(service: str) -> list[str]  # KeyError → 400
```

**`app/ingest/index.py` → `indexer_un_document(...)`**
```python
def indexer_un_document(
    doc_titre: str,
    chemin: str,
    type_doc: str,            # "md" | "pdf"
    source: str,
    sensibilite: str,         # "interne" par défaut
    allowed_groups: list[str],
    chunks_parents: list,     # objets ChunkPret déjà produits
    chunks_enfants: list,
    settings,
) -> dict:                    # {"document_id": int, "nb_parents": int, "nb_enfants": int}
```
Logique (réutiliser EXACTEMENT le format d'insertion de la fonction `indexer` existante — littéral vecteur, `tsv`, colonnes) mais :
1. `UPSERT` dans `documents` sur `chemin` (ON CONFLICT (chemin) DO UPDATE) → récupérer `document_id`.
2. `DELETE FROM chunks WHERE document_id = :document_id` (idempotence : ré-upload du même fichier = remplacement propre).
3. Insérer parents puis enfants avec `embedding`, `embedding_model=settings.embedding_model`, `embedding_dim=settings.embedding_dim`, `allowed_groups`, breadcrumb, page, nb_tokens.
4. **Pas de TRUNCATE. Pas de commit global qui touche les autres docs.**

**`POST /api/admin/ingest`** (dans `app/api/admin.py`)
- Auth : utilisateur connecté requis (`Depends(utilisateur_courant)` — Module 2).
- Corps `multipart/form-data` : `file` (UploadFile), `service` (str), `sensibilite` (str = "interne").
- Étapes : valider `service ∈ SERVICES` et extension ∈ {`.md`, `.pdf`} ; sauver dans `corpus/uploads/{service}/{nom_fichier}` ; `charger()` → `decouper_en_sections()` → `construire_chunks()` → `vectoriser()` (modèle + dim depuis settings) → `indexer_un_document(allowed_groups=groupes_du_service(service), ...)`.
- Réponse : `{"document": nom, "service": service, "label": ..., "groups": [...], "nb_enfants": N, "nb_parents": M}`.

**Front `upload-doc.tsx`** : input file (drag & drop simple), `<select>` service, bouton « Indexer ». Pendant l'appel : spinner + « Découpage et vectorisation… ». Au retour : encart de succès « ✅ {document} indexé — {N} passages — visible par : {label} ». En-tête `Authorization: Bearer <token>`.

### Definition of Done — Module 1
```bash
# Depuis l'UI /admin, onglet "Ajouter un document" :
# déposer un .md de test taggé "cse" → succès affiché.
# Puis dans le chat, poser une question sur ce doc :
```
- Un utilisateur avec `grp-cse` obtient la réponse **avec citation** du doc uploadé.
- Marie (RH, sans grp-cse) sur la même question → « je n'ai pas d'information accessible ».
- Ré-uploader le même fichier ne crée pas de doublons (le nombre de chunks reste stable en base).

---

## MODULE 2 — Authentification complète (email + mot de passe, JWT, rôles)

### But
Vraie page de connexion. `/api/chat` et `/api/admin/*` protégés par JWT. Les groupes viennent du **jeton**, plus du corps de la requête. Boutons démo (Marie/Paul/Admin) = vrai login en un clic.

### Fichiers à créer / modifier
- **créer** `app/security/passwords.py`, `app/security/jwt.py`, `app/security/deps.py`.
- **créer** `app/api/auth.py` — `POST /auth/login`, `GET /auth/me`.
- **modifier** `app/main.py` — inclure le router auth.
- **modifier** `app/api/chat.py` — protéger par `utilisateur_courant`, dériver les groupes du jeton.
- **créer** `web/app/login/page.tsx`, `web/lib/auth.ts` (contexte + stockage token), **modifier** `web/lib/use-rag-chat.ts` (header Authorization) et `web/components/user-selector.tsx` (re-login au switch).

### Spécifications

**`app/security/passwords.py`** — `verifier_mot_de_passe(clair: str, hash_bcrypt: str) -> bool` (bcrypt direct, PAS passlib).

**`app/security/jwt.py`** (pyjwt, PAS python-jose)
```python
def creer_token(user: dict) -> str      # payload: sub=user_id, email, nom, groupes, role, exp
def decoder_token(token: str) -> dict    # lève 401 si invalide/expiré
```

**`app/security/deps.py`**
```python
def utilisateur_courant(authorization: str = Header(None)) -> dict
    # "Bearer <token>" → decoder_token → {id, email, nom, groupes, role} ; sinon 401
def admin_requis(user: dict = Depends(utilisateur_courant)) -> dict
    # user["role"] == "admin" sinon 403
```

**`app/api/auth.py`**
- `POST /auth/login` : corps `{email, mot_de_passe}` → SELECT user → `verifier_mot_de_passe` → `creer_token` → `{"access_token": ..., "token_type": "bearer", "user": {email, nom, groupes, role}}`. Échec → 401.
- `GET /auth/me` : `Depends(utilisateur_courant)` → renvoie l'utilisateur.

**`app/api/chat.py`** : ajouter `user = Depends(utilisateur_courant)`. Les groupes utilisés par le pipeline = `user["groupes"]` (ignorer/écraser tout `user_groups` du corps — la sécurité ne vient jamais du corps). Ne rien changer d'autre au flux SSE.

**Front**
- `web/lib/auth.ts` : contexte React, token stocké en `localStorage` (`dyneff_token`), helpers `login/logout/getToken/getUser`.
- `web/app/login/page.tsx` : formulaire email + mot de passe ; **3 boutons démo** « Marie (RH) », « Paul (Commercial) », « Admin » qui appellent `/auth/login` avec les creds seed (`marie@dyneff.fr` / `paul@dyneff.fr` / `admin@dyneff.fr`, mdp `demo1234`) puis redirigent vers le chat. Design : bleu profond, sobre, sans emoji.
- Gate : si pas de token, rediriger vers `/login`. `use-rag-chat.ts` et tous les appels admin ajoutent `Authorization: Bearer <token>`.
- `user-selector.tsx` : au lieu d'envoyer des groupes dans le corps, il **re-logue** en tant que l'utilisateur choisi (appel `/auth/login`, remplace le token). Le switch démo devient de la vraie auth.

### Definition of Done — Module 2
- `/login` : se connecter avec `paul@dyneff.fr` / `demo1234` → arrive sur le chat.
- Question « grille des salaires » connecté en **Paul** → « je n'ai pas d'information accessible ». En **Marie** → la grille. (ACL pilotée par le jeton.)
- Sans jeton, `curl POST /api/chat` → **401**.
- Les 3 boutons démo connectent en un clic.

---

## MODULE 3 — Dashboard admin + seed d'usage

### But
Page `/admin` (onglet « Statistiques ») : 5 cartes KPI, top 10 des questions, trous du corpus. Alimentée par la table `messages`, remplie par un script de seed (sinon vide).

### Fichiers à créer / modifier
- **créer** `scripts/seed_usage.py`.
- **créer/compléter** `app/api/admin.py` — `GET /api/admin/stats`, `/api/admin/top-questions`, `/api/admin/gaps` (tous `Depends(admin_requis)`).
- **compléter** `web/app/admin/page.tsx` — le second onglet « Statistiques ».

### Spécifications

**`scripts/seed_usage.py`** (stdlib + psycopg) : insère ~250 lignes dans `messages` réparties sur 30 jours.
- Crée d'abord une conversation démo (`conversations`) rattachée à l'utilisateur admin, pour respecter la FK.
- ~89 % `a_repondu=true`, ~11 % `false`. `latence_ms` entre 1500 et 4000. `cout` entre 0.003 et 0.008. `modele='gpt-5.6-terra'`. `role='user'`.
- Questions répétées et réalistes en français RH pour peupler le top 10 : « Combien de jours de RTT ? », « Comment poser un congé sans solde ? », « Plafond note de frais repas ? », « Comment déclarer un arrêt maladie ? », « Prime d'ancienneté ? », etc. (avec des fréquences différentes).
- Questions `a_repondu=false` qui simulent des trous : « procédure de mobilité internationale », « congé proche aidant », « barème télétravail à l'étranger ».
- Idempotent : `DELETE FROM messages WHERE contenu LIKE '[SEED]%'` en tête, et préfixer les questions seedées d'un marqueur invisible ou d'une colonne repérable (ex. `modele='seed'`) pour pouvoir nettoyer.

**Endpoints admin**
- `GET /api/admin/stats` → `{nb_questions, pct_sourcees, pct_je_ne_sais_pas, latence_moyenne_ms, cout_moyen}` via `COUNT/AVG` sur `messages` (role='user').
- `GET /api/admin/top-questions` → 10 lignes `{question, count}` (`GROUP BY lower(contenu) ORDER BY count DESC LIMIT 10`).
- `GET /api/admin/gaps` → questions `a_repondu=false` regroupées → `{cluster, count, document_suggere}` (mapping simple mot-clé → doc manquant, en dur c'est acceptable pour la démo).

**Front `/admin` onglet Statistiques** : 5 cartes (questions, % sourcées, % « je ne sais pas », latence moyenne, coût moyen) ; liste top 10 avec barres proportionnelles ; liste des trous du corpus. Style conforme au design (bleu profond, fond blanc cassé, icônes fines, aucun emoji).

### Definition of Done — Module 3
```bash
docker compose exec api python scripts/seed_usage.py   # → "N messages seedés"
```
- Connecté en **admin**, `/admin` onglet Statistiques affiche des chiffres non nuls (≈ 89 % sourcées, une latence, un coût), un top 10 avec barres, et une liste de trous.
- Connecté en **Paul** (non-admin), `/admin` ou les endpoints → **403**.

---

## MODULE 4 — Bouton « Transmettre au service »

### But
Quand une réponse est un « je ne sais pas » (`a_repondu=false`), un bouton apparaît sous la réponse : « Transmettre la question au service {X} ». Clic → la demande est enregistrée → toast de confirmation.

### Fichiers à créer / modifier
- **créer** `app/db_migrate.py` — `assurer_tables_supplementaires()` : `CREATE TABLE IF NOT EXISTS demandes (id SERIAL PK, user_email TEXT, service TEXT, question TEXT, cree_le TIMESTAMPTZ DEFAULT now())`.
- **modifier** `app/main.py` — appeler `assurer_tables_supplementaires()` au démarrage (lifespan/startup). **Pas de `init.sql`, pas de `down -v`.**
- **créer** `app/api/demandes.py` — `POST /api/demandes` `{question, service}` (auth requise) → INSERT → `{"ok": true, "id": ...}`.
- **modifier** `web/components/chat-message.tsx` — bouton conditionnel + toast.

### Definition of Done — Module 4
- Poser une question hors corpus (ex. « congé proche aidant ») → réponse « je ne sais pas » → le bouton « Transmettre au service RH » apparaît.
- Clic → toast « Demande transmise au service RH » → une ligne dans `SELECT * FROM demandes`.

---

## MODULE 5 — Polish interface + affichage « recherche en direct » (type Claude)

### But
L'élément signature : pendant la génération, afficher les étapes en direct (« Reformulation… », « Recherche dans N documents… », « Sélection des 5 passages… »), façon indicateur de recherche de Claude, puis les replier une fois la réponse arrivée. Le backend **émet déjà** ces événements `status` en SSE — il s'agit de bien les afficher.

### Fichiers à créer / modifier
- **créer** `web/components/status-steps.tsx` — liste animée des étapes reçues.
- **modifier** `web/lib/use-rag-chat.ts` — exposer les événements `status` reçus (les collecter dans un state).
- **modifier** `web/components/chat.tsx` / `chat-message.tsx` — rendre `StatusSteps` au-dessus de la réponse en cours ; une fois `done` reçu, replier en une ligne « Recherche effectuée dans N documents ».
- Polish global : appliquer la direction visuelle (accent bleu profond, sidebar anthracite, fond blanc cassé, icônes fines `lucide-react`, **aucun emoji**, pas de dégradé, pas de glassmorphism). Markdown déjà propre (`react-markdown` + `prose`).

### Definition of Done — Module 5
- Poser une question → les étapes s'affichent une par une pendant le traitement, puis se replient quand la réponse commence à streamer. L'ensemble a l'air fini et cohérent avec les cartes de sources et le download .docx.

---

## DEFINITION OF DONE GLOBALE

À valider dans cet ordre (chaque module est indépendamment testable) :

1. **Module 1** — upload d'un doc CSE depuis `/admin` → réponse citée pour un user CSE, invisible pour Marie.
2. **Module 2** — login réel ; Paul ne voit pas les salaires, Marie oui ; `/api/chat` sans token = 401 ; 3 boutons démo OK.
3. **Module 3** — `seed_usage.py` lancé → `/admin` Statistiques rempli ; non-admin = 403.
4. **Module 4** — question hors corpus → bouton « Transmettre » → toast + ligne en base.
5. **Module 5** — étapes en direct affichées puis repliées ; interface cohérente.

Rien de tout ça ne nécessite `docker compose down -v`. Aucune modif de `init.sql`. OpenAI conservé partout.

---

## ANNEXE OPTIONNELLE — si tu as 10 min à la fin (non bloquant)

Centraliser le client OpenAI pour rendre l'archi visiblement agnostique (argument souveraineté) :
- **créer** `app/openai_client.py` : `client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)` avec `OPENAI_BASE_URL` par défaut `https://api.openai.com/v1` dans `.env`.
- remplacer les 4 instanciations `OpenAI(...)` (dans `llm/generate.py`, `ingest/embed.py`, `retrieval/rerank.py`, `files/generate_doc.py`) par `from app.openai_client import client`.
- Aucun changement de comportement. Bénéfice : demain tu peux montrer qu'un seul `OPENAI_BASE_URL` bascule tout vers un modèle interne (Ollama expose la même API). À NE FAIRE que si les 5 modules sont finis et testés.
