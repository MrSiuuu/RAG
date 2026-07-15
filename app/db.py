"""Connexion à Postgres via SQLAlchemy 2.

⚠️ DATABASE_URL doit commencer par postgresql+psycopg:// (psycopg 3).
   Sans le "+psycopg", SQLAlchemy cherche psycopg2, qui n'est pas installé,
   et lève un ModuleNotFoundError incompréhensible.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # teste la connexion avant de s'en servir
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session, la ferme quoi qu'il arrive."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_est_joignable() -> bool:
    """Renvoie True si la base répond."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
