from fastapi import APIRouter, Depends, Query, Request
import asyncpg

router = APIRouter()

def get_pool(r: Request): return r.app.state.pool

@router.get("/")
async def search(
    q:    str          = Query(..., min_length=2),
    lang: str          = Query("fr"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Recherche full-text + ILIKE dans les CCT"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji, is_dfo,
                   min_wage_chf, vacation_weeks, source_url,
                   scope_description_fr, updated_at
            FROM cct
            WHERE
                name ILIKE $1
                OR branch ILIKE $1
                OR scope_description_fr ILIKE $1
                OR content_fr ILIKE $1
                OR name_de ILIKE $1
                OR name_it ILIKE $1
                OR name_en ILIKE $1
                OR name_tr ILIKE $1
                OR name_uk ILIKE $1
            ORDER BY is_dfo DESC, name ASC
            LIMIT 20
        """, f"%{q}%")
    return {"query": q, "total": len(rows), "data": [dict(r) for r in rows]}
