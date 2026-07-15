"""Citations structurées à partir des chunks enfants (précis)."""

from __future__ import annotations

from pydantic import BaseModel


class Citation(BaseModel):
    chunk_id: int
    document: str
    section: str
    page: int | None
    extrait: str


def _parser_breadcrumb(breadcrumb: str) -> tuple[str, str]:
    """Extrait document + section depuis le fil d'Ariane d'ingestion."""
    document = ""
    section = ""
    for ligne in breadcrumb.split("\n"):
        ligne = ligne.strip()
        if ligne.startswith("Document :"):
            document = ligne.removeprefix("Document :").strip()
        elif ligne.startswith("Section"):
            _, _, reste = ligne.partition(":")
            section = reste.strip()
    return document, section


def extraire_citations(chunks_enfants: list[dict]) -> list[Citation]:
    """Construit les citations à partir des ENFANTS — pas des parents."""
    citations: list[Citation] = []
    for enfant in chunks_enfants:
        document, section = _parser_breadcrumb(enfant.get("breadcrumb", ""))
        citations.append(
            Citation(
                chunk_id=enfant["id"],
                document=document,
                section=section,
                page=enfant.get("page"),
                extrait=(enfant.get("contenu") or "")[:200],
            )
        )
    return citations
