# CCTswiss.ch — Context Projet (v2)

## URLs Production
- **cctswiss.ch** (custom domain — SSL Railway)
- **responsible-trust-production-56a7.up.railway.app** (Railway direct)
- **GitHub**: https://github.com/O-N-2950/cctswiss (commit: a813259+)

## Architecture
- FastAPI (Python 3.11) + PostgreSQL sur Railway
- Frontend mobile-first (11 langues, bottom nav, search temps réel, print/share)
- Auto-updater Fedlex SPARQL chaque nuit 02:00 CET

## API v2 — Source de vérité NEO

### Endpoints publics
| Méthode | Route | Description |
|---|---|---|
| GET | /api/cct/ | Liste CCTs (filtres branch, canton, is_dfo) |
| GET | /api/cct/dfo-list | Tous DFO avec NOGA, salaires |
| GET | /api/cct/by-noga/:code | CCT complète par NOGA → WIN WIN, SwissRH |
| POST | /api/cct/check-compliance | Vérif IJM/LAA/salaires |
| GET | /api/salary/minimums | 9 cantons avec minimum 2026 |
| GET | /api/salary/minimums/:canton | Min d'un canton |
| POST | /api/salary/check | Vérif salaire vs min (cantonal + CCT) |
| GET | /api/search/?q= | Recherche full-text |

### Admin (SEED_SECRET: cctswiss-neo-seed-2025)
| Route | Description |
|---|---|
| POST /api/admin/init | Init complète en 1 appel (recommandé) |
| POST /api/admin/seed | 10 CCTs enrichis + traduits |
| POST /api/admin/seed-full | 29 CCTs DFO supplémentaires |
| POST /api/admin/seed-enriched | NOGA + IJM + LAA + Salaires |
| POST /api/admin/translate | Traductions Claude API |
| POST /api/admin/fix-data | Répare noms/emojis corrompus |

## Base de données
- **41 CCTs** total (36 DFO)
- **9 cantons** avec salaire minimum légal (GE 24.32, VD 21.23, NE 21.09...)
- **11 langues**: FR DE IT RM EN PT ES SQ BS TR UK
- Auto-updater: Fedlex SPARQL + SECO + L-GAV (nuit 02:00 CET)

## Données enrichies (10 CCTs)
Restauration, Construction, Nettoyage x2, MEM, Coiffure, Horlogerie, Intérim, Sécurité, Boulangerie
- NOGA codes, IJM (taux, carence, topup), LAA, CO 324a
- Salaires minimums par catégorie

## Variables Railway
- DATABASE_URL: postgresql://cctswiss:{PW}@postgres.railway.internal:5432/cctswiss
- PORT: 8000
- SEED_SECRET: cctswiss-neo-seed-2025
- ANTHROPIC_API_KEY: (depuis Soluris)

## CORS autorisé
winwin.swiss, swissrh.ch, soluris.ch, cctswiss.ch, *.railway.app

## Partenaires intégrés
- WIN WIN Finance (winwin.swiss) — FINMA F01042365
- SwissRH (swissrh.ch) — RH & salaires
- Soluris.ch — IA juridique
- Matcho, DevisPro, Boom, Horlogis, immo.cool
