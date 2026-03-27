# CCTswiss.ch — Contexte Projet

> Fichier mis à jour automatiquement à chaque session. Sert de mémoire persistante.

## 🎯 Vision

**CCTswiss.ch** = Le répertoire suisse de référence des conventions collectives de travail (CCT).
Gratuit, multilingue (11 langues), mis à jour automatiquement depuis Fedlex chaque nuit à 02:00 CET.

## 🏗️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Frontend | HTML/CSS/JS vanilla (Swiss Design) |
| Backend | FastAPI (Python 3.11) |
| Base de données | PostgreSQL (Railway) |
| Auto-updater | APScheduler (nuit 02:00 CET + dimanche 03:00) |
| Sources | Fedlex SPARQL + SECO + L-GAV |
| Hébergement | Railway |
| Domaine | cctswiss.ch (Infomaniak) |
| Repo | https://github.com/O-N-2950/cctswiss |

## 🌐 URLs

- **Production** : https://focused-enthusiasm-production-dc69.up.railway.app
- **Domaine** : https://cctswiss.ch (DNS propagation en cours)
- **API docs** : /api/docs
- **Health** : /health

## 🗃️ Base de données

- **29 CCTs DFO** chargées depuis SECO + 8 CCTs importantes (horlogerie, MEM, etc.)
- **37 CCTs total** en production
- Scheduler : nuit à 02:00 CET (Fedlex SPARQL) + dimanche 03:00 (vérification profonde)

## 🌍 Langues implémentées (11)

FR · DE · IT · RM · EN · PT · ES · SQ (albanais) · BS (BCMS) · TR (turc) · UA (ukrainien)

Logique : les communautés étrangères en Suisse (albanais, BCMS, turcs, ukrainiens) sont sur-représentées dans les branches soumises aux CCT → accès à l'info dans leur langue = enjeu social fort.

## 🔗 Écosystème Groupe NEO intégré

- SwissRH (swissrh.ch) — gestion RH/salaires conformes CCT
- WinWin Finance (winwin.swiss) — assurances obligatoires CCT
- Matcho.digital — réconciliation bancaire
- DevisPro.ch (devispro.ch) — devis artisans avec coûts CCT
- Boom.contact — constats amiables numériques
- Horlogis.ch — portail horlogerie
- **Soluris.ch** — IA juridique suisse (lien dans nav + footer)

## 📁 Structure

```
cctswiss/
├── Dockerfile           ← Python 3.11-slim, explicit COPY
├── railway.toml         ← healthcheck /health, ON_FAILURE restart
├── requirements.txt
├── backend/
│   ├── main.py          ← FastAPI + lifespan + scheduler
│   ├── db/schema.py     ← PostgreSQL + migrations
│   ├── routers/
│   │   ├── cct.py       ← /api/cct/ CRUD
│   │   ├── search.py    ← /api/search/ full-text
│   │   ├── health.py    ← /health
│   │   ├── changelog.py ← /api/changelog/
│   │   └── seed.py      ← /api/admin/seed (secret)
│   └── scrapers/
│       └── auto_updater.py ← Fedlex SPARQL + SECO + L-GAV
└── frontend/
    └── index.html       ← Site complet 11 langues + API live
```

## 🔑 Variables Railway

- DATABASE_URL : postgresql://cctswiss:{PW}@postgres.railway.internal:5432/cctswiss
- PORT : 8000
- SEED_SECRET : cctswiss-neo-seed-2025

## ⚖️ Légalité

- Sources uniquement officielles (Fedlex, SECO, L-GAV)
- Disclaimer sur chaque page
- Changelog public et traçable
- Pas de conseil juridique — orientation seulement

## 🚨 Points d'attention

- Railway crée un nouveau service à chaque githubRepoDeploy → toujours vérifier le bon service
- Les domaines custom Railway sont limités — utiliser le domaine Railway.app + DNS Infomaniak
- L'auto-updater Fedlex : la query SPARQL utilise jolux:Act + schema:name — les CCTs DFO ne sont pas toutes dans Fedlex RS, certaines sont dans le FGA
