-- ═══════════════════════════════════════════════════════════════════
--  RAG DYNEFF — SCHÉMA COMPLET DE LA BASE
--
--  ⚠️ Ce fichier n'est exécuté QU'UNE SEULE FOIS : à la création du
--     volume Postgres. Pour le rejouer :   docker compose down -v
--
--  ⚠️ Il n'y a PAS d'outil de migration (pas d'Alembic — décision figée).
--     C'est pourquoi TOUTES les tables sont créées ici, y compris celles
--     qui ne seront utilisées que plus tard (fichiers, feedback, audit).
--     Une table vide ne coûte rien. Une migration la veille de la démo, si.
-- ═══════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════════════════════════
--  LES GROUPES — convention (pas de table, c'est du text[])
--
--    grp-tous    : tout le monde
--    grp-rh      : le service RH → accède aux documents confidentiels RH
--    grp-admin   : administration technique
-- ═══════════════════════════════════════════════════════════════════


-- ───────────────────────────────────────────────────────────────────
--  1. DOCUMENTS — un fichier du corpus (CDC 2)
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE documents (
    id              SERIAL PRIMARY KEY,
    chemin          TEXT        NOT NULL UNIQUE,
    titre           TEXT        NOT NULL,
    type            TEXT        NOT NULL CHECK (type IN ('md', 'pdf')),
    source          TEXT        NOT NULL CHECK (source IN ('public', 'synthetique', 'fictif')),
    sensibilite     TEXT        NOT NULL CHECK (sensibilite IN ('public', 'interne', 'confidentiel')),
    allowed_groups  TEXT[]      NOT NULL,
    nb_chunks       INTEGER     NOT NULL DEFAULT 0,
    indexe_le       TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE  documents        IS 'Un fichier du corpus RH.';
COMMENT ON COLUMN documents.source IS 'public = Légifrance | synthetique = rédigé par nous | fictif = inventé pour la démo ACL. AUCUN document réel de l''entreprise.';


-- ───────────────────────────────────────────────────────────────────
--  2. CHUNKS — le cœur du RAG (CDC 2)
--
--  type = 'child'  → petit morceau, VECTORISÉ, c'est lui qu'on cherche
--  type = 'parent' → section complète, PAS vectorisé, c'est lui qu'on lit
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE chunks (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    type            TEXT    NOT NULL DEFAULT 'child'
                            CHECK (type IN ('child', 'parent')),
    parent_id       INTEGER REFERENCES chunks(id) ON DELETE CASCADE,
    ordre           INTEGER NOT NULL,

    breadcrumb      TEXT    NOT NULL,
    contenu         TEXT    NOT NULL,
    contenu_indexe  TEXT    NOT NULL,
    page            INTEGER,
    nb_tokens       INTEGER NOT NULL,

    embedding       vector(1536),
    embedding_model TEXT,
    embedding_dim   INTEGER,

    allowed_groups  TEXT[]  NOT NULL,

    tsv             tsvector GENERATED ALWAYS AS
                        (to_tsvector('french', contenu_indexe)) STORED
);

COMMENT ON COLUMN chunks.breadcrumb      IS 'Fil d''Ariane : Document + Section.';
COMMENT ON COLUMN chunks.contenu_indexe  IS 'Texte vectorisé et indexé en full-text (breadcrumb + contenu).';
COMMENT ON COLUMN chunks.parent_id       IS 'Small-to-big : on CHERCHE l''enfant, on DONNE le parent au LLM.';
COMMENT ON COLUMN chunks.allowed_groups  IS 'ACL recopiée du manifest à l''indexation. Filtrée en SQL AVANT la recherche.';


-- ───────────────────────────────────────────────────────────────────
--  3. USERS
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id           SERIAL      PRIMARY KEY,
    email        TEXT        NOT NULL UNIQUE,
    nom          TEXT        NOT NULL,
    mot_de_passe TEXT        NOT NULL,   -- hash bcrypt. JAMAIS de clair.
    groupes      TEXT[]      NOT NULL DEFAULT '{grp-tous}',
    role         TEXT        NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    cree_le      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  4. CONVERSATIONS (CDC 7)
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE conversations (
    id      SERIAL      PRIMARY KEY,
    user_id INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    titre   TEXT        NOT NULL DEFAULT 'Nouvelle conversation',
    resume  TEXT,                      -- mémoire glissante (CDC 7)
    cree_le TIMESTAMPTZ NOT NULL DEFAULT now(),
    maj_le  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  5. MESSAGES
--     C'est CETTE table qui alimentera le dashboard du CDC 12.
--     Tout ce qui s'y trouve sera un SELECT COUNT(*).
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE messages (
    id                SERIAL        PRIMARY KEY,
    conversation_id   INTEGER       NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,

    role              TEXT          NOT NULL CHECK (role IN ('user', 'assistant')),
    contenu           TEXT          NOT NULL,
    question_reecrite TEXT,                            -- query rewriting (CDC 7)

    chunk_ids         INTEGER[]     NOT NULL DEFAULT '{}',
    sources           JSONB,                           -- citations structurées
    a_repondu         BOOLEAN,                         -- FALSE = "je ne sais pas"
    web_active        BOOLEAN       NOT NULL DEFAULT FALSE,

    modele            TEXT,
    tokens_in         INTEGER,
    tokens_out        INTEGER,
    latence_ms        INTEGER,
    cout_eur          NUMERIC(12, 6),

    cree_le           TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMENT ON COLUMN messages.a_repondu IS 'FALSE = le RAG a répondu "je ne sais pas". C''est ce champ qui produit les "trous du corpus" du dashboard (CDC 12).';


-- ───────────────────────────────────────────────────────────────────
--  6. FEEDBACK (CDC 7) — 👍 / 👎
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE feedback (
    id          SERIAL      PRIMARY KEY,
    message_id  INTEGER     NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    valeur      SMALLINT    NOT NULL CHECK (valeur IN (-1, 1)),   -- -1 = 👎, 1 = 👍
    commentaire TEXT,
    cree_le     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  7. FICHIERS (CDC 9) — les .docx générés
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE fichiers (
    id         SERIAL      PRIMARY KEY,
    message_id INTEGER     REFERENCES messages(id) ON DELETE CASCADE,
    nom        TEXT        NOT NULL,
    chemin     TEXT        NOT NULL,
    type_mime  TEXT        NOT NULL DEFAULT
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    taille     INTEGER,
    cree_le    TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ───────────────────────────────────────────────────────────────────
--  8. AUDIT_LOG (CDC 6) — la table qu'on montre au RSSI
--
--     user_email et user_groups sont DÉNORMALISÉS À DESSEIN :
--     un journal d'audit doit rester vrai même si l'utilisateur change
--     de groupe ou est supprimé. On fige l'état AU MOMENT de la requête.
-- ───────────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
    id          BIGSERIAL   PRIMARY KEY,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    user_email  TEXT,
    user_groups TEXT[],
    question    TEXT        NOT NULL,
    chunk_ids   INTEGER[]   NOT NULL DEFAULT '{}',
    nb_chunks   INTEGER     NOT NULL DEFAULT 0,
    a_repondu   BOOLEAN,
    latence_ms  INTEGER,
    cout_eur    NUMERIC(12, 6),
    ip          INET,
    horodatage  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════
--  LES INDEX
-- ═══════════════════════════════════════════════════════════════════

-- Recherche VECTORIELLE (CDC 3)
CREATE INDEX idx_chunks_embedding
    ON chunks USING hnsw (embedding vector_cosine_ops);

-- Recherche PLEIN TEXTE française (CDC 3)
CREATE INDEX idx_chunks_tsv
    ON chunks USING gin (tsv);

-- Filtrage ACL — appliqué AVANT tout le reste (CDC 3)
CREATE INDEX idx_chunks_acl
    ON chunks USING gin (allowed_groups);

CREATE INDEX idx_chunks_type      ON chunks (type);
CREATE INDEX idx_chunks_parent    ON chunks (parent_id);
CREATE INDEX idx_chunks_document  ON chunks (document_id);
CREATE INDEX idx_conversations_user_id    ON conversations (user_id);
CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX idx_messages_cree_le         ON messages (cree_le DESC);
CREATE INDEX idx_messages_a_repondu       ON messages (a_repondu);
CREATE INDEX idx_feedback_message_id      ON feedback (message_id);
CREATE INDEX idx_fichiers_message_id      ON fichiers (message_id);
CREATE INDEX idx_audit_horodatage         ON audit_log (horodatage DESC);
CREATE INDEX idx_audit_user_id            ON audit_log (user_id);


-- ═══════════════════════════════════════════════════════════════════
--  SEED — 3 utilisateurs de démonstration
--
--  Mot de passe pour les trois : demo1234
--  Hash bcrypt (cost 12) déjà calculés — NE PAS les régénérer.
-- ═══════════════════════════════════════════════════════════════════
INSERT INTO users (email, nom, mot_de_passe, groupes, role) VALUES
    ('marie@dyneff.fr', 'Marie Lefèvre',
     '$2b$12$XdOu722hLDAz0pKh9CAavuwVASM5ZfNJbbufoXwZq01cjWod7CqTW',
     ARRAY['grp-tous', 'grp-rh'], 'user'),

    ('paul@dyneff.fr', 'Paul Marchand',
     '$2b$12$dHvJAyaZUMJauviv.G0wTur27Slsf0xdaxBJw7iAmLumXu2cnphZi',
     ARRAY['grp-tous'], 'user'),

    ('admin@dyneff.fr', 'Administrateur',
     '$2b$12$2/A8UFzonF91IPaRkiEbvuVkZ8cKIrR4CUDIgdEfPmE8zpdTajB4y',
     ARRAY['grp-tous', 'grp-rh', 'grp-admin'], 'admin');

-- Marie  = RH         → verra la grille des salaires
-- Paul   = commercial → ne la verra JAMAIS
-- C'est le moment n°2 de la démo.
