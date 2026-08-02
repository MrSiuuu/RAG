"""Seed d'usage réaliste pour le dashboard admin (~250 messages / 30 jours).

Usage :
  docker compose exec api python scripts/seed_usage.py
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

MODELE_SEED = "seed"
SERVICES = ["rh", "cse", "hse", "juridique"]

QUESTIONS_OK = [
    ("Combien de jours de RTT ?", 28),
    ("Comment poser un congé sans solde ?", 22),
    ("Plafond note de frais repas ?", 20),
    ("Comment déclarer un arrêt maladie ?", 18),
    ("Prime d'ancienneté ?", 16),
    ("Combien de jours de congés payés par an ?", 15),
    ("Quel est le plafond de télétravail ?", 14),
    ("Comment demander une mobilité interne ?", 12),
    ("Quels sont les délais pour une note de frais ?", 10),
    ("Qui contacter pour l'entretien annuel ?", 9),
    ("Comment fonctionne la mutuelle Confort ?", 8),
    ("Puis-je télétravailler 3 jours par semaine ?", 7),
]

QUESTIONS_GAP = [
    ("procédure de mobilité internationale", 8),
    ("congé proche aidant", 7),
    ("barème télétravail à l'étranger", 6),
    ("règles du congé paternité 2026", 5),
]


def _url() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> int:
    random.seed(42)
    now = datetime.now(timezone.utc)

    with psycopg.connect(_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM messages WHERE modele = %s OR contenu LIKE %s",
                (MODELE_SEED, "[SEED]%"),
            )
            cur.execute(
                "DELETE FROM conversations WHERE titre LIKE %s",
                ("[SEED]%",),
            )

            cur.execute("SELECT id, email FROM users ORDER BY id")
            users = cur.fetchall()
            if not users:
                print("Aucun utilisateur.")
                return 1

            conv_ids: list[int] = []
            for uid, email in users:
                cur.execute(
                    """
                    INSERT INTO conversations (user_id, titre)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (uid, f"[SEED] Usage {email}"),
                )
                conv_ids.append(cur.fetchone()[0])

            pool: list[tuple[str, bool]] = []
            for q, n in QUESTIONS_OK:
                pool.extend([(q, True)] * n)
            for q, n in QUESTIONS_GAP:
                pool.extend([(q, False)] * n)
            while len(pool) < 250:
                q, ok = random.choice(QUESTIONS_OK)
                pool.append((q, True))
            pool = pool[:250]
            random.shuffle(pool)

            for question, a_repondu in pool:
                jour = now - timedelta(
                    days=random.randint(0, 29),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                latence = random.randint(1500, 4000)
                cout = round(random.uniform(0.003, 0.008), 6)
                service = random.choice(SERVICES)
                fichier = random.random() < 0.15 and a_repondu
                conv_id = random.choice(conv_ids)

                cur.execute(
                    """
                    INSERT INTO messages (
                        conversation_id, role, contenu,
                        a_repondu, web_active, modele,
                        latence_ms, cout_eur, cree_le,
                        service, fichier_genere
                    ) VALUES (
                        %s, 'user', %s,
                        %s, FALSE, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                    """,
                    (
                        conv_id,
                        question,
                        a_repondu,
                        MODELE_SEED,
                        latence,
                        cout,
                        jour,
                        service,
                        fichier,
                    ),
                )

            conn.commit()

    print(f"{len(pool)} messages seedés ({len(conv_ids)} conversations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
