"""Chargement des fichiers corpus → markdown (+ pagination PDF)."""

from pathlib import Path


def page_de(offset: int, offsets_pages: dict[int, int]) -> int | None:
    """Numéro de page à un offset caractère. None si pas de pagination."""
    if not offsets_pages:
        return None
    page: int | None = None
    for debut in sorted(offsets_pages):
        if debut <= offset:
            page = offsets_pages[debut]
        else:
            break
    return page


def charger(chemin: Path, type_doc: str) -> tuple[str, dict[int, int]]:
    """Renvoie (markdown, offsets_pages).

    offsets_pages : {offset_caractere_de_debut: numero_de_page}
                    dictionnaire VIDE pour un .md (pas de pagination)
    """
    if type_doc == "md":
        return chemin.read_text(encoding="utf-8"), {}

    if type_doc == "pdf":
        import pymupdf4llm

        pages = pymupdf4llm.to_markdown(str(chemin), page_chunks=True)
        morceaux: list[str] = []
        offsets: dict[int, int] = {}
        curseur = 0
        for p in pages:
            texte = p["text"]
            offsets[curseur] = p["metadata"]["page"]
            morceaux.append(texte)
            curseur += len(texte) + 2
        return "\n\n".join(morceaux), offsets

    raise ValueError(f"Type de document non supporté : {type_doc}")
