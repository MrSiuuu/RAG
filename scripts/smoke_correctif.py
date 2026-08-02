"""Smoke correctif : bavardage + congés sans web."""
from __future__ import annotations

import json
import re
import urllib.request

API = "http://localhost:8000"


def login(email: str) -> str:
    req = urllib.request.Request(
        API + "/auth/login",
        data=json.dumps({"email": email, "mot_de_passe": "demo1234"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["access_token"]


def chat(token: str, question: str, historique=None, web=False) -> dict:
    body = {
        "question": question,
        "web_active": web,
        "historique": historique or [],
    }
    req = urllib.request.Request(
        API + "/api/chat",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8", "replace")
    texts = []
    for m in re.finditer(r"event: token\ndata: (.*)\n", raw):
        try:
            texts.append(json.loads(m.group(1)).get("texte", ""))
        except Exception:
            pass
    done = {}
    for m in re.finditer(r"event: done\ndata: (.*)\n", raw):
        try:
            done = json.loads(m.group(1))
        except Exception:
            pass
    has_web = '"type": "web"' in raw or '"type":"web"' in raw
    return {
        "answer": "".join(texts).strip(),
        "done": done,
        "has_web": has_web,
        "nb_sources_event": raw.count("chunk_id"),
    }


def main() -> None:
    token = login("marie@dyneff.fr")
    r1 = chat(token, "Salut qui es-tu ?")
    print(
        "bavardage",
        r1["done"].get("bavardage"),
        "a_repondu",
        r1["done"].get("a_repondu"),
        "nb_sources",
        r1["done"].get("nb_sources"),
        "snippet",
        r1["answer"][:80],
    )

    r2 = chat(token, "Combien de jours de congés payés par an ?", web=False)
    print(
        "conges",
        "a_repondu",
        r2["done"].get("a_repondu"),
        "has_web",
        r2["has_web"],
        "snippet",
        r2["answer"][:80].replace("\n", " "),
    )

    hist = [
        {"role": "user", "contenu": "c'est quoi le salaire d'un cadre niveau 6 ?"},
        {"role": "assistant", "contenu": "Le salaire de référence est 54 000 euros."},
    ]
    r3 = chat(token, "tes sûr ?", historique=hist, web=False)
    print(
        "suivi",
        "a_repondu",
        r3["done"].get("a_repondu"),
        "has_web",
        r3["has_web"],
        "bavardage",
        r3["done"].get("bavardage"),
        "snippet",
        r3["answer"][:100].replace("\n", " "),
    )


if __name__ == "__main__":
    main()
