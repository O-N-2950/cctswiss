"""
CCTswiss.ch — Backend FastAPI
"""
import logging
import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.db.schema import init_schema
from backend.routers import cct, search, health, changelog
from backend.scrapers.auto_updater import start_scheduler, run_auto_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cctswiss")

DATABASE_URL = os.environ["DATABASE_URL"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    log.info("🚀 CCTswiss.ch démarrage...")
    app.state.pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    await init_schema(app.state.pool)

    # Premier run si DB vide
    async with app.state.pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM cct")
    if count == 0:
        log.info("DB vide — lancement initial de l'auto-updater...")
        await run_auto_update(DATABASE_URL)

    # Lancer le scheduler automatique
    app.state.scheduler = start_scheduler(DATABASE_URL)

    yield

    # Shutdown
    app.state.scheduler.shutdown()
    await app.state.pool.close()
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

# Routers
app.include_router(health.router,    prefix="/health",        tags=["health"])
app.include_router(cct.router,       prefix="/api/cct",       tags=["cct"])
app.include_router(search.router,    prefix="/api/search",    tags=["search"])
app.include_router(changelog.router, prefix="/api/changelog", tags=["changelog"])

# Servir le frontend statique
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
