"""Génère eval/golden.jsonl depuis le corpus (32 Q/R + 8 trous)."""

from __future__ import annotations

import json
import random
from pathlib import Path

from openai import BadRequestError, OpenAI
from sqlalchemy import text

from app.config import settings
from app.db import engine

client = OpenAI(api_key=settings.openai_api_key)

OUT = Path(__file__).parent / "golden.jsonl"
N_ANSWERABLE = 32
PER_DOC_MAX = 5

# Sujets ABSENTS du corpus (cf. CDC 1 hors-périmètre / manifest).
# ⚠️ Pas de « mobilité interne » : elle EST dans le corpus.
GAP_QUESTIONS = [
    "Quelles sont les règles du congé paternité en 2026 ?",
    "Quelles sont les conditions d'expatriation et de rémunération à l'étranger chez Dyneff ?",
    "Qu'est-ce que le congé proche aidant ?",
    "Quel est le barème du télétravail à l'international ?",
    "Quelle est la politique de voiture de fonction ?",
    "Comment sont calculées les primes d'intéressement ?",
    "Quelle est la procédure à suivre en cas de harcèlement ?",
    "Quels sont les avantages proposés par le comité social et économique ?",
]

_GEN_SYS = (
    "Tu génères UNE paire question/réponse d'évaluation à partir d'un extrait "
    "de document RH.\n"
    "La QUESTION doit être naturelle (posée par un salarié) et sa réponse doit "
    "être ENTIÈREMENT contenue dans l'extrait.\n"
    "La RÉPONSE doit être courte et factuelle. "
    'Réponds STRICTEMENT en JSON : {"question": "...", "reponse": "..."}.'
)


def _appel(**kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise


def _fetch_child_chunks() -> list[dict]:
    """Chunks ENFANTS vectorisés (ceux que le retrieval cherche)."""
    sql = text(
        """
        SELECT c.id, c.parent_id, c.contenu, c.breadcrumb, d.titre AS document
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.type = 'child' AND c.embedding IS NOT NULL
        ORDER BY d.titre, c.id
        """
    )
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(sql).mappings().all()]


def _sample(chunks: list[dict]) -> list[dict]:
    by_doc: dict[str, list[dict]] = {}
    for c in chunks:
        by_doc.setdefault(c["document"], []).append(c)
    selected: list[dict] = []
    for items in by_doc.values():
        random.shuffle(items)
        selected.extend(items[:PER_DOC_MAX])
    random.shuffle(selected)
    return selected[:N_ANSWERABLE]


def _gen_qa(chunk: dict) -> tuple[str, str]:
    r = _appel(
        model=settings.llm_model,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _GEN_SYS},
            {
                "role": "user",
                "content": (
                    f"Document : {chunk['document']}\n"
                    f"Section : {chunk['breadcrumb']}\n---\n{chunk['contenu']}"
                ),
            },
        ],
    )
    data = json.loads(r.choices[0].message.content or "{}")
    return data.get("question", "").strip(), data.get("reponse", "").strip()


def main() -> None:
    random.seed(42)
    chunks = _fetch_child_chunks()
    print(f"{len(chunks)} chunks enfants récupérés")
    selected = _sample(chunks)
    print(f"{len(selected)} chunks sélectionnés\n")

    items: list[dict] = []
    for i, ch in enumerate(selected, 1):
        try:
            q, a = _gen_qa(ch)
            if not q:
                continue
            items.append(
                {
                    "id": f"a{i:03d}",
                    "question": q,
                    "reponse_attendue": a,
                    "chunk_id": ch["id"],
                    "parent_id": ch["parent_id"],
                    "document": ch["document"],
                    "section": ch["breadcrumb"],
                    "answerable": True,
                }
            )
            print(f"  [{i:02d}] {q}")
        except Exception as e:
            print(f"  [{i:02d}] échec : {e}")

    for j, q in enumerate(GAP_QUESTIONS, 1):
        items.append(
            {
                "id": f"g{j:03d}",
                "question": q,
                "reponse_attendue": "je ne sais pas",
                "chunk_id": None,
                "parent_id": None,
                "document": None,
                "section": None,
                "answerable": False,
            }
        )
        print(f"  [g{j:02d}] {q}")

    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"\n✅ {len(items)} paires écrites dans {OUT}")
    print("⚠️  RELIS golden.jsonl À LA MAIN avant de lancer l'éval.")


if __name__ == "__main__":
    main()
