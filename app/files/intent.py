"""Détection d'intention de rédaction de document (regex + slash /doc)."""

from __future__ import annotations

import re

_DOC_TRIGGERS = [
    r"\brédige",
    r"\bredige",
    r"\brediger",
    r"\brédigez",
    r"\bgénère",
    r"\bgenerer",
    r"\bgénérer",
    r"\bécris\b",
    r"\becrire\b",
    r"\bécrire\b",
    r"\bprépare",
    r"\bpreparer",
    r"\bfais(?:-| )?(?:moi )?une note",
    r"\bnote de synthèse",
    r"\bcourrier\b",
    r"\blettre\b",
    r"\bmodèle de\b",
    r"\brédiger?\b",
    r"\bfiche d'?onboarding",
    r"\bfiche de\b",
]
_DOC_RE = re.compile("|".join(_DOC_TRIGGERS), re.IGNORECASE)


def preparer_intention_document(message: str) -> tuple[bool, str]:
    """Retourne (force_doc, message_sans_slash).

    Si le message commence par `/doc`, force l'intention document et retire
    le préfixe avant le reste du traitement.
    """
    texte = (message or "").strip()
    if texte.lower().startswith("/doc"):
        reste = texte[4:].strip()
        return True, reste
    return False, texte


def detect_document_intent(question: str) -> bool:
    """True si intention de rédaction (regex). `/doc` est géré en amont."""
    return bool(_DOC_RE.search(question or ""))
