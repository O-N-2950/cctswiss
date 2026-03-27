"""CCTswiss.ch — Schéma PostgreSQL complet avec 11 langues"""

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS cct (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rs_number               VARCHAR(50) UNIQUE NOT NULL,
    -- Langues nationales
    name                    TEXT NOT NULL,
    name_de                 TEXT,
    name_it                 TEXT,
    -- Langues internationales
    name_en                 TEXT,
    name_pt                 TEXT,
    name_es                 TEXT,
    -- Communautés étrangères importantes en Suisse
    name_sq                 TEXT,   -- Albanais
    name_bs                 TEXT,   -- BCMS (Bosniaque/Croate/Monténégrin/Serbe)
    name_tr                 TEXT,   -- Turc
    name_uk                 TEXT,   -- Ukrainien
    name_rm                 TEXT,   -- Romanche (4e langue nationale)
    branch                  VARCHAR(100),
    emoji                   VARCHAR(10),
    is_dfo                  BOOLEAN DEFAULT FALSE,
    dfo_since               DATE,
    dfo_until               DATE,
    scope_cantons           TEXT[],
    scope_description_fr    TEXT,
    min_wage_chf            NUMERIC(10,2),
    min_wage_details        JSONB,
    vacation_weeks          NUMERIC(4,1),
    weekly_hours            NUMERIC(4,1),
    has_13th_salary         BOOLEAN DEFAULT FALSE,
    source_url              TEXT,
    fedlex_uri              TEXT,
    last_consolidation_date DATE,
    content_fr              TEXT,
    content_hash            VARCHAR(64),
    legal_disclaimer_fr     TEXT DEFAULT 'Ce résumé est fourni à titre informatif uniquement. Il ne constitue pas un avis juridique. Consultez le texte officiel ou un professionnel du droit du travail.',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    auto_updated_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cct_changelog (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rs_number   VARCHAR(50) REFERENCES cct(rs_number),
    changed_at  TIMESTAMPTZ DEFAULT NOW(),
    change_type VARCHAR(50),
    source      TEXT,
    details     JSONB,
    verified_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS cct_wages_cache (
    source      VARCHAR(50) PRIMARY KEY,
    data        JSONB,
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cct_views (
    rs_number   VARCHAR(50),
    lang        VARCHAR(5),
    viewed_at   DATE DEFAULT CURRENT_DATE,
    count       INTEGER DEFAULT 1,
    PRIMARY KEY (rs_number, lang, viewed_at)
);

CREATE INDEX IF NOT EXISTS idx_cct_branch     ON cct(branch);
CREATE INDEX IF NOT EXISTS idx_cct_is_dfo     ON cct(is_dfo);
CREATE INDEX IF NOT EXISTS idx_cct_updated    ON cct(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_changelog_rs   ON cct_changelog(rs_number, changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_cct_fts ON cct
    USING gin(to_tsvector('french',
        coalesce(name,'') || ' ' ||
        coalesce(name_de,'') || ' ' ||
        coalesce(branch,'') || ' ' ||
        coalesce(scope_description_fr,'')
    ));

CREATE OR REPLACE VIEW cct_public AS
SELECT id, rs_number, name, name_de, name_it, name_en, name_pt, name_es,
       name_sq, name_bs, name_tr, name_uk, name_rm,
       branch, emoji, is_dfo, dfo_since, dfo_until,
       scope_cantons, scope_description_fr,
       min_wage_chf, min_wage_details, vacation_weeks, weekly_hours,
       has_13th_salary, source_url, fedlex_uri,
       last_consolidation_date, legal_disclaimer_fr, updated_at
FROM cct;
"""

async def init_schema(pool):
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
