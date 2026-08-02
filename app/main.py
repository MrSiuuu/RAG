"""API RAG Dyneff — point d'entrée FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.demandes import router as demandes_router
from app.api.files import router as files_router
from app.api.search import router as search_router
from app.config import settings
from app.db import db_est_joignable, engine
from app.db_migrate import assurer_tables_supplementaires


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Tables supplémentaires (demandes) + user CSE démo — sans toucher init.sql.
    assurer_tables_supplementaires()
    yield


app = FastAPI(
    title="RAG Dyneff — API",
    description="POC RAG pour le service RH. Deux portes, un seul cerveau.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(admin_router)
app.include_router(demandes_router)
app.include_router(conversations_router)

# Le front Next.js arrive sur le port 3000 (CDC 8).
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
    """Endpoint de debug : prouve que pgvector et le schéma sont en place."""
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
