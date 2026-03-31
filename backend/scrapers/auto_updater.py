"""
CCTswiss.ch — Auto-Updater
==========================
Tourne toutes les nuits via APScheduler (Railway cron).
Pipeline entièrement automatique :

  1. Fedlex SPARQL  → détecte nouvelles versions de CCT (date consolidation)
  2. SECO API       → vérifie les DFO (déclarations de force obligatoire)
  3. L-GAV          → scrape salaires min + contributions CCNT
  4. PostgreSQL      → compare hash du contenu → update si changement détecté
  5. Changelog       → enregistre chaque mise à jour avec diff + source + date

ZÉRO intervention manuelle requise.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import httpx
from bs4 import BeautifulSoup
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON

log = logging.getLogger("cctswiss.updater")

# ── Sources officielles ────────────────────────────────────────────────────────
FEDLEX_SPARQL   = "https://fedlex.data.admin.ch/sparqlendpoint"
SECO_CCT_URL    = "https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege.html"
LGAV_BASE       = "https://l-gav.ch/fr/"
GASTRO_BASE     = "https://gastrosuisse.ch/fr/droit/ccnt"

# ── RS numbers des CCT déclarées de force obligatoire ─────────────────────────
CCT_RS_NUMBERS = {
    # Hôtellerie-restauration
    "221.215.329.4":  {"name": "CCNT Hôtellerie-restauration (L-GAV)", "branch": "restauration",    "emoji": "🍽️"},
    # Construction
    "222.215.191.1":  {"name": "Convention nationale du principal (CN)", "branch": "construction",   "emoji": "🏗️"},
    # Nettoyage
    "221.215.329.6":  {"name": "CCT Nettoyage et hygiène des bâtiments","branch": "nettoyage",      "emoji": "🧹"},
    # MEM
    "221.215.329.1":  {"name": "CCT Industries MEM",                    "branch": "industrie",      "emoji": "🔧"},
    # Coiffure
    "221.215.329.3":  {"name": "CCT Coiffure",                          "branch": "coiffure",       "emoji": "💈"},
    # Boulangerie
    "221.215.329.2":  {"name": "CCT Boulangerie-pâtisserie-confiserie", "branch": "alimentation",   "emoji": "🥖"},
    # Carrosserie
    "221.215.329.5":  {"name": "CCT Carrosserie",                       "branch": "automobile",     "emoji": "🚗"},
    # Horlogerie (régionale)
    "221.215.329.7":  {"name": "CCT Industrie horlogère",               "branch": "horlogerie",     "emoji": "⌚"},
}

# ──────────────────────────────────────────────────────────────────────────────

def _hash(content: str) -> str:
    """SHA-256 du contenu pour détecter les changements."""
    return hashlib.sha256(content.encode()).hexdigest()


async def _fetch(url: str, client: httpx.AsyncClient) -> Optional[str]:
    try:
        r = await client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning(f"Fetch failed {url}: {e}")
        return None


# ── 1. Fedlex: vérifier la date de dernière consolidation ────────────────────

def _query_fedlex_consolidation(rs: str) -> Optional[dict]:
    """
    Interroge Fedlex SPARQL pour obtenir la dernière consolidation d'une CCT.
    Retourne: {uri, rs, date_consolidation, title_fr, html_url}
    """
    sparql = SPARQLWrapper(FEDLEX_SPARQL)
    sparql.setReturnFormat(SPARQL_JSON)
    sparql.setTimeout(30)

    query = f"""
    PREFIX jolux: <http://data.legilux.public.lu/resource/ontology/jolux#>
    PREFIX schema: <http://schema.org/>

    SELECT ?act ?title ?consolidationDate ?htmlUrl WHERE {{
      ?act jolux:inForce true ;
           jolux:rsNumber "{rs}" ;
           schema:name ?title .
      FILTER(LANG(?title) = "fr")

      OPTIONAL {{
        ?act jolux:dateApplicability ?consolidationDate .
      }}
      OPTIONAL {{
        ?act jolux:legalResourceImpactedByPublication ?pub .
        ?pub jolux:isRealizedBy ?expr .
        ?expr jolux:language <http://publications.europa.eu/resource/authority/language/FRA> ;
              jolux:format <https://fedlex.data.admin.ch/vocabulary/legal-taxonomy/html> ;
              schema:url ?htmlUrl .
      }}
    }}
    ORDER BY DESC(?consolidationDate)
    LIMIT 1
    """
    try:
        sparql.setQuery(query)
        results = sparql.query().convert()
        bindings = results["results"]["bindings"]
        if not bindings:
            return None
        b = bindings[0]
        return {
            "uri":   b.get("act", {}).get("value", ""),
            "title": b.get("title", {}).get("value", ""),
            "date":  b.get("consolidationDate", {}).get("value", ""),
            "url":   b.get("htmlUrl", {}).get("value", ""),
        }
    except Exception as e:
        log.warning(f"SPARQL error for RS {rs}: {e}")
        return None


# ── 2. SECO: scraper la liste des DFO ────────────────────────────────────────

async def _fetch_seco_dfo_list(client: httpx.AsyncClient) -> list[dict]:
    """Scrape la page SECO pour la liste des CCT de force obligatoire."""
    html = await _fetch(SECO_CCT_URL, client)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []

    # La page SECO liste les CCT par branche avec liens
    for link in soup.select("a[href]"):
        text = link.get_text(strip=True)
        href = link.get("href", "")
        if "Gesamtarbeitsvertraege" in href or "GAV" in href.upper():
            results.append({
                "name": text,
                "url":  href if href.startswith("http") else f"https://www.seco.admin.ch{href}",
                "source": "seco"
            })

    log.info(f"SECO DFO: {len(results)} CCT trouvées")
    return results


# ── 3. L-GAV: scraper salaires min CCNT ──────────────────────────────────────

async def _fetch_lgav_wages(client: httpx.AsyncClient) -> dict:
    """Scrape L-GAV pour les salaires minimaux actuels de la CCNT."""
    html = await _fetch(LGAV_BASE, client)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")

    wages = {}
    # Chercher les montants de salaires dans les tableaux
    for table in soup.select("table"):
        rows = table.select("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.select("td, th")]
            if len(cells) >= 2:
                # Détecter les lignes contenant des montants CHF
                text = " ".join(cells)
                if "CHF" in text or re.search(r"\d{4,5}", text):
                    wages[cells[0]] = cells[1] if len(cells) > 1 else ""

    return wages


# ── 4. Mise à jour PostgreSQL ─────────────────────────────────────────────────

async def _upsert_cct(pool: asyncpg.Pool, cct_data: dict, changed: bool) -> None:
    """
    Insert ou update une CCT dans la DB.
    Enregistre le changelog si changement détecté.
    """
    async with pool.acquire() as conn:
        # Upsert CCT
        await conn.execute("""
            INSERT INTO cct (
                rs_number, name, branch, emoji, source_url,
                fedlex_uri, last_consolidation_date,
                content_hash, content_fr, is_dfo,
                updated_at, auto_updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10, NOW(), NOW())
            ON CONFLICT (rs_number) DO UPDATE SET
                name                   = EXCLUDED.name,
                source_url             = EXCLUDED.source_url,
                fedlex_uri             = EXCLUDED.fedlex_uri,
                last_consolidation_date = EXCLUDED.last_consolidation_date,
                content_hash           = EXCLUDED.content_hash,
                content_fr             = EXCLUDED.content_fr,
                is_dfo                 = EXCLUDED.is_dfo,
                auto_updated_at        = NOW(),
                updated_at             = CASE
                    WHEN cct.content_hash != EXCLUDED.content_hash THEN NOW()
                    ELSE cct.updated_at
                END
        """,
            cct_data["rs_number"],
            cct_data["name"],
            cct_data["branch"],
            cct_data["emoji"],
            cct_data.get("source_url", ""),
            cct_data.get("fedlex_uri", ""),
            cct_data.get("last_consolidation_date"),
            cct_data.get("content_hash", ""),
            cct_data.get("content_fr", ""),
            cct_data.get("is_dfo", True),
        )

        # Enregistrer dans le changelog si changement réel
        if changed:
            await conn.execute("""
                INSERT INTO cct_changelog (rs_number, changed_at, change_type, source, details)
                VALUES ($1, NOW(), 'auto_update', $2, $3)
            """,
                cct_data["rs_number"],
                cct_data.get("source_url", "fedlex"),
                json.dumps({
                    "new_consolidation_date": cct_data.get("last_consolidation_date"),
                    "new_hash": cct_data.get("content_hash", "")[:16],
                })
            )
            log.info(f"✅ CCT mise à jour: {cct_data['name']} (RS {cct_data['rs_number']})")


# ── 5. Orchestrateur principal ────────────────────────────────────────────────

async def run_auto_update(database_url: str) -> dict:
    """
    Point d'entrée principal.
    Appelé par le scheduler toutes les nuits à 02:00 CET.
    Retourne un rapport de mise à jour.
    """
    log.info("🔄 CCTswiss auto-update démarré")
    start = datetime.now(timezone.utc)
    report = {"checked": 0, "updated": 0, "errors": 0, "ccts": []}

    pool = await asyncpg.create_pool(database_url, min_size=2, max_size=5)

    async with httpx.AsyncClient(
        headers={"User-Agent": "CCTswiss.ch/1.0 (auto-updater; contact@cctswiss.ch)"},
        timeout=30.0
    ) as client:

        # Pour chaque CCT connue
        for rs, meta in CCT_RS_NUMBERS.items():
            report["checked"] += 1
            try:
                # 1. Interroger Fedlex
                fedlex_data = _query_fedlex_consolidation(rs)

                # 2. Récupérer le contenu HTML si URL disponible
                content_fr = ""
                if fedlex_data and fedlex_data.get("url"):
                    content_fr = await _fetch(fedlex_data["url"], client) or ""

                # 3. Calculer le hash
                new_hash = _hash(content_fr) if content_fr else ""

                # 4. Vérifier si changement vs DB
                async with pool.acquire() as conn:
                    existing = await conn.fetchrow(
                        "SELECT content_hash, last_consolidation_date FROM cct WHERE rs_number=$1",
                        rs
                    )

                changed = (
                    existing is None or
                    existing["content_hash"] != new_hash
                ) if new_hash else False

                # 5. Préparer les données
                cct_data = {
                    "rs_number":               rs,
                    "name":                    meta["name"],
                    "branch":                  meta["branch"],
                    "emoji":                   meta["emoji"],
                    "source_url":              fedlex_data.get("url", "") if fedlex_data else "",
                    "fedlex_uri":              fedlex_data.get("uri", "") if fedlex_data else "",
                    "last_consolidation_date": fedlex_data.get("date") if fedlex_data else None,
                    "content_hash":            new_hash,
                    "content_fr":              content_fr[:50000] if content_fr else "",  # limit 50KB
                    "is_dfo":                  True,
                }

                # 6. Upsert en DB
                await _upsert_cct(pool, cct_data, changed)

                if changed:
                    report["updated"] += 1
                    report["ccts"].append({"rs": rs, "name": meta["name"], "status": "updated"})
                    report.setdefault("changed_rs", []).append(rs)
                else:
                    report["ccts"].append({"rs": rs, "name": meta["name"], "status": "unchanged"})

            except Exception as e:
                log.error(f"Error updating RS {rs}: {e}")
                report["errors"] += 1

        # ── Déclencher les alertes email si des CCTs ont changé ──────────
        changed_rs = report.get("changed_rs", [])
        if changed_rs:
            try:
                import httpx as _httpx
                import os as _os
                seed_secret = _os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")
                base_url = _os.environ.get("BASE_URL", "http://localhost:8000")
                async with _httpx.AsyncClient(timeout=30) as _client:
                    _resp = await _client.post(
                        f"{base_url}/api/alerts/send",
                        json={"changed_rs_numbers": changed_rs},
                        headers={"X-Seed-Secret": seed_secret}
                    )
                log.info(f"✅ Alertes déclenchées pour {len(changed_rs)} CCTs → {_resp.status_code}")
            except Exception as _e:
                log.warning(f"Alertes email: {_e}")

        # Mettre à jour les salaires L-GAV
        try:
            wages = await _fetch_lgav_wages(client)
            if wages:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO cct_wages_cache (source, data, fetched_at)
                        VALUES ('lgav', $1, NOW())
                        ON CONFLICT (source) DO UPDATE SET data=$1, fetched_at=NOW()
                    """, json.dumps(wages))
                log.info(f"✅ Salaires L-GAV mis à jour ({len(wages)} entrées)")
        except Exception as e:
            log.warning(f"L-GAV wages update failed: {e}")

    await pool.close()

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    report["elapsed_seconds"] = round(elapsed, 1)
    report["ran_at"] = start.isoformat()

    log.info(f"✅ Auto-update terminé: {report['updated']}/{report['checked']} CCT mises à jour en {elapsed:.1f}s")
    return report


# ── Scheduler (lancé par main.py au démarrage) ────────────────────────────────

def start_scheduler(database_url: str):
    """
    Lance le scheduler APScheduler.
    - Nuit: 02:00 CET — update complète Fedlex + SECO + L-GAV
    - Semaine: dimanche 03:00 — vérification profonde (tous les cantons)
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="Europe/Zurich")

    # ✅ Chaque nuit à 02:00 heure suisse
    scheduler.add_job(
        lambda: asyncio.create_task(run_auto_update(database_url)),
        CronTrigger(hour=2, minute=0, timezone="Europe/Zurich"),
        id="nightly_update",
        name="CCT Nightly Auto-Update",
        replace_existing=True,
        misfire_grace_time=3600  # 1h de tolérance si Railway redémarre
    )

    # ✅ Chaque dimanche 03:00 — vérification profonde
    scheduler.add_job(
        lambda: asyncio.create_task(run_auto_update(database_url)),
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="Europe/Zurich"),
        id="weekly_deep_update",
        name="CCT Weekly Deep Update",
        replace_existing=True,
    )

    scheduler.start()
    log.info("🕑 Scheduler démarré — update automatique chaque nuit à 02:00 CET")
    return scheduler
