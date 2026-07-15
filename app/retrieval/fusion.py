"""Reciprocal Rank Fusion — fusionner vectoriel + plein texte sans librairie."""


def rrf(
    liste_vecteur: list[dict],
    liste_texte: list[dict],
    k: int = 60,
) -> list[dict]:
    """Fusionne deux listes classées en une seule via RRF."""
    scores: dict[int, float] = {}
    meta: dict[int, dict] = {}

    for rang, chunk in enumerate(liste_vecteur, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rang)
        meta[chunk["id"]] = chunk

    for rang, chunk in enumerate(liste_texte, start=1):
        scores[chunk["id"]] = scores.get(chunk["id"], 0) + 1 / (k + rang)
        if chunk["id"] not in meta:
            meta[chunk["id"]] = chunk

    fusionnes = sorted(meta.values(), key=lambda c: scores[c["id"]], reverse=True)
    for chunk in fusionnes:
        chunk["score_rrf"] = scores[chunk["id"]]

    return fusionnes
