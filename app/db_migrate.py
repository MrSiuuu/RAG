"""CREATE TABLE IF NOT EXISTS au démarrage — sans toucher init.sql ni le volume."""

from __future__ import annotations

from sqlalchemy import text

from app.db import engine

# Même hash bcrypt que le seed init.sql (mot de passe demo1234).
_HASH_DEMO = (
    "$2b$12$dHvJAyaZUMJauviv.G0wTur27Slsf0xdaxBJw7iAmLumXu2cnphZi"
)


def assurer_tables_supplementaires() -> None:
    """Crée la table `demandes`, colonnes analytics, user CSE démo."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS demandes (
                    id          SERIAL PRIMARY KEY,
                    user_email  TEXT,
                    service     TEXT NOT NULL,
                    question    TEXT NOT NULL,
                    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        conn.execute(
            text(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS service TEXT"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN IF NOT EXISTS fichier_genere BOOLEAN DEFAULT FALSE"
            )
        )
        # Utilisateur CSE pour la démo multi-service.
        conn.execute(
            text(
                """
                INSERT INTO users (email, nom, mot_de_passe, groupes, role)
                SELECT
                    'cse@dyneff.fr',
                    'Léa Martin',
                    :hash,
                    ARRAY['grp-tous', 'grp-cse']::text[],
                    'user'
                WHERE NOT EXISTS (
                    SELECT 1 FROM users WHERE email = 'cse@dyneff.fr'
                )
                """
            ),
            {"hash": _HASH_DEMO},
        )
