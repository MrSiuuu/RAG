"""LLM-juges : Correctness + Faithfulness (sans Ragas)."""

from __future__ import annotations

import json

from openai import BadRequestError, OpenAI

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)

_CORRECT_SYS = (
    "Tu es correcteur. On te donne une QUESTION, une RÉPONSE ATTENDUE "
    "et une RÉPONSE OBTENUE.\n"
    "Dis si la RÉPONSE OBTENUE est correcte au regard de la RÉPONSE ATTENDUE "
    "(mêmes faits essentiels).\n"
    "Une reformulation exacte compte comme correcte. "
    'Réponds STRICTEMENT en JSON : {"correct": true|false, "raison": "..."}.'
)

_FAITHFUL_SYS = (
    "Tu es vérificateur d'hallucination. On te donne un CONTEXTE (extraits) "
    "et une RÉPONSE.\n"
    "Dis si CHAQUE affirmation de la RÉPONSE est appuyée par le CONTEXTE. "
    "Si la réponse dit ne pas savoir, elle est fidèle.\n"
    'Réponds STRICTEMENT en JSON : {"faithful": true|false, "raison": "..."}.'
)


def _appel(**kwargs):
    """Appel chat avec repli si temperature n'est pas acceptée."""
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise


def _judge(system: str, user: str) -> dict:
    r = _appel(
        model=settings.llm_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(r.choices[0].message.content or "{}")


def judge_correctness(question: str, attendu: str, obtenu: str) -> bool:
    v = _judge(
        _CORRECT_SYS,
        f"QUESTION :\n{question}\n\n"
        f"RÉPONSE ATTENDUE :\n{attendu}\n\n"
        f"RÉPONSE OBTENUE :\n{obtenu}",
    )
    return bool(v.get("correct"))


def judge_faithfulness(contexte: str, obtenu: str) -> bool:
    v = _judge(
        _FAITHFUL_SYS,
        f"CONTEXTE :\n{contexte}\n\nRÉPONSE :\n{obtenu}",
    )
    return bool(v.get("faithful"))
