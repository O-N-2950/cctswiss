"""
CCTswiss — /api/salary/* endpoints
Source de vérité pour salaires minimums (cantonaux + CCT)
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncpg, time

router = APIRouter()

def get_pool(r: Request): return r.app.state.pool

# In-memory cache 24h
_cache: dict = {}

def _cache_key(*args): return "|".join(str(a) for a in args)

def _cached(key):
    if key in _cache:
        val, ts = _cache[key]
        if time.time() - ts < 86400:  # 24h
            return val, True
    return None, False

def _set_cache(key, val):
    _cache[key] = (val, time.time())


# ── GET /api/salary/minimums/:canton ──────────────────────────────────
@router.get("/minimums/{canton}")
async def canton_minimum(canton: str, pool: asyncpg.Pool = Depends(get_pool)):
    """Salaire minimum cantonal en vigueur."""
    key = _cache_key("canton_min", canton.upper())
    cached, hit = _cached(key)
    if hit:
        return JSONResponse(cached, headers={"X-Cache":"HIT"})

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT canton, min_hourly, valid_from, valid_to, legal_basis, notes
            FROM cantonal_salary_minimums
            WHERE canton = $1 AND valid_from <= CURRENT_DATE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
            ORDER BY valid_from DESC LIMIT 1
        """, canton.upper())

    if row:
        result = {
            "canton": row["canton"],
            "minimum": float(row["min_hourly"]),
            "currency": "CHF",
            "period": "hourly",
            "valid_from": str(row["valid_from"]),
            "valid_to": str(row["valid_to"]) if row["valid_to"] else None,
            "legal_basis": row["legal_basis"],
            "notes": row["notes"],
        }
    else:
        result = {
            "canton": canton.upper(),
            "minimum": None,
            "note": f"Pas de salaire minimum légal dans le canton {canton.upper()}. Le minimum fédéral s'applique selon CO art. 322.",
            "federal_note": "La Suisse n'a pas de salaire minimum fédéral général au 2025."
        }

    _set_cache(key, result)
    return JSONResponse(result, headers={"X-Cache":"MISS"})


# ── GET /api/salary/minimums (all cantons) ────────────────────────────
@router.get("/minimums")
async def all_minimums(pool: asyncpg.Pool = Depends(get_pool)):
    """Tous les salaires minimums cantonaux en vigueur."""
    key = "all_canton_minimums"
    cached, hit = _cached(key)
    if hit:
        return JSONResponse(cached, headers={"X-Cache":"HIT"})

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (canton)
                canton, min_hourly, valid_from, legal_basis, notes
            FROM cantonal_salary_minimums
            WHERE valid_from <= CURRENT_DATE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
            ORDER BY canton, valid_from DESC
        """)

    cantons_with_min = [
        {"canton": r["canton"], "min_hourly": float(r["min_hourly"]),
         "valid_from": str(r["valid_from"]), "legal_basis": r["legal_basis"]}
        for r in rows
    ]
    all_cantons = ["AG","AI","AR","BE","BL","BS","FR","GE","GL","GR",
                   "JU","LU","NE","NW","OW","SG","SH","SO","SZ","TG","TI",
                   "UR","VD","VS","ZG","ZH"]
    cantons_with = {c["canton"] for c in cantons_with_min}
    cantons_without = [
        {"canton": c, "min_hourly": None, "note": "Pas de minimum légal cantonal"}
        for c in all_cantons if c not in cantons_with
    ]

    result = {
        "total_with_minimum": len(cantons_with_min),
        "total_without": len(cantons_without),
        "cantons_with_minimum": sorted(cantons_with_min, key=lambda x: -x["min_hourly"]),
        "cantons_without_minimum": sorted(cantons_without, key=lambda x: x["canton"]),
        "updated": "2026-01-01",
    }
    _set_cache(key, result)
    return JSONResponse(result, headers={"X-Cache":"MISS"})


# ── POST /api/salary/check ────────────────────────────────────────────
@router.post("/check")
async def check_salary(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    """
    Vérifie un salaire vs minimum cantonal ET minimum CCT.
    Retourne le plus élevé comme référence obligatoire.
    """
    body = await request.json()
    canton = (body.get("canton") or "").upper()
    noga = body.get("noga_code","").strip()
    hourly = body.get("hourly_rate")
    monthly = body.get("monthly_rate")

    results = {"canton": canton, "noga_code": noga, "issues": [], "status": "ok"}

    async with pool.acquire() as conn:
        # Minimum cantonal
        canton_row = None
        if canton:
            canton_row = await conn.fetchrow("""
                SELECT min_hourly, legal_basis FROM cantonal_salary_minimums
                WHERE canton=$1 AND valid_from <= CURRENT_DATE
                  AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
                ORDER BY valid_from DESC LIMIT 1
            """, canton)

        # Minimum CCT par NOGA
        cct_row = None
        if noga:
            cct_row = await conn.fetchrow("""
                SELECT name, salary_min_hourly, salary_min_monthly,
                       salary_min_by_category, rs_number
                FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1
            """, noga)

    canton_min = float(canton_row["min_hourly"]) if canton_row else None
    cct_min_h  = float(cct_row["salary_min_hourly"]) if cct_row and cct_row["salary_min_hourly"] else None
    cct_min_m  = float(cct_row["salary_min_monthly"]) if cct_row and cct_row["salary_min_monthly"] else None

    # Reference minimum = max(cantonal, CCT)
    ref_hourly = max([x for x in [canton_min, cct_min_h] if x is not None], default=None)
    ref_monthly = cct_min_m

    results["references"] = {
        "canton_min_hourly": canton_min,
        "canton_min_basis": canton_row["legal_basis"] if canton_row else None,
        "cct_min_hourly": cct_min_h,
        "cct_min_monthly": cct_min_m,
        "cct_name": cct_row["name"] if cct_row else None,
        "applicable_min_hourly": ref_hourly,
        "note": "Le minimum le plus élevé (cantonal ou CCT) fait référence."
    }

    # Check violations
    if hourly and ref_hourly and hourly < ref_hourly:
        results["issues"].append({
            "type": "salary_below_minimum",
            "severity": "critical",
            "message": f"Salaire horaire CHF {hourly:.2f} inférieur au minimum applicable (CHF {ref_hourly:.2f}/h)",
            "legal_basis": (cct_row["name"] if cct_min_h and cct_min_h >= (canton_min or 0) else (canton_row["legal_basis"] if canton_row else "CCT")) if cct_row or canton_row else "CO 322",
            "gap": round(ref_hourly - hourly, 2)
        })

    if monthly and ref_monthly and monthly < ref_monthly:
        results["issues"].append({
            "type": "monthly_below_minimum",
            "severity": "critical",
            "message": f"Salaire mensuel CHF {monthly:.2f} inférieur au minimum CCT (CHF {ref_monthly:.2f}/mois)",
            "legal_basis": cct_row["name"] if cct_row else "CCT",
            "gap": round(ref_monthly - monthly, 2)
        })

    results["status"] = "non_compliant" if results["issues"] else "compliant"
    return JSONResponse(results)
