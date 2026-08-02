"""Test ACL : CSE voit budget CSE, Marie refuse."""
from __future__ import annotations

import json
import re
import urllib.request

API = "http://localhost:8000"
Q = "Quel est le budget CSE pour 2026 ?"


def login(email: str) -> str:
    req = urllib.request.Request(
        API + "/auth/login",
        data=json.dumps({"email": email, "mot_de_passe": "demo1234"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["access_token"]


def chat(token: str, question: str) -> tuple[str, bool]:
    req = urllib.request.Request(
        API + "/api/chat",
        data=json.dumps({"question": question, "web": False}).encode(),
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
    answer = "".join(texts)
    done = None
    for m in re.finditer(r"event: done\ndata: (.*)\n", raw):
        try:
            done = json.loads(m.group(1))
        except Exception:
            pass
    return answer, bool(done and done.get("a_repondu"))


def main() -> None:
    cse = login("cse@dyneff.fr")
    marie = login("marie@dyneff.fr")
    a_cse, ok_cse = chat(cse, Q)
    a_marie, ok_marie = chat(marie, Q)
    print("cse_a_repondu", ok_cse, "has_120000", "120" in a_cse or "120 000" in a_cse)
    print("marie_a_repondu", ok_marie)
    print("cse_snippet", a_cse[:160].replace("\n", " "))
    print("marie_snippet", a_marie[:160].replace("\n", " "))


if __name__ == "__main__":
    main()
