# CDC 5 — L'évaluation ⭐

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Faire passer à ton RAG un **contrôle de 40 questions** dont tu connais déjà les réponses, et en sortir un **tableau de scores chiffrés** : combien de bonnes réponses, combien d'inventions, combien de « je ne sais pas » corrects.

---

## 💡 Pourquoi c'est important

C'est **ton arme n°1 contre l'objection « ça hallucine, on ne peut pas faire confiance ».**

| Sans éval | Avec éval |
|---|---|
| Tu poses 3 questions au pif, ça a l'air de marcher, quelqu'un pose une question tordue en réunion → ça hallucine → **tu es mort** | Tu arrives et tu poses un chiffre sur la table : *« 40 questions réelles, 0 % d'hallucination, 100 % sourcé »* |

**Personne d'autre dans la boîte ne peut sortir ce chiffre.** C'est exactement ce qui sépare *« il a bricolé un chatbot »* de *« il a industrialisé une brique »*. Aujourd'hui tu as la preuve **qualitative** (tes tests DoD passent). Ce CDC te donne la preuve **quantitative**.

---

## 📚 Les concepts à comprendre

### 1. Ce n'est PAS de l'entraînement

⚠️ Le piège de vocabulaire le plus courant. **Rien n'est entraîné dans un RAG.** Les 40 questions/réponses ne servent **pas** à faire marcher le système — elles servent à **le noter**.

**L'image :** ton RAG est un stagiaire. Tu veux savoir s'il est bon ? Tu lui fais passer un contrôle : 40 questions dont **tu connais déjà les réponses**. Il répond, tu comptes. 22/40 → le découpage est mauvais, tu ajustes. 35/40 → tu es prêt.

### 2. Le « golden set » — le corrigé

C'est le fichier `golden.jsonl` : 40 paires **question → réponse attendue**. Deux types de questions :
- **32 questions « avec réponse »** : générées automatiquement **depuis ton corpus**. Pour chacune, on note **quel chunk contient la réponse** (c'est ce qui permet de mesurer si le retrieval l'a bien retrouvé).
- **8 questions « trou de corpus »** : sur des sujets **absents** de ton corpus (congé paternité 2026, mobilité internationale…). La bonne réponse attendue est **« je ne sais pas »**. Elles testent sa **prudence**.

> **On génère les 40 avec le LLM, puis ON RELIT À LA MAIN.** Non négociable. Une paire fausse dans le corrigé fausse tout le score.

### 3. Les 4 métriques (chacune teste une partie différente)

| Métrique | La question qu'elle pose | Ce qu'elle teste |
|---|---|---|
| **Recall@5** | Le bon passage est-il dans les 5 récupérés ? | Le **retrieval** (la recherche) |
| **Correctness** | La réponse est-elle juste ? | La **génération** |
| **Faithfulness** | La réponse s'appuie-t-elle vraiment sur les sources (zéro invention) ? | L'**hallucination** |
| **Taux de « je ne sais pas »** | Refuse-t-il quand il ne sait pas ? | La **prudence** |

**C'est un diagnostic**, pas juste une note :
- Recall bas → ton **découpage** est à revoir.
- Recall bon mais Correctness basse → c'est ton **prompt de génération**.

### 4. Le « LLM-juge »

Pour noter la Correctness et la Faithfulness sur 40 réponses, on ne va pas lire à la main à chaque fois. On demande à un **second appel au modèle** de jouer le **correcteur** : on lui donne la question, la réponse attendue et la réponse obtenue, il dit « correct / incorrect ».

**L'image :** un premier élève répond, un second élève corrige avec le corrigé sous les yeux. Température 0, et tu **vérifies quelques verdicts à la main** pour te rassurer. Ce n'est pas parfait, mais c'est **directionnellement juste et défendable** devant le DSI — et surtout, **sans Ragas** (interdit) : ~100 lignes que tu as écrites et que tu maîtrises.

---

## 🧩 Où ça s'insère

**Ce qui existe déjà (on réutilise) :**
- `app/retrieval/pipeline.py` — le retrieval. L'éval l'appelle **avec tous les groupes** (on teste la qualité, pas l'ACL).
- `app/llm/contexte.py` — l'assemblage du contexte parent.
- `app/llm/prompts.py` — le **prompt système produit** (on l'utilise tel quel pour que l'éval teste le vrai système).
- La connexion base (CDC 0) — pour lire les chunks.

**Ce que ce CDC ajoute :** un dossier `eval/` **isolé**, qui ne touche à rien du produit.
```
eval/
├── pricing.py          ← les prix des modèles (à vérifier)
├── generate_golden.py  ← génère golden.jsonl depuis le corpus
├── judges.py           ← les LLM-juges (correctness + faithfulness)
├── run_eval.py         ← lance les 40 questions, écrit results.md
├── golden.jsonl        ← GÉNÉRÉ, puis relu à la main
└── results.md          ← GÉNÉRÉ — le tableau qui va dans tes slides
```

---

## ⚠️ Les pièges de ce CDC

| Piège | Conséquence | Solution |
|---|---|---|
| **Ne pas relire `golden.jsonl`** | Une question/réponse fausse dans le corrigé → score faux → il s'effondre en réunion | **Relire à la main.** 10 min. Non négociable. |
| **Confondre l'éval et l'ACL** | Si tu filtres par groupe pendant l'éval, tu mesures l'ACL, pas la qualité | L'éval tourne avec **tous les groupes**. Aucun chunk n'est filtré. |
| **Prix des modèles bidons** | Le coût/question est faux | `eval/pricing.py` contient des **placeholders** — remplace-les par les vrais prix de tes modèles (platform.openai.com). |
| **Détection de refus désalignée** | Les « je ne sais pas » mal comptés | Aligner la liste `REFUS_MARQUEURS` sur la **vraie phrase de refus** de `prompts.py`. |
| **Truquer la config pour gonfler le chiffre** | Chiffre non défendable | L'éval te DIT si tu dois ajuster (chunk_size, top_k). Tu ajustes **pour de vraies raisons**, pas pour le score. |

---

## 🗣️ Ce que je pourrai dire en réunion grâce à ça

> *« Je ne vous demande pas de me croire sur parole. J'ai testé le système sur 40 questions réelles issues de la base RH. Voici le tableau : X % de réponses justes, Y % sans la moindre invention, et quand l'information n'est pas dans la base, il refuse de répondre dans Z % des cas au lieu d'inventer. Et si ce n'était pas assez bon, je sais exactement quel levier tourner. »*

Puis tu poses `results.md` à l'écran. **C'est le moment où l'objection « ça hallucine » meurt.**

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

RAG RH Dyneff. On ajoute une **suite d'évaluation** isolée dans `eval/`, **sans Ragas ni aucune lib d'éval** (interdit) — tout est du Python nu défendable. Elle génère un golden set de 40 Q/R depuis le corpus, lance le pipeline (retrieval + génération) sur chacune, et calcule Recall@5, Correctness, Faithfulness, taux de « je ne sais pas », latence et coût, puis écrit un tableau markdown. Elle **réutilise** le retrieval, l'assemblage de contexte et le prompt système existants — elle ne les réécrit pas. Elle **ne modifie aucun fichier de `app/`**.

## État actuel du code

```
app/
├── retrieval/pipeline.py   ← retrieval filtré ACL (question + user_groups → chunks finaux + métadonnées)
├── llm/contexte.py         ← assemble les chunks parents en texte de contexte
├── llm/prompts.py          ← contient le PROMPT SYSTÈME produit (citations, "je ne sais pas", FR)
├── config.py               ← settings: OPENAI_API_KEY, LLM_MODEL, LLM_MODEL_FAST, TOP_K, TOP_N, CHUNK_SIZE
└── db / connexion          ← engine/session SQLAlchemy (CDC 0)
```

> **⚠️ AVANT DE CODER**, ouvre et repère les noms/signatures réels :
> - la fonction de **retrieval** dans `app/retrieval/pipeline.py` (entrée : question + groupes ; sortie : la liste des chunks **finaux** après rerank, avec au minimum `id` et `parent_id`),
> - la fonction d'**assemblage de contexte** dans `app/llm/contexte.py`,
> - la constante du **prompt système** dans `app/llm/prompts.py`,
> - le **helper de connexion DB** (engine SQLAlchemy) de CDC 0,
> - la colonne qui distingue **chunk enfant vs parent** dans la table `chunks`.
>
> Remplace les imports et signatures marqués `⚠️ adapter` par les vrais. Ne réécris pas ces fonctions.

---

## Ce qu'il faut construire

1. `eval/pricing.py` — prix des modèles + fonction de coût.
2. `eval/generate_golden.py` — génère `eval/golden.jsonl` (32 questions depuis le corpus + 8 trous).
3. `eval/judges.py` — LLM-juges correctness + faithfulness.
4. `eval/run_eval.py` — lance l'éval, écrit `eval/results.md`.
5. `eval/__init__.py` (vide).

---

## Spécifications techniques

### 1. `eval/pricing.py`

```python
# Prix des modèles OpenAI, en € par MILLION de tokens.
# ⚠️ À VÉRIFIER sur platform.openai.com/docs/pricing — les prix changent.
#     Les clés doivent correspondre aux valeurs de settings.LLM_MODEL / LLM_MODEL_FAST.
PRICING = {
    "terra": (2.50, 10.00),                  # placeholder — modèle fort (input, output)
    "luna": (0.15, 0.60),                    # placeholder — modèle mini
    "text-embedding-3-large": (0.13, 0.0),   # placeholder
}


def cost_eur(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price_in, price_out = PRICING.get(model, (0.0, 0.0))
    return prompt_tokens / 1_000_000 * price_in + completion_tokens / 1_000_000 * price_out
```

### 2. `eval/generate_golden.py`

```python
import json
import random
from pathlib import Path

from openai import OpenAI
from sqlalchemy import text

from app.config import settings
from app.db import engine          # ⚠️ adapter au helper de connexion réel (CDC 0)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

OUT = Path(__file__).parent / "golden.jsonl"
N_ANSWERABLE = 32
PER_DOC_MAX = 5

# Sujets ABSENTS du corpus (cf. CDC 1). Réponse attendue = refus. Testent la prudence.
GAP_QUESTIONS = [
    "Quelles sont les règles du congé paternité en 2026 ?",
    "Comment fonctionne la mobilité interne chez Dyneff ?",
    "Qu'est-ce que le congé proche aidant ?",
    "Quel est le barème du télétravail à l'international ?",
    "Quelle est la politique de voiture de fonction ?",
    "Comment sont calculées les primes d'intéressement ?",
    "Quelle est la procédure à suivre en cas de harcèlement ?",
    "Quels sont les avantages proposés par le comité social et économique ?",
]

_GEN_SYS = """Tu génères UNE paire question/réponse d'évaluation à partir d'un extrait de document RH.
La QUESTION doit être naturelle (posée par un salarié) et sa réponse doit être ENTIÈREMENT contenue dans l'extrait.
La RÉPONSE doit être courte et factuelle. Réponds STRICTEMENT en JSON : {"question": "...", "reponse": "..."}."""


def _fetch_child_chunks():
    # ⚠️ Adapter au schéma réel : on veut les chunks ENFANTS (ceux qui portent un embedding et servent à la recherche).
    sql = text("""
        SELECT c.id, c.parent_id, c.contenu, c.breadcrumb, d.titre AS document
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
        ORDER BY d.titre, c.id
    """)
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(sql).mappings().all()]


def _sample(chunks):
    by_doc = {}
    for c in chunks:
        by_doc.setdefault(c["document"], []).append(c)
    selected = []
    for items in by_doc.values():
        random.shuffle(items)
        selected.extend(items[:PER_DOC_MAX])
    random.shuffle(selected)
    return selected[:N_ANSWERABLE]


def _gen_qa(chunk):
    r = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _GEN_SYS},
            {"role": "user", "content": f"Document : {chunk['document']}\nSection : {chunk['breadcrumb']}\n---\n{chunk['contenu']}"},
        ],
    )
    data = json.loads(r.choices[0].message.content)
    return data.get("question", "").strip(), data.get("reponse", "").strip()


def main():
    random.seed(42)
    chunks = _fetch_child_chunks()
    print(f"{len(chunks)} chunks enfants récupérés")
    selected = _sample(chunks)
    print(f"{len(selected)} chunks sélectionnés\n")

    items = []
    for i, ch in enumerate(selected, 1):
        try:
            q, a = _gen_qa(ch)
            if not q:
                continue
            items.append({
                "id": f"a{i:03d}", "question": q, "reponse_attendue": a,
                "chunk_id": ch["id"], "parent_id": ch["parent_id"],
                "document": ch["document"], "section": ch["breadcrumb"],
                "answerable": True,
            })
            print(f"  [{i:02d}] {q}")
        except Exception as e:
            print(f"  [{i:02d}] échec : {e}")

    for j, q in enumerate(GAP_QUESTIONS, 1):
        items.append({
            "id": f"g{j:03d}", "question": q, "reponse_attendue": "je ne sais pas",
            "chunk_id": None, "parent_id": None, "document": None, "section": None,
            "answerable": False,
        })

    with OUT.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"\n✅ {len(items)} paires écrites dans {OUT}")
    print("⚠️  RELIS golden.jsonl À LA MAIN avant de lancer l'éval.")


if __name__ == "__main__":
    main()
```

### 3. `eval/judges.py`

```python
import json

from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

_CORRECT_SYS = """Tu es correcteur. On te donne une QUESTION, une RÉPONSE ATTENDUE et une RÉPONSE OBTENUE.
Dis si la RÉPONSE OBTENUE est correcte au regard de la RÉPONSE ATTENDUE (mêmes faits essentiels).
Une reformulation exacte compte comme correcte. Réponds STRICTEMENT en JSON : {"correct": true|false, "raison": "..."}."""

_FAITHFUL_SYS = """Tu es vérificateur d'hallucination. On te donne un CONTEXTE (extraits) et une RÉPONSE.
Dis si CHAQUE affirmation de la RÉPONSE est appuyée par le CONTEXTE. Si la réponse dit ne pas savoir, elle est fidèle.
Réponds STRICTEMENT en JSON : {"faithful": true|false, "raison": "..."}."""


def _judge(system, user):
    r = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return json.loads(r.choices[0].message.content)


def judge_correctness(question, attendu, obtenu) -> bool:
    v = _judge(_CORRECT_SYS, f"QUESTION :\n{question}\n\nRÉPONSE ATTENDUE :\n{attendu}\n\nRÉPONSE OBTENUE :\n{obtenu}")
    return bool(v.get("correct"))


def judge_faithfulness(contexte, obtenu) -> bool:
    v = _judge(_FAITHFUL_SYS, f"CONTEXTE :\n{contexte}\n\nRÉPONSE :\n{obtenu}")
    return bool(v.get("faithful"))
```

### 4. `eval/run_eval.py`

```python
import json
import time
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.retrieval.pipeline import retrieve      # ⚠️ adapter au nom réel
from app.llm.contexte import build_context       # ⚠️ adapter au nom réel
from app.llm.prompts import SYSTEM_PROMPT        # ⚠️ réutiliser le prompt produit réel

from eval.pricing import cost_eur
from eval.judges import judge_correctness, judge_faithfulness

client = OpenAI(api_key=settings.OPENAI_API_KEY)

GOLDEN = Path(__file__).parent / "golden.jsonl"
RESULTS = Path(__file__).parent / "results.md"

# ⚠️ TOUS les groupes : on teste la qualité du retrieval, PAS l'ACL. Aucun chunk filtré.
ALL_GROUPS = ["grp-rh", "grp-tous", "grp-direction"]

# ⚠️ Aligner sur la vraie phrase de refus de prompts.py.
REFUS_MARQUEURS = ["je n'ai pas trouvé", "je ne sais pas", "pas d'information", "aucune information"]


def load_golden():
    with GOLDEN.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def is_refusal(answer: str) -> bool:
    a = (answer or "").lower()
    return any(m in a for m in REFUS_MARQUEURS)


def generate_answer(question, contexte):
    """Génération NON-streamée pour capter l'usage — même prompt système et même modèle que le produit."""
    r = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexte :\n{contexte}\n\nQuestion : {question}"},
        ],
    )
    return r.choices[0].message.content, r.usage


def recall_hit(item, retrieved) -> bool:
    ids = {c["id"] for c in retrieved}
    parents = {c.get("parent_id") for c in retrieved}
    return item["chunk_id"] in ids or (item["parent_id"] is not None and item["parent_id"] in parents)


def _pct(values):
    vals = [v for v in values if v is not None]
    return 100 * sum(1 for v in vals if v) / len(vals) if vals else 0.0


def write_results(rows):
    answerable = [r for r in rows if r["answerable"]]
    gaps = [r for r in rows if not r["answerable"]]

    recall = _pct([r["recall"] for r in answerable])
    correctness = _pct([r["correct"] for r in answerable])
    faithfulness = _pct([r["faithful"] for r in rows])
    idk_ok = _pct([r["correct"] for r in gaps])       # % de trous correctement refusés
    idk_rate = _pct([r["refused"] for r in rows])      # taux de refus global
    lat = sum(r["latency_ms"] for r in rows) / len(rows)
    cost = sum(r["cost"] for r in rows) / len(rows)

    md = f"""# Résultats de l'évaluation — RAG Dyneff

Golden set : **{len(rows)} questions** ({len(answerable)} avec réponse, {len(gaps)} trous de corpus)
Config : modèle `{settings.LLM_MODEL}` · TOP_K={settings.TOP_K} · TOP_N={settings.TOP_N} · CHUNK_SIZE={settings.CHUNK_SIZE}

| Métrique | Score | Ce qu'elle mesure |
|---|---|---|
| **Recall@{settings.TOP_N}** | **{recall:.0f} %** | Le bon passage est-il récupéré ? (retrieval) |
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
        md += (f"| {r['id']} | {typ} | {rec} | {'✅' if r['correct'] else '❌'} | "
               f"{'✅' if r['faithful'] else '❌'} | {'oui' if r['refused'] else 'non'} | "
               f"{r['latency_ms'] / 1000:.1f} s |\n")

    RESULTS.write_text(md, encoding="utf-8")


def main():
    golden = load_golden()
    print(f"{len(golden)} questions dans le golden set\n")

    rows = []
    for it in golden:
        t0 = time.perf_counter()
        retrieved = retrieve(it["question"], user_groups=ALL_GROUPS)   # ⚠️ adapter la signature ; doit renvoyer les chunks FINAUX (post-rerank) avec id + parent_id
        contexte = build_context(retrieved)                            # ⚠️ adapter la signature
        answer, usage = generate_answer(it["question"], contexte)
        latency_ms = (time.perf_counter() - t0) * 1000

        refused = is_refusal(answer)
        cost = cost_eur(settings.LLM_MODEL, usage.prompt_tokens, usage.completion_tokens)

        if it["answerable"]:
            recall = recall_hit(it, retrieved)
            if refused:
                correct, faithful = False, True          # refuser à tort : faux, mais n'invente rien
            else:
                correct = judge_correctness(it["question"], it["reponse_attendue"], answer)
                faithful = judge_faithfulness(contexte, answer)
        else:                                            # question "trou de corpus"
            recall = None
            correct = refused                            # bonne réponse = savoir refuser
            faithful = True if refused else judge_faithfulness(contexte, answer)

        rows.append({
            "id": it["id"], "answerable": it["answerable"], "recall": recall,
            "correct": correct, "faithful": faithful, "refused": refused,
            "latency_ms": latency_ms, "cost": cost,
        })
        print(f"{'✅' if correct else '❌'} [{it['id']}] {it['question'][:60]}")

    write_results(rows)

    ans = [r for r in rows if r["answerable"]]
    gaps = [r for r in rows if not r["answerable"]]
    print("\n" + "=" * 55)
    print(f"Recall@{settings.TOP_N}    : {_pct([r['recall'] for r in ans]):.0f}%")
    print(f"Correctness  : {_pct([r['correct'] for r in ans]):.0f}%")
    print(f"Faithfulness : {_pct([r['faithful'] for r in rows]):.0f}%")
    print(f"Refus trous  : {_pct([r['correct'] for r in gaps]):.0f}%")
    print(f"Latence moy. : {sum(r['latency_ms'] for r in rows) / len(rows) / 1000:.1f}s")
    print(f"Coût/question: {sum(r['cost'] for r in rows) / len(rows):.4f}€")
    print(f"✅ Tableau écrit dans {RESULTS}")


if __name__ == "__main__":
    main()
```

---

## Contraintes impératives

- **INTERDIT** : Ragas, toute lib d'évaluation, LangChain. Python nu uniquement.
- **Ne modifier aucun fichier de `app/`.** L'éval réutilise le retrieval, le contexte et le prompt système existants.
- **Tous les groupes** pendant l'éval (`ALL_GROUPS`) : on mesure la qualité, pas l'ACL.
- **`golden.jsonl` est généré puis relu à la main** — le script `generate_golden.py` l'affiche à l'écran pendant la génération pour faciliter la relecture.
- **`json_object` + température 0** pour la génération du golden et les juges.
- Aligner `REFUS_MARQUEURS` sur la vraie phrase de refus de `prompts.py`, et les clés de chunk (`id`, `parent_id`) sur la sortie réelle du retrieval.
- Mettre les **vrais prix** dans `pricing.py`.

---

## Definition of Done

```bash
cd c:\Users\ISSA\Desktop\RAG
docker compose up -d          # la base doit tourner (corpus déjà ingéré)

# 1) Générer le corrigé
python -m eval.generate_golden
#    → eval/golden.jsonl créé, ~40 lignes affichées à l'écran

# 2) ⚠️ RELIRE eval/golden.jsonl À LA MAIN (corriger toute paire douteuse)

# 3) Lancer l'évaluation
python -m eval.run_eval
```

**Résultat attendu exactement :**

1. `eval/generate_golden.py` affiche ~32 questions générées + écrit **`eval/golden.jsonl`** (~40 lignes : `a001…` avec `chunk_id`, `g001…` sans).
2. Après relecture, `eval/run_eval.py` traite les 40 questions une par une (✅/❌ en direct) et écrit **`eval/results.md`**.
3. `eval/results.md` contient **le tableau de scores** : Recall@5, Correctness, Faithfulness, taux de refus, latence, coût — plus le détail par question.
4. Ordre de grandeur sain d'un pipeline correct : **Recall@5 ≥ 80 %**, **Faithfulness ≥ 95 %**, **trous correctement refusés ≥ 80 %**. Si Recall bas → revoir le découpage (CDC 2) ; si Correctness basse mais Recall bon → revoir le prompt (CDC 4).

**C'est `eval/results.md` qui va dans la note d'architecture et dans les slides (CDC 14).** Sans ce tableau, le CDC n'est pas fini.
