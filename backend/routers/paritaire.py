"""
CCTswiss — /api/cct/paritaire-rules
Source de vérité: cotisations paritaires obligatoires par CCT.

Utilisé par SwissRH pour calculer les déductions et générer les déclarations.

Types supportés:
  - forfait_per_employee : montant fixe par employé selon durée d'engagement
  - percent_avs          : pourcentage de la masse salariale AVS
  - external             : calcul géré par organisme externe (SUVA, RESOR…)
  - null                 : pas de cotisation paritaire pour cette CCT
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
import asyncpg, json as _json

router = APIRouter()

def get_pool(r: Request): return r.app.state.pool


# ── Format JSON normalisé des cotisations ────────────────────────────
#
# type: forfait_per_employee
# {
#   "type": "forfait_per_employee",
#   "beneficiary": "CCNT",
#   "beneficiary_full": "Commission paritaire nationale Hôtels/Restaurants/Cafés",
#   "url": "www.ccnt.ch",
#   "contact": "info@ccnt.ch",
#   "employer_share_ratio": 0.3333,   # employeur paie 1/3 du total employés
#   "tva_rate": 0.04,
#   "invoice_formula": "{ccnt_no}0{year}{seq2}",
#   "rules": [
#     {"duration_min_months": 1, "duration_max_months": 6,  "amount_chf": 49.50, "role": "soumis"},
#     {"duration_min_months": 7, "duration_max_months": 12, "amount_chf": 99.00, "role": "soumis"},
#     {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00,  "role": "chef_etablissement"},
#     {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00,  "role": "apprenti"},
#     {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00,  "role": "exclu"}
#   ]
# }
#
# type: percent_avs
# {
#   "type": "percent_avs",
#   "rate": 0.007,         # 0.7%
#   "basis": "avs_mass",   # assiette = masse salariale AVS
#   "beneficiary": "CPPREN",
#   "beneficiary_full": "Caisse de perfectionnement du personnel ...",
#   "url": "www.cppren.ch",
#   "split": {"employer": 0.5, "employee": 0.5},   # partage employeur/employé
#   "notes": "..."
# }
#
# type: external
# {
#   "type": "external",
#   "handler": "SUVA",       # organisme gestionnaire
#   "notes": "Cotisation LAA/SUVA gérée directement — pas de calcul SwissRH"
# }

# ── Données canoniques (source de vérité) ────────────────────────────
PARITAIRE_DATA = {
    # CCNT HRC — RS 221.131 / rs_number 221.215.329.4
    "221.215.329.4": {
        "type": "forfait_per_employee",
        "rs_number": "221.215.329.4",
        "cct_name": "CCNT Hôtels, Restaurants et Cafés (L-GAV)",
        "beneficiary": "CCNT",
        "beneficiary_full": "Commission paritaire nationale des hôtels, restaurants et cafés",
        "address": "Dufourstrasse 23, Case postale 357, 4010 Bâle",
        "contact": "info@ccnt.ch",
        "url": "www.ccnt.ch",
        "employer_share_ratio": 0.3333,
        "tva_rate": 0.04,
        "invoice_formula": "{ccnt_etablissement_number}0{year}{seq_padded_2}",
        "rules": [
            {"duration_min_months": 1,  "duration_max_months": 6,  "amount_chf": 49.50, "role": "soumis",            "label": "Collaborateur 1–6 mois"},
            {"duration_min_months": 7,  "duration_max_months": 12, "amount_chf": 99.00, "role": "soumis",            "label": "Collaborateur 7–12 mois"},
            {"duration_min_months": 1,  "duration_max_months": 12, "amount_chf": 0.00,  "role": "chef_etablissement","label": "Chef d'établissement / Directeur"},
            {"duration_min_months": 1,  "duration_max_months": 12, "amount_chf": 0.00,  "role": "apprenti",          "label": "Apprenti"},
            {"duration_min_months": 1,  "duration_max_months": 12, "amount_chf": 0.00,  "role": "exclu",             "label": "Exclu du champ d'application"},
        ],
        "logic": (
            "1. Calculer la durée d'engagement en mois entiers pour l'année déclarée. "
            "2. Appliquer le montant selon la tranche (1-6 mois = CHF 49.50, 7-12 mois = CHF 99.00). "
            "3. Chefs d'établissement, directeurs, apprentis, exclus = CHF 0.00. "
            "4. Total collaborateurs = somme des montants individuels. "
            "5. Contribution établissement = Total collaborateurs × 1/3 (arrondi au centime). "
            "6. Total à verser = Total collaborateurs + Contribution établissement. "
            "7. N° facture = ccnt_etablissement_number + '0' + année + séquence (01)."
        ),
        "legal_basis": "CCNT art. 43 — frais d'exécution et de formation",
        "frequency": "annual",
        "swissrh_calculator": "ccnt_hrc_v2025",
    },

    # Nettoyage — CCT Nettoyage et hygiène des bâtiments (CPPREN)
    "221.215.329.6": {
        "type": "percent_avs",
        "rs_number": "221.215.329.6",
        "cct_name": "CCT Nettoyage et hygiène des bâtiments",
        "rate": 0.007,
        "basis": "avs_mass",
        "beneficiary": "CPPREN",
        "beneficiary_full": "Caisse de perfectionnement du personnel du nettoyage en Romandie",
        "url": "www.cppren.ch",
        "split": {"employer": 1.0, "employee": 0.0},
        "cantons": ["GE", "VD", "VS", "NE", "FR", "JU", "BE"],
        "notes": (
            "0.7% de la masse salariale AVS des collaborateurs soumis à la CCT Nettoyage (Romandie). "
            "Contribution employeur uniquement. Versement trimestriel à CPPREN."
        ),
        "legal_basis": "CCT Nettoyage art. 28 — Formation professionnelle",
        "frequency": "quarterly",
        "swissrh_calculator": "cppren_nettoyage_v2025",
    },

    # Second-œuvre romand (SOR/RESOR)
    # rs_number: à confirmer — utiliser le rs_number de la CCT second-œuvre
    "second_oeuvre_romand": {
        "type": "percent_avs",
        "rs_number": "second_oeuvre_romand",
        "cct_name": "CCT Second-œuvre romand (SOR)",
        "rate": 0.025,
        "basis": "avs_mass",
        "beneficiary": "RESOR",
        "beneficiary_full": "Caisse de retraite et de prévoyance du second-œuvre romand",
        "url": "www.resor.ch",
        "split": {"employer": 0.50, "employee": 0.50},
        "notes": (
            "2.5% paritaire de la masse salariale AVS (employeur 50% + employé 50%). "
            "S'applique aux cantons romands: GE, VD, VS, NE, FR, JU, BE (partiellement)."
        ),
        "legal_basis": "CCT Second-œuvre romand — contributions paritaires",
        "frequency": "monthly",
        "swissrh_calculator": "resor_sor_v2025",
    },

    # Construction — CN 822.22 → via organismes externes
    "822.22": {
        "type": "external",
        "rs_number": "822.22",
        "cct_name": "Convention nationale du principal (CN) — Construction",
        "handler": "SUVA / RESOR",
        "handlers": [
            {
                "name": "SUVA",
                "type": "laa_accident",
                "url": "www.suva.ch",
                "notes": "LAA accidents professionnels et non-professionnels — gérée directement par SUVA. Tarification selon la branche construction.",
            },
            {
                "name": "RESOR / FAR",
                "type": "retraite_anticipee",
                "url": "www.far.ch",
                "notes": "FAR (Fonds de retraite anticipée) — cotisation 3% masse salariale brute, répartition 2/3 employeur + 1/3 employé.",
                "rate": 0.03,
                "split": {"employer": 0.6667, "employee": 0.3333},
            },
        ],
        "notes": (
            "Les cotisations paritaires de la construction sont gérées par des organismes spécialisés (SUVA, FAR). "
            "SwissRH ne calcule pas ces cotisations directement. "
            "Contacter la SBI (Société suisse des entrepreneurs) pour les détails."
        ),
        "swissrh_calculator": None,
        "url": "www.baumeister.swiss",
    },
}


# ── GET /api/cct/paritaire-rules ─────────────────────────────────────
@router.get("/paritaire-rules")
async def paritaire_rules(
    rs_number: str = Query(..., description="Numéro RS de la CCT (ex: 221.215.329.4)"),
    pool: asyncpg.Pool = Depends(get_pool),
):
    """
    Retourne les règles de cotisations paritaires pour une CCT donnée.
    
    Utilisé par SwissRH pour:
    - Calculer les déductions paritaires lors de l'établissement des salaires
    - Générer les déclarations annuelles (ex: formulaire CCNT)
    - Vérifier la conformité des contributions
    
    Réponse:
    - data_source: "db" si données en DB, "builtin" si hardcodé, "not_found" si absent
    - paritaire_contribution: null si aucune cotisation paritaire pour cette CCT
    """
    # 1. Check DB first (live data, updateable)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT rs_number, name, paritaire_contribution FROM cct WHERE rs_number = $1",
            rs_number
        )

    if not row:
        return JSONResponse({
            "rs_number": rs_number,
            "cct_found": False,
            "paritaire_contribution": None,
            "data_source": "not_found",
            "message": f"CCT '{rs_number}' non trouvée dans la base de données."
        }, status_code=404)

    # Parse DB JSONB
    db_contribution = None
    if row["paritaire_contribution"]:
        try:
            raw = row["paritaire_contribution"]
            db_contribution = _json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            pass

    # 2. Fallback to built-in canonical data
    builtin = PARITAIRE_DATA.get(rs_number)

    contribution = db_contribution or builtin
    data_source = "db" if db_contribution else ("builtin" if builtin else "none")

    return JSONResponse({
        "rs_number": rs_number,
        "cct_found": True,
        "cct_name": row["name"],
        "paritaire_contribution": contribution,
        "data_source": data_source,
        "has_contribution": contribution is not None,
        "swissrh_compatible": (
            contribution is not None and
            contribution.get("type") in ("forfait_per_employee", "percent_avs") and
            contribution.get("swissrh_calculator") is not None
        ),
        "_meta": {
            "doc": "https://cctswiss.ch/api/docs#/paritaire",
            "contact": "swissrh@neo.ch",
        }
    })


# ── GET /api/cct/paritaire-list ──────────────────────────────────────
@router.get("/paritaire-list")
async def paritaire_list(pool: asyncpg.Pool = Depends(get_pool)):
    """
    Liste toutes les CCTs qui ont des cotisations paritaires définies.
    Utile pour SwissRH pour savoir quelles CCTs nécessitent un traitement spécial.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT rs_number, name, branch, emoji, paritaire_contribution
            FROM cct
            WHERE paritaire_contribution IS NOT NULL
            ORDER BY name
        """)

    # Merge with built-in (for CCTs in builtin but not yet in DB)
    db_rs = {r["rs_number"] for r in rows}
    result = []

    for row in rows:
        try:
            raw = row["paritaire_contribution"]
            contrib = _json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            contrib = None
        result.append({
            "rs_number": row["rs_number"],
            "name": row["name"],
            "branch": row["branch"],
            "emoji": row["emoji"],
            "contribution_type": contrib.get("type") if contrib else None,
            "beneficiary": contrib.get("beneficiary") if contrib else None,
            "swissrh_calculator": contrib.get("swissrh_calculator") if contrib else None,
        })

    # Add built-in entries not yet in DB
    for rs, contrib in PARITAIRE_DATA.items():
        if rs not in db_rs:
            result.append({
                "rs_number": rs,
                "name": contrib.get("cct_name"),
                "branch": None,
                "emoji": None,
                "contribution_type": contrib.get("type"),
                "beneficiary": contrib.get("beneficiary") or contrib.get("handler"),
                "swissrh_calculator": contrib.get("swissrh_calculator"),
                "_note": "builtin_not_in_db",
            })

    return JSONResponse({
        "total": len(result),
        "data": result,
    })
