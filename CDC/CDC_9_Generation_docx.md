# CDC 9 — La génération de fichiers (.docx)

═══════════════════════════════════════════════════════════
                 PARTIE A — POUR ISSA
      (comprendre — NE PAS coller dans Cursor)
═══════════════════════════════════════════════════════════

## 🎯 L'objectif en une phrase

Quand l'utilisateur écrit « **rédige le courrier de refus de télétravail…** », l'assistant ne se contente pas de répondre à l'écran : il **génère un vrai fichier Word**, rédigé à partir de la procédure interne, sourcé, et le propose au **téléchargement**.

---

## 💡 Pourquoi c'est important

**C'est LA feature.** Datasulting a été payé 50–100 k€ et **n'avait pas ça**.

| Un RAG qui répond | Un RAG qui produit le document |
|---|---|
| « La procédure télétravail dit ceci… » | **Un `.docx` se télécharge, rédigé, prêt à relire** |
| Informe. Gain : 30 s | **Remplace du travail. Gain : 45 min** |

C'est le **moment n°3** de ta démo — celui qui fait basculer la salle de « outil sympa » à « ROI ». La phrase à sortir juste après le téléchargement : *« Ça, Datasulting ne savait pas le faire. »*

---

## 📚 Les concepts à comprendre

### 1. La détection d'intention

**L'image :** un aiguillage. À chaque message, on regarde s'il contient une demande de rédaction (« rédige », « génère un courrier », « fais une note », « prépare la fiche »). Si oui → on part sur la branche « génération de document ». Sinon → réponse chat normale.

Pour le POC c'est une **liste de mots-clés** (~10 lignes de regex). Simple, défendable, et améliorable plus tard par un vrai classifieur ou la commande `/doc` (CDC 11). Tu peux le dire tel quel en réunion : *« détection d'intention par règles, évolutive vers un classifieur. »*

### 2. Générer une **structure JSON**, pas du texte libre

**Le problème :** si on demande au LLM « écris-moi un courrier », il rend du texte en vrac, impossible à mettre en forme proprement dans Word.

**La solution :** on lui demande de répondre en **JSON structuré** — `{titre, objet, destinataire, blocs:[…], signature}` — où chaque bloc est un paragraphe, un titre, une liste ou un tableau. Ensuite, du code Python transforme ce JSON en `.docx` avec la mise en forme Dyneff.

**L'image :** le LLM remplit un **formulaire**, le code Python **imprime** le formulaire proprement. On garde le contrôle de la mise en page.

> On force le mode JSON de l'API (`response_format={"type":"json_object"}`) + température 0. Sans ça, le modèle bavarde et le `json.loads` plante.

### 3. Construire le `.docx` en mémoire (`python-docx`)

`python-docx` (déjà dans ta stack) crée le document. On l'écrit dans un **tampon mémoire** (`BytesIO`) plutôt que sur le disque — on récupère directement les octets à renvoyer au navigateur.

**Bonnes pratiques appliquées** (elles évitent un rendu cassé chez le destinataire) :
- styles Word intégrés pour les titres (`add_heading`), listes à puces via le style `List Bullet` (jamais un « • » tapé à la main),
- tableaux avec le style `Table Grid` et un ombrage d'en-tête **gris clair** (jamais un noir plein),
- un filet horizontal via une **bordure de paragraphe**, pas un tableau détourné,
- des **paragraphes séparés**, jamais de `\n` fourré dans un run.

### 4. Le stockage du fichier + l'endpoint de téléchargement

Une fois les octets produits, on les range dans un **petit stockage mémoire** (un dictionnaire `id → fichier`) et on renvoie l'`id`. Le navigateur télécharge via `GET /api/files/{id}`, qui renvoie les octets avec l'en-tête `Content-Disposition: attachment` (c'est cet en-tête qui déclenche le téléchargement au lieu d'afficher le fichier).

> **Pour le POC :** stockage en mémoire (worker unique). Simple et sans risque pour la démo. Limite assumée : les fichiers sont perdus si l'API redémarre — sans importance, tu génères et télécharges dans la même session. En prod : object storage ou colonne binaire dans la table `fichiers` (qui existe déjà). Une phrase suffit à le dire en réunion.

### 5. Un nouvel événement SSE : `file`

Le flux de streaming gagne un événement : après le petit message (« Voici le document… »), le backend envoie `event: file {id, filename}`. Le front le transforme en **carte de téléchargement**.

---

## 🧩 Où ça s'insère

**Ce qui existe déjà (on réutilise, on ne réécrit pas) :**
- `app/api/chat.py` — le streaming SSE (CDC 4). On y **insère une branche** « intention doc ».
- `app/retrieval/pipeline.py` — le retrieval **filtré par ACL**. On le réutilise tel quel.
- `app/llm/contexte.py` — l'assemblage des chunks parents. Réutilisé pour nourrir la rédaction.
- Le sérialiseur de sources existant (champs réels : `document`, `section`, `page`, `texte`…).
- `web/lib/use-rag-chat.ts` + `web/components/chat-message.tsx` (CDC 8). On y ajoute la gestion de `file`.

**Ce que ce CDC ajoute :**
```
app/files/
├── intent.py          ← détection d'intention (regex)
├── generate_doc.py    ← LLM → JSON structuré
├── docx.py            ← JSON → octets .docx (python-docx)
└── store.py           ← stockage mémoire id → fichier
app/api/files.py       ← GET /api/files/{id}
web/components/file-download.tsx  ← la carte de téléchargement
```

---

## ⚠️ Les pièges de ce CDC

| Piège | Pourquoi c'est grave | Solution |
|---|---|---|
| **Générer un document sans chunks** | Un courrier officiel **inventé** (motifs de refus hallucinés) est un risque réel. | Si le retrieval renvoie 0 chunk (ACL ou hors corpus) → **chemin « je ne sais pas », AUCUN fichier.** |
| **ACL contournée par la génération** | Si Paul pouvait générer une note sur la grille des salaires, l'ACL ne servirait à rien. | La génération **réutilise le retrieval filtré**. Paul → 0 chunk → pas de fichier. **À tester explicitement.** |
| **Le LLM bavarde au lieu de rendre du JSON** | `json.loads` plante, pas de document. | `response_format={"type":"json_object"}` + température 0. |
| **Réinventer le format SSE / les sources** | Le vrai format est `{"texte":…}`, sources en `document`. | **Réutiliser les helpers existants de `chat.py`**, ne rien redéfinir. |
| **Le fichier ne se télécharge pas, il s'affiche** | En-tête manquant. | `Content-Disposition: attachment; filename="…"` sur la réponse. |

---

## 🗣️ Ce que je pourrai dire en réunion grâce à ça

> *« Je ne demande pas à l'IA de me résumer la procédure. Je lui demande de rédiger le courrier. »* **[le .docx se télécharge]** *« Sourcé, conforme, prêt à relire et signer. Datasulting a coûté entre 50 et 100 000 € et ne savait pas faire ça. Un RAG qui répond, ça informe. Un RAG qui produit le document, ça remplace du travail. »*

---

═══════════════════════════════════════════════════════════
                PARTIE B — POUR CURSOR
        (copier-coller INTÉGRALEMENT dans Cursor)
═══════════════════════════════════════════════════════════

## Contexte du projet

RAG RH Dyneff. Backend FastAPI + Postgres/pgvector + OpenAI (SDK `openai`), front Next.js. On ajoute la **génération de documents Word** : détecter une demande de rédaction, générer le contenu en JSON structuré via le LLM (à partir des chunks récupérés, **filtrés par ACL**), construire un `.docx` avec **python-docx** (déjà installé), et le proposer au téléchargement. **Interdit** : LangChain, toute autre lib docx que `python-docx`. **Ne pas modifier** le pipeline de retrieval ni le format SSE existant — on les réutilise.

## État actuel du code

```
app/
├── api/chat.py            ← POST /api/chat en SSE. Émet des événements status/sources/token/done
│                            via un helper interne. Token = {"texte": "..."}. Latence = "latence_ms".
├── retrieval/pipeline.py  ← fonction de retrieval filtrée ACL (question + user_groups → chunks + sources)
├── llm/contexte.py        ← assemble les chunks parents en texte de contexte
├── llm/generate.py        ← génération streaming (client openai déjà configuré)
├── config.py              ← settings: OPENAI_API_KEY, LLM_MODEL, LLM_MODEL_FAST, …
└── main.py                ← app FastAPI, monte les routers (+ CORS déjà OK)
web/
├── lib/use-rag-chat.ts    ← client SSE custom (parse status/sources/token/done)
├── lib/types.ts           ← type Message, Source
└── components/chat-message.tsx ← rend un message + sources + actions
```

> **⚠️ AVANT DE CODER :** ouvre `app/api/chat.py` et repère (a) le **helper qui formate un événement SSE** (ex. une fonction `sse(event, data)`), (b) la fonction qui **appelle le retrieval**, (c) la variable qui contient les **sources sérialisées** et le **contexte parent**. Tu **réutilises** ces trois éléments dans la branche ci-dessous. Ne les réécris pas. Aligne aussi les **clés des sources** (`document`, `section`, `page`…) sur ce que `chat.py` produit réellement.

---

## Ce qu'il faut construire

1. `app/files/intent.py` — détection d'intention par regex.
2. `app/files/generate_doc.py` — LLM → payload JSON structuré (mode JSON, température 0).
3. `app/files/docx.py` — payload JSON + sources → octets `.docx` (python-docx).
4. `app/files/store.py` — stockage mémoire `id → {content, filename}`.
5. `app/api/files.py` — `GET /api/files/{id}` (téléchargement), monté dans `main.py`.
6. **Branche « intention doc »** insérée dans le générateur SSE de `app/api/chat.py`.
7. Front : nouvel événement `file` géré dans `use-rag-chat.ts`, champ `file` sur `Message`, composant `file-download.tsx` rendu dans `chat-message.tsx`.

---

## Spécifications techniques

### 1. `app/files/intent.py`

```python
import re

_DOC_TRIGGERS = [
    r"\brédige", r"\brediger", r"\brédigez",
    r"\bgénère", r"\bgenerer", r"\bgénérer",
    r"\bécris\b", r"\becrire\b", r"\bécrire\b",
    r"\bprépare", r"\bpreparer",
    r"\bfais(?:-| )?(?:moi )?une note", r"\bnote de synthèse",
    r"\bcourrier\b", r"\blettre\b", r"\bmodèle de\b", r"\brédiger?\b",
    r"\bfiche d'?onboarding", r"\bfiche de\b",
]
_DOC_RE = re.compile("|".join(_DOC_TRIGGERS), re.IGNORECASE)


def detect_document_intent(question: str) -> bool:
    """Détection d'intention par règles (POC). Évolutive vers un classifieur / la commande /doc."""
    return bool(_DOC_RE.search(question or ""))
```

### 2. `app/files/generate_doc.py`

```python
import json

from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_DOC = """Tu es un assistant RH qui rédige des documents professionnels pour Dyneff.
Tu rédiges UNIQUEMENT à partir des extraits fournis. Tu n'inventes aucune règle, aucun chiffre,
aucune procédure absente des extraits. Le style est sobre et professionnel, en français.

Tu réponds STRICTEMENT en JSON valide, sans aucun texte autour, au format exact :
{
  "type": "courrier" ou "note",
  "titre": "titre du document",
  "objet": "objet du courrier, ou null",
  "destinataire": "bloc destinataire (nom, fonction), ou null",
  "blocs": [
    {"type": "paragraphe", "texte": "..."},
    {"type": "titre", "texte": "..."},
    {"type": "liste", "items": ["...", "..."]},
    {"type": "tableau", "entetes": ["...", "..."], "lignes": [["...", "..."]]}
  ],
  "signature": "bloc de signature, ou null"
}

Pour un refus, expose les motifs prévus par la procédure (extraits). Reste factuel."""


def generate_document_payload(question: str, contexte: str) -> dict:
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,          # le modèle fort
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_DOC},
            {"role": "user", "content": f"Demande :\n{question}\n\nExtraits disponibles :\n{contexte}"},
        ],
    )
    return json.loads(resp.choices[0].message.content)
```

> Si un client `openai` est déjà instancié ailleurs (ex. `app/llm/generate.py`), réutilise-le au lieu d'en recréer un.

### 3. `app/files/docx.py`

```python
from io import BytesIO
from datetime import date

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PETROLE = RGBColor(0x1C, 0x2B, 0x33)   # encre pétrole (charte Dyneff)
GRIS = RGBColor(0x55, 0x60, 0x66)


def _set_cell_background(cell, hex_color: str) -> None:
    """Ombrage de cellule (clear/auto — jamais un noir plein)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def _add_bottom_border(paragraph) -> None:
    """Filet horizontal via bordure de paragraphe (pas un tableau détourné)."""
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "1C2B33")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def build_document(payload: dict, sources: list[dict]) -> bytes:
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # En-tête / papier à en-tête
    head = doc.add_paragraph()
    r = head.add_run("DYNEFF")
    r.bold = True
    r.font.size = Pt(18)
    r.font.color.rgb = PETROLE

    sub = doc.add_paragraph()
    rs = sub.add_run("Direction des Ressources Humaines")
    rs.font.size = Pt(10)
    rs.font.color.rgb = GRIS
    _add_bottom_border(sub)

    # Date (à droite)
    d = doc.add_paragraph()
    d.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    d.add_run(date.today().strftime("Le %d/%m/%Y")).font.size = Pt(10)

    # Destinataire (courrier)
    if payload.get("destinataire"):
        doc.add_paragraph().add_run(str(payload["destinataire"])).font.size = Pt(11)

    # Objet
    if payload.get("objet"):
        obj = doc.add_paragraph()
        lab = obj.add_run("Objet : ")
        lab.bold = True
        obj.add_run(str(payload["objet"]))

    # Titre (note)
    if payload.get("type") == "note" and payload.get("titre"):
        doc.add_heading(str(payload["titre"]), level=1)

    # Corps
    for bloc in payload.get("blocs", []) or []:
        t = bloc.get("type")
        if t == "titre":
            doc.add_heading(str(bloc.get("texte", "")), level=2)
        elif t == "paragraphe":
            doc.add_paragraph(str(bloc.get("texte", "")))
        elif t == "liste":
            for item in bloc.get("items", []) or []:
                doc.add_paragraph(str(item), style="List Bullet")
        elif t == "tableau":
            entetes = bloc.get("entetes", []) or []
            lignes = bloc.get("lignes", []) or []
            if entetes:
                table = doc.add_table(rows=1, cols=len(entetes))
                table.style = "Table Grid"
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                hdr = table.rows[0].cells
                for i, texte in enumerate(entetes):
                    hdr[i].text = ""
                    run = hdr[i].paragraphs[0].add_run(str(texte))
                    run.bold = True
                    _set_cell_background(hdr[i], "E8ECEF")
                for ligne in lignes:
                    cells = table.add_row().cells
                    for i, val in enumerate(ligne):
                        if i < len(cells):
                            cells[i].text = str(val)

    # Signature
    if payload.get("signature"):
        doc.add_paragraph()
        doc.add_paragraph().add_run(str(payload["signature"])).font.size = Pt(11)

    # Sources
    if sources:
        doc.add_paragraph()
        rule = doc.add_paragraph()
        _add_bottom_border(rule)
        sh = doc.add_paragraph().add_run("Sources")
        sh.bold = True
        sh.font.size = Pt(10)
        for i, s in enumerate(sources, start=1):
            # ⚠️ aligne ces clés sur le sérialiseur de sources réel de chat.py
            libelle = " · ".join(
                str(x)
                for x in [
                    s.get("document"),
                    s.get("section"),
                    f"p.{s.get('page')}" if s.get("page") else None,
                ]
                if x
            )
            doc.add_paragraph().add_run(f"[{i}] {libelle}").font.size = Pt(9)

    # Pied de page (mention honnête)
    fp = doc.sections[0].footer.paragraphs[0]
    fp.text = "Document généré par l'Assistant RH Dyneff — à relire avant signature."
    for run in fp.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x88, 0x90, 0x96)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
```

### 4. `app/files/store.py`

```python
import uuid

# Stockage mémoire pour le POC (worker unique).
# Prod : object storage ou colonne binaire dans la table `fichiers`.
_FILES: dict[str, dict] = {}


def save_file(content: bytes, filename: str) -> str:
    file_id = uuid.uuid4().hex
    _FILES[file_id] = {"content": content, "filename": filename}
    return file_id


def get_file(file_id: str) -> dict | None:
    return _FILES.get(file_id)
```

### 5. `app/api/files.py`

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.files.store import get_file

router = APIRouter()

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.get("/api/files/{file_id}")
def download_file(file_id: str):
    f = get_file(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return Response(
        content=f["content"],
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{f["filename"]}"'},
    )
```

Monter le router dans `app/main.py` (à côté des routers existants) :
```python
from app.api import files as files_router
app.include_router(files_router.router)
```

### 6. Branche « intention doc » dans `app/api/chat.py`

Dans le **générateur SSE**, **après** que le retrieval a produit les chunks/sources/contexte et **avant** la génération chat normale, insérer la branche suivante. `sse(...)`, l'appel retrieval, `sources` et `contexte` sont les **helpers/variables existants** — réutilise-les tels quels.

```python
import re
import unicodedata

from app.files.intent import detect_document_intent
from app.files.generate_doc import generate_document_payload
from app.files.docx import build_document
from app.files.store import save_file


def _slugify(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^a-zA-Z0-9]+", "-", texte).strip("-").lower()
    return texte[:60] or "document"


# --- dans le générateur, après le retrieval (chunks, sources, contexte connus) ---
if detect_document_intent(question):
    if not chunks:                      # 0 chunk = ACL ou hors corpus
        # → NE PAS générer de fichier. Suivre le chemin "je ne sais pas" habituel.
        # (réutiliser exactement le bloc existant qui streame le refus + done a_repondu=false)
        ...
    else:
        yield sse("status", {"label": "Rédaction du document…"})
        payload = generate_document_payload(question, contexte)
        content = build_document(payload, sources)
        filename = _slugify(payload.get("titre") or "document") + ".docx"
        file_id = save_file(content, filename)

        yield sse("sources", sources)   # même sérialiseur que le chat normal

        message = ("Voici le document, rédigé à partir des procédures internes. "
                   "Vous pouvez le télécharger ci-dessous.")
        for mot in message.split(" "):
            yield sse("token", {"texte": mot + " "})

        yield sse("file", {"id": file_id, "filename": filename})
        yield sse("done", {"latence_ms": 0})   # remplace par la vraie latence mesurée
        return
```

> Adapte les noms (`question`, `chunks`, `sources`, `contexte`, `sse`) aux identifiants réels de `chat.py`. Le point non négociable : **si `chunks` est vide → aucun fichier, chemin refus.**

### 7. Front — gérer l'événement `file`

**`web/lib/types.ts`** — ajouter le champ sur `Message` :
```typescript
export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  latencyMs?: number;
  aRepondu?: boolean;
  file?: { id: string; filename: string };   // ← NOUVEAU
};
```

**`web/lib/use-rag-chat.ts`** — dans la boucle d'événements, ajouter un cas :
```typescript
} else if (event === "file") {
  const f = safeJson<{ id: string; filename: string }>(data);
  if (f?.id) patch((m) => ({ ...m, file: f }));
}
```

**`web/components/file-download.tsx`** — nouveau fichier :
```tsx
"use client";

import { FileDown } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function FileDownload({ id, filename }: { id: string; filename: string }) {
  return (
    <a
      href={`${API_URL}/api/files/${id}`}
      download={filename}
      className="mt-3 inline-flex items-center gap-2 rounded-xl border bg-card px-4 py-3 text-sm transition-colors hover:bg-accent"
    >
      <FileDown className="h-4 w-4 shrink-0 text-blue-600" />
      <span className="font-medium">{filename}</span>
      <span className="text-muted-foreground">· Télécharger</span>
    </a>
  );
}
```

**`web/components/chat-message.tsx`** — importer et rendre la carte quand `message.file` existe (après le composant `Sources`) :
```tsx
import { FileDownload } from "./file-download";

// … dans le rendu du message assistant, sous <Sources … /> :
{message.file && (
  <FileDownload id={message.file.id} filename={message.file.filename} />
)}
```

---

## Contraintes impératives

- **INTERDIT** : LangChain, toute lib docx autre que `python-docx`.
- **Ne pas modifier** `app/retrieval/pipeline.py` ni le format SSE existant. Réutiliser le helper `sse`, l'appel retrieval, le sérialiseur de sources, l'assemblage de contexte.
- **ACL non négociable** : la génération réutilise le retrieval **filtré par groupes**. `chunks` vide → **aucun fichier**, chemin « je ne sais pas ».
- **Génération JSON** : `response_format={"type":"json_object"}` + `temperature=0`.
- Aligner les **clés de sources** (`document`, `section`, `page`) sur le sérialiseur réel.
- Le téléchargement passe par `Content-Disposition: attachment`.

---

## Definition of Done

```bash
# Backend + front en marche
cd c:\Users\ISSA\Desktop\RAG
docker compose up -d
cd web
npm run dev
# → http://localhost:3000
```

**Résultat attendu exactement :**

1. **Génération (utilisateur Marie)** — taper :
   > `Rédige le courrier de refus de télétravail 3 jours par semaine pour M. Dupont, conforme à notre procédure`
   - un statut « Rédaction du document… » apparaît,
   - un court message se streame (« Voici le document… »),
   - une **carte de téléchargement bleue** apparaît avec un nom de fichier `.docx`.
2. **Le fichier** — cliquer la carte → un `.docx` **se télécharge** (il ne s'affiche pas dans l'onglet). En l'ouvrant :
   - en-tête **DYNEFF — Direction des Ressources Humaines** (encre pétrole),
   - la date, un **Objet**, un corps de courrier **fondé sur la procédure** (plafond 2 j/semaine, motifs de refus),
   - une signature, une section **Sources** en bas, un pied de page « à relire avant signature ».
3. **ACL sur la génération (utilisateur Paul)** — taper :
   > `Rédige une note de synthèse sur la grille des salaires`
   - réponse « je n'ai pas d'information accessible » (ou équivalent),
   - **AUCUNE carte de téléchargement**. ← la sécurité s'applique aussi à la génération.
4. **Chat normal intact** — une question simple (« combien de jours de congés ? ») répond **comme avant**, sans fichier.

**Si un document se génère alors que `chunks` est vide, ou si le fichier s'affiche au lieu de se télécharger → NON conforme.**
