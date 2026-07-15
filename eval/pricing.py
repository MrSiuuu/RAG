"""Prix des modèles OpenAI, en € par MILLION de tokens.

Sources (juil. 2026) : developers.openai.com/api/docs/pricing
USD ≈ EUR pour le POC (ordre de grandeur défendable en réunion).
"""

from __future__ import annotations

# (input, output) — clés = noms exacts de settings.llm_model / llm_model_fast
PRICING: dict[str, tuple[float, float]] = {
    "gpt-5.6-terra": (2.50, 15.00),
    "gpt-5.6-luna": (1.00, 6.00),
    "gpt-5.6-sol": (5.00, 30.00),
    "gpt-5.6": (5.00, 30.00),  # alias → Sol
    "text-embedding-3-large": (0.13, 0.0),
    "text-embedding-3-small": (0.02, 0.0),
}


def cost_eur(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Coût approximatif d'un appel chat, en euros."""
    price_in, price_out = PRICING.get(model, (0.0, 0.0))
    return (
        prompt_tokens / 1_000_000 * price_in
        + completion_tokens / 1_000_000 * price_out
    )
