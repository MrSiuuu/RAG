"""POST /api/chat — génération en streaming SSE (+ .docx + web optionnel)."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Iterator

import psycopg
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.files.docx import build_document
from app.files.generate_doc import generate_document_payload
from app.files.intent import detect_document_intent
from app.files.store import save_file
from app.llm.citations import extraire_citations
from app.llm.contexte import assembler_contexte
from app.llm.generate import generer_streaming
from app.llm.prompts import MESSAGE_AUCUN_ACCES
from app.retrieval.pipeline import rechercher
from app.tools.web import format_web_context, web_search

router = APIRouter()

# Sujets qui ne doivent produire un .docx QUE si le retrieval a ramené
# un passage du document correspondant (évite d'inventer la grille des salaires).
_SUJET_SENSIBLE = re.compile(
    r"grille\s+(des\s+)?salaires|r[eé]mun[eé]ration\s*2026|"
    r"bar[eè]me\s+salarial|salaire\s+d[' ]?un\s+cadre",
    re.IGNORECASE,
)

_NOTE_WEB = (
    "\n\n(Note : des résultats [WEB] figurent dans le contexte. "
    "Signale clairement quand une information provient du web.)"
)

# Préfixe injecté dans le contexte quand le toggle web est actif —
# empêche le refus alors que l'info est dans un bloc [WEB].
_CONTEXTE_WEB_PRIORITY = (
    "INSTRUCTION PRIORITAIRE : l'utilisateur a activé la recherche web. "
    "Les blocs [WEB] ci-dessous sont des sources AUTORISÉES. "
    "Si l'information y figure, tu réponds en la citant "
    "(ex. [WEB · titre de la page]) et tu n'utilises PAS le message de refus. "
    "Indique clairement ce qui vient du web.\n\n"
)


class RequeteChat(BaseModel):
    question: str = Field(..., min_length=1)
    user_groups: list[str] = ["grp-tous"]
    # FALSE par défaut — le LLM ne décide JAMAIS d'aller sur le web.
    web: bool = False


def _contenu_couvre_la_demande(question: str, chunks_enfants: list[dict]) -> bool:
    """Refuse de générer un doc si la question vise un sujet sensible
    mais aucun chunk ramené n'en parle (ex. Paul + grille des salaires)."""
    if not _SUJET_SENSIBLE.search(question or ""):
        return True
    for c in chunks_enfants:
        texte = f"{c.get('breadcrumb', '')} {c.get('contenu', '')}".lower()
        if "remuneration" in texte or "rémunération" in texte or "grille" in texte:
            if any(
                x in texte
                for x in ("54 000", "54000", "cadre confirm", "coefficient", "niveau 6")
            ):
                return True
            if "grille de remuneration" in texte or "grille de rémunération" in texte:
                return True
    return False


def _url_psycopg() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def sse(evenement: str, donnees: dict | list) -> str:
    """Formate un événement SSE (accents français préservés)."""
    charge = json.dumps(donnees, ensure_ascii=False)
    return f"event: {evenement}\ndata: {charge}\n\n"


def _slugify(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode(
        "ascii"
    )
    texte = re.sub(r"[^a-zA-Z0-9]+", "-", texte).strip("-").lower()
    return texte[:60] or "document"


def _refus(debut: float) -> Iterator[str]:
    yield sse("sources", [])
    yield sse("token", {"texte": MESSAGE_AUCUN_ACCES})
    yield sse(
        "done",
        {
            "latence_ms": int((time.perf_counter() - debut) * 1000),
            "a_repondu": False,
            "nb_sources": 0,
        },
    )


def flux_evenements(requete: RequeteChat) -> Iterator[str]:
    """Pipeline chat : retrieval → (web?) → (docx | réponse streamée) → done."""
    debut = time.perf_counter()

    yield sse("status", {"label": "Recherche dans les documents RH…"})

    with psycopg.connect(_url_psycopg()) as conn:
        resultat = rechercher(
            conn,
            question=requete.question,
            groupes_utilisateur=requete.user_groups,
            settings=settings,
        )

    citations = (
        extraire_citations(resultat.chunks_enfants) if resultat.chunks_enfants else []
    )
    sources: list[dict] = [c.model_dump() for c in citations]
    contexte = (
        assembler_contexte(resultat.chunks_parents, resultat.chunks_enfants)
        if resultat.chunks_enfants
        else ""
    )

    # ── Branche web (CDC 10) — UNIQUEMENT si toggle utilisateur ──
    web_results: list[dict] = []
    if requete.web:
        yield sse("status", {"label": "Recherche sur le web…"})
        web_results = web_search(requete.question)
        if web_results:
            web_ctx = format_web_context(web_results)
            contexte = f"{contexte}\n\n{web_ctx}" if contexte else web_ctx
            contexte = _CONTEXTE_WEB_PRIORITY + contexte
            for r in web_results:
                sources.append(
                    {
                        "type": "web",
                        "chunk_id": None,
                        "document": r["title"],
                        "section": "Web",
                        "page": None,
                        "url": r["url"],
                        "extrait": (r["content"] or "")[:300],
                    }
                )

    # Aucun contexte interne NI web → refus (pas d'invention)
    if not resultat.chunks_enfants and not web_results:
        yield from _refus(debut)
        return

    if resultat.chunks_enfants:
        yield sse(
            "status",
            {
                "label": (
                    f"Sélection des {len(resultat.chunks_enfants)} "
                    f"passages les plus pertinents…"
                )
            },
        )

    # ── Branche génération .docx (CDC 9) — corpus interne uniquement ──
    if detect_document_intent(requete.question):
        if not resultat.chunks_enfants or not _contenu_couvre_la_demande(
            requete.question, resultat.chunks_enfants
        ):
            yield from _refus(debut)
            return

        contexte_doc = assembler_contexte(
            resultat.chunks_parents, resultat.chunks_enfants
        )
        sources_doc = [c.model_dump() for c in citations]

        yield sse("status", {"label": "Rédaction du document…"})
        yield sse("sources", sources_doc)

        payload = generate_document_payload(requete.question, contexte_doc)
        content = build_document(payload, sources_doc)
        filename = _slugify(payload.get("titre") or "document") + ".docx"
        file_id = save_file(content, filename)

        message = (
            "Voici le document, rédigé à partir des procédures internes. "
            "Vous pouvez le télécharger ci-dessous."
        )
        for mot in message.split(" "):
            yield sse("token", {"texte": mot + " "})

        yield sse("file", {"id": file_id, "filename": filename})
        yield sse(
            "done",
            {
                "latence_ms": int((time.perf_counter() - debut) * 1000),
                "a_repondu": True,
                "nb_sources": len(citations),
            },
        )
        return

    # ── Chat normal (CDC 4 + 10) ──────────────────────────────────
    yield sse("sources", sources)
    yield sse("status", {"label": "Rédaction de la réponse…"})

    question_llm = requete.question
    if web_results:
        question_llm = requete.question + _NOTE_WEB

    reponse_complete: list[str] = []
    for texte in generer_streaming(
        question=question_llm,
        contexte=contexte,
        modele=settings.llm_model,
        temperature=settings.temperature,
    ):
        reponse_complete.append(texte)
        yield sse("token", {"texte": texte})

    texte_final = "".join(reponse_complete)
    a_repondu = MESSAGE_AUCUN_ACCES not in texte_final

    yield sse(
        "done",
        {
            "latence_ms": int((time.perf_counter() - debut) * 1000),
            "a_repondu": a_repondu,
            "nb_sources": len(sources),
        },
    )


@router.post("/api/chat")
async def chat(requete: RequeteChat) -> StreamingResponse:
    """Endpoint SSE — chat + génération de documents + web optionnel."""
    return StreamingResponse(
        flux_evenements(requete),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
