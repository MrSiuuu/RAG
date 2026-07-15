"""LLM → payload JSON structuré pour un document RH."""

from __future__ import annotations

import json

from openai import OpenAI

from app.config import settings
from app.llm.generate import _appel_avec_temperature

SYSTEM_DOC = """Tu es un assistant RH qui rédige des documents professionnels pour Dyneff.
Tu rédiges UNIQUEMENT à partir des extraits fournis. Tu n'inventes aucune règle, aucun chiffre,
aucune procédure absente des extraits. Le style est sobre et professionnel, en français.

Tu réponds STRICTEMENT en JSON valide, sans aucun texte autour, au format exact :
{
  "type": "courrier" ou "note",
  "titre": "titre du document",
  "objet": "objet du courrier, ou null",
  "destinataire": "bloc destinataire (nom, fonction), ou null",
  "blocs": [
    {"type": "paragraphe", "texte": "..."},
    {"type": "titre", "texte": "..."},
    {"type": "liste", "items": ["...", "..."]},
    {"type": "tableau", "entetes": ["...", "..."], "lignes": [["...", "..."]]}
  ],
  "signature": "bloc de signature, ou null"
}

Pour un refus, expose les motifs prévus par la procédure (extraits). Reste factuel.
Cite les chiffres exacts présents dans les extraits (ex. plafond 2 jours/semaine)."""


def generate_document_payload(question: str, contexte: str) -> dict:
    """Génère le formulaire JSON du document — temperature 0 si le modèle l'accepte."""
    client = OpenAI()
    resp = _appel_avec_temperature(
        client,
        model=settings.llm_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_DOC},
            {
                "role": "user",
                "content": f"Demande :\n{question}\n\nExtraits disponibles :\n{contexte}",
            },
        ],
    )
    contenu = resp.choices[0].message.content or "{}"
    return json.loads(contenu)
