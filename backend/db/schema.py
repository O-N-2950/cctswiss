"""CCTswiss.ch — PostgreSQL Schema + Migrations"""
import logging
log = logging.getLogger("cctswiss.db")

TABLES = [
    """CREATE EXTENSION IF NOT EXISTS "uuid-ossp" """,

    # ── Table principale CCT ────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cct (
        id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rs_number               VARCHAR(50) UNIQUE NOT NULL,
        name                    TEXT NOT NULL,
        branch                  VARCHAR(100),
        emoji                   VARCHAR(10),
        is_dfo                  BOOLEAN DEFAULT FALSE,
        dfo_until               DATE,
        scope_description_fr    TEXT,
        scope_cantons           TEXT[],
        min_wage_chf            NUMERIC(10,2),
        vacation_weeks          NUMERIC(4,1),
        weekly_hours            NUMERIC(4,1),
        has_13th_salary         BOOLEAN DEFAULT FALSE,
        source_url              TEXT,
        fedlex_uri              TEXT,
        last_consolidation_date DATE,
        content_fr              TEXT,
        content_hash            VARCHAR(64),
        legal_disclaimer_fr     TEXT,
        created_at              TIMESTAMPTZ DEFAULT NOW(),
        updated_at              TIMESTAMPTZ DEFAULT NOW(),
        auto_updated_at         TIMESTAMPTZ DEFAULT NOW()
    )
    """,

    # ── Table salaires minimums cantonaux ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cantonal_salary_minimums (
        id            SERIAL PRIMARY KEY,
        canton        TEXT NOT NULL,
        min_hourly    DECIMAL(6,2) NOT NULL,
        valid_from    DATE NOT NULL,
        valid_to      DATE,
        legal_basis   TEXT,
        notes         TEXT,
        created_at    TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(canton, valid_from)
    )
    """,

    # ── Changelog ──────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cct_changelog (
        id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rs_number   VARCHAR(50),
        changed_at  TIMESTAMPTZ DEFAULT NOW(),
        change_type VARCHAR(50),
        source      TEXT,
        details     JSONB
    )
    """,
    """CREATE TABLE IF NOT EXISTS cct_wages_cache (source VARCHAR(50) PRIMARY KEY, data JSONB, fetched_at TIMESTAMPTZ DEFAULT NOW())""",
    """CREATE TABLE IF NOT EXISTS cct_views (rs_number VARCHAR(50), lang VARCHAR(5), viewed_at DATE DEFAULT CURRENT_DATE, count INTEGER DEFAULT 1, PRIMARY KEY (rs_number, lang, viewed_at))""",

    # Indexes
    "CREATE INDEX IF NOT EXISTS idx_cct_branch   ON cct(branch)",
    "CREATE INDEX IF NOT EXISTS idx_cct_is_dfo   ON cct(is_dfo)",
    "CREATE INDEX IF NOT EXISTS idx_cct_updated  ON cct(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_csm_canton   ON cantonal_salary_minimums(canton)",
    "CREATE INDEX IF NOT EXISTS idx_csm_current  ON cantonal_salary_minimums(canton, valid_from DESC)",
]

# ── Migrations additives (ALTER TABLE ... ADD COLUMN IF NOT EXISTS) ────
MIGRATIONS = [
    # Multilingual names
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_de  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_it  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_en  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_pt  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_es  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_sq  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_bs  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_tr  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_uk  TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_rm  TEXT",

    # NOGA & DFO
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS noga_codes            TEXT[]",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS dfo                   BOOLEAN DEFAULT FALSE",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS dfo_cantons           TEXT[]",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS dfo_since             DATE",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS voluntary_only        BOOLEAN DEFAULT FALSE",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS membership_required   TEXT",

    # IJM (indemnité journalière maladie)
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS ijm_min_rate              INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS ijm_max_carence_days      INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS ijm_min_coverage_days     INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS ijm_employer_topup        BOOLEAN DEFAULT FALSE",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS ijm_topup_to              INTEGER",

    # LAA (accident)
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS laa_min_rate                  INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS laa_max_carence_days          INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS laa_complementaire_required   BOOLEAN DEFAULT FALSE",

    # CO 324a (sans CCT)
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS co324a_year1_days INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS co324a_year2_days INTEGER",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS co324a_year5_days INTEGER",

    # Salaires minimums enrichis
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS salary_min_hourly      DECIMAL(6,2)",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS salary_min_monthly     DECIMAL(8,2)",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS salary_min_by_category JSONB",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS salary_min_updated     DATE",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS data_complete          BOOLEAN DEFAULT FALSE",

    # Paritaire contributions (cotisations paritaires)
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS paritaire_contribution JSONB",
    "CREATE INDEX IF NOT EXISTS idx_cct_paritaire ON cct USING gin(paritaire_contribution) WHERE paritaire_contribution IS NOT NULL",

    # Full-text search index
    "CREATE INDEX IF NOT EXISTS idx_cct_fts ON cct USING gin(to_tsvector('french', coalesce(name,'') || ' ' || coalesce(scope_description_fr,'') || ' ' || coalesce(content_fr,'')))",
]

# ── Seed données cantonales salaires minimums ──────────────────────────
CANTONAL_WAGES_SEED = [
    # (canton, min_hourly, valid_from, legal_basis, notes)
    ("GE", 24.32, "2026-01-01", "Loi sur le salaire minimum GE (LSMI)", "Indexé annuellement sur l'IPC"),
    ("NE", 21.09, "2026-01-01", "Loi sur l'emploi NE", "Valeur 2026"),
    ("JU",  21.00, "2026-01-01", "Loi sur l'emploi et la protection des travailleurs JU (LEPT)", None),
    ("VD",  21.23, "2026-01-01", "Loi sur l'emploi VD", "Valeur 2026"),
    ("TI",  19.00, "2026-01-01", "Legge sul lavoro TI", "Valeur 2025, révision 2026 en cours"),
    ("VS",  19.30, "2026-01-01", "Loi sur le marché du travail VS", "Valeur 2026"),
    ("FR",  19.85, "2026-01-01", "Loi sur l'emploi FR", "Valeur 2026"),
    ("BS",  21.00, "2025-01-01", "Mindestlohngesetz BS", "Valeur 2025"),
    ("SO",  20.00, "2024-01-01", "Initiative salaire minimum SO", "Valeur 2024, révision prévue"),
]

async def init_schema(pool):
    async with pool.acquire() as conn:
        for stmt in TABLES:
            try:
                await conn.execute(stmt)
            except Exception as e:
                log.warning(f"Table: {e}")
        for stmt in MIGRATIONS:
            try:
                await conn.execute(stmt)
            except Exception as e:
                log.debug(f"Migration: {e}")

        # Seed cantonal minimums if empty
        count = await conn.fetchval("SELECT COUNT(*) FROM cantonal_salary_minimums")
        if count == 0:
            for canton, rate, vf, basis, notes in CANTONAL_WAGES_SEED:
                try:
                    from datetime import date
                    parts = vf.split("-")
                    vf_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    await conn.execute("""
                        INSERT INTO cantonal_salary_minimums (canton,min_hourly,valid_from,legal_basis,notes)
                        VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING
                    """, canton, rate, vf_date, basis, notes)
                except Exception as e:
                    log.warning(f"Cantonal seed {canton}: {e}")
            log.info("✅ Cantonal salary minimums seeded")

    log.info("✅ Schema initialized + migrations applied")
