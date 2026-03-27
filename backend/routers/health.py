from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("")
@router.get("/")
async def health(request: Request):
    pool = getattr(request.app.state, "pool", None)
    db_ok = False
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
        except:
            pass
    return JSONResponse({
        "status": "ok",
        "app": "CCTswiss.ch",
        "db": "connected" if db_ok else "starting"
    })
