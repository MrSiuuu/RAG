"""API RAG Dyneff — point d'entrée FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.search import router as search_router
from app.config import settings
from app.db import db_est_joignable, engine

app = FastAPI(
    title="RAG Dyneff — API",
    description="POC RAG pour le service RH. Deux portes, un seul cerveau.",
    version="0.1.0",
)

app.include_router(search_router)

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
