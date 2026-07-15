"""Recherche web via Tavily (httpx) — UNIQUEMENT si le toggle utilisateur est ON.

Sécurité : ne jamais appeler cette fonction sans `web=true` dans la requête.
Sans clé → [] (dégradation douce).
"""

from __future__ import annotations

import httpx

from app.config import settings

TAVILY_URL = "https://api.tavily.com/search"


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Recherche web via Tavily. Renvoie [{title, url, content}].

    Ne DOIT être appelée QUE lorsque l'utilisateur a activé le toggle
    (jamais automatique).
    """
    if not settings.tavily_api_key:
        return []
    try:
        resp = httpx.post(
            TAVILY_URL,
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json={
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "title": r.get("title", "") or "",
                "url": r.get("url", "") or "",
                "content": r.get("content", "") or "",
            }
            for r in data.get("results", [])
        ]
    except Exception:
        return []


def format_web_context(results: list[dict]) -> str:
    """Formate les résultats pour le LLM — blocs clairement labellisés [WEB]."""
    if not results:
        return ""
    blocs = [
        f"[WEB {i}] {r['title']}\nURL : {r['url']}\n{r['content']}"
        for i, r in enumerate(results, 1)
    ]
    return (
        "=== RÉSULTATS WEB (source externe, à vérifier) ===\n"
        + "\n\n".join(blocs)
    )
