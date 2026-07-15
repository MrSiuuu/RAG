"""Assemblage des passages parents pour la lecture du LLM."""


def assembler_contexte(
    chunks_parents: list[dict],
    chunks_enfants: list[dict],
) -> str:
    """Assemble les passages en un bloc lisible par le LLM.

    On donne les PARENTS (sections complètes). L'enfant sert à trouver
    et à citer — pas à lire hors contexte.
    """
    parents_par_id = {p["id"]: p for p in chunks_parents}
    passages: list[dict] = []
    vus: set[int] = set()

    for enfant in chunks_enfants:
        pid = enfant.get("parent_id")
        if pid is not None and pid in parents_par_id:
            if pid not in vus:
                vus.add(pid)
                passages.append(parents_par_id[pid])
        else:
            if enfant["id"] not in vus:
                vus.add(enfant["id"])
                passages.append(enfant)

    blocs: list[str] = []
    for i, p in enumerate(passages, start=1):
        blocs.append(
            f"─── PASSAGE {i} ───\n"
            f"{p['breadcrumb']}\n"
            f"{p['contenu']}"
        )
    return "\n\n".join(blocs)
