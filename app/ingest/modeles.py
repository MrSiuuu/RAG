"""Structures de données du pipeline d'ingestion."""

from dataclasses import dataclass, field


@dataclass
class Section:
    """Une section de markdown, délimitée par un titre."""

    niveau: int
    titre: str
    contenu: str
    chemin: list[str]
    page: int | None = None


@dataclass
class ChunkPret:
    """Un chunk prêt à être inséré — relié au parent par clé logique."""

    cle: str
    cle_parent: str | None
    type: str
    ordre: int
    breadcrumb: str
    contenu: str
    contenu_indexe: str
    nb_tokens: int
    page: int | None
    embedding: list[float] | None = None


@dataclass
class StatsDocument:
    """Statistiques de découpage pour un document."""

    titre: str
    chemin: str
    allowed_groups: list[str]
    nb_enfants: int = 0
    nb_parents: int = 0
    tok_moy: int = 0
    tok_max: int = 0
    blocs_insecables: int = 0
    enfants: list[ChunkPret] = field(default_factory=list)
    parents: list[ChunkPret] = field(default_factory=list)
