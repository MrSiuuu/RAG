"""Smoke tests CDC 6-12 — n'affiche jamais les jetons."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

API = "http://localhost:8000"


def post(path: str, body: dict | None = None, token: str | None = None, data: bytes | None = None, content_type: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = data
    if body is not None:
        payload = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(API + path, data=payload, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def login(email: str) -> str:
    code, raw = post("/auth/login", {"email": email, "mot_de_passe": "demo1234"})
    assert code == 200, raw
    return json.loads(raw)["access_token"]


def main() -> None:
    # Chat sans token
    code, _ = post("/api/chat", {"question": "test"})
    print("chat_sans_token", code)

    paul = login("paul@dyneff.fr")
    marie = login("marie@dyneff.fr")
    admin = login("admin@dyneff.fr")
    cse = login("cse@dyneff.fr")
    print("logins_ok")

    code, _ = post("/api/admin/stats", token=paul)
    # GET
    req = urllib.request.Request(API + "/api/admin/stats", headers={"Authorization": f"Bearer {paul}"})
    try:
        urllib.request.urlopen(req)
        print("paul_stats", 200)
    except urllib.error.HTTPError as e:
        print("paul_stats", e.code)

    req = urllib.request.Request(API + "/api/admin/stats", headers={"Authorization": f"Bearer {admin}"})
    with urllib.request.urlopen(req) as r:
        print("admin_stats", r.status)

    # Seed
    import subprocess
    subprocess.check_call(["python", "/srv/scripts/seed_usage.py"])
    with urllib.request.urlopen(req) as r:
        stats = json.loads(r.read())
    print("stats_apres_seed", stats.get("nb_questions"), stats.get("pct_sourcees"))

    # Ingest CSE doc as admin
    md = Path("/srv/corpus/uploads/cse-budget-2026-test.md").read_bytes()
    boundary = "----Boundary7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="service"\r\n\r\ncse\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="sensibilite"\r\n\r\ninterne\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="cse-budget-2026-test.md"\r\n'
        f"Content-Type: text/markdown\r\n\r\n"
    ).encode() + md + f"\r\n--{boundary}--\r\n".encode()
    code, raw = post(
        "/api/admin/ingest",
        token=admin,
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    print("ingest", code, json.loads(raw).get("nb_enfants") if code == 200 else raw[:200])

    # Demande
    code, raw = post(
        "/api/demandes",
        {"question": "congé proche aidant", "service": "rh"},
        token=marie,
    )
    print("demande", code, json.loads(raw) if code == 200 else raw[:120])

    print("DONE")


if __name__ == "__main__":
    main()
