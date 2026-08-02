# CDC FINAL — Refonte de l'interface (style produit, OpenWebUI / ChatGPT)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
═══════════════════════════════════════════════════════════

## 🎯 Objectif en une phrase
Passer d'une interface de démo (barre de switch Marie/Paul/Léa en haut) à une vraie interface produit type ChatGPT/OpenWebUI : sidebar à gauche avec l'historique, menu utilisateur discret, zone de chat propre.

## 💡 Pourquoi
- La barre de switch d'utilisateurs en haut fait « démo bricolée ». On l'enlève.
- Depuis qu'on n'a plus de murs ACL, afficher « Marie · grp-tous, grp-rh » n'a plus aucun sens. On enlève les labels de groupe partout.
- Une sidebar avec l'historique = ça ressemble immédiatement à un produit fini que les gens connaissent.

## 🧩 Ce qui change
- **Plus de switcher en haut.** L'identité vient du login. Pour la démo, tu changes d'utilisateur en te déconnectant/reconnectant (les boutons démo restent sur `/login`).
- **Sidebar à gauche** (anthracite) : bouton « Nouvelle conversation », historique des conversations, et en bas un menu utilisateur (nom + déconnexion, + « Tableau de bord » si admin, + « Importer un document »).
- **Zone de chat épurée** : messages, étapes de recherche en direct (la signature), sources, download .docx, toggle web discret (éteint par défaut).
- **Persistance** : chaque conversation est sauvée, rechargée au clic dans la sidebar.

## ⚠️ Pièges
- 🔴 Toujours **interdit** : `docker compose down -v`, modifier `init.sql`.
- 🔴 Ne pas casser le streaming SSE ni la génération .docx.
- 🔴 Garder les boutons démo sur `/login` — c'est ton seul moyen de switcher d'utilisateur en démo maintenant que la barre du haut disparaît.

## 🗣️ En réunion
Tu n'expliques rien : ça a l'air d'un produit que tout le monde connaît. C'est exactement l'effet voulu — « ce n'est pas une maquette, c'est un outil ».

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
═══════════════════════════════════════════════════════════

## Contexte
RAG interne RH Dyneff. Next.js 15 + TypeScript + Tailwind + shadcn/ui (dossier `web/`), backend FastAPI opérationnel. Ce CDC refait entièrement l'interface pour un style produit (type OpenWebUI / ChatGPT) et ajoute la persistance des conversations. Aucune régression sur le streaming, les sources, le .docx.

## État actuel à remplacer
- `web/components/user-selector.tsx` : barre de switch Marie/Paul/Léa/Admin en haut → **à supprimer**.
- En-tête affichant « {Nom} · {groupes} » → **à supprimer** (plus aucun label de groupe dans l'UI).
- `web/app/page.tsx` : page unique de chat sans sidebar → **à restructurer** en layout sidebar + zone principale.
- Backend : `app/chat/` vide, pas de CRUD conversations. `messages` et `conversations` existent en base.

## CONTRAINTES GLOBALES
- Interdit : `docker compose down -v`, modifier `init.sql`, LangChain/useChat, emojis dans l'UI, dégradés, glassmorphism, ombres lourdes.
- Garder OpenAI, le SSE custom, les composants sources/docx existants (les re-styler, pas les réécrire).

---

## PARTIE 1 — Backend : persistance des conversations (minimal)

**créer** `app/api/conversations.py` (toutes les routes `Depends(utilisateur_courant)`) :
- `POST /api/conversations` → crée une conversation vide pour l'utilisateur courant → `{id, titre: null}`.
- `GET /api/conversations` → liste les conversations de l'utilisateur courant, triées par date desc → `[{id, titre, cree_le}]`.
- `GET /api/conversations/{id}/messages` → messages de la conversation (vérifier qu'elle appartient à l'utilisateur) → `[{role, contenu, sources, a_repondu, cree_le}]`.
- `DELETE /api/conversations/{id}` → supprime (si propriétaire).

**modifier** `app/api/chat.py` :
- `RequeteChat` accepte `conversation_id: int | None`. Si `None` → créer une conversation.
- Persister le message utilisateur AVANT génération, et le message assistant APRÈS (avec `sources` JSONB, `a_repondu`, `latence_ms`, `cout`, `modele`, `service`, `fichier_genere`).
- Si la conversation n'a pas de `titre`, le fixer aux ~50 premiers caractères de la première question.
- Émettre `conversation_id` dans l'événement SSE `done` pour que le front sache où il écrit.

**DoD Partie 1** : poser 2 questions → `GET /api/conversations` renvoie 1 conversation avec un titre ; `GET /api/conversations/{id}/messages` renvoie les 4 messages (2 user + 2 assistant).

---

## PARTIE 2 — Design system (tokens)

Définir dans `globals.css` / config Tailwind. **Fond plat, aucun dégradé.**

```
Palette
  --sidebar-bg      #1E232B   (anthracite)
  --sidebar-text    #E8EAED
  --sidebar-muted   #9AA0A6
  --sidebar-hover   #2A2F38
  --bg              #FAFAF8   (off-white, plat)
  --surface         #FFFFFF
  --border          #E6E6E1   (hairline)
  --text            #1A1D21
  --text-muted      #6B7280
  --accent          #2E4B6B   (bleu profond — liens, état actif, bouton envoyer)
  --accent-hover    #24405C
  --web             #C2641E   (orange — UNIQUEMENT les sources web, pour les distinguer)

Type
  UI / body : Inter (ou system-ui)
  Wordmark "Dyneff" : Inter 600, légèrement resserré
  Échelle sobre, sentence case partout, aucun emoji

Icônes : lucide-react, trait fin, taille 16–18px
Rayons : 8px (cartes/bulles), 6px (boutons)
```

Signature (le seul élément « fort ») : **les étapes de recherche en direct**. Tout le reste reste calme.

---

## PARTIE 3 — Layout (sidebar + zone principale)

Wireframe :
```
┌───────────────┬──────────────────────────────────────────┐
│  Dyneff       │                                           │
│  Assistant RH │            (zone de chat)                 │
│               │                                           │
│ + Nouvelle    │        état vide OU conversation          │
│   conversation│                                           │
│  ───────────  │                                           │
│  Historique   │                                           │
│  · Congés…    │                                           │
│  · Note frais…│                                           │
│  · Budget CSE…│                                           │
│               │  ┌─────────────────────────────────────┐  │
│               │  │ 🌐 Web (éteint)   [tape /rh /cse…]  ►│  │
│  ───────────  │  └─────────────────────────────────────┘  │
│  ◐ Nom user ▾ │                                           │
└───────────────┴──────────────────────────────────────────┘
```

**modifier** `web/app/layout.tsx` : layout à deux colonnes, gate d'auth (pas de token → redirection `/login`). Sidebar fixe à gauche (largeur ~260px, repliable), zone principale à droite.

**créer** `web/components/sidebar/sidebar.tsx` :
- Haut : wordmark « Dyneff / Assistant RH » + bouton « Nouvelle conversation » (icône `Plus`).
- Milieu : liste de l'historique (`GET /api/conversations`), chaque item = titre tronqué ; clic → charge la conversation ; survol → icône suppression (`Trash2` → `DELETE`).
- Bas : `user-menu.tsx`.

**créer** `web/components/sidebar/user-menu.tsx` :
- Avatar = initiale du nom sur pastille accent + nom (⚠️ **aucun label de groupe**).
- Menu déroulant (`▾`) : « Tableau de bord » (**visible seulement si role === 'admin'** → `/admin`), « Importer un document » → `/upload`, « Se déconnecter » (efface le token → `/login`).

**supprimer** `web/components/user-selector.tsx` et toute référence. Retirer l'en-tête « {nom} · {groupes} ».

---

## PARTIE 4 — Zone de chat

**créer** `web/components/chat/chat.tsx` (remplace le contenu de `page.tsx`) :

**État vide** (nouvelle conversation) :
- Wordmark centré + sous-titre.
- Copie (sentence case, sans jargon, **sans notion de périmètre/groupe**) :
  > **Dyneff — Assistant RH**
  > Posez une question sur vos procédures internes. Chaque réponse cite ses sources.
- 3 questions suggérées (cartes cliquables) : « Combien de jours de congés par an ? », « Comment poser une note de frais ? », « /cse Quel est le budget CSE 2026 ? ».

**Conversation** :
- Message **utilisateur** : bulle discrète alignée à droite (fond `--surface`, bordure hairline).
- Message **assistant** : pleine largeur, sans bulle (style ChatGPT), texte sur `--bg`.
- **`status-steps.tsx`** (signature) : pendant la génération, les événements SSE `status` s'affichent en liste animée (« Reformulation… », « Recherche dans N passages… », « Sélection des passages pertinents… ») ; à `done`, repli en une ligne discrète « Recherche effectuée dans N passages ▾ ».
- **`sources.tsx`** : cartes sous la réponse. Internes = accent bleu + icône `FileText`. Web = accent orange + icône `Globe` (visuellement distinctes).
- **Download .docx** : carte dédiée avec icône `FileDown` + « Télécharger le document ».
- Sous chaque réponse : `Copy`, `ThumbsUp`, `ThumbsDown` (trait fin, discrets).
- Réponse « je ne sais pas » (`a_repondu === false`) → bouton « Transmettre au service {X} ».

**créer** `web/components/chat/composer.tsx` (barre d'entrée) :
- Textarea auto-grow, placeholder « Écrivez votre question… (ou /rh /cse pour cibler un service) ».
- Toggle **Web éteint par défaut** (icône `Globe`) ; allumé → libellé « Web actif · votre question quitte l'entreprise » en orange.
- Autocomplétion au `/` : menu `/rh /cse /hse /juridique`.
- Bouton envoyer (`Send`) en accent bleu.

**DoD Partie 4** : interface qui ressemble à un produit ; état vide propre ; question → étapes en direct puis réponse sourcée ; historique cliquable à gauche ; aucun switcher, aucun label de groupe visible.

---

## DoD GLOBALE (le produit fini)
1. Se connecter en **Paul** → sidebar avec SES conversations, menu utilisateur en bas, **pas** de « Tableau de bord ».
2. Se connecter en **Admin** → menu utilisateur montre « Tableau de bord » → `/admin`.
3. Nouvelle conversation → poser une question → apparaît dans l'historique → recharger la page → toujours là.
4. Aucune barre de switch en haut, aucun label de groupe nulle part.
5. Étapes de recherche en direct visibles ; sources internes bleues / web orange ; .docx téléchargeable.

Aucun `down -v`. Aucune modif `init.sql`. OpenAI conservé.

---

## ✅ CHECKLIST FINALE AVANT LA DÉMO (à faire après ce CDC)
Ce sont les 3 trucs qui cassent une démo en live — ne les saute pas :

1. **Tester le download .docx CONNECTÉ.** Un download navigateur n'envoie pas le header `Authorization`. Si `/api/files/{id}` est protégé → 401 silencieux → rien ne se télécharge. Clique vraiment sur le bouton. Si ça foire, le fix : passer le token en query param sur cette route, ou la laisser ouverte (id non devinable, fichier éphémère).
2. **Commit GitHub.** `git status` (vérifier que `.env` n'apparaît PAS), puis `git add -A && git commit && git push`. C'est ta preuve datée que c'est toi qui as construit ça.
3. **Vidéo de secours (3 min).** Enregistre la démo une fois qu'elle tourne. Si le live plante devant Rémi, la vidéo te sauve.
