"""CCTswiss.ch — Backend FastAPI — Source de vérité NEO"""
import asyncio, logging, os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.db.schema import init_schema

# ── Sentry (backend monitoring) ───────────────────────────────────────
import sentry_sdk
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.environ.get("RAILWAY_ENVIRONMENT", "production"),
        release=os.environ.get("RAILWAY_GIT_COMMIT_SHA", "unknown")[:12],
        traces_sample_rate=0.2,        # 20% des transactions profilées
        profiles_sample_rate=0.1,
        send_default_pii=False,        # RGPD: pas d'IP ni d'email
        ignore_errors=[KeyboardInterrupt],
    )
    log.info(f"✅ Sentry actif: {SENTRY_DSN[:30]}…")
else:
    log.info("ℹ️  Sentry désactivé (SENTRY_DSN non défini)")
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
                log.info(f"✅ Auto-seeded {len(CCT_SEED_DATA)} CCTs from admin")
            except Exception as e:
                log.warning(f"Auto-seed admin: {e}")
            
            # Also seed from seed.py (29 DFO CCTs)
            try:
                from backend.routers.seed import CCT_DATA as SEED_DATA
                async with pool.acquire() as conn:
                    for s in SEED_DATA:
                        try:
                            dfu = None
                            if s.get("dfo_until"):
                                from datetime import date
                                p = s["dfo_until"].split("-")
                                dfu = date(int(p[0]), int(p[1]), int(p[2]))
                            await conn.execute("""
                                INSERT INTO cct (rs_number,name,branch,emoji,is_dfo,dfo_until,
                                    min_wage_chf,vacation_weeks,weekly_hours,has_13th_salary,
                                    source_url,scope_cantons,scope_description_fr,content_hash)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'seeded-v2')
                                ON CONFLICT (rs_number) DO NOTHING
                            """, s["rs_number"],s["name"],s["branch"],s["emoji"],
                                s.get("is_dfo",True),dfu,s.get("min_wage_chf"),
                                s.get("vacation_weeks"),s.get("weekly_hours"),
                                s.get("has_13th_salary",False),s.get("source_url",""),
                                s.get("scope_cantons"),s.get("scope_description_fr",""))
                        except: pass
                log.info(f"✅ Auto-seeded {len(SEED_DATA)} CCTs from seed.py")
            except Exception as e:
                log.warning(f"Auto-seed seed.py: {e}")
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

# ── Sentry middleware (capture exceptions HTTP) ──────────────────────
if SENTRY_DSN:
    try:
        from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
        app.add_middleware(SentryAsgiMiddleware)
        log.info("✅ Sentry ASGI middleware actif")
    except Exception as e:
        log.warning(f"Sentry middleware: {e}")

# ── Test route Sentry (à ne pas appeler en prod normalement) ─────────
@app.get("/api/sentry-test", tags=["monitoring"], include_in_schema=False)
async def sentry_test():
    """Route de test Sentry — génère une exception capturée."""
    raise ValueError("CCTswiss Sentry test — si tu vois ça dans Sentry, ça fonctionne ✅")

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

# Alertes email abonnés CCT
try:
    from backend.routers.alerts import router as alerts_router
    app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])
    log.info("✅ Alerts router (/subscribe, /confirm, /unsubscribe, /send, /stats)")
except Exception as e:
    log.warning(f"Alerts: {e}")

# Config publique frontend (GA4 ID, feature flags)
try:
    from backend.routers.config import router as config_router
    app.include_router(config_router, prefix="/api", tags=["config"])
    log.info("✅ Config router (/api/config)")
except Exception as e:
    log.warning(f"Config: {e}")
# Paritaire MUST be before cct.router (avoid /{rs_number} catching paritaire-rules)
try:
    from backend.routers.paritaire import router as paritaire_router
    app.include_router(paritaire_router, prefix="/api/cct", tags=["paritaire"], dependencies=[rl])
    log.info("✅ Paritaire router mounted before cct (avoids route collision)")
except Exception as e:
    log.warning(f"Paritaire: {e}")

app.include_router(cct.router,          prefix="/api/cct",        tags=["cct"],        dependencies=[rl])
app.include_router(search.router,       prefix="/api/search",     tags=["search"],     dependencies=[rl])
app.include_router(changelog.router,    prefix="/api/changelog",  tags=["changelog"])

# Google Search Console — vérification HTML file method
# Mettre le code dans SEARCH_CONSOLE_VERIFICATION Railway var
import os as _os
_sc_token = _os.environ.get("SEARCH_CONSOLE_VERIFICATION", "")
if _sc_token:
    @app.get(f"/google{_sc_token}.html", tags=["monitoring"], include_in_schema=False)
    async def search_console_verify():
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(f"google-site-verification: google{_sc_token}.html")

# Compliance endpoints are in cct.py (before /{rs_number})

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

# Seed.py router (29 CCTs DFO complets)
try:
    from backend.routers.seed import router as seed_router
    app.include_router(seed_router, prefix="/api/admin", tags=["admin"])
    log.info("✅ Seed router (29 CCTs)")
except Exception as e:
    log.warning(f"Seed: {e}")

# Frontend statique
if os.path.isdir(FRONTEND_PATH):
    app.mount("/", StaticFiles(directory=FRONTEND_PATH, html=True), name="frontend")
    log.info(f"✅ Frontend: {FRONTEND_PATH}")
else:
    @app.get("/")
    async def root(): return JSONResponse({"status":"ok","app":"CCTswiss.ch","version":"2.0"})
