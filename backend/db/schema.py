"""
CCTswiss.ch — Schéma PostgreSQL
================================
Tables principales + système de changelog automatique.
"""

SCHEMA_SQL = """
-- Extension pour les timestamps
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Table principale des CCT ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cct (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rs_number               VARCHAR(50) UNIQUE NOT NULL,   -- ex: "221.215.329.4"
    name                    TEXT NOT NULL,                  -- Nom officiel FR
    name_de                 TEXT,                           -- Nom officiel DE
    name_it                 TEXT,                           -- Nom officiel IT
    name_en                 TEXT,                           -- Traduction EN
    name_pt                 TEXT,                           -- Traduction PT
    name_es                 TEXT,                           -- Traduction ES
    branch                  VARCHAR(100),                   -- ex: "restauration"
    emoji                   VARCHAR(10),                    -- ex: "🍽️"
    is_dfo                  BOOLEAN DEFAULT FALSE,          -- Déclarée de force obligatoire
    dfo_since               DATE,                           -- Date DFO
    dfo_until               DATE,                           -- Fin DFO (NULL = en cours)
    scope_cantons           TEXT[],                         -- Cantons concernés (NULL = toute CH)
    scope_description_fr    TEXT,                           -- Description champ d'application FR
    min_wage_chf            NUMERIC(10,2),                  -- Salaire min mensuel CHF
    min_wage_details        JSONB,                          -- Détail par catégorie
    vacation_weeks          NUMERIC(4,1),                   -- Semaines de vacances
    weekly_hours            NUMERIC(4,1),                   -- Heures hebdomadaires
    has_13th_salary         BOOLEAN DEFAULT FALSE,
    source_url              TEXT,                           -- URL source officielle
    fedlex_uri              TEXT,                           -- URI Fedlex
    last_consolidation_date DATE,                           -- Dernière consolidation Fedlex
    content_fr              TEXT,                           -- Contenu texte FR (50KB max)
    content_hash            VARCHAR(64),                    -- SHA-256 pour détecter changements
    legal_disclaimer_fr     TEXT DEFAULT 'Ce résumé est fourni à titre informatif uniquement. Il ne constitue pas un avis juridique. Consultez le texte officiel sur Fedlex ou un professionnel du droit.',
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),      -- Dernière vraie mise à jour
    auto_updated_at         TIMESTAMPTZ DEFAULT NOW()       -- Dernière vérification auto
);

-- ── Changelog automatique ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cct_changelog (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rs_number   VARCHAR(50) REFERENCES cct(rs_number),
    changed_at  TIMESTAMPTZ DEFAULT NOW(),
    change_type VARCHAR(50),   -- 'auto_update', 'manual', 'initial'
    source      TEXT,          -- URL source du changement
    details     JSONB,         -- Détails du diff
    verified_by VARCHAR(100)   -- NULL = auto, sinon nom de l'admin
);

-- ── Cache salaires L-GAV ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cct_wages_cache (
    source      VARCHAR(50) PRIMARY KEY,  -- 'lgav', 'gastrosuisse', etc.
    data        JSONB,
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Traductions (multilingue) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cct_translations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rs_number   VARCHAR(50) REFERENCES cct(rs_number),
    lang        VARCHAR(5) NOT NULL,    -- 'de','it','en','pt','es','rm'
    field       VARCHAR(100) NOT NULL,  -- 'name','scope_description','summary'
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(rs_number, lang, field)
);

-- ── Stats de consultation ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cct_views (
    rs_number   VARCHAR(50),
    lang        VARCHAR(5),
    viewed_at   DATE DEFAULT CURRENT_DATE,
    count       INTEGER DEFAULT 1,
    PRIMARY KEY (rs_number, lang, viewed_at)
);

-- ── Index ─────────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_cct_branch       ON cct(branch);
CREATE INDEX IF NOT EXISTS idx_cct_is_dfo       ON cct(is_dfo);
CREATE INDEX IF NOT EXISTS idx_cct_updated_at   ON cct(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_changelog_rs     ON cct_changelog(rs_number, changed_at DESC);

-- Full-text search sur le nom et le contenu
CREATE INDEX IF NOT EXISTS idx_cct_fts ON cct
    USING gin(to_tsvector('french', coalesce(name,'') || ' ' || coalesce(content_fr,'')));

-- ── Vue publique (sans le contenu brut) ───────────────────────────────────────
CREATE OR REPLACE VIEW cct_public AS
SELECT
    id, rs_number, name, name_de, name_it, name_en, name_pt, name_es,
    branch, emoji, is_dfo, dfo_since, dfo_until,
    scope_cantons, scope_description_fr,
    min_wage_chf, min_wage_details, vacation_weeks, weekly_hours,
    has_13th_salary, source_url, fedlex_uri,
    last_consolidation_date, legal_disclaimer_fr,
    updated_at
FROM cct;

-- ── Fonction trigger: updated_at automatique ──────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS cct_updated_at ON cct;
CREATE TRIGGER cct_updated_at
    BEFORE UPDATE ON cct
    FOR EACH ROW
    WHEN (OLD.content_hash IS DISTINCT FROM NEW.content_hash)
    EXECUTE FUNCTION update_updated_at();
"""

async def init_schema(pool):
    """Initialise le schéma DB au démarrage."""
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
