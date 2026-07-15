"""Endpoint de debug POST /search — teste le retrieval sans front."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.retrieval.pipeline import rechercher

router = APIRouter()


class RequeteRecherche(BaseModel):
    question: str = Field(..., min_length=1)
    user_groups: list[str]


class ChunkResultat(BaseModel):
    id: int
    breadcrumb: str
    extrait: str
    page: int | None
    score_rrf: float | None = None


class ReponseRecherche(BaseModel):
    question: str
    chunks: list[ChunkResultat]
    nb_candidats_avant_rerank: int
    duree_ms: int


def _url_psycopg() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@router.post("/search", response_model=ReponseRecherche)
async def chercher(requete: RequeteRecherche) -> ReponseRecherche:
    """Endpoint de DEBUG — pas destiné au front final."""
    try:
        with psycopg.connect(_url_psycopg()) as conn:
            resultat = rechercher(
                conn,
                requete.question,
                requete.user_groups,
                settings,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chunks = [
        ChunkResultat(
            id=c["id"],
            breadcrumb=c["breadcrumb"],
            extrait=c["contenu"][:300],
            page=c.get("page"),
            score_rrf=c.get("score_rrf"),
        )
        for c in resultat.chunks_enfants
    ]

    return ReponseRecherche(
        question=resultat.question_recrite,
        chunks=chunks,
        nb_candidats_avant_rerank=resultat.nb_candidats_avant_rerank,
        duree_ms=resultat.duree_ms,
    )
