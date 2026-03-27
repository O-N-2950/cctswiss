from fastapi import APIRouter, Request
import asyncpg

# ── Health ──────────────────────────────────────────────────────────────────
health_router = APIRouter()
router = health_router

@health_router.get("/")
async def health(request: Request):
    try:
        async with request.app.state.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
