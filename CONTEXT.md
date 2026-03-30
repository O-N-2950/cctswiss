# CCTswiss.ch — Context Projet (v3)
*Dernière mise à jour: 2026-03-31 — commit 68e60bf*

---

## URLs Production

| URL | Statut |
|---|---|
| https://cctswiss.ch | ✅ Live (custom domain SSL Railway) |
| https://www.cctswiss.ch | ✅ Live |
| https://mellow-adaptation-production-a073.up.railway.app | Railway direct |

- **GitHub**: https://github.com/O-N-2950/cctswiss (commit: `68e60bf`)
- **Railway projet**: `952d4452` · Service live: `f9832aee` · Postgres: `a949c443`
- **Infomaniak domaine ID**: `2119347`

---

## Architecture

```
FastAPI (Python 3.11) + PostgreSQL on Railway
Frontend: HTML/CSS/JS — Swiss Brutalist Editorial
  - Fonts: Bebas Neue (display) + Instrument Serif (italic) + DM Sans + DM Mono
  - Design: dark hero full-bleed, bande stats rouge, grille cards
  - Mobile-first: bottom nav, swipe sheet, safe-area iOS
  - 11 langues: FR DE IT EN PT ES SQ BS TR UK + RM
Auto-updater: Fedlex SPARQL chaque nuit à 02:00 CET
```

---

## Variables Railway (service live)

```
DATABASE_URL   postgresql://cctswiss:{PW}@postgres.railway.internal:5432/cctswiss
PORT           8000
SEED_SECRET    cctswiss-neo-seed-2025
ANTHROPIC_API_KEY  (depuis Soluris projet d03ee6e4, service ab5f76b2)
```

---

## Structure fichiers

```
backend/
  main.py                ← FastAPI app, lifespan, routers montés
  db/schema.py           ← Tables + 30+ migrations additives
  routers/
    cct.py               ← /api/cct/ + dfo-list + by-noga + check-compliance
                            + ccnt-contribution-rules (backward compat)
    paritaire.py         ← /api/cct/paritaire-rules + /paritaire-list  ← NOUVEAU
    salary.py            ← /api/salary/minimums + /check
    search.py            ← /api/search/?q=
    admin.py             ← /api/admin/seed + init + fix-data + seed-paritaire
    noga_seed.py         ← /api/admin/seed-enriched (NOGA+IJM+LAA)
    seed.py              ← /api/admin/seed-full (29 CCTs DFO)
    compliance.py        ← compliance router (monté /api/v2, non utilisé production)
    health.py            ← /health
    changelog.py
  scrapers/auto_updater.py  ← Fedlex SPARQL + APScheduler
  services/rate_limiter.py  ← 100 req/min par IP
frontend/index.html      ← SPA complète (1224 lignes)
```

---

## Base de données

### Table `cct`
- **41 CCTs** total | **36 DFO** | 0 records brisés
- Colonnes clés: `rs_number`, `name` (+ 10 traductions), `branch`, `emoji`,
  `is_dfo`, `dfo`, `noga_codes TEXT[]`, `salary_min_hourly`, `salary_min_monthly`,
  `salary_min_by_category JSONB`, `ijm_min_rate`, `laa_min_rate`,
  **`paritaire_contribution JSONB`** ← ajouté 2026-03-31
- Index GIN sur `noga_codes` + `paritaire_contribution`

### Table `cantonal_salary_minimums`
9 cantons avec minimum 2026 :
GE 24.32 · VD 21.23 · NE 21.09 · BS/JU 21.00 · SO 20.00 · FR 19.85 · VS 19.30 · TI 19.00 CHF/h

### Cotisations paritaires peuplées (`paritaire_contribution`)
| rs_number | CCT | Type | Détail |
|---|---|---|---|
| 221.215.329.4 | CCNT HRC | `forfait_per_employee` | 49.50/99.00 CHF · topup 1/3 établissement |
| 221.215.329.6 | Nettoyage | `percent_avs` | 0.7% masse AVS → CPPREN (Romandie) |
| 822.22 | Construction CN | `external` | SUVA + FAR 3% — pas de calcul SwissRH |
| second_oeuvre_romand | SOR | `percent_avs` | 2.5% paritaire → RESOR *(rs_number à confirmer)* |

---

## API — Endpoints complets

### Publics (rate limit: 100 req/min/IP)

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/cct/` | Liste CCTs (filtres: branch, canton, is_dfo) |
| GET | `/api/cct/branches` | Branches disponibles |
| GET | `/api/cct/status` | Statut auto-update + total |
| GET | `/api/cct/dfo-list` | DFO avec NOGA codes + salaires |
| GET | `/api/cct/by-noga/:code` | CCT complète par NOGA → WIN WIN, SwissRH |
| POST | `/api/cct/check-compliance` | Vérif IJM/LAA/salaires |
| GET | `/api/cct/:rs_number` | Détail d'une CCT |
| **GET** | **`/api/cct/paritaire-rules?rs_number=`** | **Cotisations paritaires → SwissRH** |
| **GET** | **`/api/cct/paritaire-list`** | **Toutes CCTs avec cotisations** |
| GET | `/api/cct/ccnt-contribution-rules` | ⚠️ Deprecated → voir paritaire-rules |
| GET | `/api/salary/minimums` | 9 cantons avec minimum légal |
| GET | `/api/salary/minimums/:canton` | Minimum d'un canton (null si absent) |
| POST | `/api/salary/check` | Vérif salaire vs max(cantonal, CCT) |
| GET | `/api/search/?q=` | Recherche full-text multilingue |
| GET | `/api/docs` | Swagger UI |
| GET | `/health` | Santé + total CCTs |

### Admin (header: `X-Seed-Secret: cctswiss-neo-seed-2025`)

| Route | Description |
|---|---|
| POST `/api/admin/init` | **Init complète atomique en 1 appel** ← à utiliser sur nouveau service |
| POST `/api/admin/seed` | 10 CCTs enrichis + traduits (admin.py) |
| POST `/api/admin/seed-full` | 29 CCTs DFO (seed.py) |
| POST `/api/admin/seed-enriched` | NOGA + IJM + LAA + Salaires |
| POST `/api/admin/seed-paritaire` | Cotisations paritaires en DB ← NOUVEAU |
| POST `/api/admin/translate-ai` | Traductions Claude API |
| POST `/api/admin/fix-data` | Répare noms/emojis corrompus |
| GET  `/api/admin/stats` | Stats DB (total, DFO, branches) |
| POST `/api/admin/reset` | Vide la table cct |

---

## Format `paritaire_contribution` (JSONB normalisé)

```json
// type: forfait_per_employee (CCNT HRC)
{
  "type": "forfait_per_employee",
  "beneficiary": "CCNT",
  "employer_share_ratio": 0.3333,
  "tva_rate": 0.04,
  "invoice_formula": "{ccnt_etablissement_number}0{year}{seq_padded_2}",
  "rules": [
    {"duration_min_months": 1, "duration_max_months": 6,  "amount_chf": 49.50, "role": "soumis"},
    {"duration_min_months": 7, "duration_max_months": 12, "amount_chf": 99.00, "role": "soumis"},
    {"duration_min_months": 1, "duration_max_months": 12, "amount_chf": 0.00,  "role": "chef_etablissement"}
  ],
  "swissrh_calculator": "ccnt_hrc_v2025"
}

// type: percent_avs (Nettoyage/CPPREN)
{
  "type": "percent_avs",
  "rate": 0.007,
  "basis": "avs_mass",
  "beneficiary": "CPPREN",
  "split": {"employer": 1.0, "employee": 0.0},
  "swissrh_calculator": "cppren_nettoyage_v2025"
}

// type: external (Construction)
{
  "type": "external",
  "handler": "SUVA / FAR",
  "swissrh_calculator": null
}
```

---

## CORS autorisé

```
winwin.swiss, swissrh.ch, soluris.ch, cctswiss.ch, *.railway.app
localhost:3000, localhost:5173
```

---

## Partenaires intégrés (écosystème NEO)

| Partenaire | URL | Rôle |
|---|---|---|
| WIN WIN Finance | winwin.swiss | Assurances CCT — FINMA F01042365 |
| SwissRH | swissrh.ch | RH & salaires conformes CCT |
| Soluris.ch | soluris.ch | IA juridique suisse |
| Matcho | matcho.digital | Réconciliation bancaire |
| DevisPro | devispro.ch | Devis artisans CCT |
| Boom | boom.contact | Constat numérique 42 langues |
| Horlogis | horlogis.ch | Portail métiers horlogerie |

---

## Patterns Railway (critique)

```python
# Déploiement latest commit (TOUJOURS githubRepoDeploy, jamais serviceInstanceDeploy)
svc = githubRepoDeploy(projectId, environmentId, repo, branch)
variableCollectionUpsert(...)   # immédiatement après (< 3 secondes)
serviceDomainCreate(...)        # puis créer le domaine Railway
# Poll deployments jusqu'à SUCCESS

# Après chaque deploy : vérifier logs Railway
deploymentLogs(deploymentId, limit=30)

# Sur un nouveau service vide :
POST /api/admin/init          # seed tout en 1 appel
POST /api/admin/seed-paritaire  # cotisations paritaires
```

---

## Bugs connus résolus

| Bug | Fix | Commit |
|---|---|---|
| `.hero-badge span {display:block}` → texte flottant iOS | `.live-dot` class dédiée | `745affe` |
| Route `/api/cct/dfo-list` capturée par `/{rs_number}` | Ordre routes FastAPI | `8ff280d` |
| `noga_seed.py` fallback INSERT avec nom `CCT {rs_number}` | Supprimé, `/init` atomique | `a813259` |
| `ccnt-contribution-rules` → 404 après refacto | Remis dans `cct.py` avant `/{rs_number}` | `68e60bf` |
| Lang pills 2 lignes sur iPhone | `flex-wrap:nowrap` + scroll | `745affe` |
