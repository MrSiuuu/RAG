"""Point d'entrée : python -m app.ingest [--dry-run] [--doc CHEMIN]"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent.parent

from app.config import settings
from app.ingest.chunk import compter_tokens, construire_chunks, decouper_en_sections
from app.ingest.embed import vectoriser
from app.ingest.index import indexer
from app.ingest.load import charger
from app.ingest.manifest import charger_manifest
from app.ingest.modeles import StatsDocument


def traiter_document(
    doc: dict,
    doc_idx: int,
    chunk_size: int,
    chunk_overlap: int,
) -> StatsDocument | None:
    """Charge, découpe et prépare les chunks d'un document."""
    chemin = RACINE / doc["chemin"]
    if not chemin.exists():
        print(f"  [!] Fichier absent, ignore : {doc['chemin']}")
        return None

    markdown, offsets = charger(chemin, doc["type"])
    sections = decouper_en_sections(markdown, offsets)
    doc_id = str(doc_idx)

    enfants, parents, insecables = construire_chunks(
        doc_id,
        doc["titre"],
        sections,
        chunk_size,
        chunk_overlap,
    )

    stats = StatsDocument(
        titre=doc["titre"],
        chemin=doc["chemin"],
        allowed_groups=doc["allowed_groups"],
        nb_enfants=len(enfants),
        nb_parents=len(parents),
        blocs_insecables=insecables,
        enfants=enfants,
        parents=parents,
    )

    if enfants:
        tokens = [e.nb_tokens for e in enfants]
        stats.tok_moy = sum(tokens) // len(tokens)
        stats.tok_max = max(tokens)

    return stats


def afficher_rapport(
    stats_list: list[StatsDocument],
    dry_run: bool,
    tokens_total: int,
    cout_estime: float,
    duree: float | None = None,
    nb_lots: int | None = None,
) -> None:
    """Affiche le tableau récapitulatif."""
    print("─" * 78)
    print(f"  {'Document':<42} {'enfants':>7} {'parents':>8} {'tok.moy':>8} {'max':>5}")
    print("─" * 78)

    total_insec = 0
    for s in stats_list:
        tag = ""
        if "grp-rh" in s.allowed_groups and "grp-tous" not in s.allowed_groups:
            tag = " [grp-rh]"
        warn = " [!]" if s.blocs_insecables > 0 else ""
        total_insec += s.blocs_insecables
        nom = Path(s.chemin).stem[:40] + tag
        print(
            f"  {nom:<42} {s.nb_enfants:>7} {s.nb_parents:>8} "
            f"{s.tok_moy:>8} {s.tok_max:>5}{warn}"
        )

    nb_enfants = sum(s.nb_enfants for s in stats_list)
    nb_parents = sum(s.nb_parents for s in stats_list)

    print("─" * 78)
    print(f"  TOTAL : {len(stats_list)} documents · {nb_enfants} enfants · {nb_parents} parents")
    print(f"  Tokens à vectoriser : {tokens_total:,}".replace(",", " "))
    print(f"  Coût estimé : {cout_estime:.3f} $")

    if total_insec > 0:
        print(
            f"\n  [!] {total_insec} blocs insécables dépassent CHUNK_SIZE "
            f"(tableaux — c'est normal et voulu)"
        )

    if dry_run:
        print("\n  [DRY-RUN] Aucun appel OpenAI. Aucune écriture en base.")
    else:
        if nb_lots is not None:
            print(f"\n  Vectorisation : {nb_enfants} textes en {nb_lots} lots... OK")
        print("─" * 78)
        print(
            f"  {nb_enfants} chunks indexés depuis {len(stats_list)} documents "
            f"(+ {nb_parents} parents)"
        )
        print(
            f"  Modèle : {settings.embedding_model} · dimension {settings.embedding_dim}"
        )
        print(f"  Tokens : {tokens_total:,} · Coût : {cout_estime:.3f} $".replace(",", " "))
        if duree is not None:
            print(f"  Durée : {duree:.1f} s")
        print("─" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingestion du corpus RAG Dyneff")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Découpe et affiche — aucun appel API, aucune écriture",
    )
    parser.add_argument(
        "--doc",
        type=str,
        default=None,
        help="Indexer un seul document (chemin relatif, ex. corpus/procedure-teletravail.md)",
    )
    args = parser.parse_args()

    if settings.embedding_dim != 1536:
        print("EMBEDDING_DIM doit valoir 1536 (limite d'indexation de pgvector).")
        return 1

    if not args.dry_run and not settings.openai_api_key:
        print("OPENAI_API_KEY absente du .env")
        return 1

    try:
        documents = charger_manifest()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erreur manifest : {exc}")
        return 1

    if args.doc:
        documents = [d for d in documents if d["chemin"] == args.doc]
        if not documents:
            print(f"Document non trouvé dans le manifest : {args.doc}")
            return 1

    stats_list: list[StatsDocument] = []
    metadonnees: list[dict] = []

    for idx, doc in enumerate(documents):
        stats = traiter_document(
            doc, idx, settings.chunk_size, settings.chunk_overlap
        )
        if stats is None:
            continue
        if stats.nb_enfants == 0:
            print(f"  [ERREUR] 0 enfant pour {doc['chemin']}")
            return 1
        stats_list.append(stats)
        metadonnees.append(doc)

    if not stats_list:
        print("Aucun document traité.")
        return 1

    tokens_total = sum(e.nb_tokens for s in stats_list for e in s.enfants)
    cout_estime = tokens_total / 1_000_000 * settings.embedding_prix_mtoken

    if args.dry_run:
        afficher_rapport(stats_list, dry_run=True, tokens_total=tokens_total, cout_estime=cout_estime)
        return 0

    debut = time.time()
    textes = [e.contenu_indexe for s in stats_list for e in s.enfants]
    nb_lots = (len(textes) + settings.embedding_batch - 1) // settings.embedding_batch

    print(f"  Vectorisation : {len(textes)} textes en {nb_lots} lots...", end=" ", flush=True)
    vecteurs = vectoriser(
        textes,
        settings.embedding_model,
        settings.embedding_dim,
        settings.embedding_batch,
    )
    print("OK")

    idx_v = 0
    for stats in stats_list:
        for enfant in stats.enfants:
            enfant.embedding = vecteurs[idx_v]
            idx_v += 1

    result = indexer(stats_list, metadonnees, settings)
    duree = time.time() - debut

    afficher_rapport(
        stats_list,
        dry_run=False,
        tokens_total=tokens_total,
        cout_estime=cout_estime,
        duree=duree,
        nb_lots=nb_lots,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
