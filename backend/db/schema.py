"""CCTswiss.ch — PostgreSQL Schema"""
import logging
log = logging.getLogger("cctswiss.db")

TABLES = [
    """CREATE EXTENSION IF NOT EXISTS "uuid-ossp" """,
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
        created_at              TIMESTAMPTZ DEFAULT NOW(),
        updated_at              TIMESTAMPTZ DEFAULT NOW(),
        auto_updated_at         TIMESTAMPTZ DEFAULT NOW()
    )
    """,
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
    """
    CREATE TABLE IF NOT EXISTS cct_wages_cache (
        source      VARCHAR(50) PRIMARY KEY,
        data        JSONB,
        fetched_at  TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cct_views (
        rs_number   VARCHAR(50),
        lang        VARCHAR(5),
        viewed_at   DATE DEFAULT CURRENT_DATE,
        count       INTEGER DEFAULT 1,
        PRIMARY KEY (rs_number, lang, viewed_at)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cct_branch ON cct(branch)",
    "CREATE INDEX IF NOT EXISTS idx_cct_is_dfo ON cct(is_dfo)",
    "CREATE INDEX IF NOT EXISTS idx_cct_updated ON cct(updated_at DESC)",
]

# Migration: add multilingual columns if they don't exist
MIGRATIONS = [
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_de TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_it TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_en TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_pt TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_es TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_sq TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_bs TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_tr TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_uk TEXT",
    "ALTER TABLE cct ADD COLUMN IF NOT EXISTS name_rm TEXT",
]

async def init_schema(pool):
    async with pool.acquire() as conn:
        for stmt in TABLES:
            try:
                await conn.execute(stmt)
            except Exception as e:
                log.warning(f"Schema stmt: {e}")
        # Run migrations
        for stmt in MIGRATIONS:
            try:
                await conn.execute(stmt)
            except Exception as e:
                log.debug(f"Migration (may already exist): {e}")
    log.info("✅ Schema initialized")
