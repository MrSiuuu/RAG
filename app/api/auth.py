"""Authentification : login + me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.db import engine
from app.security.deps import utilisateur_courant
from app.security.jwt import creer_token
from app.security.passwords import verifier_mot_de_passe

router = APIRouter(tags=["auth"])


class RequeteLogin(BaseModel):
    email: str = Field(..., min_length=3)
    mot_de_passe: str = Field(..., min_length=1)


@router.post("/auth/login")
def login(corps: RequeteLogin) -> dict:
    """Email + mot de passe → jeton JWT + profil."""
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, email, nom, mot_de_passe, groupes, role
                FROM users
                WHERE lower(email) = lower(:email)
                """
            ),
            {"email": corps.email.strip()},
        ).mappings().first()

    if not row or not verifier_mot_de_passe(corps.mot_de_passe, row["mot_de_passe"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")

    user = {
        "id": row["id"],
        "email": row["email"],
        "nom": row["nom"],
        "groupes": list(row["groupes"] or []),
        "role": row["role"],
    }
    token = creer_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nom": user["nom"],
            "groupes": user["groupes"],
            "role": user["role"],
        },
    }


@router.get("/auth/me")
def me(user: dict = Depends(utilisateur_courant)) -> dict:
    """Profil de l'utilisateur authentifié."""
    return user
