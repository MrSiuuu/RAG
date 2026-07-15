"""Recherche par proximité de sens (pgvector + cosine)."""

from __future__ import annotations

import psycopg.rows


def vers_litteral_vecteur(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def recherche_vectorielle(
    conn,
    vecteur_question: list[float],
    groupes_utilisateur: list[str],
    top_k: int,
) -> list[dict]:
    """Cherche les top_k chunks enfants les plus proches.

    Le filtre ACL est dans le WHERE, AVANT le ORDER BY — jamais après.
    """
    vecteur_str = vers_litteral_vecteur(vecteur_question)

    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT
                c.id,
                c.document_id,
                c.breadcrumb,
                c.contenu,
                c.contenu_indexe,
                c.parent_id,
                c.page,
                c.allowed_groups,
                (c.embedding <=> %s::vector) AS score_vecteur
            FROM chunks c
            WHERE c.type = 'child'
              AND c.embedding IS NOT NULL
              AND c.allowed_groups && %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (vecteur_str, groupes_utilisateur, vecteur_str, top_k),
        )
        lignes = cur.fetchall()

    return [_normaliser_ligne(dict(l)) for l in lignes]


def _normaliser_ligne(ligne: dict) -> dict:
    if ligne.get("score_vecteur") is not None:
        ligne["score_vecteur"] = float(ligne["score_vecteur"])
    if ligne.get("allowed_groups") is not None:
        ligne["allowed_groups"] = list(ligne["allowed_groups"])
    return ligne
