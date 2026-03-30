# CCTswiss.ch — TODO
*Dernière mise à jour: 2026-03-31*

---

## 🔴 CRITIQUE (bloquant pour intégrations)

### SOR — Confirmer le rs_number du Second-œuvre romand
- Les données `second_oeuvre_romand` dans `paritaire.py` utilisent une clé provisoire
- Action : vérifier le rs_number officiel sur Fedlex → mettre à jour dans `paritaire.py` + re-seed
- Impact : SwissRH ne peut pas calculer RESOR sans ce rs_number

---

## 🟠 IMPORTANT (prochaine session)

### SwissRH — Migration vers `/api/cct/paritaire-rules`
- SwissRH doit migrer depuis `/api/cct/ccnt-contribution-rules` (deprecated)
- Nouveau call : `GET /api/cct/paritaire-rules?rs_number=221.215.329.4`
- L'ancien endpoint reste opérationnel mais signale `_deprecated: true`
- **Deadline suggérée** : avant v2025-06 SwissRH

### Nettoyage zombies Railway automatique
- Actuellement : nettoyage manuel après chaque deploy
- À faire : script de nettoyage automatique post-deploy dans `use-railway` skill

### Traductions — 31 CCTs seed.py non traduites
- 10 CCTs admin.py ont toutes les traductions (10 langues)
- 31 CCTs seed.py : uniquement FR + DE partiels
- Action : appeler `POST /api/admin/translate-ai` sur le service live
- Note : vérifier que la route `/translate-ai` fonctionne (était en conflit par le passé)

---

## 🟡 AMÉLIORATION (backlog)

### Cotisations paritaires manquantes
Les CCTs suivantes ont potentiellement des cotisations paritaires non encore documentées :
- [ ] **Boulangerie** (221.215.329.8) — vérifier FCPP / fonds formation
- [ ] **Coiffure** (221.215.329.3) — vérifier fonds branche
- [ ] **Horlogerie** (221.215.329.7) — vérifier CPIH / fonds formation
- [ ] **MEM / Swissmem** (221.215.329.1) — vérifier contributions paritaires
- [ ] **Sécurité privée** (221.215.329.10) — vérifier CPPSP

### Endpoint `/api/cct/paritaire-calculate`
- À créer : POST avec `{rs_number, employees: [{role, months}], year}`
- Retourne le calcul complet prêt pour SwissRH
- Évite que SwissRH re-implémente la logique de calcul

### Frontend — CCT detail URL propre
- Actuellement : `#cct-{rs_number}` (hash URL)
- Idéal : `/cct/{rs_number}` avec SSR ou redirection Railway
- Bénéfice : SEO + partage mobile plus propre

### Frontend — Page Cantons salaires minimaux
- Afficher les 9 cantons avec un graphique barres comparatif
- Source : `/api/salary/minimums`

### OpenGraph image dynamique
- `og:image` générique aujourd'hui
- Idéal : image générée par CCT (nom + salaire + emoji)

### Webhook Fedlex
- Aujourd'hui : polling SPARQL chaque nuit
- Idéal : webhook Fedlex → notification + re-scrape immédiat
- Fedlex ne propose pas encore de webhook public (à surveiller)

---

## ✅ FAIT — Historique des sessions

### Session 2026-03-31 (paritaires)
- [x] Migration `paritaire_contribution JSONB` dans schema.py
- [x] `GET /api/cct/paritaire-rules?rs_number=` (SwissRH source de vérité)
- [x] `GET /api/cct/paritaire-list`
- [x] `POST /api/admin/seed-paritaire`
- [x] CCNT HRC: `forfait_per_employee` (49.50/99.00 CHF)
- [x] Nettoyage/CPPREN: `percent_avs` 0.7%
- [x] Construction/CN: `external` SUVA+FAR
- [x] `/ccnt-contribution-rules` backward compat + `_deprecated` + `_successor`
- [x] Paritaire router monté AVANT cct.router (évite collision `/{rs_number}`)
- [x] DNS cctswiss.ch mis à jour · 4 zombies Railway supprimés

### Session 2026-03-30 (redesign + compliance)
- [x] Redesign complet : Swiss Brutalist Editorial (Bebas Neue + Instrument Serif)
- [x] Bug `.hero-badge span {display:block}` corrigé → `.live-dot` class
- [x] Lang pills 2 lignes → `flex-wrap:nowrap` scroll horizontal
- [x] `GET /api/cct/by-noga/:code` (WIN WIN + SwissRH)
- [x] `POST /api/cct/check-compliance` (IJM/LAA/salaires)
- [x] `GET /api/salary/minimums` + `POST /api/salary/check`
- [x] 9 cantons salaires minimums 2026 en DB
- [x] `POST /api/admin/init` — seed atomique en 1 appel
- [x] 41 CCTs · 36 DFO · 0 records brisés
- [x] Favicon SVG inline + OpenGraph meta

### Session 2026-03-29 (infrastructure v2)
- [x] Schema enrichi : NOGA codes, IJM, LAA, CO 324a, salaires/catégorie
- [x] 10 CCTs enrichies avec NOGA + IJM + LAA + salaires
- [x] Rate limiting 100 req/min par IP
- [x] Cache in-memory 24h + X-Cache header
- [x] CORS WIN WIN, SwissRH, Soluris, Railway
- [x] Auto-updater Fedlex SPARQL 02:00 CET
- [x] cctswiss.ch + www.cctswiss.ch SSL live

---

## 📋 POUR RÉFÉRENCE

### Commande init nouveau service
```bash
# Après githubRepoDeploy sur Railway :
curl -X POST https://{domain}/api/admin/init \
  -H "X-Seed-Secret: cctswiss-neo-seed-2025"

curl -X POST https://{domain}/api/admin/seed-paritaire \
  -H "X-Seed-Secret: cctswiss-neo-seed-2025"
```

### Test paritaire rapide
```bash
curl "https://cctswiss.ch/api/cct/paritaire-rules?rs_number=221.215.329.4"
curl "https://cctswiss.ch/api/cct/paritaire-list"
```

### Test régression complet
```bash
for ep in "/health" "/api/cct/" "/api/cct/dfo-list" \
          "/api/cct/by-noga/5610" "/api/salary/minimums/GE" \
          "/api/cct/paritaire-rules?rs_number=221.215.329.4" \
          "/api/cct/ccnt-contribution-rules"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://cctswiss.ch$ep")
  echo "$code $ep"
done
```
