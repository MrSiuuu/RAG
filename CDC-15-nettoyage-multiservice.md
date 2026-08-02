# CDC 15 — Nettoyage ACL + /doc + multi-service + demandes visibles

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Enlever tout le concept de groupes/permissions, ouvrir l'assistant à tous les services (pas que RH), ajouter `/doc`, et rendre les demandes transmises visibles côté admin.

## Ce qu'on enlève / garde / ajoute

| On enlève | On garde | On ajoute |
|---|---|---|
| Le filtre par groupes dans la recherche | La colonne `allowed_groups` en base (dormante) | Le slash `/doc` |
| Les slash `/rh /cse /hse /juridique` | La génération de `.docx` (déjà OK) | Du contenu CSE dans le corpus |
| Les 2 docs confidentiels du corpus | Le login + le rôle admin | Un onglet « Demandes » dans /admin |
| La distinction Marie/Paul/Léa | | |

## Le point important

L'ACL était **déjà à moitié retirée** : sans slash, la recherche tourne sur tout le corpus. On finit juste le travail. **On ne touche pas au schéma de la base** — la colonne `allowed_groups` reste là, inerte. Si un jour tu la reveux, c'est un interrupteur, pas une migration.

Et rappel de base : le multi-service marche **tout seul** par le sens (l'embedding). Une question CSE tombe dans le quartier CSE de la carte du sens sans qu'on ait à dire `/cse`. C'est pour ça qu'on peut virer les slash de service sans rien perdre.

## Ce que tu pourras dire en réunion

> « Un seul assistant, tous les services dedans. Le collaborateur pose sa question, l'outil trouve la bonne procédure, peu importe le service. Et quand l'assistant ne sait pas, la demande remonte au service concerné — que l'admin voit dans son tableau de bord. »


═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte

Projet RAG interne (FastAPI + Postgres/pgvector + Next.js). On simplifie : plus de groupes/permissions, l'assistant devient multi-service, on ajoute un slash `/doc`, et on rend visibles les demandes transmises. Ne rien casser du pipeline de retrieval ni de la génération de docx, tous deux fonctionnels.

## Chantier 1 — Retirer les groupes / permissions

- Dans `app/retrieval/pipeline.py` : retire le paramètre `filtre_service` de `rechercher()` et tout ce qui le propage.
- Dans `app/retrieval/vector.py` et `fulltext.py` : retire les clauses SQL qui filtrent sur `allowed_groups && ARRAY[...]`. La recherche tourne toujours sur tout le corpus (child chunks).
- Dans `app/chat/routing.py` : supprime les slash `/rh /cse /hse /juridique`. Ce fichier peut disparaître s'il ne sert plus qu'à ça.
- Dans `app/api/chat.py` et `search.py` : retire les appels à `filtre_service` / au routing.
- `app/retrieval/acl.py` : n'est appelé nulle part → supprime le fichier.
- Corpus : sors du corpus les fichiers `CONFIDENTIEL-grille-remuneration-2026.md` et `CONFIDENTIEL-procedure-disciplinaire.md`, et retire-les du `manifest.json`.
- Login : ne casse pas l'auth. Les groupes ne filtrant plus rien, Marie/Paul/Léa deviennent équivalents. Réduis les boutons démo de `/login` à deux : un utilisateur normal + un Admin (le rôle admin reste nécessaire pour accéder à `/admin`).
- **Ne touche PAS** à la colonne `allowed_groups` dans `db/init.sql` ni au schéma. Elle reste, non utilisée.

## Chantier 2 — Ajouter le slash `/doc`

- Dans `app/files/intent.py` : si le message commence par `/doc`, force l'intention « document » (bypass de la regex), puis retire `/doc` du texte avant le reste du traitement.
- Dans `web/components/chat/composer.tsx` : le menu d'autocomplétion au `/` propose désormais `/doc` (à la place des anciens slash de service).
- Ne change rien à `generate_doc.py` ni `docx.py` : la génération elle-même reste identique.

## Chantier 3 — Ajouter du contenu CSE

- Crée 2 à 3 documents CSE synthétiques en markdown dans `corpus/` (ex. : budget et activités sociales du CSE, réunions et heures de délégation, avantages CSE). Contenu inventé mais cohérent et structuré avec des titres (## / ###).
- Ajoute-les au `manifest.json` avec `"service": "cse"` et `allowed_groups: ["grp-tous"]` (plus d'ACL, tout le monde y accède).
- Relance l'ingestion pour les indexer.

## Chantier 4 — Portail multi-service (plus « Assistant RH »)

- Remplace « Assistant RH » par un nom qui couvre tous les services. Utilise **« Assistant Dyneff »**.
- Fichiers à modifier : `web/components/chat/chat.tsx` (wordmark + sous-titre + suggestions), `web/app/layout.tsx` (titre navigateur), `web/components/sidebar/sidebar.tsx`.
- Sous-titre proposé : « Posez une question sur vos procédures internes. Chaque réponse cite ses sources. »
- Les 3 suggestions d'accueil : garde une question congés, une note de frais, et remplace la suggestion `/cse …` par une **question CSE normale sans slash** (ex. « Quel est le budget du CSE pour 2026 ? »).

## Chantier 5 — Rendre les demandes visibles par l'admin

- Back : ajoute `GET /api/demandes` (admin uniquement) qui renvoie la liste des demandes (`id, user_email, service, question, cree_le`), triées de la plus récente à la plus ancienne.
- Front : dans `web/app/admin/page.tsx` (ou le composant dashboard), ajoute un onglet / une section **« Demandes »** qui appelle cette route et affiche la liste (colonnes : date, utilisateur, service, question).
- Bouton dans `web/components/chat-message.tsx` : renomme « Transmettre au service RH » en **« Transmettre au service concerné »** (l'outil n'est plus RH-only). La demande peut garder un champ `service` ; affiche-le dans la liste admin pour distinguer RH / CSE / autre.

## Definition of Done

```bash
# 1. Multi-service par le sens (sans aucun slash)
#    → poser une question CSE dans le chat → réponse correcte, sources CSE

# 2. Génération forcée
#    → "/doc rédige une note sur le budget CSE" → un .docx se télécharge

# 3. Plus de slash de service
#    → taper "/" dans le composer → seul "/doc" est proposé

# 4. Portail neutre
#    → l'accueil affiche "Assistant Dyneff", plus "Assistant RH"

# 5. Confidentiels partis
#    → les 2 docs CONFIDENTIEL-* ne sont plus indexés (vérifier en base)

# 6. Demandes visibles
#    → depuis une réponse "je ne sais pas", cliquer "Transmettre"
#    → la demande apparaît dans l'onglet "Demandes" de /admin
```

**Si un seul de ces points est faux, le CDC n'est pas fini.**
