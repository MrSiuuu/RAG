"""Vectorisation OpenAI — dimensions=1536 obligatoire."""

import time

from openai import OpenAI


def vectoriser(
    textes: list[str],
    modele: str,
    dimension: int,
    taille_lot: int = 64,
) -> list[list[float]]:
    """Appelle l'API OpenAI par lots. Renvoie les vecteurs DANS L'ORDRE d'entrée."""
    if not textes:
        return []

    client = OpenAI()
    vecteurs: list[list[float]] = []

    for debut in range(0, len(textes), taille_lot):
        lot = textes[debut : debut + taille_lot]

        for tentative in range(5):
            try:
                reponse = client.embeddings.create(
                    model=modele,
                    input=lot,
                    dimensions=dimension,
                )
                break
            except Exception:
                if tentative == 4:
                    raise
                time.sleep(2**tentative)

        for item in sorted(reponse.data, key=lambda d: d.index):
            vecteurs.append(item.embedding)

    for v in vecteurs:
        if len(v) != dimension:
            raise ValueError(
                f"Dimension recue : {len(v)}, attendue : {dimension}. "
                f"Le parametre dimensions= n'a pas ete pris en compte."
            )

    return vecteurs
