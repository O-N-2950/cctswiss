"""
CCTswiss — /api/admin/seed-enriched
Source de vérité NOGA + IJM + LAA + Salaires minimums

rs_numbers = ceux de admin.py (source officielle)
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import os, json
from datetime import date

router = APIRouter()
SEED_SECRET = os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")

def _d(s):
    """Convert 'YYYY-MM-DD' string to date."""
    if not s: return None
    p = s.split("-")
    return date(int(p[0]), int(p[1]), int(p[2]))

# ─────────────────────────────────────────────────────────────────────────
# DATASET ENRICHI — rs_numbers = ceux de admin.py
# Chaque entrée est un UPDATE additionnel sur les colonnes enrichies
# ─────────────────────────────────────────────────────────────────────────
ENRICHED = [
    # ── Restauration / Hôtellerie ─────────────────────────────────────
    {
        "rs": "221.215.329.4",          # CCNT Hôtellerie-restauration (L-GAV)
        "noga_codes": ["5610","5621","5629","5630","5510","5520","5530","5590"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "1999-01-01",
        "voluntary_only": False,
        # IJM : L-GAV art. 20 — carence 1 jour (J+2 effectivement)
        "ijm_min_rate": 80, "ijm_max_carence_days": 1,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        # LAA SUVA J+0
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        # CO 324a référence
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        # Salaires L-GAV 2025
        "salary_min_hourly": 22.42,
        "salary_min_monthly": 3880.0,
        "salary_min_by_category": {
            "sans_formation_1an": 3880,
            "sans_formation_5ans": 4070,
            "avec_cfc": 4420,
            "chef_de_rang": 4640,
            "chef_cuisine": 5200,
            "note": "L-GAV 2025 — vérifier annexe salariale annuelle"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Construction ─────────────────────────────────────────────────
    {
        "rs": "822.22",                 # CN secteur principal construction
        "noga_codes": ["4120","4211","4212","4213","4221","4291",
                       "4311","4312","4321","4322","4329","4331","4332","4333","4339","4391"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "1941-01-01",
        "voluntary_only": False,
        # IJM : CN art. 44 — carence 4 jours
        "ijm_min_rate": 80, "ijm_max_carence_days": 4,
        "ijm_min_coverage_days": 730,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        # CN 2025 — taux horaires 41.5h/semaine
        "salary_min_hourly": 30.64,
        "salary_min_monthly": 5300.0,
        "salary_min_by_category": {
            "manoeuvre_cat_A": 30.64,
            "ouvrier_qualifie_cat_B": 33.44,
            "chef_equipe_cat_C": 36.09,
            "chef_groupe_cat_D": 38.40,
            "contremaitre": 42.00,
            "note": "CN 2025 — taux horaires, 41.5h/semaine"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Nettoyage ────────────────────────────────────────────────────
    {
        "rs": "221.215.329.6",          # CCT Nettoyage et hygiène des bâtiments
        "noga_codes": ["8121","8122","8129"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "2004-01-01",
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": False, "ijm_topup_to": 80,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        # IMPORTANT: secteur à risque de sous-rémunération
        "salary_min_hourly": 19.50,
        "salary_min_monthly": None,
        "salary_min_by_category": {
            "categorie_A_sans_formation": 19.50,
            "categorie_B_avec_formation": 21.80,
            "categorie_C_qualification_sup": 24.20,
            "note": "CCT Nettoyage Suisse 2025 — secteur à risque sous-rémunération"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── MEM (Machines, Électronique, Métallurgie) ────────────────────
    {
        "rs": "221.215.329.1",
        "noga_codes": ["2511","2512","2521","2530","2540","2561","2562",
                       "2571","2572","2573","2591","2592","2593","2599",
                       "2611","2612","2619","2620","2630","2640",
                       "2711","2712","2731","2732","2733","2740",
                       "2811","2812","2813","2814","2815","2821","2822",
                       "2823","2824","2829","2891","2899","2910"],
        "dfo": False, "dfo_cantons": [], "dfo_since": None,
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 26.01,
        "salary_min_monthly": 4500.0,
        "salary_min_by_category": {
            "employe_sans_formation": 4500,
            "technicien_cfc": 5100,
            "ingenieur_technicien_hes": 5800,
            "note": "CCT MEM / Swissmem 2025"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Coiffure ─────────────────────────────────────────────────────
    {
        "rs": "221.215.329.3",
        "noga_codes": ["9602"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "2003-01-01",
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": False, "ijm_topup_to": 80,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 20.23,
        "salary_min_monthly": 3500.0,
        "salary_min_by_category": {
            "diplome_sans_experience": 3500,
            "avec_3ans_experience": 3850,
            "specialiste_chef_salon": 4200,
            "note": "CN Coiffure 2025"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Horlogerie ───────────────────────────────────────────────────
    {
        "rs": "221.215.329.7",
        "noga_codes": ["2652","2653","3212","3213"],
        "dfo": False, "dfo_cantons": [], "dfo_since": None,
        "voluntary_only": False,
        "membership_required": "Membre FH (Fédération Horlogère) ou CPIH",
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 23.70,
        "salary_min_monthly": 4100.0,
        "salary_min_by_category": {
            "technicien_cfc": 4100,
            "technicien_qualifie": 4850,
            "ingenieur_hes": 6200,
            "note": "CCT Horlogerie 2025 — Arc jurassien (JU, NE, BE, VD, SO, FR, GE)"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Location de services (intérim) ───────────────────────────────
    {
        "rs": "822.211",
        "noga_codes": ["7820","7830"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "2012-01-01",
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": False, "ijm_topup_to": 80,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 20.06,
        "salary_min_monthly": 3470.0,
        "salary_min_by_category": {
            "minimum_absolu_interim": 3470,
            "note": "Minimum absolu CCT Location de services 2025 — si aucune CCT de branche applicable"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Sécurité privée ──────────────────────────────────────────────
    {
        "rs": "221.215.329.10",
        "noga_codes": ["8010","8020"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "2009-01-01",
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": True,   # LAAC obligatoire
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 22.65,
        "salary_min_monthly": 3900.0,
        "salary_min_by_category": {
            "agent_securite_base": 3900,
            "agent_qualifie_brevet": 4280,
            "chef_equipe": 4760,
            "note": "CCT Sécurité 2025 — LAAC obligatoire par CCT"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Boulangerie ──────────────────────────────────────────────────
    {
        "rs": "221.215.329.8",
        "noga_codes": ["1071","1072","1073","4724"],
        "dfo": True, "dfo_cantons": [], "dfo_since": "2003-01-01",
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": True, "ijm_topup_to": 100,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 21.39,
        "salary_min_monthly": 3700.0,
        "salary_min_by_category": {
            "apprenti_diplome": 3700,
            "avec_experience_3ans": 4100,
            "chef_patissier": 4800,
            "note": "CCT Boulangerie-pâtisserie 2025"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": True,
    },
    # ── Commerce de détail alimentaire ───────────────────────────────
    {
        "rs": "221.215.329.9",
        "noga_codes": ["4711","4712","4721","4722","4723","4724","4725","4729"],
        "dfo": False, "dfo_cantons": [], "dfo_since": None,
        "voluntary_only": False,
        "ijm_min_rate": 80, "ijm_max_carence_days": 3,
        "ijm_min_coverage_days": 720,
        "ijm_employer_topup": False, "ijm_topup_to": 80,
        "laa_min_rate": 80, "laa_max_carence_days": 0,
        "laa_complementaire_required": False,
        "co324a_year1_days": 21, "co324a_year2_days": 56, "co324a_year5_days": 90,
        "salary_min_hourly": 20.81,
        "salary_min_monthly": 3600.0,
        "salary_min_by_category": {
            "employe_commerce": 3600,
            "chef_rayon": 4200,
            "note": "Indicatif 2025 — varie par enseigne (Migros, Coop, Denner)"
        },
        "salary_min_updated": "2025-01-01",
        "data_complete": False,   # données partielles — varie par enseigne
    },
]


@router.post("/seed-enriched")
async def seed_enriched(request: Request, x_seed_secret: str = Header(None)):
    """
    Charge les données enrichies NOGA/IJM/LAA/Salaires.
    UPDATE sur les rs_numbers existants en DB.
    Si absent: INSERT minimal puis UPDATE.
    """
    if x_seed_secret != SEED_SECRET:
        raise HTTPException(403, "Invalid seed secret")
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not ready")

    updated = 0
    inserted = 0
    errors = []

    async with pool.acquire() as conn:
        for d in ENRICHED:
            rs = d["rs"]
            try:
                # Check if exists
                exists = await conn.fetchval(
                    "SELECT COUNT(*) FROM cct WHERE rs_number=$1", rs
                )

                if not exists:
                    # Minimal INSERT if missing (shouldn't happen after /seed)
                    await conn.execute("""
                        INSERT INTO cct (rs_number, name, branch, is_dfo, content_hash)
                        VALUES ($1, $2, 'divers', $3, 'enriched-v2')
                        ON CONFLICT (rs_number) DO NOTHING
                    """, rs, f"CCT {rs}", d.get("dfo", False))
                    inserted += 1

                # UPDATE enriched fields
                by_cat = None
                if d.get("salary_min_by_category"):
                    by_cat = json.dumps(d["salary_min_by_category"], ensure_ascii=False)

                result = await conn.execute("""
                    UPDATE cct SET
                        noga_codes                  = $2,
                        dfo                         = $3,
                        dfo_cantons                 = $4,
                        dfo_since                   = $5,
                        voluntary_only              = $6,
                        membership_required         = $7,
                        ijm_min_rate                = $8,
                        ijm_max_carence_days        = $9,
                        ijm_min_coverage_days       = $10,
                        ijm_employer_topup          = $11,
                        ijm_topup_to                = $12,
                        laa_min_rate                = $13,
                        laa_max_carence_days        = $14,
                        laa_complementaire_required = $15,
                        co324a_year1_days           = $16,
                        co324a_year2_days           = $17,
                        co324a_year5_days           = $18,
                        salary_min_hourly           = $19,
                        salary_min_monthly          = $20,
                        salary_min_by_category      = $21::jsonb,
                        salary_min_updated          = $22,
                        data_complete               = $23,
                        is_dfo                      = $3,
                        updated_at                  = NOW()
                    WHERE rs_number = $1
                """,
                    rs,
                    d.get("noga_codes"),
                    d.get("dfo", False),
                    d.get("dfo_cantons") or [],
                    _d(d.get("dfo_since")),
                    d.get("voluntary_only", False),
                    d.get("membership_required"),
                    d.get("ijm_min_rate"),
                    d.get("ijm_max_carence_days"),
                    d.get("ijm_min_coverage_days"),
                    d.get("ijm_employer_topup", False),
                    d.get("ijm_topup_to"),
                    d.get("laa_min_rate"),
                    d.get("laa_max_carence_days"),
                    d.get("laa_complementaire_required", False),
                    d.get("co324a_year1_days"),
                    d.get("co324a_year2_days"),
                    d.get("co324a_year5_days"),
                    d.get("salary_min_hourly"),
                    d.get("salary_min_monthly"),
                    by_cat,
                    _d(d.get("salary_min_updated")),
                    d.get("data_complete", False),
                )
                rows = int(result.split()[-1])
                if rows > 0:
                    updated += 1
                else:
                    errors.append(f"{rs}: UPDATE matched 0 rows")

            except Exception as e:
                errors.append(f"{rs}: {str(e)[:150]}")

    return JSONResponse({
        "updated": updated,
        "inserted_missing": inserted,
        "errors": errors,
        "total_in_dataset": len(ENRICHED),
        "success": updated == len(ENRICHED),
    })
