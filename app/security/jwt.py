"""Création et décodage des jetons JWT (PyJWT, pas python-jose)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import settings


def creer_token(user: dict) -> str:
    """Signe un jeton contenant l'identité et les groupes (bracelet de festival)."""
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "nom": user["nom"],
        "groupes": list(user["groupes"]),
        "role": user["role"],
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decoder_token(token: str) -> dict:
    """Décode le jeton ou lève 401 si invalide / expiré."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré") from e
