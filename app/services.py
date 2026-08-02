"""Catalogue des services → groupes ACL (self-service ingestion)."""

from __future__ import annotations

SERVICES: dict[str, dict] = {
    "rh": {"label": "Ressources Humaines", "groups": ["grp-rh"]},
    "cse": {"label": "CSE", "groups": ["grp-cse"]},
    "hse": {"label": "HSE", "groups": ["grp-hse"]},
    "juridique": {"label": "Juridique", "groups": ["grp-juridique"]},
    "public": {"label": "Public (tous)", "groups": ["grp-tous"]},
}


def groupes_du_service(service: str) -> list[str]:
    """Renvoie les groupes ACL du service. KeyError si inconnu."""
    return list(SERVICES[service]["groups"])


def label_du_service(service: str) -> str:
    return SERVICES[service]["label"]
