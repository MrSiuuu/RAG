"""Validation des groupes utilisateur avant toute recherche."""


def valider_groupes(groupes: list[str]) -> list[str]:
    """Valide et normalise la liste des groupes d'un utilisateur.

    Règles :
    - Chaque groupe doit commencer par 'grp-'
    - Liste vide → ValueError (pas de groupes = pas d'accès)
    - Doublons supprimés, ordre trié
    """
    if not groupes:
        raise ValueError("Aucun groupe fourni — accès refusé.")

    normalises: list[str] = []
    for g in groupes:
        if not g.startswith("grp-"):
            raise ValueError(f"Groupe invalide : '{g}' (doit commencer par 'grp-')")
        if g not in normalises:
            normalises.append(g)

    return sorted(normalises)
