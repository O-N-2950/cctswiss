"""
CCTswiss.ch — Backend FastAPI
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

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

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Absolute path to frontend dir (works regardless of CWD)
BASE_DIR     = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 CCTswiss.ch démarrage...")

    if not DATABASE_URL:
        log.error("DATABASE_URL manquant — vérifiez les variables Railway")
        yield
        return

    # DB pool avec retry (PostgreSQL peut mettre quelques secondes à démarrer)
    import asyncio
    pool = None
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            await pool.fetchval("SELECT 1")
            log.info(f"✅ DB connectée (tentative {attempt+1})")
            break
        except Exception as e:
            log.warning(f"DB pas encore prête ({attempt+1}/10): {e}")
            await asyncio.sleep(5)

    if pool is None:
        log.error("Impossible de se connecter à la DB après 10 tentatives")
        yield
        return

    app.state.pool = pool
    await init_schema(pool)

    # Premier chargement si DB vide
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM cct")
        if count == 0:
            log.info("DB vide — premier chargement CCT depuis Fedlex...")
            await run_auto_update(DATABASE_URL)
    except Exception as e:
        log.warning(f"Init data error: {e}")

    # Scheduler automatique (nuit à 02:00 CET)
    app.state.scheduler = start_scheduler(DATABASE_URL)

    yield

    app.state.scheduler.shutdown()
    await pool.close()
    log.info("CCTswiss.ch arrêté proprement.")


app = FastAPI(
    title="CCTswiss.ch API",
    description="Le répertoire suisse des conventions collectives de travail",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Routers API
app.include_router(health.router,    prefix="/health",        tags=["health"])
app.include_router(cct.router,       prefix="/api/cct",       tags=["cct"])
app.include_router(search.router,    prefix="/api/search",    tags=["search"])
app.include_router(changelog.router, prefix="/api/changelog", tags=["changelog"])

# Frontend statique — chemin absolu
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    log.info(f"✅ Frontend servi depuis {FRONTEND_DIR}")
else:
    log.warning(f"⚠️  Frontend dir introuvable: {FRONTEND_DIR}")
    @app.get("/")
    async def root():
        return JSONResponse({"status": "ok", "message": "CCTswiss.ch API — frontend not found"})
