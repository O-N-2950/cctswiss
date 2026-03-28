"""CCTswiss.ch — Backend FastAPI — Source de vérité NEO"""
import asyncio, logging, os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.db.schema import init_schema
from backend.routers import cct, search, health, changelog
from backend.scrapers.auto_updater import start_scheduler, run_auto_update
from backend.services.rate_limiter import rate_limit

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cctswiss")

DATABASE_URL  = os.environ.get("DATABASE_URL", "")
FRONTEND_PATH = "/app/frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("🚀 CCTswiss.ch démarrage...")
    if not DATABASE_URL:
        log.error("DATABASE_URL manquant"); yield; return

    pool = None
    for attempt in range(10):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=15)
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

    # Auto-seed si vide
    try:
        count = await pool.fetchval("SELECT COUNT(*) FROM cct")
        if count == 0:
            log.info("DB vide — auto-seed depuis admin.py...")
            try:
                from backend.routers.admin import CCT_SEED_DATA
                import json
                async with pool.acquire() as conn:
                    for cct_d in CCT_SEED_DATA:
                        try:
                            lcd = None
                            if cct_d.get("last_consolidation_date"):
                                from datetime import date
                                p = cct_d["last_consolidation_date"].split("-")
                                lcd = date(int(p[0]),int(p[1]),int(p[2]))
                            await conn.execute("""
                                INSERT INTO cct (rs_number,name,name_de,name_it,name_en,
                                    name_pt,name_es,name_sq,name_bs,name_tr,name_uk,
                                    branch,emoji,is_dfo,scope_cantons,scope_description_fr,
                                    min_wage_chf,vacation_weeks,weekly_hours,has_13th_salary,
                                    source_url,fedlex_uri,content_hash,legal_disclaimer_fr,
                                    last_consolidation_date)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                                    $16,$17,$18,$19,$20,$21,$22,$23,$24,$25)
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
                                cct_d.get("content_hash","v2025"),
                                cct_d.get("legal_disclaimer_fr",""), lcd)
                        except Exception as e:
                            log.warning(f"Seed {cct_d['rs_number']}: {e}")
                log.info(f"✅ Auto-seeded {len(CCT_SEED_DATA)} CCTs")
            except Exception as e:
                log.warning(f"Auto-seed: {e}")
    except Exception as e:
        log.warning(f"Count: {e}")

    app.state.scheduler = start_scheduler(DATABASE_URL)
    yield
    app.state.scheduler.shutdown()
    await pool.close()


# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CCTswiss.ch API",
    description="Source de vérité CCT pour l'écosystème NEO (WIN WIN, SwissRH)",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — autoriser WIN WIN, SwissRH et Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://winwin.swiss", "https://www.winwin.swiss",
        "https://swissrh.ch",   "https://www.swissrh.ch",
        "https://soluris.ch",   "https://devispro.ch",
        "https://cctswiss.ch",  "https://www.cctswiss.ch",
        "http://localhost:3000","http://localhost:5173",
    ],
    allow_origin_regex=r"https://.*\.railway\.app",
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Cache","X-Data-Source","X-RateLimit-Remaining"],
)

# Rate limit dependency
rl = Depends(rate_limit(100))

# ── Routers ────────────────────────────────────────────────────────────
app.include_router(health.router,       prefix="/health",         tags=["health"])
app.include_router(cct.router,          prefix="/api/cct",        tags=["cct"],        dependencies=[rl])
app.include_router(search.router,       prefix="/api/search",     tags=["search"],     dependencies=[rl])
app.include_router(changelog.router,    prefix="/api/changelog",  tags=["changelog"])

# Compliance & NOGA (WIN WIN + SwissRH)
try:
    from backend.routers.compliance import router as compliance_router
    app.include_router(compliance_router, prefix="/api/cct", tags=["compliance"], dependencies=[rl])
    log.info("✅ Compliance router (by-noga, check-compliance, dfo-list)")
except Exception as e:
    log.warning(f"Compliance: {e}")

# Salary minimums
try:
    from backend.routers.salary import router as salary_router
    app.include_router(salary_router, prefix="/api/salary", tags=["salary"], dependencies=[rl])
    log.info("✅ Salary router (minimums, check)")
except Exception as e:
    log.warning(f"Salary: {e}")

# Admin (seed, translate, stats)
try:
    from backend.routers.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    log.info("✅ Admin router")
except Exception as e:
    log.warning(f"Admin: {e}")

# NOGA enriched seed
try:
    from backend.routers.noga_seed import router as noga_router
    app.include_router(noga_router, prefix="/api/admin", tags=["admin"])
    log.info("✅ NOGA seed router")
except Exception as e:
    log.warning(f"NOGA seed: {e}")

# Frontend statique
if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
    log.info(f"✅ Frontend: {FRONTEND_PATH}")
else:
    @app.get("/")
    async def root(): return JSONResponse({"status":"ok","app":"CCTswiss.ch","version":"2.0"})
