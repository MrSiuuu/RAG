"""Recherche plein texte française (tsvector + plainto_tsquery)."""

from __future__ import annotations

import psycopg.rows


def recherche_plein_texte(
    conn,
    question: str,
    groupes_utilisateur: list[str],
    top_k: int,
) -> list[dict]:
    """Cherche par mots exacts avec le dictionnaire 'french' de Postgres."""
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
                ts_rank(c.tsv, plainto_tsquery('french', %s)) AS score_texte
            FROM chunks c
            WHERE c.type = 'child'
              AND c.allowed_groups && %s
              AND c.tsv @@ plainto_tsquery('french', %s)
            ORDER BY score_texte DESC
            LIMIT %s
            """,
            (question, groupes_utilisateur, question, top_k),
        )
        lignes = cur.fetchall()

    resultats = []
    for l in lignes:
        d = dict(l)
        if d.get("score_texte") is not None:
            d["score_texte"] = float(d["score_texte"])
        if d.get("allowed_groups") is not None:
            d["allowed_groups"] = list(d["allowed_groups"])
        resultats.append(d)
    return resultats
