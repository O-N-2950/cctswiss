from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/")
async def health(request: Request):
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        return JSONResponse({"status": "ok", "db": "not_connected"})
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return JSONResponse({"status": "ok", "db": "connected", "app": "CCTswiss.ch"})
    except Exception as e:
        return JSONResponse({"status": "ok", "db": f"error: {e}"})
