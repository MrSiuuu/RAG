"""Transmission d'une question au service métier."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db import engine
from app.security.deps import admin_requis, utilisateur_courant
from app.services import SERVICES

router = APIRouter(tags=["demandes"])


class RequeteDemande(BaseModel):
    question: str = Field(..., min_length=1)
    service: str = Field(default="rh")


@router.post("/api/demandes")
def creer_demande(
    corps: RequeteDemande,
    user: dict = Depends(utilisateur_courant),
) -> dict:
    """Enregistre une demande « je ne sais pas → transmettre au service »."""
    service = (corps.service or "rh").strip().lower()
    if service not in SERVICES:
        service = "rh"

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO demandes (user_email, service, question)
                VALUES (:email, :service, :question)
                RETURNING id
                """
            ),
            {
                "email": user.get("email"),
                "service": service,
                "question": corps.question.strip(),
            },
        ).first()

    return {
        "ok": True,
        "id": row[0],
        "service": service,
        "label": SERVICES[service]["label"],
    }


@router.get("/api/demandes")
def lister_demandes(admin: dict = Depends(admin_requis)) -> list[dict]:
    """Liste les demandes transmises — réservé aux administrateurs."""
    _ = admin
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, user_email, service, question, cree_le
                FROM demandes
                ORDER BY cree_le DESC, id DESC
                """
            )
        ).mappings().all()

    return [
        {
            "id": r["id"],
            "user_email": r["user_email"],
            "service": r["service"],
            "question": r["question"],
            "cree_le": r["cree_le"].isoformat() if r["cree_le"] else None,
        }
        for r in rows
    ]
