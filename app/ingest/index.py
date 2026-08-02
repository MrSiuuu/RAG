"""Écriture en base — TRUNCATE puis insertion idempotente."""

from __future__ import annotations

import psycopg

from app.config import Settings
from app.ingest.modeles import ChunkPret, StatsDocument


def vers_litteral_vecteur(v: list[float]) -> str:
    """Forme textuelle pgvector '[0.1,0.2,...]' castée en ::vector."""
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


def _url_psycopg(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://")


def indexer(
    stats_docs: list[StatsDocument],
    metadonnees: list[dict],
    settings: Settings,
) -> dict:
    """Écrit tout en base. Reconstruction complète à chaque run."""
    url = _url_psycopg(settings.database_url)
    nb_enfants = 0
    nb_parents = 0

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE chunks, documents RESTART IDENTITY CASCADE")

            doc_ids: dict[str, int] = {}
            for meta, stats in zip(metadonnees, stats_docs, strict=True):
                cur.execute(
                    """
                    INSERT INTO documents (
                        chemin, titre, type, source, sensibilite, allowed_groups
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        meta["chemin"],
                        meta["titre"],
                        meta["type"],
                        meta["source"],
                        meta["sensibilite"],
                        meta["allowed_groups"],
                    ),
                )
                doc_id = cur.fetchone()[0]
                doc_ids[meta["chemin"]] = doc_id

                map_cle_parent: dict[str, int] = {}
                for p in stats.parents:
                    cur.execute(
                        """
                        INSERT INTO chunks (
                            document_id, type, parent_id, ordre,
                            breadcrumb, contenu, contenu_indexe, page, nb_tokens,
                            embedding, embedding_model, embedding_dim, allowed_groups
                        ) VALUES (
                            %s, 'parent', NULL, %s,
                            %s, %s, %s, %s, %s,
                            NULL, NULL, NULL, %s
                        ) RETURNING id
                        """,
                        (
                            doc_id,
                            p.ordre,
                            p.breadcrumb,
                            p.contenu,
                            p.contenu_indexe,
                            p.page,
                            p.nb_tokens,
                            meta["allowed_groups"],
                        ),
                    )
                    map_cle_parent[p.cle] = cur.fetchone()[0]
                    nb_parents += 1

                lignes_enfants = []
                for e in stats.enfants:
                    parent_id = map_cle_parent.get(e.cle_parent or "")
                    if e.embedding is None:
                        raise ValueError(f"Enfant sans embedding : {e.cle}")
                    lignes_enfants.append(
                        (
                            doc_id,
                            parent_id,
                            e.ordre,
                            e.breadcrumb,
                            e.contenu,
                            e.contenu_indexe,
                            e.page,
                            e.nb_tokens,
                            vers_litteral_vecteur(e.embedding),
                            settings.embedding_model,
                            settings.embedding_dim,
                            meta["allowed_groups"],
                        )
                    )

                if lignes_enfants:
                    cur.executemany(
                        """
                        INSERT INTO chunks (
                            document_id, type, parent_id, ordre,
                            breadcrumb, contenu, contenu_indexe, page, nb_tokens,
                            embedding, embedding_model, embedding_dim, allowed_groups
                        ) VALUES (
                            %s, 'child', %s, %s,
                            %s, %s, %s, %s, %s,
                            %s::vector, %s, %s, %s
                        )
                        """,
                        lignes_enfants,
                    )
                    nb_enfants += len(lignes_enfants)

                cur.execute(
                    """
                    UPDATE documents SET nb_chunks = %s WHERE id = %s
                    """,
                    (len(stats.enfants), doc_id),
                )

            conn.commit()

    return {
        "nb_enfants": nb_enfants,
        "nb_parents": nb_parents,
        "nb_documents": len(stats_docs),
    }


def indexer_un_document(
    doc_titre: str,
    chemin: str,
    type_doc: str,
    source: str,
    sensibilite: str,
    allowed_groups: list[str],
    chunks_parents: list[ChunkPret],
    chunks_enfants: list[ChunkPret],
    settings: Settings,
) -> dict:
    """Insert / remplace UN document — sans TRUNCATE des autres."""
    url = _url_psycopg(settings.database_url)

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (
                    chemin, titre, type, source, sensibilite, allowed_groups, nb_chunks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chemin) DO UPDATE SET
                    titre = EXCLUDED.titre,
                    type = EXCLUDED.type,
                    source = EXCLUDED.source,
                    sensibilite = EXCLUDED.sensibilite,
                    allowed_groups = EXCLUDED.allowed_groups,
                    nb_chunks = EXCLUDED.nb_chunks,
                    indexe_le = now()
                RETURNING id
                """,
                (
                    chemin,
                    doc_titre,
                    type_doc,
                    source,
                    sensibilite,
                    allowed_groups,
                    len(chunks_enfants),
                ),
            )
            document_id = cur.fetchone()[0]

            # Idempotence : on remplace les chunks de CE document uniquement.
            cur.execute(
                "DELETE FROM chunks WHERE document_id = %s",
                (document_id,),
            )

            map_cle_parent: dict[str, int] = {}
            for p in chunks_parents:
                cur.execute(
                    """
                    INSERT INTO chunks (
                        document_id, type, parent_id, ordre,
                        breadcrumb, contenu, contenu_indexe, page, nb_tokens,
                        embedding, embedding_model, embedding_dim, allowed_groups
                    ) VALUES (
                        %s, 'parent', NULL, %s,
                        %s, %s, %s, %s, %s,
                        NULL, NULL, NULL, %s
                    ) RETURNING id
                    """,
                    (
                        document_id,
                        p.ordre,
                        p.breadcrumb,
                        p.contenu,
                        p.contenu_indexe,
                        p.page,
                        p.nb_tokens,
                        allowed_groups,
                    ),
                )
                map_cle_parent[p.cle] = cur.fetchone()[0]

            lignes_enfants = []
            for e in chunks_enfants:
                parent_id = map_cle_parent.get(e.cle_parent or "")
                if e.embedding is None:
                    raise ValueError(f"Enfant sans embedding : {e.cle}")
                lignes_enfants.append(
                    (
                        document_id,
                        parent_id,
                        e.ordre,
                        e.breadcrumb,
                        e.contenu,
                        e.contenu_indexe,
                        e.page,
                        e.nb_tokens,
                        vers_litteral_vecteur(e.embedding),
                        settings.embedding_model,
                        settings.embedding_dim,
                        allowed_groups,
                    )
                )

            if lignes_enfants:
                cur.executemany(
                    """
                    INSERT INTO chunks (
                        document_id, type, parent_id, ordre,
                        breadcrumb, contenu, contenu_indexe, page, nb_tokens,
                        embedding, embedding_model, embedding_dim, allowed_groups
                    ) VALUES (
                        %s, 'child', %s, %s,
                        %s, %s, %s, %s, %s,
                        %s::vector, %s, %s, %s
                    )
                    """,
                    lignes_enfants,
                )

            conn.commit()

    return {
        "document_id": document_id,
        "nb_parents": len(chunks_parents),
        "nb_enfants": len(chunks_enfants),
    }
