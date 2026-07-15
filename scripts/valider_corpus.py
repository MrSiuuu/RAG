#!/usr/bin/env python3
"""Valide le corpus et son manifest AVANT l'ingestion (CDC 2).

Bibliotheque standard UNIQUEMENT : ce script doit pouvoir tourner
sur n'importe quelle machine, sans venv, sans Docker, sans dependance.

Usage :
    python scripts/valider_corpus.py

Codes de sortie :
    0 = corpus valide
    1 = corpus invalide
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent
MANIFEST = RACINE / "corpus" / "manifest.json"
CORPUS_DIR = RACINE / "corpus"

TYPES_VALIDES = {"pdf", "md"}
SOURCES_VALIDES = {"public", "synthetique", "fictif"}
SENSIBILITES_VALIDES = {"public", "interne", "confidentiel"}
GROUPES_VALIDES = {"grp-tous", "grp-rh", "grp-admin"}

MOTS_MINIMUM = 900
TITRES_H2_MIN = 4
MOTS_PAR_CHUNK = 150


def charger_manifest() -> dict:
    """Lit et parse le manifest. Erreur claire si absent ou malforme."""
    if not MANIFEST.exists():
        raise FileNotFoundError(f"Manifest introuvable : {MANIFEST}")
    try:
        with MANIFEST.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalide dans {MANIFEST} : {exc}") from exc


def compter_mots(texte: str) -> int:
    """Compte les mots hors blocs de code et hors tableaux."""
    lignes = []
    dans_code = False
    for ligne in texte.splitlines():
        if ligne.strip().startswith("```"):
            dans_code = not dans_code
            continue
        if dans_code:
            continue
        if re.match(r"^\s*\|", ligne):
            continue
        if re.match(r"^\s*[-:|]+\s*$", ligne):
            continue
        lignes.append(ligne)
    corps = "\n".join(lignes)
    mots = re.findall(r"\b[\wÀ-ÿ'-]+\b", corps, flags=re.UNICODE)
    return len(mots)


def compter_titres(texte: str, niveau: int) -> int:
    """Compte les titres markdown de niveau donne (#, ## ou ###)."""
    prefix = "#" * niveau + " "
    pattern = re.compile(rf"^{re.escape(prefix)}[^\n]+", re.MULTILINE)
    return len(pattern.findall(texte))


def estimer_chunks(texte: str) -> int:
    """Estimation grossiere : nombre de ### ou equivalent mot."""
    nb_h3 = compter_titres(texte, 3)
    if nb_h3 > 0:
        return nb_h3
    return max(1, compter_mots(texte) // MOTS_PAR_CHUNK)


def controle_securite(documents: list, erreurs: list) -> None:
    """Le controle qui compte : aucun document confidentiel ne doit
    etre accessible a grp-tous.

    Si ce controle passe, la demo ACL du CDC 6 fonctionnera.
    S'il echoue, la grille des salaires est publique. Le projet meurt.
    """
    confidentiels = [d for d in documents if d.get("sensibilite") == "confidentiel"]

    for doc in confidentiels:
        groupes = doc.get("allowed_groups", [])
        if "grp-tous" in groupes:
            erreurs.append(
                f"FATAL - {doc['chemin']} est CONFIDENTIEL mais accessible a grp-tous !"
            )
        if groupes != ["grp-rh"]:
            erreurs.append(
                f"{doc['chemin']} : un document confidentiel doit etre restreint "
                f"a ['grp-rh'], trouve {groupes}"
            )

    if len(confidentiels) != 2:
        erreurs.append(
            f"Attendu : 2 documents confidentiels. Trouve : {len(confidentiels)}"
        )


def fichiers_orphelins(documents: list) -> list[str]:
    """Les .md de corpus/ non declares au manifest."""
    declares = {Path(d["chemin"]).name for d in documents}
    orphelins = []
    for fichier in sorted(CORPUS_DIR.glob("*.md")):
        if fichier.name not in declares:
            orphelins.append(str(fichier.relative_to(RACINE)))
    return orphelins


def valider_document(
    doc: dict,
    erreurs: list,
    avertissements: list,
) -> dict:
    """Valide un document, renvoie ses statistiques."""
    chemin = RACINE / doc["chemin"]
    nom = Path(doc["chemin"]).name
    stats: dict = {
        "nom": nom,
        "type": doc.get("type", "?"),
        "sensibilite": doc.get("sensibilite", "?"),
        "groupes": ",".join(doc.get("allowed_groups", [])),
        "mots": "-",
        "h2": "-",
        "chunks": "-",
        "existe": chemin.exists(),
    }

    if doc.get("type") not in TYPES_VALIDES:
        erreurs.append(f"{doc['chemin']} : type invalide '{doc.get('type')}'")

    if doc.get("source") not in SOURCES_VALIDES:
        erreurs.append(f"{doc['chemin']} : source invalide '{doc.get('source')}'")

    if doc.get("sensibilite") not in SENSIBILITES_VALIDES:
        erreurs.append(
            f"{doc['chemin']} : sensibilite invalide '{doc.get('sensibilite')}'"
        )

    groupes = doc.get("allowed_groups", [])
    if not groupes:
        erreurs.append(f"{doc['chemin']} : allowed_groups vide")
    else:
        for g in groupes:
            if g not in GROUPES_VALIDES:
                erreurs.append(f"{doc['chemin']} : groupe inconnu '{g}'")

    if doc.get("sensibilite") == "confidentiel" and "grp-tous" in groupes:
        erreurs.append(
            f"FATAL - {doc['chemin']} est CONFIDENTIEL mais accessible a grp-tous !"
        )

    ext = chemin.suffix.lower().lstrip(".")
    if doc.get("type") and ext and doc["type"] != ext:
        erreurs.append(
            f"{doc['chemin']} : type '{doc['type']}' incoherent avec extension '.{ext}'"
        )

    if not chemin.exists():
        if doc.get("type") == "pdf" and "convention-collective" in nom:
            avertissements.append(
                f"{doc['chemin']} : fichier PDF absent (depot manuel attendu)"
            )
            stats["chunks"] = "~200"
        else:
            erreurs.append(f"{doc['chemin']} : fichier introuvable")
        return stats

    if doc.get("type") == "md":
        texte = chemin.read_text(encoding="utf-8")
        nb_mots = compter_mots(texte)
        nb_h2 = compter_titres(texte, 2)
        nb_h1 = compter_titres(texte, 1)
        nb_chunks = estimer_chunks(texte)

        stats["mots"] = str(nb_mots)
        stats["h2"] = str(nb_h2)
        stats["chunks"] = str(nb_chunks)

        if nb_h1 != 1:
            erreurs.append(
                f"{doc['chemin']} : attendu exactement 1 titre #, trouve {nb_h1}"
            )
        if nb_h2 < TITRES_H2_MIN:
            erreurs.append(
                f"{doc['chemin']} : {nb_h2} titres ## (minimum {TITRES_H2_MIN})"
            )
        if nb_mots < MOTS_MINIMUM:
            erreurs.append(
                f"{doc['chemin']} : {nb_mots} mots (minimum {MOTS_MINIMUM})"
            )

        conf = doc.get("sensibilite") == "confidentiel"
        if conf:
            if "DOCUMENT CONFIDENTIEL" not in texte:
                avertissements.append(
                    f"{doc['chemin']} : bandeau DOCUMENT CONFIDENTIEL absent"
                )
        elif "Document synthétique" not in texte and "Document synthetique" not in texte:
            avertissements.append(
                f"{doc['chemin']} : mention 'Document synthetique' absente"
            )

    elif doc.get("type") == "pdf":
        stats["chunks"] = "~200"

    return stats


def afficher_rapport(
    stats_list: list[dict],
    manifest: dict,
    erreurs: list,
    avertissements: list,
) -> None:
    """Affiche le tableau recapitulatif et le verdict."""
    print("=" * 77)
    print("  VALIDATION DU CORPUS - RAG DYNEFF")
    print("=" * 77)
    print()
    print(
        f"  {'FICHIER':<42} {'TYPE':<5} {'SENSIBILITE':<13} "
        f"{'GROUPES':<11} {'MOTS':>5} {'##':>3} {'~CHUNKS':>8}"
    )
    print("  " + "-" * 93)

    total_chunks = 0
    for s in stats_list:
        chunks_aff = s["chunks"]
        if chunks_aff not in ("-",) and chunks_aff.startswith("~"):
            try:
                total_chunks += int(chunks_aff.replace("~", ""))
            except ValueError:
                pass
        elif chunks_aff.isdigit():
            total_chunks += int(chunks_aff)

        print(
            f"  {s['nom']:<42} {s['type']:<5} {s['sensibilite']:<13} "
            f"{s['groupes']:<11} {str(s['mots']):>5} {str(s['h2']):>3} "
            f"{str(s['chunks']):>8}"
        )

    documents = manifest.get("documents", [])
    nb_public = sum(
        1 for d in documents if "grp-tous" in d.get("allowed_groups", [])
    )
    nb_conf = sum(1 for d in documents if d.get("sensibilite") == "confidentiel")
    nb_trous = len(manifest.get("trous_connus", []))

    print()
    print("  " + "-" * 93)
    print(f"  {len(documents)} documents declares")
    print(f"  {nb_public} accessibles a tous (grp-tous)")
    print(f"  {nb_conf} CONFIDENTIELS (grp-rh uniquement)")
    print(f"  ~{total_chunks} chunks estimes")
    print(f"  {nb_trous} trous connus declares")
    print()
    print("  CONTROLE DE SECURITE")
    print("  " + "-" * 20)

    fatal_acl = any("FATAL" in e for e in erreurs)
    if fatal_acl:
        print("  [ECHEC] Document confidentiel accessible a grp-tous !")
    else:
        print("  [OK] Aucun document confidentiel accessible a grp-tous")
        if nb_conf == 2:
            print("  [OK] Les 2 documents confidentiels sont bien restreints a grp-rh")

    if avertissements:
        print()
        for av in avertissements:
            print(f"  [AVERTISSEMENT] {av}")

    if erreurs:
        print()
        for err in erreurs:
            print(f"  [ERREUR] {err}")

    print()
    print("  " + "=" * 77)
    if erreurs:
        print(f"  [ECHEC] CORPUS INVALIDE - {len(erreurs)} erreur(s)")
    else:
        print("  [OK] CORPUS VALIDE")
    print("  " + "=" * 77)


def main() -> int:
    erreurs: list[str] = []
    avertissements: list[str] = []

    try:
        manifest = charger_manifest()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERREUR] {exc}")
        return 1

    for cle in ("version", "documents", "trous_connus"):
        if cle not in manifest:
            erreurs.append(f"Cle manquante dans manifest : '{cle}'")

    documents = manifest.get("documents", [])
    stats_list: list[dict] = []

    for doc in documents:
        stats = valider_document(doc, erreurs, avertissements)
        stats_list.append(stats)

    controle_securite(documents, erreurs)

    for orphelin in fichiers_orphelins(documents):
        avertissements.append(f"fichier orphelin : {orphelin}")

    afficher_rapport(stats_list, manifest, erreurs, avertissements)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
