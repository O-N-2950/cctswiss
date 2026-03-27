from fastapi import APIRouter, Depends, Query, Request
import asyncpg

router = APIRouter()

def get_pool(r: Request): return r.app.state.pool

@router.get("/")
async def search(
    q:    str          = Query(..., min_length=2, description="Terme de recherche"),
    lang: str          = Query("fr"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """Recherche full-text dans les CCT (nom + contenu)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji, is_dfo,
                   min_wage_chf, vacation_weeks, source_url, updated_at,
                   ts_rank(
                       to_tsvector('french', coalesce(name,'') || ' ' || coalesce(content_fr,'')),
                       plainto_tsquery('french', $1)
                   ) AS rank
            FROM cct
            WHERE to_tsvector('french', coalesce(name,'') || ' ' || coalesce(content_fr,''))
                  @@ plainto_tsquery('french', $1)
               OR name ILIKE $2
            ORDER BY rank DESC, is_dfo DESC
            LIMIT 20
        """, q, f"%{q}%")

    return {"query": q, "total": len(rows), "data": [dict(r) for r in rows]}
