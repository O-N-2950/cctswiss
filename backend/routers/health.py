from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/")
async def health(request: Request):
    try:
        async with request.app.state.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "db": "connected", "service": "CCTswiss.ch"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
