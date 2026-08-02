"""Hachage / vérification des mots de passe (bcrypt, pas passlib)."""

from __future__ import annotations

import bcrypt


def verifier_mot_de_passe(clair: str, hash_bcrypt: str) -> bool:
    """Compare un mot de passe en clair au hash bcrypt stocké."""
    try:
        return bcrypt.checkpw(
            clair.encode("utf-8"),
            hash_bcrypt.encode("utf-8"),
        )
    except Exception:
        return False
