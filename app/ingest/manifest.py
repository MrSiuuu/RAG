"""Lecture et validation du manifest.json avant indexation."""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
MANIFEST_DEFAUT = RACINE / "corpus" / "manifest.json"


def charger_manifest(chemin: Path | None = None) -> list[dict]:
    """Lit le manifest et renvoie la liste des documents.

    GARDE-FOU DE SÉCURITÉ — refuse d'indexer si un document 'confidentiel'
    est accessible à 'grp-tous'. Défense en profondeur : le validateur
    scripts/valider_corpus.py peut ne pas avoir été lancé.
    """
    chemin_manifest = chemin or MANIFEST_DEFAUT
    if not chemin_manifest.exists():
        raise FileNotFoundError(f"Manifest introuvable : {chemin_manifest}")

    with chemin_manifest.open(encoding="utf-8") as f:
        data = json.load(f)

    documents = data.get("documents", [])
    if not documents:
        raise ValueError("Le manifest ne contient aucun document.")

    for doc in documents:
        if doc.get("sensibilite") == "confidentiel" and "grp-tous" in doc.get(
            "allowed_groups", []
        ):
            raise ValueError(
                f"REFUS D'INDEXER — {doc['chemin']} est confidentiel "
                f"mais accessible a grp-tous. Corrige le manifest."
            )

    return documents
