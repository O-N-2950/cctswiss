"""
CCTswiss — /api/cct/by-noga + /api/cct/check-compliance + /api/cct/dfo-list
Source de vérité pour WIN WIN et SwissRH
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
import asyncpg, time, json as json_lib

router = APIRouter()

def get_pool(r: Request): return r.app.state.pool

# Cache 24h
_cache: dict = {}
def _cache_key(*args): return "|".join(str(a) for a in args)
def _cached(key):
    if key in _cache:
        v, ts = _cache[key]
        if time.time() - ts < 86400: return v, True
    return None, False
def _set_cache(k, v): _cache[k] = (v, time.time())


# ── GET /api/cct/by-noga/:noga_code ──────────────────────────────────
@router.get("/by-noga/{noga_code}")
async def cct_by_noga(noga_code: str, pool: asyncpg.Pool = Depends(get_pool)):
    """Retourne la CCT complète pour un code NOGA donné."""
    key = _cache_key("by_noga", noga_code)
    cached, hit = _cached(key)
    if hit:
        return JSONResponse(cached, headers={"X-Cache":"HIT","X-Data-Source":"CCTswiss"})

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1
        """, noga_code)

    if not row:
        result = {
            "noga_code": noga_code,
            "cct_found": False,
            "data_complete": False,
            "message": f"Aucune CCT répertoriée pour le code NOGA {noga_code}.",
            "fallback": "Vérifiez via SECO ou appliquez CO art. 324a",
            "co324a_fallback": {
                "year1_days": 21, "year2_days": 28, "year5_days": 35,
                "note": "Continuation de salaire minimale selon CO 324a (sans CCT)"
            }
        }
        return JSONResponse(result, status_code=200,
                           headers={"X-Cache":"MISS","X-Data-Source":"CCTswiss"})

    # IJM
    ijm = None
    if row["ijm_min_rate"]:
        ijm = {
            "min_rate": row["ijm_min_rate"],
            "max_carence_days": row["ijm_max_carence_days"],
            "min_coverage_days": row["ijm_min_coverage_days"],
            "employer_topup_required": row["ijm_employer_topup"],
            "employer_topup_to": row["ijm_topup_to"],
        }

    # LAA
    laa = None
    if row["laa_min_rate"]:
        laa = {
            "min_rate": row["laa_min_rate"],
            "max_carence_days": row["laa_max_carence_days"],
            "complementaire_required": row["laa_complementaire_required"],
            "note": "LAA SUVA obligatoire pour tous les employeurs suisses."
        }

    # Salaires
    salary = None
    if row["salary_min_hourly"] or row["salary_min_monthly"]:
        by_cat = None
        if row["salary_min_by_category"]:
            try:
                by_cat = json_lib.loads(row["salary_min_by_category"]) if isinstance(row["salary_min_by_category"], str) else dict(row["salary_min_by_category"])
            except: pass
        salary = {
            "hourly":      float(row["salary_min_hourly"]) if row["salary_min_hourly"] else None,
            "monthly":     float(row["salary_min_monthly"]) if row["salary_min_monthly"] else None,
            "by_category": by_cat,
            "updated":     str(row["salary_min_updated"]) if row["salary_min_updated"] else None,
        }

    result = {
        "noga_code":     noga_code,
        "cct_found":     True,
        "cct_name":      row["name"],
        "rs_number":     row["rs_number"],
        "data_complete": row.get("data_complete", False),
        "dfo":           row.get("dfo", row.get("is_dfo", False)),
        "dfo_cantons":   row["dfo_cantons"] or [],
        "dfo_since":     str(row["dfo_since"]) if row.get("dfo_since") else None,
        "voluntary_only": row.get("voluntary_only", False),
        "membership_required": row.get("membership_required"),
        "ijm":           ijm,
        "laa":           laa,
        "salary_minimums": salary,
        "co324a_fallback": {
            "year1_days": row.get("co324a_year1_days") or 21,
            "year2_days": row.get("co324a_year2_days") or 28,
            "year5_days": row.get("co324a_year5_days") or 35,
            "note": "Minimum légal CO 324a si pas de CCT plus favorable"
        },
        "source_url":  row["source_url"],
        "last_updated": str(row["updated_at"])[:10] if row["updated_at"] else None,
    }

    _set_cache(key, result)
    return JSONResponse(result, headers={"X-Cache":"MISS","X-Data-Source":"CCTswiss"})


# ── GET /api/cct/dfo-list ─────────────────────────────────────────────
@router.get("/dfo-list")
async def dfo_list(pool: asyncpg.Pool = Depends(get_pool)):
    """Tous les secteurs DFO=true avec NOGA codes."""
    key = "dfo_list"
    cached, hit = _cached(key)
    if hit:
        return JSONResponse(cached, headers={"X-Cache":"HIT"})

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji, noga_codes,
                   dfo_cantons, dfo_since, salary_min_hourly, data_complete
            FROM cct WHERE (is_dfo=true OR dfo=true OR (noga_codes IS NOT NULL AND dfo IS NOT DISTINCT FROM true))
            ORDER BY name
        """)

    result = {
        "total": len(rows), "dfo_count": len(rows),
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
    _set_cache(key, result)
    return JSONResponse(result, headers={"X-Cache":"MISS"})


# ── POST /api/cct/check-compliance ───────────────────────────────────
@router.post("/check-compliance")
async def check_compliance(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    """
    Vérifie la conformité CCT d'un contrat d'assurance ou d'un dossier employeur.
    Utilisé par WIN WIN Finance et SwissRH.
    """
    body = await request.json()
    noga          = body.get("noga_code","").strip()
    canton        = (body.get("canton") or "").upper()
    ijm_rate      = body.get("ijm_rate")
    ijm_carence   = body.get("ijm_carence_days")
    ijm_coverage  = body.get("ijm_coverage_days")
    laa_rate      = body.get("laa_rate")
    laa_carence   = body.get("laa_carence_days")
    salary_hourly = body.get("salary_hourly")
    salary_monthly= body.get("salary_monthly")

    issues = []
    warnings = []

    async with pool.acquire() as conn:
        # Get CCT by NOGA
        cct = None
        if noga:
            cct = await conn.fetchrow(
                "SELECT * FROM cct WHERE $1 = ANY(noga_codes) LIMIT 1", noga
            )

        # Get cantonal minimum
        cantonal = None
        if canton:
            cantonal = await conn.fetchrow("""
                SELECT min_hourly, legal_basis FROM cantonal_salary_minimums
                WHERE canton=$1 AND valid_from<=CURRENT_DATE
                  AND (valid_to IS NULL OR valid_to>=CURRENT_DATE)
                ORDER BY valid_from DESC LIMIT 1
            """, canton)

    # ── IJM checks ────────────────────────────────────────────────────
    if cct and cct["ijm_min_rate"]:
        if ijm_rate is not None and ijm_rate < cct["ijm_min_rate"]:
            issues.append({
                "type": "ijm_rate_too_low",
                "severity": "critical",
                "message": f"Taux IJM {ijm_rate}% inférieur au minimum CCT ({cct['ijm_min_rate']}%)",
                "legal_basis": cct["name"],
                "required": cct["ijm_min_rate"],
                "current": ijm_rate
            })

        if ijm_carence is not None and cct["ijm_max_carence_days"] is not None:
            if ijm_carence > cct["ijm_max_carence_days"]:
                issues.append({
                    "type": "ijm_carence_too_long",
                    "severity": "warning",
                    "message": f"Délai de carence IJM {ijm_carence}j dépasse le maximum CCT ({cct['ijm_max_carence_days']}j)",
                    "legal_basis": cct["name"],
                    "max_allowed": cct["ijm_max_carence_days"],
                    "current": ijm_carence
                })

        if ijm_coverage is not None and cct["ijm_min_coverage_days"] is not None:
            if ijm_coverage < cct["ijm_min_coverage_days"]:
                issues.append({
                    "type": "ijm_coverage_too_short",
                    "severity": "critical",
                    "message": f"Durée couverture IJM {ijm_coverage}j inférieure au minimum CCT ({cct['ijm_min_coverage_days']}j)",
                    "legal_basis": cct["name"],
                    "required": cct["ijm_min_coverage_days"],
                    "current": ijm_coverage
                })

        if cct["ijm_employer_topup"] and ijm_rate and ijm_rate < (cct["ijm_topup_to"] or 100):
            warnings.append({
                "type": "ijm_topup_required",
                "severity": "warning",
                "message": f"La CCT exige que l'employeur complète l'IJM jusqu'à {cct['ijm_topup_to'] or 100}% du salaire",
                "legal_basis": cct["name"]
            })

    # ── LAA checks ────────────────────────────────────────────────────
    if cct and cct["laa_min_rate"]:
        if laa_rate is not None and laa_rate < cct["laa_min_rate"]:
            issues.append({
                "type": "laa_rate_too_low",
                "severity": "critical",
                "message": f"Taux LAA {laa_rate}% inférieur au minimum CCT ({cct['laa_min_rate']}%)",
                "legal_basis": cct["name"],
                "required": cct["laa_min_rate"],
                "current": laa_rate
            })

        if laa_carence is not None and cct["laa_max_carence_days"] is not None:
            if laa_carence > cct["laa_max_carence_days"]:
                issues.append({
                    "type": "laa_carence_too_long",
                    "severity": "critical",
                    "message": f"Carence LAA {laa_carence}j supérieure au maximum CCT ({cct['laa_max_carence_days']}j) — SUVA couvre dès J+0",
                    "legal_basis": cct["name"]
                })

        if cct["laa_complementaire_required"]:
            warnings.append({
                "type": "laac_required",
                "severity": "warning",
                "message": "La CCT exige une assurance accidents complémentaire (LAAC)",
                "legal_basis": cct["name"]
            })

    # ── Salary checks ─────────────────────────────────────────────────
    canton_min = float(cantonal["min_hourly"]) if cantonal else None
    cct_min_h  = float(cct["salary_min_hourly"]) if cct and cct["salary_min_hourly"] else None
    cct_min_m  = float(cct["salary_min_monthly"]) if cct and cct["salary_min_monthly"] else None
    ref_hourly = max([x for x in [canton_min, cct_min_h] if x is not None], default=None)

    if salary_hourly and ref_hourly and salary_hourly < ref_hourly:
        basis = (cct["name"] if cct_min_h and cct_min_h >= (canton_min or 0) else cantonal["legal_basis"]) if (cct or cantonal) else "CCT"
        issues.append({
            "type": "salary_below_minimum",
            "severity": "critical",
            "message": f"Salaire horaire CHF {salary_hourly:.2f} inférieur au minimum applicable (CHF {ref_hourly:.2f}/h)",
            "legal_basis": basis,
            "required": ref_hourly,
            "current": salary_hourly,
            "gap": round(ref_hourly - salary_hourly, 2)
        })

    if salary_monthly and cct_min_m and salary_monthly < cct_min_m:
        issues.append({
            "type": "monthly_below_minimum",
            "severity": "critical",
            "message": f"Salaire mensuel CHF {salary_monthly:.2f} inférieur au minimum CCT (CHF {cct_min_m:.2f}/mois)",
            "legal_basis": cct["name"] if cct else "CCT",
            "required": cct_min_m,
            "current": salary_monthly,
            "gap": round(cct_min_m - salary_monthly, 2)
        })

    all_issues = issues + warnings
    status = "compliant" if not issues else "non_compliant"
    if not issues and warnings:
        status = "compliant_with_warnings"

    return JSONResponse({
        "status": status,
        "cct_found": bool(cct),
        "cct_name": cct["name"] if cct else None,
        "canton": canton,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "critical": len(issues),
            "warnings": len(warnings),
            "checks_performed": len([x for x in [ijm_rate, ijm_carence, laa_rate, salary_hourly, salary_monthly] if x is not None])
        }
    })


# ── GET /api/cct/ccnt-contribution-rules ──────────────────────────────
# Règles de cotisation CCNT Hôtels/Restaurants/Cafés
# Source: CCNT art. 43 — frais d'exécution et formation
# SwissRH appelle cet endpoint pour calculer la déclaration annuelle
@router.get("/ccnt-contribution-rules")
async def ccnt_contribution_rules():
    """
    Retourne les règles de calcul des cotisations CCNT (HRC).
    Utilisé par SwissRH pour générer automatiquement la déclaration annuelle.
    """
    # ⚠️  DEPRECATED — utiliser /api/cct/paritaire-rules?rs_number=221.215.329.4
    # Maintenu pour backward compatibility SwissRH < v2025-06
    return {
        "cct": "CCNT Hôtels, Restaurants et Cafés",
        "_deprecated": True,
        "_successor": "/api/cct/paritaire-rules?rs_number=221.215.329.4",
        "_note": "Ce endpoint est maintenu pour compatibilité. Migrez vers /api/cct/paritaire-rules.",
        "rs_number": "221.131",
        "version": "2025",
        "emetteur": "CCNT · Dufourstrasse 23 · Case postale 357 · 4010 Bâle",
        "contact": "info@ccnt.ch · www.ccnt.ch",
        "invoice_number_formula": "{ccnt_etablissement_number}0{year}{seq_padded_2}",
        "employer_contribution_rate": 0.3333,  # 1/3 du total collaborateurs
        "tva_rate": 0.04,  # 4% TVA si applicable (ligne /4.00%)
        "roles": {
            "soumis": {
                "label": "Collaborateur soumis à la CCNT",
                "rules": [
                    {"duration_min_months": 1, "duration_max_months": 6, "amount_chf": 49.50},
                    {"duration_min_months": 7, "duration_max_months": 12, "amount_chf": 99.00},
                ]
            },
            "chef_etablissement": {
                "label": "Chef d'établissement / Directeur",
                "rules": [
                    {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00}
                ]
            },
            "apprenti": {
                "label": "Apprenti",
                "rules": [
                    {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00}
                ]
            },
            "exclu": {
                "label": "Exclu du champ d'application",
                "rules": [
                    {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00}
                ]
            }
        },
        "logic": (
            "1. Calculer la durée d'engagement en mois pour l'année déclarée. "
            "2. Appliquer le montant selon la tranche (1-6 mois = 49.50 CHF, 7-12 mois = 99.00 CHF). "
            "3. Les chefs d'établissement, directeurs, apprentis et exclus = 0.00 CHF. "
            "4. Total collaborateurs = somme des montants individuels. "
            "5. Contribution établissement = Total collaborateurs / 3 (arrondi au centime). "
            "6. Total à verser = Total collaborateurs + Contribution établissement. "
            "7. Numéro facture = ccnt_etablissement_number + '0' + année + séquence (01)."
        )
    }
