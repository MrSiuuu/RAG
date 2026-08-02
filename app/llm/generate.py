"""Génération OpenAI en streaming + helper température."""

from __future__ import annotations

from collections.abc import Iterator

from openai import BadRequestError, OpenAI

from app.llm.prompts import PROMPT_SYSTEME


def _appel_avec_temperature(client: OpenAI, **kwargs):
    """Appelle l'API en essayant temperature=0.

    Certains modèles récents refusent temperature=0 (constaté au CDC 3).
    On essaie avec, puis on réessaie sans le paramètre.
    """
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise


def generer_streaming(
    question: str,
    contexte: str,
    modele: str,
    temperature: float,
    historique: list[dict] | None = None,
) -> Iterator[str]:
    """Génère la réponse en STREAMING — yield immédiat de chaque morceau."""
    client = OpenAI()

    messages: list[dict] = [
        {"role": "system", "content": PROMPT_SYSTEME.format(contexte=contexte)},
    ]
    # Mémoire légère : derniers tours avant la question courante
    for tour in (historique or [])[-6:]:
        role = tour.get("role") or "user"
        if role not in {"user", "assistant"}:
            continue
        contenu = tour.get("contenu") or tour.get("content") or ""
        if contenu:
            messages.append({"role": role, "content": contenu})
    messages.append({"role": "user", "content": question})

    flux = _appel_avec_temperature(
        client,
        model=modele,
        temperature=temperature,
        stream=True,
        messages=messages,
    )

    for morceau in flux:
        if not morceau.choices:
            continue
        texte = morceau.choices[0].delta.content
        if texte:
            yield texte
