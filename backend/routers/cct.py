"""
CCTswiss.ch — Router /api/cct
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Optional
import asyncpg

router = APIRouter()

def get_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


@router.get("/")
async def list_ccts(
    branch:  Optional[str] = Query(None, description="ex: restauration, construction"),
    canton:  Optional[str] = Query(None, description="ex: JU, GE, VD"),
    is_dfo:  Optional[bool] = Query(None, description="Filtre DFO uniquement"),
    lang:    str            = Query("fr", description="Langue: fr, de, it, en, pt, es"),
    pool:    asyncpg.Pool   = Depends(get_pool),
):
    """Liste toutes les CCT avec filtres optionnels."""
    conditions = []
    params = []

    if branch:
        params.append(branch.lower())
        conditions.append(f"branch = ${len(params)}")

    if canton:
        params.append(canton.upper())
        conditions.append(f"(scope_cantons IS NULL OR ${ len(params)} = ANY(scope_cantons))")

    if is_dfo is not None:
        params.append(is_dfo)
        conditions.append(f"is_dfo = ${len(params)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT
                rs_number, name, name_de, name_it, name_en, name_pt, name_es,
                branch, emoji, is_dfo, scope_cantons,
                min_wage_chf, vacation_weeks, weekly_hours, has_13th_salary,
                source_url, fedlex_uri, last_consolidation_date,
                legal_disclaimer_fr, updated_at
            FROM cct_public
            {where}
            ORDER BY is_dfo DESC, name ASC
        """, *params)

    return {
        "total": len(rows),
        "lang":  lang,
        "data":  [_serialize_cct(r, lang) for r in rows]
    }


@router.get("/branches")
async def list_branches(pool: asyncpg.Pool = Depends(get_pool)):
    """Liste toutes les branches disponibles."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT branch, emoji, COUNT(*) as count
            FROM cct GROUP BY branch, emoji ORDER BY count DESC
        """)
    return [dict(r) for r in rows]


@router.get("/status")
async def update_status(pool: asyncpg.Pool = Depends(get_pool)):
    """Statut de la dernière mise à jour automatique."""
    async with pool.acquire() as conn:
        last = await conn.fetchrow("""
            SELECT MAX(auto_updated_at) as last_check,
                   MAX(updated_at)      as last_change,
                   COUNT(*)             as total_ccts
            FROM cct
        """)
        changes = await conn.fetch("""
            SELECT rs_number, changed_at, change_type, details
            FROM cct_changelog
            ORDER BY changed_at DESC LIMIT 10
        """)
    return {
        "last_auto_check":  last["last_check"],
        "last_real_change": last["last_change"],
        "total_ccts":       last["total_ccts"],
        "recent_changes":   [dict(c) for c in changes],
        "next_check":       "Chaque nuit à 02:00 CET (automatique)",
    }


@router.get("/{rs_number}")
async def get_cct(
    rs_number: str,
    lang:      str          = Query("fr"),
    pool:      asyncpg.Pool = Depends(get_pool),
):
    """Détail complet d'une CCT par numéro RS."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cct WHERE rs_number = $1", rs_number
        )
        if not row:
            raise HTTPException(404, f"CCT RS {rs_number} introuvable")

        # Enregistrer la vue
        await conn.execute("""
            INSERT INTO cct_views (rs_number, lang, viewed_at, count)
            VALUES ($1, $2, CURRENT_DATE, 1)
            ON CONFLICT (rs_number, lang, viewed_at)
            DO UPDATE SET count = cct_views.count + 1
        """, rs_number, lang)

        # Historique des changements
        history = await conn.fetch("""
            SELECT changed_at, change_type, source, details
            FROM cct_changelog WHERE rs_number = $1
            ORDER BY changed_at DESC LIMIT 20
        """, rs_number)

    return {
        **_serialize_cct(row, lang),
        "legal_disclaimer": row["legal_disclaimer_fr"],
        "change_history":   [dict(h) for h in history],
    }


def _serialize_cct(row, lang: str) -> dict:
    """Sérialise une CCT selon la langue demandée."""
    name_map = {
        "fr": row["name"],
        "de": row.get("name_de") or row["name"],
        "it": row.get("name_it") or row["name"],
        "en": row.get("name_en") or row["name"],
        "pt": row.get("name_pt") or row["name"],
        "es": row.get("name_es") or row["name"],
    }
    return {
        "rs_number":               row["rs_number"],
        "name":                    name_map.get(lang, row["name"]),
        "branch":                  row["branch"],
        "emoji":                   row["emoji"],
        "is_dfo":                  row["is_dfo"],
        "scope_cantons":           row.get("scope_cantons"),
        "min_wage_chf":            float(row["min_wage_chf"]) if row.get("min_wage_chf") else None,
        "vacation_weeks":          float(row["vacation_weeks"]) if row.get("vacation_weeks") else None,
        "weekly_hours":            float(row["weekly_hours"]) if row.get("weekly_hours") else None,
        "has_13th_salary":         row.get("has_13th_salary"),
        "source_url":              row["source_url"],
        "fedlex_uri":              row.get("fedlex_uri"),
        "last_consolidation_date": str(row["last_consolidation_date"]) if row.get("last_consolidation_date") else None,
        "updated_at":              str(row["updated_at"]) if row.get("updated_at") else None,
    }
