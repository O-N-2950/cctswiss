"""CCTswiss — /health"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime

router = APIRouter()

@router.get("")
@router.get("/")
async def health(request: Request):
    pool = getattr(request.app.state, "pool", None)
    db_ok = False
    total_ccts = 0
    
    if pool:
        try:
            total_ccts = await pool.fetchval("SELECT COUNT(*) FROM cct")
            db_ok = True
        except:
            db_ok = False
    
    return JSONResponse({
        "status": "ok" if db_ok else "degraded",
        "app": "CCTswiss.ch",
        "version": "2.0",
        "db": "connected" if db_ok else "error",
        "total_ccts": total_ccts,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
