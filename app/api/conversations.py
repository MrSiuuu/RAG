"""CRUD conversations — persistance pour la sidebar."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.db import engine
from app.security.deps import utilisateur_courant

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("")
def creer_conversation(user: dict = Depends(utilisateur_courant)) -> dict:
    """Crée une conversation vide pour l'utilisateur courant."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO conversations (user_id, titre)
                VALUES (:uid, :titre)
                RETURNING id, titre, cree_le
                """
            ),
            {"uid": user["id"], "titre": "Nouvelle conversation"},
        ).mappings().one()
    return {
        "id": row["id"],
        "titre": None if row["titre"] == "Nouvelle conversation" else row["titre"],
        "cree_le": row["cree_le"].isoformat() if row["cree_le"] else None,
    }


@router.get("")
def lister_conversations(user: dict = Depends(utilisateur_courant)) -> list[dict]:
    """Liste les conversations de l'utilisateur, plus récentes d'abord."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, titre, cree_le, maj_le
                FROM conversations
                WHERE user_id = :uid
                ORDER BY COALESCE(maj_le, cree_le) DESC, id DESC
                """
            ),
            {"uid": user["id"]},
        ).mappings().all()
    out = []
    for r in rows:
        titre = r["titre"]
        if titre in (None, "", "Nouvelle conversation", "Conversation"):
            titre = "Nouvelle conversation"
        out.append(
            {
                "id": r["id"],
                "titre": titre,
                "cree_le": r["cree_le"].isoformat() if r["cree_le"] else None,
            }
        )
    return out


@router.get("/{conversation_id}/messages")
def messages_conversation(
    conversation_id: int,
    user: dict = Depends(utilisateur_courant),
) -> list[dict]:
    """Messages d'une conversation (propriétaire uniquement)."""
    with engine.connect() as conn:
        own = conn.execute(
            text(
                "SELECT id FROM conversations WHERE id = :cid AND user_id = :uid"
            ),
            {"cid": conversation_id, "uid": user["id"]},
        ).first()
        if not own:
            raise HTTPException(status_code=404, detail="Conversation introuvable")

        rows = conn.execute(
            text(
                """
                SELECT role, contenu, sources, a_repondu, cree_le,
                       fichier_genere, latence_ms
                FROM messages
                WHERE conversation_id = :cid
                ORDER BY id ASC
                """
            ),
            {"cid": conversation_id},
        ).mappings().all()

    result = []
    for r in rows:
        result.append(
            {
                "role": r["role"],
                "contenu": r["contenu"],
                "sources": r["sources"],
                "a_repondu": r["a_repondu"],
                "cree_le": r["cree_le"].isoformat() if r["cree_le"] else None,
                "fichier_genere": bool(r["fichier_genere"]),
                "latence_ms": r["latence_ms"],
            }
        )
    return result


@router.delete("/{conversation_id}")
def supprimer_conversation(
    conversation_id: int,
    user: dict = Depends(utilisateur_courant),
) -> dict:
    """Supprime une conversation et ses messages (cascade)."""
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                DELETE FROM conversations
                WHERE id = :cid AND user_id = :uid
                RETURNING id
                """
            ),
            {"cid": conversation_id, "uid": user["id"]},
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"ok": True, "id": conversation_id}
