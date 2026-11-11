-- Schema Lexia (PostgreSQL >= 15 + extension pgvector).
-- Idempotent : peut etre rejoue sans perte.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
    id               text PRIMARY KEY,
    nom              text NOT NULL,
    type             text NOT NULL,
    autorite         text,
    url              text,
    statut           text NOT NULL,
    derniere_synchro timestamptz
);

CREATE TABLE IF NOT EXISTS passages (
    id                text PRIMARY KEY,
    source_id         text NOT NULL REFERENCES sources(id),
    type              text NOT NULL,              -- article, preambule, motifs, dispositif, sommaire
    numero            text,                       -- numero d'article ou plage de paragraphes
    titre             text,
    entete            text NOT NULL DEFAULT '',
    texte             text NOT NULL,
    url               text NOT NULL,
    version           text NOT NULL DEFAULT '',
    date_recuperation timestamptz,
    empreinte         char(64) NOT NULL,
    meta              jsonb NOT NULL DEFAULT '{}'::jsonb,
    -- Vigueur (textes) : NULL pour la jurisprudence
    en_vigueur        boolean,
    date_debut        date,
    date_fin          date,
    -- Date de la decision (jurisprudence)
    date_decision     date,
    -- Recherche lexicale francaise
    tsv               tsvector GENERATED ALWAYS AS (
                          setweight(to_tsvector('french', coalesce(entete, '')), 'A') ||
                          setweight(to_tsvector('french', texte), 'B')
                      ) STORED,
    -- Recherche semantique
    embedding         vector(768),
    embedding_model   text,
    maj_le            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS passages_source_idx   ON passages (source_id);
CREATE INDEX IF NOT EXISTS passages_vigueur_idx  ON passages (source_id, en_vigueur);
CREATE INDEX IF NOT EXISTS passages_date_idx     ON passages (date_decision);
CREATE INDEX IF NOT EXISTS passages_tsv_idx      ON passages USING gin (tsv);
CREATE INDEX IF NOT EXISTS passages_meta_idx     ON passages USING gin (meta jsonb_path_ops);
CREATE INDEX IF NOT EXISTS passages_embedding_idx
    ON passages USING hnsw (embedding vector_cosine_ops);

-- Historique des synchronisations (une ligne par execution de chargement)
CREATE TABLE IF NOT EXISTS synchros (
    id          bigserial PRIMARY KEY,
    source_id   text NOT NULL REFERENCES sources(id),
    debut       timestamptz NOT NULL DEFAULT now(),
    fin         timestamptz,
    inseres     integer,
    modifies    integer,
    inchanges   integer,
    supprimes   integer,
    statut      text NOT NULL DEFAULT 'en_cours'
);
