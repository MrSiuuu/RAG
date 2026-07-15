"""Détection d'intention de rédaction de document (POC, règles regex)."""

import re

_DOC_TRIGGERS = [
    r"\brédige",
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


def detect_document_intent(question: str) -> bool:
    """Détection d'intention par règles. Évolutive vers un classifieur / /doc."""
    return bool(_DOC_RE.search(question or ""))
