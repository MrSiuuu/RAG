"""Orchestration du pipeline de retrieval complet."""

from __future__ import annotations

import time
from dataclasses import dataclass

import psycopg.rows

from app.config import Settings
from app.ingest.embed import vectoriser
from app.retrieval.fulltext import recherche_plein_texte
from app.retrieval.fusion import rrf
from app.retrieval.rerank import reranker
from app.retrieval.vector import recherche_vectorielle


@dataclass
class ResultatRecherche:
    chunks_enfants: list[dict]
    chunks_parents: list[dict]
    question_recrite: str
    nb_candidats_avant_rerank: int
    duree_ms: int


def charger_parents(conn, chunks_enfants: list[dict]) -> list[dict]:
    """Charge les sections parentes pour le contexte élargi (CDC 4)."""
    parent_ids = list(
        {c["parent_id"] for c in chunks_enfants if c.get("parent_id") is not None}
    )
    if not parent_ids:
        return []

    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            "SELECT * FROM chunks WHERE id = ANY(%s)",
            (parent_ids,),
        )
        return [dict(l) for l in cur.fetchall()]


def rechercher(
    conn,
    question: str,
    settings: Settings,
) -> ResultatRecherche:
    """Pipeline : vectoriel + full-text → RRF → rerank → parents.

    Corpus ouvert : aucun filtre de groupes / service.
    """
    debut = time.perf_counter()
    question = question.strip()

    vecteur = vectoriser(
        [question],
        settings.embedding_model,
        settings.embedding_dim,
        taille_lot=1,
    )[0]

    res_vecteur = recherche_vectorielle(conn, vecteur, settings.top_k)
    res_texte = recherche_plein_texte(conn, question, settings.top_k)

    candidats = rrf(res_vecteur, res_texte)[: settings.top_k]
    nb_candidats = len(candidats)

    if not candidats:
        return ResultatRecherche(
            chunks_enfants=[],
            chunks_parents=[],
            question_recrite=question,
            nb_candidats_avant_rerank=0,
            duree_ms=int((time.perf_counter() - debut) * 1000),
        )

    enfants = reranker(question, candidats, settings.top_n, settings.llm_model_fast)
    parents = charger_parents(conn, enfants)

    return ResultatRecherche(
        chunks_enfants=enfants,
        chunks_parents=parents,
        question_recrite=question,
        nb_candidats_avant_rerank=nb_candidats,
        duree_ms=int((time.perf_counter() - debut) * 1000),
    )
