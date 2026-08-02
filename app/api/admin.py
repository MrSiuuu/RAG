"""API admin : ingestion self-service + statistiques dashboard."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.ingest.chunk import construire_chunks, decouper_en_sections
from app.ingest.embed import vectoriser
from app.ingest.index import indexer_un_document
from app.ingest.load import charger
from app.security.deps import admin_requis, utilisateur_courant
from app.services import SERVICES, groupes_du_service, label_du_service

router = APIRouter(prefix="/api/admin", tags=["admin"])

RACINE = Path(__file__).resolve().parent.parent.parent
UPLOAD_ROOT = RACINE / "corpus" / "uploads"

_GAP_MAP = [
    (re.compile(r"mobilit[eé].*international|expatriation", re.I), "Procédure mobilité internationale"),
    (re.compile(r"proche\s+aidant", re.I), "Procédure congé proche aidant"),
    (re.compile(r"t[eé]l[eé]travail.*[eé]tranger|international", re.I), "Barème télétravail international"),
    (re.compile(r"paternit", re.I), "Procédure congé paternité"),
    (re.compile(r"int[eé]ressement", re.I), "Accord d'intéressement"),
    (re.compile(r"voiture\s+de\s+fonction", re.I), "Politique véhicule de fonction"),
    (re.compile(r"harc[eè]lement", re.I), "Procédure harcèlement"),
]


def _slug_fichier(nom: str) -> str:
    base = Path(nom).name
    stem = Path(base).stem
    ext = Path(base).suffix.lower()
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem).strip("-").lower() or "document"
    return f"{stem}{ext}"


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    service: str = Form(...),
    sensibilite: str = Form("interne"),
    user: dict = Depends(utilisateur_courant),
) -> dict:
    """Upload .md/.pdf → découpe → embeddings → indexation incrémentale."""
    _ = user  # auth requise ; tout utilisateur connecté peut déposer
    service = (service or "").strip().lower()
    if service not in SERVICES:
        raise HTTPException(status_code=400, detail=f"Service inconnu : {service}")

    nom_orig = file.filename or "document.md"
    ext = Path(nom_orig).suffix.lower()
    if ext not in {".md", ".pdf"}:
        raise HTTPException(status_code=400, detail="Extension acceptée : .md ou .pdf")

    type_doc = "md" if ext == ".md" else "pdf"
    nom_safe = _slug_fichier(nom_orig)
    dossier = UPLOAD_ROOT / service
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_abs = dossier / nom_safe
    contenu = await file.read()
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide")
    chemin_abs.write_bytes(contenu)

    chemin_rel = f"corpus/uploads/{service}/{nom_safe}"
    titre = Path(nom_safe).stem.replace("-", " ").replace("_", " ").title()

    markdown, offsets = charger(chemin_abs, type_doc)
    sections = decouper_en_sections(markdown, offsets)
    enfants, parents, _ = construire_chunks(
        "upload",
        titre,
        sections,
        settings.chunk_size,
        settings.chunk_overlap,
    )
    if not enfants:
        raise HTTPException(status_code=400, detail="Aucun passage extractible du fichier")

    textes = [e.contenu_indexe for e in enfants]
    vecteurs = vectoriser(
        textes,
        settings.embedding_model,
        settings.embedding_dim,
        taille_lot=settings.embedding_batch,
    )
    for e, v in zip(enfants, vecteurs, strict=True):
        e.embedding = v

    groups = groupes_du_service(service)
    result = indexer_un_document(
        doc_titre=titre,
        chemin=chemin_rel,
        type_doc=type_doc,
        source="synthetique",
        sensibilite=sensibilite or "interne",
        allowed_groups=groups,
        chunks_parents=parents,
        chunks_enfants=enfants,
        settings=settings,
    )

    return {
        "document": titre,
        "service": service,
        "label": label_du_service(service),
        "groups": groups,
        "nb_enfants": result["nb_enfants"],
        "nb_parents": result["nb_parents"],
        "chemin": chemin_rel,
    }


@router.get("/stats")
def stats(admin: dict = Depends(admin_requis)) -> dict:
    """Alias legacy → kpis."""
    return kpis(admin)


@router.get("/kpis")
def kpis(admin: dict = Depends(admin_requis)) -> dict:
    """KPI dashboard analytics."""
    _ = admin
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE role = 'user')::int AS nb_questions,
                    COALESCE(
                        100.0 * AVG(
                            CASE WHEN a_repondu IS TRUE THEN 1.0
                                 WHEN a_repondu IS FALSE THEN 0.0 END
                        ) FILTER (WHERE a_repondu IS NOT NULL),
                        0
                    ) AS taux_reponse,
                    COALESCE(
                        100.0 * AVG(
                            CASE WHEN a_repondu IS FALSE THEN 1.0
                                 WHEN a_repondu IS TRUE THEN 0.0 END
                        ) FILTER (WHERE a_repondu IS NOT NULL),
                        0
                    ) AS taux_je_ne_sais_pas,
                    COALESCE(
                        100.0 * AVG(
                            CASE WHEN fichier_genere IS TRUE THEN 1.0 ELSE 0.0 END
                        ) FILTER (WHERE role = 'assistant' OR fichier_genere IS TRUE),
                        0
                    ) AS taux_succes_generation,
                    COALESCE(AVG(latence_ms) FILTER (WHERE latence_ms IS NOT NULL), 0)
                        AS latence_moyenne_ms,
                    COALESCE(AVG(cout_eur) FILTER (WHERE cout_eur IS NOT NULL), 0)
                        AS cout_moyen
                FROM messages
                """
            )
        ).mappings().one()
    return {
        "nb_questions": row["nb_questions"],
        "taux_reponse": round(float(row["taux_reponse"]), 1),
        "taux_je_ne_sais_pas": round(float(row["taux_je_ne_sais_pas"]), 1),
        "taux_succes_generation": round(float(row["taux_succes_generation"]), 1),
        "latence_moyenne_ms": round(float(row["latence_moyenne_ms"]), 0),
        "cout_moyen": round(float(row["cout_moyen"]), 4),
        "pct_sourcees": round(float(row["taux_reponse"]), 1),
        "pct_je_ne_sais_pas": round(float(row["taux_je_ne_sais_pas"]), 1),
    }


@router.get("/top-questions")
def top_questions(admin: dict = Depends(admin_requis)) -> list[dict]:
    _ = admin
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT lower(contenu) AS question, COUNT(*)::int AS count
                FROM messages
                WHERE role = 'user'
                GROUP BY lower(contenu)
                ORDER BY count DESC
                LIMIT 10
                """
            )
        ).mappings().all()
    return [{"question": r["question"], "count": r["count"]} for r in rows]


@router.get("/top-user")
def top_user(admin: dict = Depends(admin_requis)) -> dict:
    _ = admin
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT u.nom, COUNT(*)::int AS count
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                JOIN users u ON u.id = c.user_id
                WHERE m.role = 'user'
                GROUP BY u.id, u.nom
                ORDER BY count DESC
                LIMIT 1
                """
            )
        ).mappings().first()
    if not row:
        return {"nom": "—", "count": 0}
    return {"nom": row["nom"], "count": row["count"]}


@router.get("/top-service")
def top_service(admin: dict = Depends(admin_requis)) -> dict:
    _ = admin
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT COALESCE(service, 'non précisé') AS service,
                       COUNT(*)::int AS count
                FROM messages
                WHERE role = 'user' AND service IS NOT NULL AND service <> ''
                GROUP BY service
                ORDER BY count DESC
                LIMIT 1
                """
            )
        ).mappings().first()
    if not row:
        return {"service": "—", "count": 0}
    return {"service": row["service"], "count": row["count"]}


@router.get("/gaps")
def gaps(admin: dict = Depends(admin_requis)) -> list[dict]:
    """Trous du corpus : questions a_repondu=false regroupées."""
    _ = admin
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT lower(contenu) AS question, COUNT(*)::int AS count
                FROM messages
                WHERE role = 'user' AND a_repondu IS FALSE
                GROUP BY lower(contenu)
                ORDER BY count DESC
                LIMIT 20
                """
            )
        ).mappings().all()

    out: list[dict] = []
    for r in rows:
        q = r["question"] or ""
        suggere = "Document manquant (à identifier)"
        for pat, doc in _GAP_MAP:
            if pat.search(q):
                suggere = doc
                break
        out.append(
            {
                "cluster": q,
                "count": r["count"],
                "document_suggere": suggere,
            }
        )
    return out


@router.get("/services")
def lister_services(user: dict = Depends(utilisateur_courant)) -> list[dict]:
    """Liste des services pour le formulaire d'upload."""
    _ = user
    return [
        {"id": sid, "label": meta["label"], "groups": meta["groups"]}
        for sid, meta in SERVICES.items()
    ]
