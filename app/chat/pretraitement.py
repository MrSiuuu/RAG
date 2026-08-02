"""Pré-traitement : bavardage vs documentaire + réécriture de suivi (luna)."""

from __future__ import annotations

import json

from openai import BadRequestError, OpenAI

_PROMPT = """Tu es le routeur d'un assistant interne nommé "Assistant Dyneff".
À partir du message et de l'historique, décide :
- si c'est du bavardage (bonjour, qui es-tu, merci, ça va, au revoir, salut) →
  type "bavardage" + une réponse persona brève
  ("Je suis l'assistant Dyneff, je réponds à vos questions sur les
  procédures internes (RH, CSE, etc.).").
- sinon → type "documentaire" + réécris la question en question autonome
  en intégrant le contexte de l'historique
  (ex. "tes sûr ?" → "Es-tu sûr de ta réponse précédente sur X ?").

Réponds UNIQUEMENT en JSON strict :
{"type":"bavardage"|"documentaire","reponse_directe":"...","question_autonome":"..."}
Pour documentaire, reponse_directe peut être "". Pour bavardage, question_autonome peut être ""."""


def _appel(client: OpenAI, **kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise


def pretraiter(
    message: str,
    historique: list[dict],
    client: OpenAI,
    modele_rapide: str,
) -> dict:
    """Classe le message et réécrit les questions de suivi.

    historique = derniers tours [{role, contenu}].
    """
    hist_lignes = []
    for tour in (historique or [])[-6:]:
        role = tour.get("role", "user")
        contenu = tour.get("contenu") or tour.get("content") or ""
        hist_lignes.append(f"{role}: {contenu}")
    hist_txt = "\n".join(hist_lignes) if hist_lignes else "(aucun)"

    user = (
        f"Historique récent :\n{hist_txt}\n\n"
        f"Message actuel :\n{message}"
    )

    try:
        r = _appel(
            client,
            model=modele_rapide,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _PROMPT},
                {"role": "user", "content": user},
            ],
        )
        data = json.loads(r.choices[0].message.content or "{}")
    except Exception:
        # Filet de sécurité : on traite comme documentaire sans réécriture
        return {
            "type": "documentaire",
            "reponse_directe": "",
            "question_autonome": message,
        }

    typ = (data.get("type") or "documentaire").strip().lower()
    if typ not in {"bavardage", "documentaire"}:
        typ = "documentaire"

    reponse = (data.get("reponse_directe") or "").strip()
    question = (data.get("question_autonome") or "").strip() or message

    if typ == "bavardage" and not reponse:
        reponse = (
            "Je suis l'assistant RH de Dyneff, je réponds à vos questions "
            "sur les procédures internes et la convention collective."
        )

    return {
        "type": typ,
        "reponse_directe": reponse,
        "question_autonome": question,
    }
