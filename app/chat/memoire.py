"""Helpers mémoire conversation (chargement / écriture messages)."""

from __future__ import annotations

import json

import psycopg
import psycopg.rows


def assurer_conversation(conn, user_id: int, conversation_id: int | None) -> int:
    """Réutilise une conversation existante ou en crée une."""
    with conn.cursor() as cur:
        if conversation_id is not None:
            cur.execute(
                "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
                (conversation_id, user_id),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        cur.execute(
            """
            INSERT INTO conversations (user_id, titre)
            VALUES (%s, %s)
            RETURNING id
            """,
            (user_id, "Nouvelle conversation"),
        )
        return cur.fetchone()[0]


def fixer_titre_si_vide(conn, conversation_id: int, question: str) -> None:
    """Titre = ~50 premiers caractères de la première question."""
    titre = (question or "").strip().replace("\n", " ")[:50]
    if not titre:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE conversations
            SET titre = %s, maj_le = now()
            WHERE id = %s
              AND (
                titre IS NULL
                OR titre = ''
                OR titre = 'Conversation'
                OR titre = 'Nouvelle conversation'
              )
            """,
            (titre, conversation_id),
        )
        cur.execute(
            "UPDATE conversations SET maj_le = now() WHERE id = %s",
            (conversation_id,),
        )


def charger_historique(conn, conversation_id: int, limite: int = 6) -> list[dict]:
    """Derniers tours [{role, contenu}] pour le pré-traitement."""
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT role, contenu
            FROM messages
            WHERE conversation_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (conversation_id, limite),
        )
        rows = list(reversed(cur.fetchall()))
    return [{"role": r["role"], "contenu": r["contenu"]} for r in rows]


def enregistrer_message(
    conn,
    *,
    conversation_id: int,
    role: str,
    contenu: str,
    question_reecrite: str | None = None,
    a_repondu: bool | None = None,
    sources: list | None = None,
    web_active: bool = False,
    latence_ms: int | None = None,
    modele: str | None = None,
    service: str | None = None,
    fichier_genere: bool = False,
    chunk_ids: list[int] | None = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO messages (
                conversation_id, role, contenu, question_reecrite,
                a_repondu, sources, web_active, latence_ms, modele,
                service, fichier_genere, chunk_ids
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s::jsonb, %s, %s, %s,
                %s, %s, %s
            )
            RETURNING id
            """,
            (
                conversation_id,
                role,
                contenu,
                question_reecrite,
                a_repondu,
                json.dumps(sources, ensure_ascii=False) if sources is not None else None,
                web_active,
                latence_ms,
                modele,
                service,
                fichier_genere,
                chunk_ids or [],
            ),
        )
        return cur.fetchone()[0]


_GROUPES_VERS_SERVICE = {
    "grp-rh": "rh",
    "grp-cse": "cse",
    "grp-hse": "hse",
    "grp-juridique": "juridique",
    "grp-tous": "public",
}


def service_depuis_chunks(chunks: list[dict]) -> str | None:
    """Déduit le service dominant des étiquettes allowed_groups des chunks."""
    compte: dict[str, int] = {}
    for c in chunks or []:
        for g in c.get("allowed_groups") or []:
            court = _GROUPES_VERS_SERVICE.get(g)
            if court and court != "public":
                compte[court] = compte.get(court, 0) + 1
    if not compte:
        return None
    return max(compte, key=compte.get)
