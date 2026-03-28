"""CCTswiss.ch — Backend FastAPI"""
import asyncio, logging, os
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

DATABASE_URL  = os.environ.get("DATABASE_URL", "")
FRONTEND_PATH = "/app/frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 CCTswiss.ch démarrage...")
    if not DATABASE_URL:
        log.error("DATABASE_URL manquant")
        yield; return

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
        log.error("DB inaccessible"); yield; return

    app.state.pool = pool
    await init_schema(pool)

    # Auto-seed if empty
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM cct")
        if count == 0:
            log.info("DB vide — seeding initial depuis admin.py...")
            try:
                from backend.routers.admin import CCT_SEED_DATA
                import json
                async with pool.acquire() as conn:
                    for cct_d in CCT_SEED_DATA:
                        try:
                            await conn.execute("""
                                INSERT INTO cct (rs_number,name,name_de,name_it,name_en,
                                    name_pt,name_es,name_sq,name_bs,name_tr,name_uk,
                                    branch,emoji,is_dfo,scope_cantons,scope_description_fr,
                                    min_wage_chf,vacation_weeks,weekly_hours,has_13th_salary,
                                    source_url,fedlex_uri,content_hash,legal_disclaimer_fr)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                                    $16,$17,$18,$19,$20,$21,$22,$23,$24)
                                ON CONFLICT (rs_number) DO NOTHING
                            """, cct_d["rs_number"],cct_d["name"],
                                cct_d.get("name_de"),cct_d.get("name_it"),cct_d.get("name_en"),
                                cct_d.get("name_pt"),cct_d.get("name_es"),
                                cct_d.get("name_sq"),cct_d.get("name_bs"),
                                cct_d.get("name_tr"),cct_d.get("name_uk"),
                                cct_d["branch"],cct_d["emoji"],cct_d["is_dfo"],
                                cct_d.get("scope_cantons"),cct_d.get("scope_description_fr",""),
                                cct_d.get("min_wage_chf"),cct_d.get("vacation_weeks"),
                                cct_d.get("weekly_hours"),cct_d.get("has_13th_salary",False),
                                cct_d.get("source_url",""),cct_d.get("fedlex_uri",""),
                                cct_d.get("content_hash","auto"),
                                cct_d.get("legal_disclaimer_fr",""))
                        except Exception as e:
                            log.warning(f"Seed {cct_d['rs_number']}: {e}")
                log.info(f"✅ Auto-seeded {len(CCT_SEED_DATA)} CCTs")
            except Exception as e:
                log.warning(f"Auto-seed failed: {e}")
    except Exception as e:
        log.warning(f"Count check: {e}")

    app.state.scheduler = start_scheduler(DATABASE_URL)
    yield
    app.state.scheduler.shutdown()
    await pool.close()

app = FastAPI(title="CCTswiss.ch API", version="1.0.0",
              lifespan=lifespan, docs_url="/api/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["GET","POST"], allow_headers=["*"])

# Routers
app.include_router(health.router,    prefix="/health",      tags=["health"])
app.include_router(cct.router,       prefix="/api/cct",     tags=["cct"])
app.include_router(search.router,    prefix="/api/search",  tags=["search"])
app.include_router(changelog.router, prefix="/api/changelog",tags=["changelog"])

# Admin router (seed, translate, stats)
try:
    from backend.routers.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    log.info("✅ Admin router loaded")
except Exception as e:
    log.warning(f"Admin router not loaded: {e}")

# Frontend statique
if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
else:
    @app.get("/")
    async def root(): return JSONResponse({"status":"ok","app":"CCTswiss.ch"})
