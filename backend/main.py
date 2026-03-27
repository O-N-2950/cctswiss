"""CCTswiss.ch — Backend FastAPI"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.db.schema import init_schema
from backend.routers import cct, search, health, changelog
from backend.scrapers.auto_updater import start_scheduler, run_auto_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cctswiss")

DATABASE_URL  = os.environ.get("DATABASE_URL", "")
FRONTEND_PATH = "/app/frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 CCTswiss.ch démarrage...")
    if not DATABASE_URL:
        log.error("DATABASE_URL manquant")
        yield
        return

    pool = None
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            await pool.fetchval("SELECT 1")
            log.info(f"✅ DB connectée (tentative {attempt+1})")
            break
        except Exception as e:
            log.warning(f"DB pas prête ({attempt+1}/10): {e}")
            await asyncio.sleep(5)

    if pool is None:
        log.error("DB inaccessible")
        yield
        return

    app.state.pool = pool
    await init_schema(pool)

    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM cct")
        if count == 0:
            log.info("DB vide — chargement initial Fedlex...")
            await run_auto_update(DATABASE_URL)
    except Exception as e:
        log.warning(f"Init: {e}")

    app.state.scheduler = start_scheduler(DATABASE_URL)
    yield
    app.state.scheduler.shutdown()
    await pool.close()

app = FastAPI(
    title="CCTswiss.ch API",
    description="Le répertoire suisse des conventions collectives de travail — API publique",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"])

# Public API
app.include_router(health.router,    prefix="/health",        tags=["health"])
app.include_router(cct.router,       prefix="/api/cct",       tags=["cct"])
app.include_router(search.router,    prefix="/api/search",    tags=["search"])
app.include_router(changelog.router, prefix="/api/changelog", tags=["changelog"])

# Admin (protected by SEED_SECRET header)
from backend.routers import admin
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

import os as _os
if _os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
    log.info(f"✅ Frontend: {FRONTEND_PATH}")
else:
    @app.get("/")
    async def root(): return JSONResponse({"status": "ok", "app": "CCTswiss.ch"})
