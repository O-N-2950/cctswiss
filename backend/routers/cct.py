"""CCTswiss.ch — Router /api/cct + compliance endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncpg, json as _json

router = APIRouter()

def get_pool(request: Request):
    return request.app.state.pool

# ── GET / — list CCTs ────────────────────────────────────────────────
@router.get("/")
async def list_ccts(
    branch:  Optional[str]  = Query(None),
    canton:  Optional[str]  = Query(None),
    is_dfo:  Optional[bool] = Query(None),
    lang:    str             = Query("fr"),
    pool:    asyncpg.Pool    = Depends(get_pool),
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
            SELECT rs_number, name, name_de, name_it, name_en,
                   name_pt, name_es, name_sq, name_bs, name_tr, name_uk,
                   branch, emoji, is_dfo, dfo, scope_cantons, scope_description_fr,
                   min_wage_chf, salary_min_hourly, salary_min_monthly,
                   vacation_weeks, weekly_hours, has_13th_salary,
                   source_url, dfo_until, data_complete, updated_at,
                   noga_codes, ijm_min_rate, laa_min_rate, membership_required
            FROM cct {where}
            ORDER BY is_dfo DESC, name ASC
        """, *params)
    return {"total": len(rows), "lang": lang, "data": [dict(r) for r in rows]}


# ── GET /branches ─────────────────────────────────────────────────────
@router.get("/branches")
async def list_branches(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT branch, emoji, COUNT(*) as count FROM cct GROUP BY branch, emoji ORDER BY count DESC"
        )
    return [dict(r) for r in rows]


# ── GET /status ───────────────────────────────────────────────────────
@router.get("/status")
async def update_status(pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        last = await conn.fetchrow(
            "SELECT MAX(auto_updated_at) as last_check, MAX(updated_at) as last_change, COUNT(*) as total_ccts FROM cct"
        )
        changes = await conn.fetch(
            "SELECT rs_number, changed_at, change_type FROM cct_changelog ORDER BY changed_at DESC LIMIT 10"
        )
    return {
        "last_auto_check": str(last["last_check"]) if last["last_check"] else None,
        "last_real_change": str(last["last_change"]) if last["last_change"] else None,
        "total_ccts": last["total_ccts"],
        "recent_changes": [dict(c) for c in changes],
        "next_check": "Chaque nuit à 02:00 CET (automatique)",
    }


# ── GET /dfo-list — BEFORE /{rs_number} ──────────────────────────────
@router.get("/dfo-list")
async def dfo_list(pool: asyncpg.Pool = Depends(get_pool)):
    """Tous les secteurs avec DFO=true + NOGA codes. Public, pour WIN WIN et SwissRH."""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji,
                   noga_codes, dfo_cantons, dfo_since,
                   salary_min_hourly, is_dfo, dfo, data_complete
            FROM cct
            WHERE is_dfo = true OR dfo = true
            ORDER BY name
        """)
    return JSONResponse({
        "total": len(rows),
        "data": [
            {
                "rs_number":        r["rs_number"],
                "name":             r["name"],
                "branch":           r["branch"],
                "emoji":            r["emoji"],
                "noga_codes":       r["noga_codes"] or [],
                "dfo_cantons":      r["dfo_cantons"] or [],
                "dfo_since":        str(r["dfo_since"]) if r["dfo_since"] else None,
                "salary_min_hourly": float(r["salary_min_hourly"]) if r["salary_min_hourly"] else None,
                "data_complete":    r["data_complete"],
            }
            for r in rows
        ]
    }, headers={"X-Cache": "MISS", "X-Data-Source": "CCTswiss"})


# ── GET /by-noga/:code — BEFORE /{rs_number} ─────────────────────────
@router.get("/by-noga/{noga_code}")
async def cct_by_noga(noga_code: str, pool: asyncpg.Pool = Depends(get_pool)):
    """Retourne la CCT complète par code NOGA. Utilisé par WIN WIN et SwissRH."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1", noga_code
        )

    if not row:
        return JSONResponse({
            "noga_code": noga_code, "cct_found": False, "data_complete": False,
            "message": f"Aucune CCT répertoriée pour NOGA {noga_code}.",
            "co324a_fallback": {
                "year1_days": 21, "year2_days": 28, "year5_days": 35,
                "note": "Minimum légal CO 324a sans CCT applicable"
            }
        }, headers={"X-Cache": "MISS"})

    def _f(v): return float(v) if v is not None else None

    ijm = None
    if row["ijm_min_rate"]:
        ijm = {
            "min_rate":               row["ijm_min_rate"],
            "max_carence_days":       row["ijm_max_carence_days"],
            "min_coverage_days":      row["ijm_min_coverage_days"],
            "employer_topup_required": row["ijm_employer_topup"],
            "employer_topup_to":      row["ijm_topup_to"],
        }

    laa = None
    if row["laa_min_rate"]:
        laa = {
            "min_rate":               row["laa_min_rate"],
            "max_carence_days":       row["laa_max_carence_days"],
            "complementaire_required": row["laa_complementaire_required"],
            "note": "LAA SUVA obligatoire pour tous les employeurs suisses.",
        }

    salary = None
    if row["salary_min_hourly"] or row["salary_min_monthly"]:
        by_cat = None
        if row["salary_min_by_category"]:
            try:
                raw = row["salary_min_by_category"]
                by_cat = _json.loads(raw) if isinstance(raw, str) else dict(raw)
            except Exception:
                pass
        salary = {
            "hourly":      _f(row["salary_min_hourly"]),
            "monthly":     _f(row["salary_min_monthly"]),
            "by_category": by_cat,
            "updated":     str(row["salary_min_updated"]) if row["salary_min_updated"] else None,
        }

    return JSONResponse({
        "noga_code":          noga_code,
        "cct_found":          True,
        "cct_name":           row["name"],
        "rs_number":          row["rs_number"],
        "data_complete":      bool(row.get("data_complete")),
        "dfo":                bool(row.get("dfo") or row.get("is_dfo")),
        "dfo_cantons":        row["dfo_cantons"] or [],
        "dfo_since":          str(row["dfo_since"]) if row.get("dfo_since") else None,
        "voluntary_only":     bool(row.get("voluntary_only")),
        "membership_required": row.get("membership_required"),
        "ijm":                ijm,
        "laa":                laa,
        "salary_minimums":    salary,
        "co324a_fallback": {
            "year1_days": row.get("co324a_year1_days") or 21,
            "year2_days": row.get("co324a_year2_days") or 28,
            "year5_days": row.get("co324a_year5_days") or 35,
            "note": "Minimum légal CO art. 324a",
        },
        "source_url":  row["source_url"],
        "last_updated": str(row["updated_at"])[:10] if row["updated_at"] else None,
    }, headers={"X-Cache": "MISS", "X-Data-Source": "CCTswiss"})


# ── POST /check-compliance — BEFORE /{rs_number} ─────────────────────
@router.post("/check-compliance")
async def check_compliance(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    """
    Vérifie la conformité CCT d'un dossier.
    Utilisé par WIN WIN Finance (souscription assurance) et SwissRH (contrats).
    """
    body = await request.json()
    noga         = body.get("noga_code", "").strip()
    canton       = (body.get("canton") or "").upper()
    ijm_rate     = body.get("ijm_rate")
    ijm_carence  = body.get("ijm_carence_days")
    ijm_coverage = body.get("ijm_coverage_days")
    laa_rate     = body.get("laa_rate")
    laa_carence  = body.get("laa_carence_days")
    sal_hourly   = body.get("salary_hourly")
    sal_monthly  = body.get("salary_monthly")

    issues, warnings = [], []

    async with pool.acquire() as conn:
        cct = await conn.fetchrow(
            "SELECT * FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1", noga
        ) if noga else None

        cantonal = await conn.fetchrow("""
            SELECT min_hourly, legal_basis FROM cantonal_salary_minimums
            WHERE canton=$1 AND valid_from <= CURRENT_DATE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
            ORDER BY valid_from DESC LIMIT 1
        """, canton) if canton else None

    # ── IJM ───────────────────────────────────────────────────────────
    if cct and cct["ijm_min_rate"]:
        req_rate = cct["ijm_min_rate"]
        if ijm_rate is not None and ijm_rate < req_rate:
            issues.append({
                "type": "ijm_rate_too_low", "severity": "critical",
                "message": f"Taux IJM {ijm_rate}% inférieur au minimum CCT ({req_rate}%)",
                "legal_basis": cct["name"], "required": req_rate, "current": ijm_rate,
            })
        max_car = cct["ijm_max_carence_days"]
        if ijm_carence is not None and max_car is not None and ijm_carence > max_car:
            issues.append({
                "type": "ijm_carence_too_long", "severity": "warning",
                "message": f"Délai carence IJM {ijm_carence}j > maximum CCT ({max_car}j)",
                "legal_basis": cct["name"], "max_allowed": max_car, "current": ijm_carence,
            })
        min_cov = cct["ijm_min_coverage_days"]
        if ijm_coverage is not None and min_cov is not None and ijm_coverage < min_cov:
            issues.append({
                "type": "ijm_coverage_too_short", "severity": "critical",
                "message": f"Couverture IJM {ijm_coverage}j < minimum CCT ({min_cov}j)",
                "legal_basis": cct["name"], "required": min_cov, "current": ijm_coverage,
            })
        if cct["ijm_employer_topup"] and ijm_rate and ijm_rate < (cct["ijm_topup_to"] or 100):
            warnings.append({
                "type": "ijm_topup_required", "severity": "warning",
                "message": f"CCT exige complément employeur à {cct['ijm_topup_to'] or 100}% du salaire",
                "legal_basis": cct["name"],
            })

    # ── LAA ───────────────────────────────────────────────────────────
    if cct and cct["laa_min_rate"]:
        if laa_rate is not None and laa_rate < cct["laa_min_rate"]:
            issues.append({
                "type": "laa_rate_too_low", "severity": "critical",
                "message": f"Taux LAA {laa_rate}% < minimum CCT ({cct['laa_min_rate']}%)",
                "legal_basis": cct["name"],
            })
        max_laa_car = cct["laa_max_carence_days"]
        if laa_carence is not None and max_laa_car is not None and laa_carence > max_laa_car:
            issues.append({
                "type": "laa_carence_too_long", "severity": "critical",
                "message": f"Carence LAA {laa_carence}j > maximum CCT ({max_laa_car}j) — SUVA couvre dès J+0",
                "legal_basis": cct["name"],
            })
        if cct["laa_complementaire_required"]:
            warnings.append({
                "type": "laac_required", "severity": "warning",
                "message": "La CCT exige une assurance accidents complémentaire (LAAC)",
                "legal_basis": cct["name"],
            })

    # ── Salaires ──────────────────────────────────────────────────────
    canton_min = float(cantonal["min_hourly"]) if cantonal else None
    cct_min_h  = float(cct["salary_min_hourly"]) if cct and cct["salary_min_hourly"] else None
    cct_min_m  = float(cct["salary_min_monthly"]) if cct and cct["salary_min_monthly"] else None
    ref_hourly = max([x for x in [canton_min, cct_min_h] if x is not None], default=None)

    if sal_hourly and ref_hourly and sal_hourly < ref_hourly:
        basis = (cct["name"] if cct_min_h and cct_min_h >= (canton_min or 0)
                 else (cantonal["legal_basis"] if cantonal else "CCT")) if (cct or cantonal) else "CO 322"
        issues.append({
            "type": "salary_below_minimum", "severity": "critical",
            "message": f"Salaire horaire CHF {sal_hourly:.2f} < minimum applicable (CHF {ref_hourly:.2f}/h)",
            "legal_basis": basis,
            "required": ref_hourly, "current": sal_hourly, "gap": round(ref_hourly - sal_hourly, 2),
        })
    if sal_monthly and cct_min_m and sal_monthly < cct_min_m:
        issues.append({
            "type": "monthly_below_minimum", "severity": "critical",
            "message": f"Salaire mensuel CHF {sal_monthly:.2f} < minimum CCT (CHF {cct_min_m:.2f}/mois)",
            "legal_basis": cct["name"] if cct else "CCT",
            "required": cct_min_m, "current": sal_monthly, "gap": round(cct_min_m - sal_monthly, 2),
        })

    status = "non_compliant" if issues else ("compliant_with_warnings" if warnings else "compliant")
    return JSONResponse({
        "status":    status,
        "cct_found": bool(cct),
        "cct_name":  cct["name"] if cct else None,
        "canton":    canton,
        "issues":    issues,
        "warnings":  warnings,
        "summary": {
            "critical": len(issues),
            "warnings": len(warnings),
            "checks_performed": len([x for x in [ijm_rate, ijm_carence, laa_rate, sal_hourly, sal_monthly] if x is not None]),
        },
    })


# ── GET /{rs_number} — MUST BE LAST ──────────────────────────────────
@router.get("/{rs_number}")
async def get_cct(rs_number: str, lang: str = Query("fr"), pool: asyncpg.Pool = Depends(get_pool)):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM cct WHERE rs_number = $1", rs_number)
        if not row:
            raise HTTPException(404, f"CCT '{rs_number}' introuvable")
        await conn.execute("""
            INSERT INTO cct_views (rs_number, lang, viewed_at, count) VALUES ($1,$2,CURRENT_DATE,1)
            ON CONFLICT (rs_number, lang, viewed_at) DO UPDATE SET count = cct_views.count + 1
        """, rs_number, lang)
        history = await conn.fetch(
            "SELECT changed_at, change_type, source FROM cct_changelog WHERE rs_number=$1 ORDER BY changed_at DESC LIMIT 10",
            rs_number
        )
    return {**dict(row), "change_history": [dict(h) for h in history]}
