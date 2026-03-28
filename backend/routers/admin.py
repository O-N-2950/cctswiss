"""CCTswiss.ch — Admin seed + stats router"""
import json
import os
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()
SEED_SECRET = os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")

CCT_SEED_DATA = [{'rs_number': '221.215.329.4', 'name': 'CCNT Hôtellerie-restauration (L-GAV)', 'name_de': 'LKAV Gastgewerbe (L-GAV)', 'name_it': 'CCNT Albergheria e ristorazione (L-GAV)', 'name_en': 'National collective labor agreement hospitality (L-GAV)', 'name_pt': 'CCNT Hotelaria e restauração (L-GAV)', 'name_es': 'CCNT Hostelería y restauración (L-GAV)', 'name_sq': 'Marrëveshja kolektive kombëtare e punës hoteleria', 'name_bs': 'Nacionalni kolektivni ugovor o radu ugostiteljstvo', 'name_tr': 'Ulusal toplu iş sözleşmesi otelcilik', 'name_uk': 'Національний колективний договір готельно-ресторанна', 'branch': 'restauration', 'emoji': '🍽️', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': "Hôtels, restaurants, cafés, traiteurs, take-away, catering, snack-bars, mini-bars hôteliers, cantines, buvettes. S'applique à toute la Suisse.", 'min_wage_chf': 3880.0, 'min_wage_details': {'sans_formation': 3880, 'avec_cfc': 4420, 'cadres': 5200, 'note': 'Salaires 2025, indexés annuellement'}, 'vacation_weeks': 5.0, 'weekly_hours': 42.0, 'has_13th_salary': True, 'source_url': 'https://l-gav.ch/fr/', 'fedlex_uri': 'https://fedlex.data.admin.ch/eli/oc/2017/ccnt-lgav', 'last_consolidation_date': '2025-01-01', 'content_hash': 'ccnt_lgav_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Il ne constitue pas un avis juridique. Consultez le texte officiel sur l-gav.ch ou un professionnel du droit du travail.'}, {'rs_number': '822.22', 'name': 'Convention nationale du principal (CN) — Construction', 'name_de': 'Landesmantelvertrag (LMV) — Bauhauptgewerbe', 'name_it': 'Contratto nazionale mantello (CNM) — Edilizia principale', 'name_en': 'National framework agreement main construction', 'name_pt': 'Convenção nacional da construção principal', 'name_es': 'Convenio nacional de la construcción principal', 'name_sq': 'Marrëveshja kombëtare ndërtimtaria kryesore', 'name_bs': 'Nacionalni okvirni ugovor glavna gradnja', 'name_tr': 'Ulusal çerçeve sözleşmesi inşaat', 'name_uk': 'Національна рамкова угода будівництво', 'branch': 'construction', 'emoji': '🏗️', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': 'Gros-œuvre, maçonnerie, génie civil, terrassement, béton armé. Toute la Suisse.', 'min_wage_chf': 5200.0, 'min_wage_details': {'manoeuvre': 5200, 'ouvrier_qualifie': 5680, 'chef_equipe': 6200, 'note': 'Salaires 2025 (40h/semaine)'}, 'vacation_weeks': 5.0, 'weekly_hours': 41.5, 'has_13th_salary': True, 'source_url': 'https://baumeister.swiss/fr/travail-et-partenaires-sociaux/convention-nationale/', 'fedlex_uri': '', 'last_consolidation_date': '2025-01-01', 'content_hash': 'cn_construction_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur baumeister.swiss.'}, {'rs_number': '221.215.329.6', 'name': 'CCT Nettoyage et hygiène des bâtiments', 'name_de': 'GAV Gebäudereinigergewerbe', 'name_it': 'CCL Pulizia e igiene degli edifici', 'name_en': 'CLA Building cleaning and hygiene', 'name_pt': 'CCT Limpeza e higiene de edifícios', 'name_es': 'CCT Limpieza e higiene de edificios', 'name_sq': 'Marrëveshja kolektive pastrimi ndërtesave', 'name_bs': 'Kolektivni ugovor čišćenje zgrada', 'name_tr': 'Toplu iş sözleşmesi bina temizliği', 'name_uk': 'Колективний договір прибирання будівель', 'branch': 'nettoyage', 'emoji': '🧹', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': "Nettoyage intérieur de bâtiments, service d'entretien, conciergerie. Toute la Suisse.", 'min_wage_chf': 3620.0, 'min_wage_details': {'categorie_1': 3620, 'categorie_2': 3950, 'categorie_3': 4320, 'note': 'Salaires 2025'}, 'vacation_weeks': 5.0, 'weekly_hours': 42.0, 'has_13th_salary': True, 'source_url': 'https://www.allpura.ch/fr/cct/', 'fedlex_uri': '', 'last_consolidation_date': '2025-01-01', 'content_hash': 'cct_nettoyage_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur allpura.ch.'}, {'rs_number': '221.215.329.1', 'name': 'CCT Industries des machines, équipements électriques et métaux (MEM)', 'name_de': 'GAV Maschinen-, Elektro- und Metallindustrie (MEM)', 'name_it': 'CCL Industrie delle macchine, delle apparecchiature elettriche e dei metalli (MEM)', 'name_en': 'CLA Mechanical and electrical engineering and metal industries (MEM)', 'name_pt': 'CCT Indústrias mecânicas e eléctricas e metais', 'name_es': 'CCT Industrias mecánicas y eléctricas y metales', 'name_sq': 'Marrëveshja kolektive industria mekanike dhe metalike', 'name_bs': 'Kolektivni ugovor strojarska i metalna industrija', 'name_tr': 'Toplu iş sözleşmesi makine ve metal endüstrisi', 'name_uk': 'Колективний договір машинобудування та металургія', 'branch': 'industrie', 'emoji': '🔧', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': "Fabrication de machines, d'équipements électriques, travail des métaux. Toute la Suisse.", 'min_wage_chf': 4500.0, 'min_wage_details': {'sans_formation': 4500, 'avec_cfc': 5100, 'technicien': 5800, 'note': 'Salaires 2025 (40h/semaine)'}, 'vacation_weeks': 5.0, 'weekly_hours': 40.0, 'has_13th_salary': True, 'source_url': 'https://www.swissmem.ch/fr/themes/la-cct.html', 'fedlex_uri': '', 'last_consolidation_date': '2025-01-01', 'content_hash': 'cct_mem_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur swissmem.ch.'}, {'rs_number': '221.215.329.3', 'name': 'CCT Coiffure', 'name_de': 'GAV Coiffure', 'name_it': 'CCL Parrucchieri', 'name_en': 'CLA Hairdressing', 'name_pt': 'CCT Cabeleireiros', 'name_es': 'CCT Peluquería', 'name_sq': 'Marrëveshja kolektive berberëve', 'name_bs': 'Kolektivni ugovor frizerstvo', 'name_tr': 'Toplu iş sözleşmesi kuaförlük', 'name_uk': 'Колективний договір перукарство', 'branch': 'coiffure', 'emoji': '💈', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': 'Salons de coiffure, barbiers, instituts capillaires. Toute la Suisse.', 'min_wage_chf': 3500.0, 'min_wage_details': {'apprenti_diplome': 3500, 'avec_experience': 3850, 'note': 'Salaires 2025'}, 'vacation_weeks': 4.0, 'weekly_hours': 42.0, 'has_13th_salary': False, 'source_url': 'https://www.coiffuresuisse.ch/fr/cct/', 'fedlex_uri': '', 'last_consolidation_date': '2024-01-01', 'content_hash': 'cct_coiffure_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur coiffuresuisse.ch.'}, {'rs_number': '221.215.329.7', 'name': 'CCT Industrie horlogère', 'name_de': 'GAV Uhrenindustrie', 'name_it': 'CCL Industria orologiera', 'name_en': 'CLA Watch industry', 'name_pt': 'CCT Indústria relojoeira', 'name_es': 'CCT Industria relojera', 'name_sq': 'Marrëveshja kolektive industria e orëve', 'name_bs': 'Kolektivni ugovor industrija satova', 'name_tr': 'Toplu iş sözleşmesi saat endüstrisi', 'name_uk': 'Колективний договір годинникова промисловість', 'branch': 'horlogerie', 'emoji': '⌚', 'is_dfo': False, 'scope_cantons': ['JU', 'BE', 'NE', 'VD', 'SO', 'FR', 'GE'], 'scope_description_fr': 'Fabrication, assemblage et réparation de montres et de composants horlogers. Arc jurassien principalement.', 'min_wage_chf': 4100.0, 'min_wage_details': {'ouvrier_non_qualifie': 4100, 'technicien_cfc': 4850, 'ingenieur': 6200, 'note': 'Salaires 2025, Arc jurassien'}, 'vacation_weeks': 5.0, 'weekly_hours': 40.0, 'has_13th_salary': True, 'source_url': 'https://www.fhs.swiss/fr/cct-horlogerie/', 'fedlex_uri': '', 'last_consolidation_date': '2025-01-01', 'content_hash': 'cct_horlogerie_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur fhs.swiss.'}, {'rs_number': '221.215.329.8', 'name': 'CCT Boulangerie-pâtisserie-confiserie artisanale', 'name_de': 'GAV Bäckerei-Konditorei-Confiserie-Gewerbe', 'name_it': 'CCL Panetteria-pasticceria-confetteria artigianale', 'name_en': 'CLA Artisan bakery, pastry and confectionery', 'name_pt': 'CCT Padaria-pastelaria-confeitaria artesanal', 'name_es': 'CCT Panadería-pastelería-confitería artesanal', 'name_sq': 'Marrëveshja kolektive furrëtaria-ëmbëlsirëtaria', 'name_bs': 'Kolektivni ugovor pekara-slastičarna', 'name_tr': 'Toplu iş sözleşmesi fırıncılık-pastacılık', 'name_uk': 'Колективний договір хлібобулочна пекарня-кондитерська', 'branch': 'alimentation', 'emoji': '🥖', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': 'Boulangeries, pâtisseries, confiseries artisanales. Toute la Suisse.', 'min_wage_chf': 3700.0, 'min_wage_details': {'apprenti_diplome': 3700, 'avec_experience': 4100, 'note': 'Salaires 2025'}, 'vacation_weeks': 5.0, 'weekly_hours': 42.0, 'has_13th_salary': True, 'source_url': 'https://www.boulangerie.ch/fr/cct/', 'fedlex_uri': '', 'last_consolidation_date': '2024-07-01', 'content_hash': 'cct_boulangerie_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur boulangerie.ch.'}, {'rs_number': '822.211', 'name': 'CCT Location de services', 'name_de': 'GAV Personalverleih', 'name_it': 'CCL Lavoro temporaneo', 'name_en': 'CLA Temporary employment', 'name_pt': 'CCT Trabalho temporário', 'name_es': 'CCT Trabajo temporal', 'name_sq': 'Marrëveshja kolektive punë e përkohshme', 'name_bs': 'Kolektivni ugovor privremeni rad', 'name_tr': 'Toplu iş sözleşmesi geçici istihdam', 'name_uk': 'Колективний договір тимчасова зайнятість', 'branch': 'interim', 'emoji': '🤝', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': 'Agences de travail temporaire et leurs travailleurs intérimaires. Toute la Suisse.', 'min_wage_chf': 3470.0, 'min_wage_details': {'min_absolu': 3470, 'note': 'Salaire minimum 2025 pour travailleurs intérimaires sans CCT de branche applicable'}, 'vacation_weeks': 5.0, 'weekly_hours': 42.0, 'has_13th_salary': True, 'source_url': 'https://www.swissstaffing.ch/fr/cct-location-de-services/', 'fedlex_uri': '', 'last_consolidation_date': '2024-01-01', 'content_hash': 'cct_interim_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur swissstaffing.ch.'}, {'rs_number': '221.215.329.9', 'name': 'CCT Commerce de détail alimentaire', 'name_de': 'GAV Detailhandel Nahrungsmittel', 'name_it': 'CCL Commercio al dettaglio alimentare', 'name_en': 'CLA Food retail trade', 'name_pt': 'CCT Comércio de retalho alimentar', 'name_es': 'CCT Comercio minorista alimentario', 'name_sq': 'Marrëveshja kolektive tregti ushqimore', 'name_bs': 'Kolektivni ugovor maloprodaja prehrambeni', 'name_tr': 'Toplu iş sözleşmesi gıda perakendeciliği', 'name_uk': 'Колективний договір роздрібна торгівля продуктами', 'branch': 'commerce', 'emoji': '🛒', 'is_dfo': False, 'scope_cantons': None, 'scope_description_fr': 'Commerce de détail en produits alimentaires. Migros, Coop, Denner et autres grandes enseignes.', 'min_wage_chf': 3600.0, 'min_wage_details': {'employe_de_commerce': 3600, 'chef_de_rayon': 4200, 'note': 'Salaires 2025 indicatifs — varie par enseigne'}, 'vacation_weeks': 5.0, 'weekly_hours': 41.0, 'has_13th_salary': True, 'source_url': 'https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege.html', 'fedlex_uri': '', 'last_consolidation_date': '2024-01-01', 'content_hash': 'cct_commerce_2025', 'legal_disclaimer_fr': "Ce résumé est fourni à titre informatif uniquement. Consultez l'enseigne concernée pour les détails."}, {'rs_number': '221.215.329.10', 'name': 'CCT Sécurité privée', 'name_de': 'GAV Sicherheitsdienstleistungen', 'name_it': 'CCL Sicurezza privata', 'name_en': 'CLA Private security', 'name_pt': 'CCT Segurança privada', 'name_es': 'CCT Seguridad privada', 'name_sq': 'Marrëveshja kolektive sigurim privat', 'name_bs': 'Kolektivni ugovor privatna sigurnost', 'name_tr': 'Toplu iş sözleşmesi özel güvenlik', 'name_uk': 'Колективний договір приватна охорона', 'branch': 'securite', 'emoji': '🛡️', 'is_dfo': True, 'scope_cantons': None, 'scope_description_fr': 'Agents de sécurité, surveillance, gardiennage, protection. Toute la Suisse.', 'min_wage_chf': 3900.0, 'min_wage_details': {'agent_base': 3900, 'agent_qualifie': 4400, 'chef_equipe': 5100, 'note': 'Salaires 2025'}, 'vacation_weeks': 5.0, 'weekly_hours': 42.0, 'has_13th_salary': True, 'source_url': 'https://www.secsuisse.ch/fr/cct', 'fedlex_uri': '', 'last_consolidation_date': '2024-07-01', 'content_hash': 'cct_securite_2025', 'legal_disclaimer_fr': 'Ce résumé est fourni à titre informatif uniquement. Consultez le texte officiel sur secsuisse.ch.'}]

@router.post("/seed")
async def seed_database(request: Request, x_seed_secret: str = Header(None)):
    """Charge les données CCT initiales en base."""
    if x_seed_secret != SEED_SECRET:
        raise HTTPException(403, "Invalid seed secret")
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not connected")
    inserted = updated = 0
    errors = []
    async with pool.acquire() as conn:
        for cct in CCT_SEED_DATA:
            try:
                cantons = cct.get("scope_cantons")
                # Convert date string to date object
                lcd_raw = cct.get("last_consolidation_date")
                if lcd_raw and isinstance(lcd_raw, str):
                    from datetime import date as _d
                    parts = lcd_raw.split("-")
                    lcd_raw = _d(int(parts[0]), int(parts[1]), int(parts[2]))
                if True:  # Always upsert
                    await conn.execute("""
                        INSERT INTO cct (
                            rs_number, name, name_de, name_it, name_en, name_pt, name_es,
                            name_sq, name_bs, name_tr, name_uk,
                            branch, emoji, is_dfo, scope_cantons, scope_description_fr,
                            min_wage_chf, min_wage_details, vacation_weeks, weekly_hours,
                            has_13th_salary, source_url, fedlex_uri, last_consolidation_date,
                            content_hash, legal_disclaimer_fr, created_at, updated_at, auto_updated_at
                        ) VALUES (
                            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
                            $17,$18,$19,$20,$21,$22,$23,$24,$25,$26,NOW(),NOW(),NOW()
                        )
                    """,
                        cct["rs_number"], cct["name"],
                        cct.get("name_de"), cct.get("name_it"), cct.get("name_en"),
                        cct.get("name_pt"), cct.get("name_es"),
                        cct.get("name_sq"), cct.get("name_bs"),
                        cct.get("name_tr"), cct.get("name_uk"),
                        cct["branch"], cct["emoji"], cct["is_dfo"],
                        cantons, cct.get("scope_description_fr"),
                        cct.get("min_wage_chf"),
                        json.dumps(cct.get("min_wage_details", {})),
                        cct.get("vacation_weeks"), cct.get("weekly_hours"),
                        cct.get("has_13th_salary", False),
                        cct.get("source_url",""), cct.get("fedlex_uri",""),
                        lcd_raw,
                        cct.get("content_hash",""),
                        cct.get("legal_disclaimer_fr",""),
                    )
                    await conn.execute(
                        "INSERT INTO cct_changelog (rs_number, changed_at, change_type, source, details) VALUES ($1,NOW(),$2,$3,$4)",
                        cct["rs_number"], "initial_seed", cct.get("source_url",""),
                        json.dumps({"from": "curated_dataset_2025"})
                    )
                    inserted += 1
            except Exception as e:
                errors.append({"rs": cct["rs_number"], "error": str(e)})
    return JSONResponse({"status":"ok","inserted":inserted,"updated":updated,"errors":errors,"total":len(CCT_SEED_DATA)})


@router.get("/stats")
async def admin_stats(request: Request):
    pool = getattr(request.app.state, "pool", None)
    if not pool: return JSONResponse({"status":"no_db"})
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM cct")
        dfo   = await conn.fetchval("SELECT COUNT(*) FROM cct WHERE is_dfo=true")
        branches = await conn.fetch("SELECT branch,emoji,COUNT(*) n FROM cct GROUP BY branch,emoji ORDER BY n DESC")
        views = await conn.fetchval("SELECT COALESCE(SUM(count),0) FROM cct_views")
    return {"total_ccts":total,"dfo_count":dfo,"total_views":views,
            "by_branch":[dict(r) for r in branches]}


@router.post("/reset")
async def reset_and_reseed(request: Request, x_seed_secret: str = Header(None)):
    """Vide la DB et recharge les données enrichies depuis zéro."""
    if x_seed_secret != SEED_SECRET:
        raise HTTPException(403, "Invalid seed secret")
    pool = getattr(request.app.state, "pool", None)
    if not pool: raise HTTPException(503, "DB not connected")
    
    async with pool.acquire() as conn:
        # Clear everything
        await conn.execute("DELETE FROM cct_views")
        await conn.execute("DELETE FROM cct_changelog")
        await conn.execute("DELETE FROM cct")
    
    # Reseed with enriched data
    inserted = errors = 0
    async with pool.acquire() as conn:
        for cct in CCT_SEED_DATA:
            try:
                cantons = cct.get("scope_cantons")
                lc = cct.get("last_consolidation_date")
                from datetime import date as d_
                lcd = d_(int(lc.split("-")[0]),int(lc.split("-")[1]),int(lc.split("-")[2])) if lc else None
                await conn.execute("""
                    INSERT INTO cct (
                        rs_number, name, name_de, name_it, name_en,
                        name_pt, name_es, name_sq, name_bs, name_tr, name_uk,
                        branch, emoji, is_dfo, scope_cantons, scope_description_fr,
                        min_wage_chf, vacation_weeks, weekly_hours, has_13th_salary,
                        source_url, fedlex_uri, last_consolidation_date,
                        content_hash, legal_disclaimer_fr
                    ) VALUES (
                        ,,,,,,,,,0,1,
                        2,3,4,5,6,7,8,9,0,
                        1,2,3,4,5
                    )
                """,
                    cct["rs_number"], cct["name"],
                    cct.get("name_de"), cct.get("name_it"), cct.get("name_en"),
                    cct.get("name_pt"), cct.get("name_es"),
                    cct.get("name_sq"), cct.get("name_bs"),
                    cct.get("name_tr"), cct.get("name_uk"),
                    cct["branch"], cct["emoji"], cct["is_dfo"],
                    cantons, cct.get("scope_description_fr",""),
                    cct.get("min_wage_chf"), cct.get("vacation_weeks"),
                    cct.get("weekly_hours"), cct.get("has_13th_salary",False),
                    cct.get("source_url",""), cct.get("fedlex_uri",""),
                    lcd,
                    cct.get("content_hash","v2025"),
                    cct.get("legal_disclaimer_fr","")
                )
                inserted += 1
            except Exception as e:
                errors += 1
    
    return {"cleared": True, "inserted": inserted, "errors": errors, "total": len(CCT_SEED_DATA)}
