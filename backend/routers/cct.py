"""CCTswiss.ch — Router /api/cct"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncpg

router = APIRouter()

def get_pool(request: Request):
    return request.app.state.pool

@router.get("/")
async def list_ccts(
    branch:  Optional[str] = Query(None),
    canton:  Optional[str] = Query(None),
    is_dfo:  Optional[bool] = Query(None),
    lang:    str            = Query("fr"),
    pool:    asyncpg.Pool   = Depends(get_pool),
):
    conditions, params = [], []
    if branch:
        params.append(branch.lower())
        conditions.append(f"branch = ${len(params)}")
    if canton:
        params.append(canton.upper())
        conditions.append(f"(scope_cantons IS NULL OR ${len(params)} = ANY(scope_cantons))")
    if is_dfo is not None:
        params.append(is_dfo)
        conditions.append(f"is_dfo = ${len(params)}")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT rs_number, name, branch, emoji, is_dfo,
                   scope_cantons, scope_description_fr,
                   min_wage_chf, vacation_weeks, weekly_hours,
                   has_13th_salary, source_url, fedlex_uri,
                   last_consolidation_date, dfo_until, updated_at
            FROM cct {where}
            ORDER BY is_dfo DESC, name ASC
        """, *params)
    return {"total": len(rows), "lang": lang, "data": [dict(r) for r in rows]}

@router.get("/branches")
async def list_branches(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT branch, emoji, COUNT(*) as count FROM cct GROUP BY branch, emoji ORDER BY count DESC")
    return [dict(r) for r in rows]

@router.get("/status")
async def update_status(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        last = await conn.fetchrow("SELECT MAX(auto_updated_at) as last_check, MAX(updated_at) as last_change, COUNT(*) as total_ccts FROM cct")
        changes = await conn.fetch("SELECT rs_number, changed_at, change_type FROM cct_changelog ORDER BY changed_at DESC LIMIT 10")
    return {
        "last_auto_check": str(last["last_check"]) if last["last_check"] else None,
        "last_real_change": str(last["last_change"]) if last["last_change"] else None,
        "total_ccts": last["total_ccts"],
        "recent_changes": [dict(c) for c in changes],
        "next_check": "Chaque nuit à 02:00 CET (automatique)",
    }

@router.get("/{rs_number}")
async def get_cct(rs_number: str, lang: str = Query("fr"), pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cct WHERE rs_number = $1", rs_number)
        if not row:
            raise HTTPException(404, f"CCT {rs_number} introuvable")
        await conn.execute("""
            INSERT INTO cct_views (rs_number, lang, viewed_at, count) VALUES ($1,$2,CURRENT_DATE,1)
            ON CONFLICT (rs_number, lang, viewed_at) DO UPDATE SET count = cct_views.count + 1
        """, rs_number, lang)
        history = await conn.fetch("SELECT changed_at, change_type, source FROM cct_changelog WHERE rs_number=$1 ORDER BY changed_at DESC LIMIT 10", rs_number)
    return {**dict(row), "change_history": [dict(h) for h in history]}

# ── Compliance endpoints (must be before /{rs_number}) ────────────────

@router.get("/dfo-list")
async def dfo_list(pool: asyncpg.Pool = Depends(get_pool)):
    """Tous les secteurs DFO avec NOGA codes et salaires."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji,
                   noga_codes, dfo_cantons, dfo_since,
                   salary_min_hourly, is_dfo, dfo, data_complete
            FROM cct
            WHERE is_dfo=true OR dfo=true
            ORDER BY name
        """)
    return {
        "total": len(rows),
        "data": [
            {
                "rs_number": r["rs_number"],
                "name": r["name"],
                "branch": r["branch"],
                "emoji": r["emoji"],
                "noga_codes": r["noga_codes"] or [],
                "dfo_cantons": r["dfo_cantons"] or [],
                "dfo_since": str(r["dfo_since"]) if r["dfo_since"] else None,
                "salary_min_hourly": float(r["salary_min_hourly"]) if r["salary_min_hourly"] else None,
                "data_complete": r["data_complete"],
            }
            for r in rows
        ]
    }


@router.get("/by-noga/{noga_code}")
async def cct_by_noga(noga_code: str, pool: asyncpg.Pool = Depends(get_pool)):
    """Retourne la CCT complète pour un code NOGA donné. Sans auth, public."""
    import json as _json, time as _time
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1", noga_code
        )

    if not row:
        return {
            "noga_code": noga_code, "cct_found": False, "data_complete": False,
            "message": f"Aucune CCT répertoriée pour NOGA {noga_code}.",
            "co324a_fallback": {"year1_days":21,"year2_days":28,"year5_days":35,
                                "note":"Minimum CO 324a sans CCT applicable"}
        }

    ijm = None
    if row["ijm_min_rate"]:
        ijm = {"min_rate": row["ijm_min_rate"],
               "max_carence_days": row["ijm_max_carence_days"],
               "min_coverage_days": row["ijm_min_coverage_days"],
               "employer_topup_required": row["ijm_employer_topup"],
               "employer_topup_to": row["ijm_topup_to"]}

    laa = None
    if row["laa_min_rate"]:
        laa = {"min_rate": row["laa_min_rate"],
               "max_carence_days": row["laa_max_carence_days"],
               "complementaire_required": row["laa_complementaire_required"],
               "note": "LAA SUVA obligatoire pour tous les employeurs suisses."}

    salary = None
    if row["salary_min_hourly"] or row["salary_min_monthly"]:
        by_cat = None
        if row["salary_min_by_category"]:
            try:
                by_cat = _json.loads(row["salary_min_by_category"]) if isinstance(row["salary_min_by_category"],str) else dict(row["salary_min_by_category"])
            except: pass
        salary = {"hourly": float(row["salary_min_hourly"]) if row["salary_min_hourly"] else None,
                  "monthly": float(row["salary_min_monthly"]) if row["salary_min_monthly"] else None,
                  "by_category": by_cat,
                  "updated": str(row["salary_min_updated"]) if row["salary_min_updated"] else None}

    return {
        "noga_code": noga_code,
        "cct_found": True,
        "cct_name": row["name"],
        "rs_number": row["rs_number"],
        "data_complete": row.get("data_complete", False),
        "dfo": row.get("dfo", row.get("is_dfo", False)),
        "dfo_cantons": row["dfo_cantons"] or [],
        "dfo_since": str(row["dfo_since"]) if row.get("dfo_since") else None,
        "voluntary_only": row.get("voluntary_only", False),
        "membership_required": row.get("membership_required"),
        "ijm": ijm, "laa": laa, "salary_minimums": salary,
        "co324a_fallback": {"year1_days": row.get("co324a_year1_days") or 21,
                            "year2_days": row.get("co324a_year2_days") or 28,
                            "year5_days": row.get("co324a_year5_days") or 35,
                            "note": "Minimum légal CO 324a"},
        "source_url": row["source_url"],
        "last_updated": str(row["updated_at"])[:10] if row["updated_at"] else None,
    }
