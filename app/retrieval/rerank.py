"""Reclassement des candidats par le petit modèle GPT."""

from __future__ import annotations

import json

from openai import OpenAI

PROMPT_RERANK = """Tu es un moteur de recherche documentaire.
On te donne une question et une liste de passages numérotés.
Réponds UNIQUEMENT avec un objet JSON : {{"ids": [id1, id2, ...]}}
Donne les {top_n} IDs des passages qui répondent le mieux à la question.
Du plus pertinent au moins pertinent.
Si aucun passage ne répond à la question, renvoie {{"ids": []}}.
PAS d'explication. PAS de markdown. JUSTE le JSON."""


def reranker(
    question: str,
    candidats: list[dict],
    top_n: int,
    modele: str,
) -> list[dict]:
    """Reclasse les candidats — garde-fou sur les IDs renvoyés par GPT."""
    if not candidats:
        return []

    if len(candidats) <= top_n:
        return candidats[:top_n]

    lignes = [f"Question : {question}\n\nPassages :"]
    for c in candidats:
        extrait = c["contenu_indexe"][:300].replace("\n", " ")
        lignes.append(f"[{c['id']}] {extrait}")
    message_user = "\n".join(lignes)

    client = OpenAI()
    reponse = client.chat.completions.create(
        model=modele,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT_RERANK.format(top_n=top_n)},
            {"role": "user", "content": message_user},
        ],
    )

    resultat = json.loads(reponse.choices[0].message.content or "{}")
    ids_gpt = resultat.get("ids", [])

    # GPT dit explicitement qu'aucun passage ne répond → on ne force pas le top RRF
    if not ids_gpt:
        return []

    ids_valides = {c["id"] for c in candidats}
    ids_filtres = [i for i in ids_gpt if i in ids_valides]

    # IDs hallucinés uniquement → repli sur le top RRF
    if not ids_filtres:
        return candidats[:top_n]

    index_par_id = {c["id"]: c for c in candidats}
    return [index_par_id[i] for i in ids_filtres[:top_n]]
