"""CCTswiss.ch — Router /api/cct"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncpg

router = APIRouter()

def get_pool(request: Request):
    return request.app.state.pool

@router.get("/")
async def list_ccts(
    branch:  Optional[str] = Query(None),
    canton:  Optional[str] = Query(None),
    is_dfo:  Optional[bool] = Query(None),
    lang:    str            = Query("fr"),
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
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT rs_number, name, branch, emoji, is_dfo,
                   scope_cantons, scope_description_fr,
                   min_wage_chf, vacation_weeks, weekly_hours,
                   has_13th_salary, source_url, fedlex_uri,
                   last_consolidation_date, dfo_until, updated_at
            FROM cct {where}
            ORDER BY is_dfo DESC, name ASC
        """, *params)
    return {"total": len(rows), "lang": lang, "data": [dict(r) for r in rows]}

@router.get("/branches")
async def list_branches(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT branch, emoji, COUNT(*) as count FROM cct GROUP BY branch, emoji ORDER BY count DESC")
    return [dict(r) for r in rows]

@router.get("/status")
async def update_status(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        last = await conn.fetchrow("SELECT MAX(auto_updated_at) as last_check, MAX(updated_at) as last_change, COUNT(*) as total_ccts FROM cct")
        changes = await conn.fetch("SELECT rs_number, changed_at, change_type FROM cct_changelog ORDER BY changed_at DESC LIMIT 10")
    return {
        "last_auto_check": str(last["last_check"]) if last["last_check"] else None,
        "last_real_change": str(last["last_change"]) if last["last_change"] else None,
        "total_ccts": last["total_ccts"],
        "recent_changes": [dict(c) for c in changes],
        "next_check": "Chaque nuit à 02:00 CET (automatique)",
    }

@router.get("/{rs_number}")
async def get_cct(rs_number: str, lang: str = Query("fr"), pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cct WHERE rs_number = $1", rs_number)
        if not row:
            raise HTTPException(404, f"CCT {rs_number} introuvable")
        await conn.execute("""
            INSERT INTO cct_views (rs_number, lang, viewed_at, count) VALUES ($1,$2,CURRENT_DATE,1)
            ON CONFLICT (rs_number, lang, viewed_at) DO UPDATE SET count = cct_views.count + 1
        """, rs_number, lang)
        history = await conn.fetch("SELECT changed_at, change_type, source FROM cct_changelog WHERE rs_number=$1 ORDER BY changed_at DESC LIMIT 10", rs_number)
    return {**dict(row), "change_history": [dict(h) for h in history]}
