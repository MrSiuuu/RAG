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

## Front (CDC 8)

```bash
# Terminal 1 — API déjà lancée via docker compose
# Terminal 2 —
cd web
npm install
npm run dev
# → http://localhost:3000
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
