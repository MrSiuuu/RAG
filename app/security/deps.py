"""Dépendances FastAPI : utilisateur courant et admin requis."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.security.jwt import decoder_token


def utilisateur_courant(
    authorization: str | None = Header(default=None),
) -> dict:
    """Extrait l'utilisateur depuis `Authorization: Bearer <token>`."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Non authentifié")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    data = decoder_token(token)
    try:
        user_id = int(data["sub"])
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=401, detail="Jeton invalide") from e
    return {
        "id": user_id,
        "email": data.get("email", ""),
        "nom": data.get("nom", ""),
        "groupes": list(data.get("groupes") or []),
        "role": data.get("role", "user"),
    }


def admin_requis(user: dict = Depends(utilisateur_courant)) -> dict:
    """Refuse (403) si l'utilisateur n'est pas admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user
