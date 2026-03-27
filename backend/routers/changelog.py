from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/")
async def get_changelog(request: Request):
    """Historique public des mises à jour automatiques."""
    async with request.app.state.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.rs_number, ct.name, c.changed_at, c.change_type, c.source
            FROM cct_changelog c
            JOIN cct ct ON ct.rs_number = c.rs_number
            ORDER BY c.changed_at DESC LIMIT 50
        """)
    return {"updates": [dict(r) for r in rows]}
