"""CCTswiss.ch — Router /api/cct — 11 langues"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncpg

router = APIRouter()

LANG_FIELDS = {
    "fr": "name", "de": "name_de", "it": "name_it",
    "en": "name_en", "pt": "name_pt", "es": "name_es",
    "sq": "name_sq", "bs": "name_bs", "hr": "name_bs",
    "sr": "name_bs", "cnr": "name_bs",
    "tr": "name_tr", "uk": "name_uk", "rm": "name_rm",
}

def get_pool(request: Request): return request.app.state.pool

def get_name(row, lang: str) -> str:
    field = LANG_FIELDS.get(lang, "name")
    return row.get(field) or row.get("name") or ""

@router.get("/")
async def list_ccts(
    branch:  Optional[str] = Query(None),
    canton:  Optional[str] = Query(None),
    is_dfo:  Optional[bool] = Query(None),
    lang:    str            = Query("fr"),
    q:       Optional[str]  = Query(None),
    pool:    asyncpg.Pool   = Depends(get_pool),
):
    conditions, params = [], []

    if branch:
        params.append(branch.lower())
        conditions.append(f"branch = ${len(params)}")
    if canton:
        params.append(canton.upper())
        conditions.append(f"(scope_cantons IS NULL OR ${len(params)} = ANY(scope_cantons))")
    if is_dfo is not None:
        params.append(is_dfo)
        conditions.append(f"is_dfo = ${len(params)}")
    if q:
        params.append(f"%{q}%")
        conditions.append(f"(name ILIKE ${len(params)} OR name_de ILIKE ${len(params)} OR branch ILIKE ${len(params)})")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT rs_number, name, name_de, name_it, name_en, name_pt, name_es,
                   name_sq, name_bs, name_tr, name_uk, name_rm,
                   branch, emoji, is_dfo, scope_cantons,
                   min_wage_chf, min_wage_details, vacation_weeks, weekly_hours,
                   has_13th_salary, source_url, fedlex_uri,
                   last_consolidation_date, updated_at
            FROM cct_public {where}
            ORDER BY is_dfo DESC, name ASC
        """, *params)

    return {
        "total": len(rows),
        "lang":  lang,
        "data":  [_ser(dict(r), lang) for r in rows]
    }


@router.get("/status")
async def update_status(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        last = await conn.fetchrow("""
            SELECT MAX(auto_updated_at) as last_check,
                   MAX(updated_at)      as last_change,
                   COUNT(*)             as total_ccts
            FROM cct
        """)
        changes = await conn.fetch("""
            SELECT rs_number, changed_at, change_type, source
            FROM cct_changelog ORDER BY changed_at DESC LIMIT 10
        """)
    return {
        "last_auto_check":   str(last["last_check"]) if last["last_check"] else None,
        "last_real_change":  str(last["last_change"]) if last["last_change"] else None,
        "total_ccts":        last["total_ccts"],
        "recent_changes":    [dict(c) for c in changes],
        "scheduler":         "Chaque nuit 02:00 CET — Fedlex + SECO + L-GAV",
        "sources":           ["fedlex.data.admin.ch","seco.admin.ch","l-gav.ch","gastrosuisse.ch"],
    }


@router.get("/branches")
async def list_branches(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT branch, emoji, COUNT(*) as count FROM cct GROUP BY branch, emoji ORDER BY count DESC")
    return [dict(r) for r in rows]


@router.get("/{rs_number}")
async def get_cct(
    rs_number: str,
    lang:      str          = Query("fr"),
    pool:      asyncpg.Pool = Depends(get_pool),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cct WHERE rs_number=$1", rs_number)
        if not row:
            raise HTTPException(404, f"CCT RS {rs_number} introuvable")

        await conn.execute("""
            INSERT INTO cct_views (rs_number, lang, viewed_at, count)
            VALUES ($1,$2,CURRENT_DATE,1)
            ON CONFLICT (rs_number,lang,viewed_at)
            DO UPDATE SET count = cct_views.count + 1
        """, rs_number, lang)

        history = await conn.fetch("""
            SELECT changed_at, change_type, source
            FROM cct_changelog WHERE rs_number=$1
            ORDER BY changed_at DESC LIMIT 20
        """, rs_number)

    d = dict(row)
    return {
        **_ser(d, lang),
        "scope_description": d.get("scope_description_fr"),
        "min_wage_details":  d.get("min_wage_details"),
        "content_fr":        d.get("content_fr"),
        "legal_disclaimer":  d.get("legal_disclaimer_fr"),
        "source_url":        d.get("source_url"),
        "fedlex_uri":        d.get("fedlex_uri"),
        "change_history":    [dict(h) for h in history],
    }


def _ser(row: dict, lang: str) -> dict:
    name_field = LANG_FIELDS.get(lang, "name")
    name = row.get(name_field) or row.get("name") or ""
    return {
        "rs_number":               row["rs_number"],
        "name":                    name,
        "branch":                  row.get("branch"),
        "emoji":                   row.get("emoji"),
        "is_dfo":                  row.get("is_dfo"),
        "scope_cantons":           row.get("scope_cantons"),
        "min_wage_chf":            float(row["min_wage_chf"]) if row.get("min_wage_chf") else None,
        "vacation_weeks":          float(row["vacation_weeks"]) if row.get("vacation_weeks") else None,
        "weekly_hours":            float(row["weekly_hours"]) if row.get("weekly_hours") else None,
        "has_13th_salary":         row.get("has_13th_salary"),
        "last_consolidation_date": str(row["last_consolidation_date"]) if row.get("last_consolidation_date") else None,
        "updated_at":              str(row["updated_at"]) if row.get("updated_at") else None,
    }
