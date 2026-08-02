# CDC CORRECTIF — Chat propre, routing par thème, dashboard analytics

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
═══════════════════════════════════════════════════════════

## 🎯 Objectif en une phrase
Rendre le chat non-débile (bonjour, questions de suivi, web qui déraille), remplacer les murs ACL par un simple filtre de thème `/rh /cse`, et refaire le dashboard en vraie page d'analytics.

## 💡 Pourquoi (les 3 problèmes constatés)
1. « Salut qui es-tu ? » → « je ne sais pas » + bouton RH. Le système envoie tout dans le RAG, même un bonjour.
2. « tes sur ? » → traduction anglaise + parfums. Le web était allumé et a lu la phrase littéralement ; et il n'y a pas de mémoire.
3. Le dashboard mélange l'upload (qui n'a rien à y faire) et les stats, et le design ne convient pas.

## 🧩 Ce qui change
- **Accès** : tout le corpus est visible par tous les utilisateurs. Plus de filtrage par groupe. (La sécurité « rien ne sort » vient du modèle interne, pas de murs internes.)
- **`/rh /cse /hse`** : filtre de **thème** (UX), pas de sécurité. Limite la recherche aux docs du service. Rien tapé = cherche partout.
- **Garde smalltalk + réécriture** : un pré-traitement classe chaque message (bavardage vs question) et réécrit les questions de suivi en questions autonomes.
- **Web OFF par défaut**, et jamais déclenché sur du bavardage.
- **Dashboard** : analytics only, sidebar + onglets, composant séparé. Upload déplacé sur `/upload`.

## ⚠️ Pièges
- 🔴 Toujours **interdit** : `docker compose down -v`. Les nouvelles colonnes se créent via `ADD COLUMN IF NOT EXISTS` au démarrage (non destructif).
- 🔴 Ne pas casser le streaming SSE existant ni la génération .docx.
- 🔴 Le pré-traitement ajoute **un** appel au modèle rapide (luna) avant chaque question. C'est léger et ça règle bavardage + suivi + « tes sur ? » d'un coup.

## 🗣️ En réunion
> *« On ne tape aucun code de sécurité. Toute l'info du RAG est de la connaissance utile, visible par tous. Le `/rh` ou `/cse` sert juste à cibler un service. Ce qui reste dans l'entreprise, c'est garanti par le modèle interne — pas par des cloisons artificielles. »*

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
═══════════════════════════════════════════════════════════

## Contexte
RAG interne RH Dyneff. FastAPI + Postgres/pgvector + OpenAI + Next.js (`web/`). Le moteur (retrieval hybride, génération streaming SSE, .docx, web) fonctionne. Ce CDC corrige le comportement du chat, remplace le filtrage ACL par un filtre de thème, et refait le dashboard.

## État actuel (ne pas casser)
- `app/api/chat.py` : `POST /api/chat` (SSE : status, sources, token, done), `flux_evenements(requete)`, `RequeteChat`.
- `app/retrieval/pipeline.py` : `rechercher(conn, question, groupes_utilisateur, settings)` filtre par groupes en SQL.
- `app/retrieval/vector.py` / `fulltext.py` : `WHERE allowed_groups && groupes_utilisateur`.
- `app/tools/web.py` : Tavily.
- `messages` a : conversation_id, role, contenu, question_reecrite, a_repondu, sources JSONB, latence_ms, cout, modele.
- Front : `web/app/page.tsx`, `components/chat.tsx`, `chat-message.tsx`, `user-selector.tsx`, `web/app/admin/page.tsx` (dashboard + upload mélangés — à séparer), `lib/use-rag-chat.ts`.

## CONTRAINTES GLOBALES
- Interdit : `docker compose down -v`, modifier `init.sql`, LangChain/LlamaIndex/Ragas/useChat.
- Nouvelles colonnes via `ADD COLUMN IF NOT EXISTS` dans `app/db_migrate.py` (appelé au démarrage). Non destructif.
- Garder OpenAI (terra = génération, luna = rapide).

---

## MODULE A — Chat propre : accès ouvert + pré-traitement (bavardage / réécriture) + web discipliné

### A.1 Accès ouvert (supprimer le mur ACL)
- `app/retrieval/pipeline.py`, `vector.py`, `fulltext.py` : **retirer** le filtre `WHERE allowed_groups && groupes_utilisateur`.
- Le remplacer par un filtre optionnel de **thème** : nouveau paramètre `filtre_service: str | None`. Si fourni → `WHERE allowed_groups && ARRAY[:filtre_service]` (on réutilise `allowed_groups` comme étiquette de service, ex. `grp-rh`, `grp-cse`). Si `None` → **aucun** filtre, cherche tout.
- `rechercher(conn, question, settings, filtre_service=None)` — retirer `groupes_utilisateur`.

### A.2 Pré-traitement (le garde qui règle bavardage + suivi + « tes sur ? »)
- **créer** `app/chat/pretraitement.py` :
```python
def pretraiter(message: str, historique: list[dict], client, modele_rapide: str) -> dict:
    # 1 appel à luna. historique = derniers tours [{role, contenu}].
    # Renvoie STRICTEMENT du JSON :
    # {
    #   "type": "bavardage" | "documentaire",
    #   "reponse_directe": "..."       # si bavardage : réponse persona courte
    #   "question_autonome": "..."     # si documentaire : question de suivi réécrite en autonome
    # }
```
Prompt système du pré-traitement (français) :
> « Tu es le routeur d'un assistant RH interne nommé "Assistant RH Dyneff". À partir du message et de l'historique, décide : si c'est du bavardage (bonjour, qui es-tu, merci, ça va, au revoir) → type "bavardage" + une réponse persona brève ("Je suis l'assistant RH de Dyneff, je réponds à vos questions sur les procédures internes et la convention collective."). Sinon → type "documentaire" + réécris la question en question autonome en intégrant le contexte de l'historique (ex. "tes sûr ?" → "Es-tu sûr de ta réponse précédente sur X ?"). Réponds uniquement en JSON. »

### A.3 Brancher dans `app/api/chat.py`
Dans `flux_evenements`, AVANT le retrieval :
1. Charger les N derniers tours (N=6) de la conversation → `historique`.
2. `resultat = pretraiter(message, historique, client, settings.llm_model_fast)`.
3. Si `type == "bavardage"` → émettre la `reponse_directe` en streaming, **pas de retrieval, pas de web, pas de sources, pas de bouton "transmettre"**, `done`. Fin.
4. Si `type == "documentaire"` → utiliser `question_autonome` pour le retrieval (c'est la réécriture / mémoire). Suite normale.
5. Passer les N derniers tours au contexte de génération (mémoire légère) en plus des chunks.

### A.4 Web discipliné
- `RequeteChat.web_active` par défaut **False**.
- Le web ne s'active QUE si `web_active == True` ET `type == "documentaire"`. Jamais sur du bavardage.
- Front : le toggle web démarre **éteint**.

### DoD Module A
- « Salut qui es-tu ? » → réponse persona (« Je suis l'assistant RH de Dyneff… »), sans sources, sans bouton RH.
- « c'est quoi le salaire ? » puis « tes sûr ? » → la 2e est réécrite, re-cherche dans le corpus, **pas de parfums, pas de web**.
- Web éteint par défaut ; « et mes congés ? » → réponse sourcée **sans** sources web.

---

## MODULE B — Routing par thème `/rh /cse /hse /juridique`

- **créer** `app/chat/routing.py` :
```python
COMMANDES = {"/rh": "grp-rh", "/cse": "grp-cse", "/hse": "grp-hse", "/juridique": "grp-juridique"}
def extraire_commande(message: str) -> tuple[str | None, str]:
    # "/rh combien de CE ?" -> ("grp-rh", "combien de CE ?")
    # "combien de congés ?"  -> (None, "combien de congés ?")
```
- Dans `chat.py` : appliquer `extraire_commande` sur le message, passer `filtre_service` au `rechercher(...)`, et retirer la commande du texte avant le pré-traitement.
- Front (`chat.tsx`) : quand l'input commence par `/`, afficher un petit menu d'autocomplétion (rh / cse / hse / juridique). Minimum acceptable : taper `/rh question` fonctionne même sans le menu.
- ⚠️ Commentaire dans le code : ceci est de l'UX (ciblage de thème), **pas** de la sécurité.

### DoD Module B
- `/cse` + une question sur un doc CSE → réponse limitée au corpus CSE.
- Sans slash → cherche dans tout le corpus.

---

## MODULE D — Dashboard analytics (refonte) + upload séparé

### D.1 Séparer l'upload
- Déplacer le formulaire d'upload de `/admin` vers **`web/app/upload/page.tsx`** (self-service : accessible à tout utilisateur connecté). Retirer tout upload de `/admin`.

### D.2 Colonnes analytics (migration non destructive)
- Dans `app/db_migrate.py`, ajouter :
```sql
ALTER TABLE messages ADD COLUMN IF NOT EXISTS service TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS fichier_genere BOOLEAN DEFAULT FALSE;
```
- Renseigner `service` (depuis la commande slash ou le thème dominant des chunks cités) et `fichier_genere` (True quand une génération .docx a réussi) à l'écriture des messages.

### D.3 Endpoints (`app/api/admin.py`, `Depends(admin_requis)`)
- `GET /api/admin/kpis` → `{nb_questions, taux_reponse, taux_je_ne_sais_pas, taux_succes_generation, latence_moyenne_ms, cout_moyen}`.
- `GET /api/admin/top-questions` → 10 × `{question, count}`.
- `GET /api/admin/top-user` → user le plus actif `{nom, count}` (join `conversations.user_id`).
- `GET /api/admin/top-service` → service le plus consulté `{service, count}` (GROUP BY `messages.service`).

### D.4 Front — `web/app/admin/page.tsx` (composant dédié `web/components/dashboard/`)
- **Layout avec sidebar** (navigation) + **onglets** : « Vue d'ensemble », « Questions », « Services ».
- Vue d'ensemble : cartes KPI (questions, taux de réponse, taux « je ne sais pas », **taux de succès génération de fichiers**, latence moyenne, coût moyen).
- Questions : top 10 avec barres proportionnelles.
- Services : service le plus consulté + user le plus actif.
- Style : sobre, accent bleu profond, fond blanc cassé, icônes fines `lucide-react`, **aucun emoji, aucun dégradé**.

### D.5 Seed
- Mettre à jour `scripts/seed_usage.py` pour renseigner `service` (rh/cse/hse variés), `fichier_genere` (~15 % True) et varier `conversations.user_id` (plusieurs users) afin que « top user » et « top service » aient du contenu.

### DoD Module D
- `python scripts/seed_usage.py` → dashboard `/admin` rempli : KPIs non nuls, top questions, top service, top user, onglets fonctionnels, sidebar.
- `/upload` séparé et fonctionnel ; plus aucun upload sur `/admin`.
- Non-admin sur `/admin` → 403.

---

## ORDRE ET DoD GLOBALE
1. **Module A** (chat propre) — tue les réponses débiles. Priorité absolue.
2. **Module B** (routing `/rh /cse`) — ce qui était demandé.
3. **Module D** (dashboard + upload séparé).

Aucun `down -v`. Aucune modif `init.sql`. OpenAI conservé.
