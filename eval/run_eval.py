"""Lance l'éval sur golden.jsonl et écrit eval/results.md."""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import psycopg
from openai import BadRequestError, OpenAI

from app.config import settings
from app.llm.contexte import assembler_contexte
from app.llm.prompts import MESSAGE_AUCUN_ACCES, PROMPT_SYSTEME
from app.retrieval.pipeline import rechercher
from eval.judges import judge_correctness, judge_faithfulness
from eval.pricing import cost_eur

client = OpenAI(api_key=settings.openai_api_key)

GOLDEN = Path(__file__).parent / "golden.jsonl"
RESULTS = Path(__file__).parent / "results.md"

# Tous les groupes : on teste la QUALITÉ, pas l'ACL.
ALL_GROUPS = ["grp-rh", "grp-tous", "grp-admin"]

# Aligné sur MESSAGE_AUCUN_ACCES (app/llm/prompts.py).
REFUS_MARQUEURS = [
    "je n'ai pas trouvé cette information",
    "je n'ai pas trouvé",
    "documents auxquels vous avez accès",
    "je ne sais pas",
    "pas d'information",
    "aucune information",
]


def _url_psycopg() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _appel(**kwargs):
    try:
        return client.chat.completions.create(**kwargs)
    except BadRequestError as e:
        if "temperature" in str(e).lower():
            kwargs.pop("temperature", None)
            return client.chat.completions.create(**kwargs)
        raise


def load_golden() -> list[dict]:
    with GOLDEN.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def is_refusal(answer: str) -> bool:
    a = (answer or "").lower()
    return any(m in a for m in REFUS_MARQUEURS)


def generate_answer(question: str, contexte: str):
    """Génération NON-streamée — même prompt / modèle que le produit."""
    if not (contexte or "").strip():
        return MESSAGE_AUCUN_ACCES, SimpleNamespace(
            prompt_tokens=0, completion_tokens=0
        )

    r = _appel(
        model=settings.llm_model,
        temperature=settings.temperature,
        messages=[
            {"role": "system", "content": PROMPT_SYSTEME.format(contexte=contexte)},
            {"role": "user", "content": question},
        ],
    )
    return r.choices[0].message.content or "", r.usage


def recall_hit(item: dict, retrieved: list[dict]) -> bool:
    ids = {c["id"] for c in retrieved}
    parents = {c.get("parent_id") for c in retrieved}
    return item["chunk_id"] in ids or (
        item["parent_id"] is not None and item["parent_id"] in parents
    )


def _pct(values) -> float:
    vals = [v for v in values if v is not None]
    return 100 * sum(1 for v in vals if v) / len(vals) if vals else 0.0


def write_results(rows: list[dict]) -> None:
    answerable = [r for r in rows if r["answerable"]]
    gaps = [r for r in rows if not r["answerable"]]

    recall = _pct([r["recall"] for r in answerable])
    correctness = _pct([r["correct"] for r in answerable])
    faithfulness = _pct([r["faithful"] for r in rows])
    idk_ok = _pct([r["correct"] for r in gaps])
    idk_rate = _pct([r["refused"] for r in rows])
    lat = sum(r["latency_ms"] for r in rows) / len(rows)
    cost = sum(r["cost"] for r in rows) / len(rows)

    md = f"""# Résultats de l'évaluation — RAG Dyneff

Golden set : **{len(rows)} questions** ({len(answerable)} avec réponse, {len(gaps)} trous de corpus)
Config : modèle `{settings.llm_model}` · TOP_K={settings.top_k} · TOP_N={settings.top_n} · CHUNK_SIZE={settings.chunk_size}

| Métrique | Score | Ce qu'elle mesure |
|---|---|---|
| **Recall@{settings.top_n}** | **{recall:.0f} %** | Le bon passage est-il récupéré ? (retrieval) |
| **Correctness** | **{correctness:.0f} %** | La réponse est-elle juste ? (génération) |
| **Faithfulness** | **{faithfulness:.0f} %** | Zéro invention ? (hallucination) |
| **Trous correctement refusés** | **{idk_ok:.0f} %** | Sait-il dire « je ne sais pas » ? (prudence) |
| Taux de refus global | {idk_rate:.0f} % | Part de « je ne sais pas » sur tout le set |
| Latence moyenne | {lat / 1000:.1f} s | Temps de réponse |
| Coût génération / question | {cost:.4f} € | Coût du modèle par question |

## Détail par question

| id | type | recall | correct | fidèle | refus | latence |
|---|---|:---:|:---:|:---:|:---:|---:|
"""
    for r in rows:
        typ = "réponse" if r["answerable"] else "trou"
        rec = "—" if r["recall"] is None else ("✅" if r["recall"] else "❌")
        md += (
            f"| {r['id']} | {typ} | {rec} | "
            f"{'✅' if r['correct'] else '❌'} | "
            f"{'✅' if r['faithful'] else '❌'} | "
            f"{'oui' if r['refused'] else 'non'} | "
            f"{r['latency_ms'] / 1000:.1f} s |\n"
        )

    RESULTS.write_text(md, encoding="utf-8")


def main() -> None:
    if not GOLDEN.exists():
        raise SystemExit(
            f"Fichier manquant : {GOLDEN}\n"
            "Lance d'abord : python -m eval.generate_golden"
        )

    golden = load_golden()
    print(f"{len(golden)} questions dans le golden set\n")

    rows: list[dict] = []
    with psycopg.connect(_url_psycopg()) as conn:
        for it in golden:
            t0 = time.perf_counter()
            resultat = rechercher(
                conn,
                question=it["question"],
                settings=settings,
            )
            enfants = resultat.chunks_enfants
            parents = resultat.chunks_parents
            contexte = assembler_contexte(parents, enfants)
            answer, usage = generate_answer(it["question"], contexte)
            latency_ms = (time.perf_counter() - t0) * 1000

            refused = is_refusal(answer)
            cost = cost_eur(
                settings.llm_model,
                getattr(usage, "prompt_tokens", 0) or 0,
                getattr(usage, "completion_tokens", 0) or 0,
            )

            if it["answerable"]:
                recall = recall_hit(it, enfants)
                if refused:
                    correct, faithful = False, True
                else:
                    correct = judge_correctness(
                        it["question"], it["reponse_attendue"], answer
                    )
                    faithful = judge_faithfulness(contexte, answer)
            else:
                recall = None
                correct = refused
                faithful = (
                    True if refused else judge_faithfulness(contexte, answer)
                )

            rows.append(
                {
                    "id": it["id"],
                    "answerable": it["answerable"],
                    "recall": recall,
                    "correct": correct,
                    "faithful": faithful,
                    "refused": refused,
                    "latency_ms": latency_ms,
                    "cost": cost,
                }
            )
            print(f"{'✅' if correct else '❌'} [{it['id']}] {it['question'][:60]}")

    write_results(rows)

    ans = [r for r in rows if r["answerable"]]
    gaps = [r for r in rows if not r["answerable"]]
    print("\n" + "=" * 55)
    print(f"Recall@{settings.top_n}    : {_pct([r['recall'] for r in ans]):.0f}%")
    print(f"Correctness  : {_pct([r['correct'] for r in ans]):.0f}%")
    print(f"Faithfulness : {_pct([r['faithful'] for r in rows]):.0f}%")
    print(f"Refus trous  : {_pct([r['correct'] for r in gaps]):.0f}%")
    print(
        f"Latence moy. : {sum(r['latency_ms'] for r in rows) / len(rows) / 1000:.1f}s"
    )
    print(
        f"Coût/question: {sum(r['cost'] for r in rows) / len(rows):.4f}€"
    )
    print(f"✅ Tableau écrit dans {RESULTS}")


if __name__ == "__main__":
    main()
