"""POST /api/chat — streaming SSE + pré-traitement + /doc + web discipliné."""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Iterator

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel, Field, model_validator

from app.chat.memoire import (
    assurer_conversation,
    charger_historique,
    enregistrer_message,
    fixer_titre_si_vide,
    service_depuis_chunks,
)
from app.chat.pretraitement import pretraiter
from app.config import settings
from app.files.docx import build_document
from app.files.generate_doc import generate_document_payload
from app.files.intent import detect_document_intent, preparer_intention_document
from app.files.store import save_file
from app.llm.citations import extraire_citations
from app.llm.contexte import assembler_contexte
from app.llm.generate import generer_streaming
from app.llm.prompts import MESSAGE_AUCUN_ACCES
from app.retrieval.pipeline import rechercher
from app.security.deps import utilisateur_courant
from app.tools.web import format_web_context, web_search

router = APIRouter()

_SUJET_SENSIBLE = re.compile(
    r"grille\s+(des\s+)?salaires|r[eé]mun[eé]ration\s*2026|"
    r"bar[eè]me\s+salarial|salaire\s+d[' ]?un\s+cadre",
    re.IGNORECASE,
)

_NOTE_WEB = (
    "\n\n(Note : des résultats [WEB] figurent dans le contexte. "
    "Signale clairement quand une information provient du web.)"
)

_CONTEXTE_WEB_PRIORITY = (
    "INSTRUCTION PRIORITAIRE : l'utilisateur a activé la recherche web. "
    "Les blocs [WEB] ci-dessous sont des sources AUTORISÉES. "
    "Si l'information y figure, tu réponds en la citant "
    "(ex. [WEB · titre de la page]) et tu n'utilises PAS le message de refus. "
    "Indique clairement ce qui vient du web.\n\n"
)


class TourHistorique(BaseModel):
    role: str
    contenu: str = ""
    content: str = ""

    def texte(self) -> str:
        return self.contenu or self.content or ""


class RequeteChat(BaseModel):
    question: str = Field(..., min_length=1)
    # Web OFF par défaut — jamais auto, jamais sur bavardage.
    web_active: bool = False
    # Alias legacy accepté
    web: bool | None = None
    historique: list[TourHistorique] = Field(default_factory=list)
    conversation_id: int | None = None

    @model_validator(mode="after")
    def _merge_web(self):
        if self.web is True:
            self.web_active = True
        return self


def _web_actif(requete: RequeteChat) -> bool:
    return bool(requete.web_active)


def _contenu_couvre_la_demande(question: str, chunks_enfants: list[dict]) -> bool:
    """Couverture pour sujets sensibles (ex. grille salariale).

    Sans docs confidentiels (CDC 15), une question salariale sans chunk
    pertinent renvoie False → refus / transmettre.
    """
    if not _SUJET_SENSIBLE.search(question or ""):
        return True
    if not chunks_enfants:
        return False
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
    charge = json.dumps(donnees, ensure_ascii=False)
    return f"event: {evenement}\ndata: {charge}\n\n"


def _slugify(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode(
        "ascii"
    )
    texte = re.sub(r"[^a-zA-Z0-9]+", "-", texte).strip("-").lower()
    return texte[:60] or "document"


def flux_evenements(requete: RequeteChat, user: dict) -> Iterator[str]:
    """Pré-traitement → (bavardage | retrieval + génération) → done."""
    debut = time.perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)
    web_on = _web_actif(requete)

    # Slash /doc = forcer la génération de document (retiré du texte).
    force_doc, message_brut = preparer_intention_document(requete.question)

    with psycopg.connect(_url_psycopg()) as conn:
        conv_id = assurer_conversation(conn, user["id"], requete.conversation_id)
        conn.commit()

        historique = [
            {"role": t.role, "contenu": t.texte()}
            for t in requete.historique
            if t.texte()
        ]
        if not historique:
            historique = charger_historique(conn, conv_id, 6)

        yield sse("status", {"label": "Analyse de votre message…"})
        pret = pretraiter(
            message_brut,
            historique,
            client,
            settings.llm_model_fast,
        )

        # Enregistre la question utilisateur
        enregistrer_message(
            conn,
            conversation_id=conv_id,
            role="user",
            contenu=requete.question,
            question_reecrite=pret.get("question_autonome"),
            web_active=web_on,
            modele=settings.llm_model_fast,
            service=None,
        )
        fixer_titre_si_vide(conn, conv_id, message_brut or requete.question)
        conn.commit()

        # ── Bavardage : réponse persona, zéro RAG / web / transmettre ──
        if pret["type"] == "bavardage":
            reponse = pret["reponse_directe"]
            yield sse("sources", [])
            for mot in reponse.split(" "):
                yield sse("token", {"texte": mot + " "})
            lat = int((time.perf_counter() - debut) * 1000)
            enregistrer_message(
                conn,
                conversation_id=conv_id,
                role="assistant",
                contenu=reponse,
                a_repondu=True,
                sources=[],
                web_active=False,
                latence_ms=lat,
                modele=settings.llm_model_fast,
                service=service_tag,
            )
            conn.commit()
            yield sse(
                "done",
                {
                    "latence_ms": lat,
                    "a_repondu": True,
                    "nb_sources": 0,
                    "conversation_id": conv_id,
                    "bavardage": True,
                },
            )
            return

        question = pret["question_autonome"] or message_brut

        yield sse("status", {"label": "Recherche dans les documents…"})
        resultat = rechercher(conn, question=question, settings=settings)

        citations = (
            extraire_citations(resultat.chunks_enfants)
            if resultat.chunks_enfants
            else []
        )
        sources: list[dict] = [c.model_dump() for c in citations]
        contexte = (
            assembler_contexte(resultat.chunks_parents, resultat.chunks_enfants)
            if resultat.chunks_enfants
            else ""
        )
        service_msg = service_depuis_chunks(resultat.chunks_enfants)

        # Web : UNIQUEMENT si toggle ON et type documentaire
        web_results: list[dict] = []
        if web_on:
            yield sse("status", {"label": "Recherche sur le web…"})
            web_results = web_search(question)
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

        if not resultat.chunks_enfants and not web_results:
            yield sse("sources", [])
            yield sse("token", {"texte": MESSAGE_AUCUN_ACCES})
            lat = int((time.perf_counter() - debut) * 1000)
            enregistrer_message(
                conn,
                conversation_id=conv_id,
                role="assistant",
                contenu=MESSAGE_AUCUN_ACCES,
                a_repondu=False,
                sources=[],
                web_active=web_on,
                latence_ms=lat,
                modele=settings.llm_model,
                service=service_msg,
            )
            conn.commit()
            yield sse(
                "done",
                {
                    "latence_ms": lat,
                    "a_repondu": False,
                    "nb_sources": 0,
                    "conversation_id": conv_id,
                },
            )
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

        # ── .docx (slash /doc ou intention détectée) ───────────
        if force_doc or detect_document_intent(message_brut):
            if not resultat.chunks_enfants or not _contenu_couvre_la_demande(
                question, resultat.chunks_enfants
            ):
                yield sse("sources", [])
                yield sse("token", {"texte": MESSAGE_AUCUN_ACCES})
                lat = int((time.perf_counter() - debut) * 1000)
                enregistrer_message(
                    conn,
                    conversation_id=conv_id,
                    role="assistant",
                    contenu=MESSAGE_AUCUN_ACCES,
                    a_repondu=False,
                    latence_ms=lat,
                    modele=settings.llm_model,
                    service=service_msg,
                )
                conn.commit()
                yield sse(
                    "done",
                    {
                        "latence_ms": lat,
                        "a_repondu": False,
                        "nb_sources": 0,
                        "conversation_id": conv_id,
                    },
                )
                return

            contexte_doc = assembler_contexte(
                resultat.chunks_parents, resultat.chunks_enfants
            )
            sources_doc = [c.model_dump() for c in citations]
            yield sse("status", {"label": "Rédaction du document…"})
            yield sse("sources", sources_doc)

            payload = generate_document_payload(question, contexte_doc)
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
            lat = int((time.perf_counter() - debut) * 1000)
            enregistrer_message(
                conn,
                conversation_id=conv_id,
                role="assistant",
                contenu=message,
                a_repondu=True,
                sources=sources_doc,
                latence_ms=lat,
                modele=settings.llm_model,
                service=service_msg,
                fichier_genere=True,
                chunk_ids=[c["id"] for c in resultat.chunks_enfants],
            )
            conn.commit()
            yield sse(
                "done",
                {
                    "latence_ms": lat,
                    "a_repondu": True,
                    "nb_sources": len(citations),
                    "conversation_id": conv_id,
                },
            )
            return

        # ── Chat documentaire ─────────────────────────────────
        yield sse("sources", sources)
        yield sse("status", {"label": "Rédaction de la réponse…"})

        question_llm = question + (_NOTE_WEB if web_results else "")
        reponse_complete: list[str] = []
        for texte in generer_streaming(
            question=question_llm,
            contexte=contexte,
            modele=settings.llm_model,
            temperature=settings.temperature,
            historique=historique,
        ):
            reponse_complete.append(texte)
            yield sse("token", {"texte": texte})

        texte_final = "".join(reponse_complete)
        a_repondu = MESSAGE_AUCUN_ACCES not in texte_final
        lat = int((time.perf_counter() - debut) * 1000)
        enregistrer_message(
            conn,
            conversation_id=conv_id,
            role="assistant",
            contenu=texte_final,
            a_repondu=a_repondu,
            sources=sources,
            web_active=web_on,
            latence_ms=lat,
            modele=settings.llm_model,
            service=service_msg,
            chunk_ids=[c["id"] for c in resultat.chunks_enfants],
        )
        conn.commit()
        yield sse(
            "done",
            {
                "latence_ms": lat,
                "a_repondu": a_repondu,
                "nb_sources": len(sources),
                "conversation_id": conv_id,
            },
        )


@router.post("/api/chat")
async def chat(
    requete: RequeteChat,
    user: dict = Depends(utilisateur_courant),
) -> StreamingResponse:
    """Chat SSE — auth JWT requise. Corpus multi-service ouvert."""
    return StreamingResponse(
        flux_evenements(requete, user),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
