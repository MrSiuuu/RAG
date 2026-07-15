"""Découpage structurel du markdown en chunks parent/enfant.

On découpe sur les TITRES, jamais au caractère. Les tableaux sont insécables.
"""

from __future__ import annotations

import re

import tiktoken

from app.ingest.load import page_de
from app.ingest.modeles import ChunkPret, Section

# cl100k_base : les modèles text-embedding-3-* l'utilisent.
# encoding_for_model lève une exception si le nom est inconnu de tiktoken.
ENCODEUR = tiktoken.get_encoding("cl100k_base")

TITRE_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def compter_tokens(texte: str) -> int:
    return len(ENCODEUR.encode(texte))


def fil_ariane(doc_titre: str, chemin: list[str]) -> str:
    """Format EXACT imposé — utilisé pour vectorisation et full-text."""
    return (
        f"Document : {doc_titre}\n"
        f"Section  : {' > '.join(chemin)}\n"
        f"---"
    )


def decouper_en_sections(
    markdown: str,
    offsets_pages: dict[int, int],
) -> list[Section]:
    """Découpe le markdown en sections # / ## / ### (les ####+ sont absorbés)."""
    lignes = markdown.splitlines()
    titres_struct: list[tuple[int, int, str, int]] = []
    offset = 0
    dans_code = False

    for idx, ligne in enumerate(lignes):
        stripped = ligne.strip()
        if stripped.startswith("```"):
            dans_code = not dans_code
        elif not dans_code:
            m = TITRE_RE.match(stripped)
            if m:
                niveau = len(m.group(1))
                if niveau <= 3:
                    titres_struct.append((idx, niveau, m.group(2).strip(), offset))
        offset += len(ligne) + 1

    if not titres_struct:
        return []

    sections: list[Section] = []
    pile: dict[int, str] = {}

    for i, (idx, niveau, titre, off_titre) in enumerate(titres_struct):
        fin = len(lignes)
        for j in range(i + 1, len(titres_struct)):
            pos, niv_suiv, _, _ = titres_struct[j]
            if niv_suiv <= niveau:
                fin = pos
                break
            if niveau < 3 and niv_suiv == niveau + 1:
                fin = pos
                break
            if niveau == 1 and niv_suiv >= 2:
                fin = pos
                break

        contenu = "\n".join(lignes[idx + 1 : fin]).strip()

        pile[niveau] = titre
        for n in list(pile):
            if n > niveau:
                del pile[n]

        if niveau == 1:
            chemin: list[str] = []
        else:
            chemin = [pile[n] for n in sorted(pile) if n > 1 and n <= niveau]

        sections.append(
            Section(
                niveau=niveau,
                titre=titre,
                contenu=contenu,
                chemin=chemin,
                page=page_de(off_titre, offsets_pages),
            )
        )

    return sections


def decouper_en_blocs(contenu: str) -> list[str]:
    """Découpe en blocs insécables : tableaux, code, paragraphes."""
    if not contenu.strip():
        return []

    blocs: list[str] = []
    lignes = contenu.splitlines()
    i = 0

    while i < len(lignes):
        ligne = lignes[i]
        stripped = ligne.strip()

        if stripped.startswith("```"):
            bloc = [ligne]
            i += 1
            while i < len(lignes):
                bloc.append(lignes[i])
                if lignes[i].strip().startswith("```") and len(bloc) > 1:
                    i += 1
                    break
                i += 1
            blocs.append("\n".join(bloc))
            continue

        if stripped.startswith("|"):
            bloc = [ligne]
            i += 1
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                bloc.append(lignes[i])
                i += 1
            blocs.append("\n".join(bloc))
            continue

        bloc = [ligne]
        i += 1
        while i < len(lignes):
            s = lignes[i].strip()
            if not s:
                break
            if s.startswith("```") or s.startswith("|"):
                break
            bloc.append(lignes[i])
            i += 1
        while i < len(lignes) and not lignes[i].strip():
            i += 1
        texte = "\n".join(bloc).strip()
        if texte:
            blocs.append(texte)

    return blocs


def regrouper_en_morceaux(
    blocs: list[str],
    breadcrumb: str,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[str], int]:
    """Remplit gloutonnement des morceaux <= chunk_size tokens (breadcrumb inclus)."""
    if not blocs:
        return [], 0

    prefixe_tokens = compter_tokens(breadcrumb + "\n")
    budget = max(chunk_size - prefixe_tokens, 100)
    morceaux: list[str] = []
    courant: list[str] = []
    courant_tokens = 0
    avertissements = 0

    def tokens_blocs(bl: list[str]) -> int:
        return compter_tokens("\n\n".join(bl))

    for bloc in blocs:
        bt = compter_tokens(bloc)
        if bt > budget:
            if courant:
                morceaux.append("\n\n".join(courant))
                courant = []
                courant_tokens = 0
            morceaux.append(bloc)
            avertissements += 1
            continue

        if courant_tokens + bt + (2 if courant else 0) > budget:
            morceaux.append("\n\n".join(courant))
            overlap: list[str] = []
            overlap_tokens = 0
            for b in reversed(courant):
                bt_o = compter_tokens(b)
                if overlap_tokens + bt_o > chunk_overlap:
                    break
                overlap.insert(0, b)
                overlap_tokens += bt_o
            courant = overlap
            courant_tokens = tokens_blocs(courant)

        courant.append(bloc)
        courant_tokens = tokens_blocs(courant)

    if courant:
        morceaux.append("\n\n".join(courant))

    return morceaux, avertissements


def _fabriquer_enfant(
    doc_id: str,
    cle_base: str,
    cle_parent: str,
    ordre: int,
    doc_titre: str,
    chemin: list[str],
    contenu: str,
    page: int | None,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[ChunkPret], int, int, int]:
    """Crée un ou plusieurs chunks enfants (re-découpe si nécessaire)."""
    bc = fil_ariane(doc_titre, chemin)
    ci = bc + "\n" + contenu
    tokens = compter_tokens(ci)
    max_tok = tokens
    insecables = 0
    chunks: list[ChunkPret] = []

    if tokens <= chunk_size:
        chunks.append(
            ChunkPret(
                cle=cle_base,
                cle_parent=cle_parent,
                type="child",
                ordre=ordre,
                breadcrumb=bc,
                contenu=contenu,
                contenu_indexe=ci,
                nb_tokens=tokens,
                page=page,
            )
        )
        return chunks, max_tok, tokens, insecables

    blocs = decouper_en_blocs(contenu)
    morceaux, insecables = regrouper_en_morceaux(
        blocs, bc, chunk_size, chunk_overlap
    )
    total_tok = 0
    for i, morceau in enumerate(morceaux):
        ci_part = bc + "\n" + morceau
        tok = compter_tokens(ci_part)
        max_tok = max(max_tok, tok)
        total_tok += tok
        chunks.append(
            ChunkPret(
                cle=f"{cle_base}::part{i}",
                cle_parent=cle_parent,
                type="child",
                ordre=ordre + i,
                breadcrumb=bc,
                contenu=morceau,
                contenu_indexe=ci_part,
                nb_tokens=tok,
                page=page,
            )
        )
    moy = total_tok // max(len(chunks), 1)
    return chunks, max_tok, moy, insecables


def construire_chunks(
    doc_id_logique: str,
    doc_titre: str,
    sections: list[Section],
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[ChunkPret], list[ChunkPret], int]:
    """Fabrique parents (##) et enfants (###) avec fil d'Ariane."""
    parents: list[ChunkPret] = []
    enfants: list[ChunkPret] = []
    blocs_insecables = 0
    ordre = 0

    secs_h2 = [s for s in sections if s.niveau == 2]
    secs_h3 = [s for s in sections if s.niveau == 3]
    premier_h2_idx = next((i for i, s in enumerate(sections) if s.niveau == 2), None)

    if premier_h2_idx is not None and premier_h2_idx > 0:
        pre = sections[:premier_h2_idx]
        contenu_pre = "\n\n".join(s.contenu for s in pre if s.contenu).strip()
        if contenu_pre:
            cle_p = f"{doc_id_logique}::p::preambule"
            bc = fil_ariane(doc_titre, ["Préambule"])
            parents.append(
                ChunkPret(
                    cle=cle_p,
                    cle_parent=None,
                    type="parent",
                    ordre=ordre,
                    breadcrumb=bc,
                    contenu=contenu_pre,
                    contenu_indexe=bc + "\n" + contenu_pre,
                    nb_tokens=compter_tokens(bc + "\n" + contenu_pre),
                    page=pre[0].page if pre else None,
                )
            )
            enf, mx, _, ins = _fabriquer_enfant(
                doc_id_logique,
                f"{doc_id_logique}::c::preambule",
                cle_p,
                ordre,
                doc_titre,
                ["Préambule"],
                contenu_pre,
                pre[0].page if pre else None,
                chunk_size,
                chunk_overlap,
            )
            enfants.extend(enf)
            blocs_insecables += ins
            ordre += len(enf)

    for i_h2, sec2 in enumerate(secs_h2):
        sous = [
            s
            for s in secs_h3
            if len(s.chemin) >= 1 and s.chemin[0] == sec2.titre
        ]

        parties_parent = [sec2.contenu] if sec2.contenu else []
        for s3 in sous:
            bloc = f"### {s3.titre}"
            if s3.contenu:
                bloc += f"\n{s3.contenu}"
            parties_parent.append(bloc)
        contenu_parent = "\n\n".join(p for p in parties_parent if p).strip()

        cle_p = f"{doc_id_logique}::p::{i_h2}"
        bc_p = fil_ariane(doc_titre, sec2.chemin)
        parents.append(
            ChunkPret(
                cle=cle_p,
                cle_parent=None,
                type="parent",
                ordre=ordre,
                breadcrumb=bc_p,
                contenu=contenu_parent,
                contenu_indexe=bc_p + "\n" + contenu_parent,
                nb_tokens=compter_tokens(bc_p + "\n" + contenu_parent),
                page=sec2.page,
            )
        )

        if sous:
            for j, s3 in enumerate(sous):
                enf, _, _, ins = _fabriquer_enfant(
                    doc_id_logique,
                    f"{doc_id_logique}::c::{i_h2}::{j}",
                    cle_p,
                    ordre,
                    doc_titre,
                    s3.chemin,
                    s3.contenu,
                    s3.page,
                    chunk_size,
                    chunk_overlap,
                )
                enfants.extend(enf)
                blocs_insecables += ins
                ordre += len(enf)
        else:
            enf, _, _, ins = _fabriquer_enfant(
                doc_id_logique,
                f"{doc_id_logique}::c::{i_h2}::solo",
                cle_p,
                ordre,
                doc_titre,
                sec2.chemin,
                sec2.contenu or contenu_parent,
                sec2.page,
                chunk_size,
                chunk_overlap,
            )
            enfants.extend(enf)
            blocs_insecables += ins
            ordre += len(enf)

    return enfants, parents, blocs_insecables
