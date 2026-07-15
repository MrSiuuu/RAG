"""Configuration de l'application, lue depuis le fichier .env.

Pydantic Settings valide et TYPE chaque variable : TOP_K devient un int,
pas la chaîne "25". Et si OPENAI_API_KEY manque, l'application refuse de
démarrer avec un message clair, au lieu de planter vingt minutes plus tard.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── IA ──────────────────────────────────────────────────
    openai_api_key: str

    # Pas de valeur par défaut : les noms de modèles changent trop vite.
    # Ils DOIVENT venir du .env. Jamais en dur dans le code.
    llm_model: str
    llm_model_fast: str
    embedding_model: str

    # Doit matcher vector(1536) dans db/init.sql.
    embedding_dim: int = 1536
    embedding_batch: int = 64
    embedding_prix_mtoken: float = 0.13

    # ─── Base de données ─────────────────────────────────────
    database_url: str

    # ─── Retrieval ───────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 25       # candidats ramenés par la recherche hybride
    top_n: int = 5        # chunks gardés après reranking
    temperature: float = 0.0

    # ─── Auth (CDC 6) ────────────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # ─── Recherche web (CDC 10) ───────────────────────────────
    # Vide = toggle sans effet (dégradation douce). Jamais de recherche auto.
    tavily_api_key: str = ""

    # ─── Divers ──────────────────────────────────────────────
    app_env: str = "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
