"""CCTswiss — Seed endpoint (admin only)"""
import json, os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import date

router = APIRouter()
SEED_SECRET = os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")

# Full CCT dataset scraped from SECO
CCT_DATA = [
    {"rs_number":"Gastgewerbe","name":"CCNT pour les hôtels, restaurants et cafés","branch":"restauration","emoji":"🍽️","is_dfo":True,"min_wage_chf":3880,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":True,"dfo_until":"2027-12-31","source_url":"https://l-gav.ch/fr/","scope_description_fr":"Tous hôtels, restaurants, cafés, traiteurs, take-away en Suisse"},
    {"rs_number":"Bauhauptgewerbe","name":"CN pour le secteur principal de la construction en Suisse","branch":"construction","emoji":"🏗️","is_dfo":True,"min_wage_chf":5200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2025-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Bauhauptgewerbe.html","scope_description_fr":"Secteur principal construction, maçonnerie, génie civil, terrassement"},
    {"rs_number":"Reinigungssektor_Westschweiz","name":"CCT du secteur du nettoyage pour la Suisse romande","branch":"nettoyage","emoji":"🧹","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Reinigungssektor_Westschweiz.html","scope_cantons":["GE","VD","VS","NE","FR","JU"],"scope_description_fr":"Nettoyage bâtiments Suisse romande (GE, VD, VS, NE, FR, JU)"},
    {"rs_number":"Reinigung_Deutschschweiz","name":"CCT für die Reinigungsbranche in der Deutschschweiz","branch":"nettoyage","emoji":"🧹","is_dfo":True,"min_wage_chf":3700,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2029-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Reinigung_Deutschschweiz.html","scope_description_fr":"Nettoyage bâtiments Suisse alémanique"},
    {"rs_number":"Coiffeurgewerbe","name":"CN des coiffeurs","branch":"coiffure","emoji":"💈","is_dfo":True,"min_wage_chf":3500,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Coiffeurgewerbe.html","scope_description_fr":"Salons de coiffure, barbiers, instituts capillaires en Suisse"},
    {"rs_number":"Personalverleih","name":"CCT de la location de services","branch":"location_services","emoji":"👔","is_dfo":True,"min_wage_chf":3500,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Personalverleih.html","scope_description_fr":"Agences de placement temporaire et location de personnel"},
    {"rs_number":"Private_Sicherheitsdienstleistungsbranche","name":"CCT pour la branche des services de sécurité privés","branch":"securite","emoji":"🔒","is_dfo":True,"min_wage_chf":3800,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Private_Sicherheitsdienstleistungsbranche.html","scope_description_fr":"Services de surveillance, gardiennage et sécurité privée"},
    {"rs_number":"Ausbaugewerbe_Westschweiz","name":"CCT romande du second oeuvre","branch":"second_oeuvre","emoji":"🔨","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Ausbaugewerbe_Westschweiz.html","scope_cantons":["GE","VD","VS","NE","FR","JU","BE"],"scope_description_fr":"Second œuvre romand — peinture, plâtrerie, revêtements"},
    {"rs_number":"Schweizerische_Baecker","name":"CCT du secteur de la boulangerie-pâtisserie-confiserie suisse","branch":"alimentation","emoji":"🥖","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Schweizerische_Baecker_Konditoren_Confiseurgewerbe.html","scope_description_fr":"Boulangeries, pâtisseries et confiseries en Suisse"},
    {"rs_number":"Carrosseriegewerbe","name":"CCT de l'industrie Suisse de la carrosserie","branch":"automobile","emoji":"🚗","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Carrosseriegewerbe.html","scope_description_fr":"Carrosserie, peinture automobile, débosselage"},
    {"rs_number":"GAV_Contact_Callcenter","name":"CCT de la branche des centres de contact et d'appel","branch":"services","emoji":"📞","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Contact-Callcenter-Branche.html","scope_description_fr":"Centres d'appel et de contact en Suisse"},
    {"rs_number":"Elektro_Installationsgewerbe","name":"CCT de la branche suisse de l'électricité","branch":"electricite","emoji":"⚡","is_dfo":True,"min_wage_chf":4500,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2029-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Elektro_Telekommunikations_Installationsgewerbes.html","scope_description_fr":"Électriciens, télécommunications, installations électriques"},
    {"rs_number":"Gebaeudehuellegewerbe","name":"CCT dans la branche suisse de l'enveloppe des édifices","branch":"construction","emoji":"🏠","is_dfo":True,"min_wage_chf":4300,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Gebaeudehuellegewerbe.html","scope_description_fr":"Toitures, façades, étanchéité, bardages"},
    {"rs_number":"Gebaeudetechnikbranche","name":"CCT dans la branche suisse des techniques du bâtiment","branch":"construction","emoji":"🔧","is_dfo":True,"min_wage_chf":4400,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2029-12-30","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Gebaeudetechnikbranche.html","scope_description_fr":"Chauffage, ventilation, climatisation, sanitaire"},
    {"rs_number":"Geruestbau","name":"CCT pour les échafaudeurs","branch":"construction","emoji":"🦺","is_dfo":True,"min_wage_chf":4100,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2029-03-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Geruestbau.html","scope_description_fr":"Montage et démontage d'échafaudages"},
    {"rs_number":"Maler_Gipsergewerbe","name":"CCT pour l'industrie de la peinture et de la plâtrerie","branch":"artisanat","emoji":"🖌️","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-03-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Maler_Gipsergewerbe.html","scope_description_fr":"Peintres, plâtriers, enduiseurs en Suisse"},
    {"rs_number":"Metallgewerbe","name":"CCT pour l'artisanat du métal","branch":"industrie","emoji":"⚙️","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-06-30","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Metallgewerbe.html","scope_description_fr":"Serrurerie, métallerie, construction métallique"},
    {"rs_number":"Metzgereigewerbe","name":"CCT pour la boucherie-charcuterie suisse","branch":"alimentation","emoji":"🥩","is_dfo":True,"min_wage_chf":3700,"vacation_weeks":4,"weekly_hours":43,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Metzgereigewerbe.html","scope_description_fr":"Bouchers, charcutiers en Suisse"},
    {"rs_number":"Moebelindustrie","name":"CCT pour l'industrie suisse du meuble","branch":"industrie","emoji":"🪑","is_dfo":True,"min_wage_chf":3900,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Moebelindustrie.html","scope_description_fr":"Fabrication de meubles et ébénisterie industrielle"},
    {"rs_number":"Isoliergewerbe","name":"CCT pour le secteur suisse de l'isolation","branch":"construction","emoji":"🏡","is_dfo":True,"min_wage_chf":4100,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Isoliergewerbe.html","scope_description_fr":"Isolation thermique, acoustique et étanchéité"},
    {"rs_number":"GAV_Tankstellenshops","name":"CCT des shops de stations-service suisses","branch":"commerce","emoji":"⛽","is_dfo":True,"min_wage_chf":3400,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Tankstellenshops_Schweiz.html","scope_description_fr":"Shops et services des stations-service en Suisse"},
    {"rs_number":"Zahntechnische_Laboratorien","name":"CCT des laboratoires de prothèse dentaire de Suisse","branch":"sante","emoji":"🦷","is_dfo":True,"min_wage_chf":3900,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Zahntechnische-Laboratorien.html","scope_description_fr":"Laboratoires de prothèse dentaire"},
    {"rs_number":"Schreinergewerbe","name":"CCT für das Schreinergewerbe","branch":"artisanat","emoji":"🪵","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":41.5,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Schreinergewerbe.html","scope_description_fr":"Menuiserie, ébénisterie, charpenterie intérieure"},
    {"rs_number":"Holzbaugewerbe","name":"CCT für das Holzbaugewerbe","branch":"construction","emoji":"🌲","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":41,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Holzbaugewerbe.html","scope_description_fr":"Construction en bois, charpente, ossature bois"},
    {"rs_number":"Plattenlegergewerbe","name":"CCNT pour la branche du carrelage","branch":"artisanat","emoji":"🏺","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Plattenlegergewerbe_AG_BE_GL_LU_NW_OW_SZ_SO_UR_ZG_ZH.html","scope_cantons":["AG","BE","GL","LU","NW","OW","SZ","SO","UR","ZG","ZH"],"scope_description_fr":"Poseurs de carrelage et revêtements (cantons AG, BE, GL, LU, NW, OW, SZ, SO, UR, ZG, ZH)"},
    {"rs_number":"GAV_Netzinfrastruktur","name":"CCT pour la branche infrastructure de réseau","branch":"construction","emoji":"🌐","is_dfo":True,"min_wage_chf":4300,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Netzinfrastruktur.html","scope_description_fr":"Pose de câbles, conduites, fibre optique"},
    {"rs_number":"FAR_Bauhauptgewerbe","name":"CCT retraite anticipée construction (FAR)","branch":"construction","emoji":"🏗️","is_dfo":True,"min_wage_chf":None,"vacation_weeks":None,"weekly_hours":None,"has_13th_salary":False,"dfo_until":"2034-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/FAR_Bauhauptgewerbe.html","scope_description_fr":"Fonds de retraite anticipée secteur principal construction"},
    # Horlogerie (not DFO but important)
    {"rs_number":"CCT_Horlogerie","name":"CCT Industrie horlogère","branch":"horlogerie","emoji":"⌚","is_dfo":False,"min_wage_chf":3800,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":True,"dfo_until":None,"source_url":"https://www.cpih.ch/convention-collective-de-travail/","scope_cantons":["JU","NE","BE","SO","GE","VD"],"scope_description_fr":"Arc jurassien — fabrication, assemblage et réparation de montres"},
    # MEM
    {"rs_number":"CCT_MEM","name":"CCT Industries MEM (Machines, Électronique, Métallurgie)","branch":"industrie","emoji":"🔩","is_dfo":False,"min_wage_chf":4500,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":None,"source_url":"https://www.swissmem.ch/fr/themes/la-cct.html","scope_description_fr":"Industrie des machines, appareils électriques et métaux"},
]

@router.post("/seed")
async def seed_cct(request: Request):
    secret = request.headers.get("X-Seed-Secret","")
    if secret != SEED_SECRET:
        raise HTTPException(403, "Not authorized")
    
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not ready")
    
    inserted = 0
    errors = []
    
    async with pool.acquire() as conn:
        for cct in CCT_DATA:
            try:
                dfo_until = None
                if cct.get("dfo_until"):
                    try:
                        from datetime import date as d_
                        parts = cct["dfo_until"].split("-")
                        dfo_until = d_(int(parts[0]),int(parts[1]),int(parts[2]))
                    except: pass
                
                await conn.execute("""
                    INSERT INTO cct (
                        rs_number, name, branch, emoji, is_dfo,
                        dfo_until, min_wage_chf, vacation_weeks,
                        weekly_hours, has_13th_salary, source_url,
                        scope_cantons, scope_description_fr, content_hash
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                    ON CONFLICT (rs_number) DO UPDATE SET
                        name=EXCLUDED.name, branch=EXCLUDED.branch,
                        emoji=EXCLUDED.emoji, is_dfo=EXCLUDED.is_dfo,
                        dfo_until=EXCLUDED.dfo_until,
                        min_wage_chf=EXCLUDED.min_wage_chf,
                        vacation_weeks=EXCLUDED.vacation_weeks,
                        weekly_hours=EXCLUDED.weekly_hours,
                        has_13th_salary=EXCLUDED.has_13th_salary,
                        source_url=EXCLUDED.source_url,
                        scope_cantons=EXCLUDED.scope_cantons,
                        scope_description_fr=EXCLUDED.scope_description_fr,
                        updated_at=NOW()
                """,
                    cct["rs_number"], cct["name"], cct["branch"], cct["emoji"],
                    cct.get("is_dfo", True), dfo_until,
                    cct.get("min_wage_chf"), cct.get("vacation_weeks"),
                    cct.get("weekly_hours"), cct.get("has_13th_salary", False),
                    cct.get("source_url",""), cct.get("scope_cantons"),
                    cct.get("scope_description_fr",""), "seeded-v1"
                )
                inserted += 1
            except Exception as e:
                errors.append(f"{cct['rs_number']}: {e}")
    
    return {"inserted": inserted, "errors": errors, "total_ccts": len(CCT_DATA)}

# ─── Translation endpoint ─────────────────────────────────────────────────────
@router.post("/translate")
async def translate_ccts(request: Request):
    """Generate multilingual translations for all CCTs using Claude API"""
    secret = request.headers.get("X-Seed-Secret","")
    if secret != SEED_SECRET:
        raise HTTPException(403, "Not authorized")
    
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not ready")
    
    import httpx, re
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY","")
    
    async with pool.acquire() as conn:
        ccts = await conn.fetch("SELECT rs_number, name FROM cct ORDER BY name")
    
    results = {"translated": 0, "errors": []}
    
    # Translate in batches of 10
    batch_size = 10
    for i in range(0, len(ccts), batch_size):
        batch = ccts[i:i+batch_size]
        names = [{"rs": r["rs_number"], "name": r["name"]} for r in batch]
        
        prompt = f"""Translate these Swiss labor convention names into 9 languages.
Return ONLY a JSON array, no markdown fences, no explanation.
Format: [{{"rs":"id","de":"...","it":"...","en":"...","pt":"...","es":"...","sq":"...","bs":"...","tr":"...","uk":"..."}}]

- SQ = Albanian (Shqip)
- BS = Bosnian/Croatian/Serbian BCMS in Latin script  
- TR = Turkish
- UK = Ukrainian in Cyrillic script

Names: {json.dumps(names, ensure_ascii=False)}"""

        try:
            if not ANTHROPIC_KEY:
                # Use hardcoded translations for key CCTs
                results["errors"].append("No ANTHROPIC_API_KEY set")
                break
            
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": "claude-haiku-4-5-20251001", "max_tokens": 3000,
                          "messages": [{"role":"user","content":prompt}]}
                )
                data = resp.json()
                text = data["content"][0]["text"]
                
                # Strip any markdown
                text = re.sub(r'```[a-z]*\n?', '', text).strip()
                translations = json.loads(text)
                
                async with pool.acquire() as conn:
                    for t in translations:
                        rs = t.get("rs")
                        for lang in ["de","it","en","pt","es","sq","bs","tr","uk"]:
                            val = t.get(lang)
                            if val:
                                try:
                                    await conn.execute(f"UPDATE cct SET name_{lang}=$1 WHERE rs_number=$2", val, rs)
                                except: pass
                
                results["translated"] += len(translations)
        except Exception as e:
            results["errors"].append(f"Batch {i}: {str(e)[:100]}")
    
    return results


@router.post("/fix-data")
async def fix_data(request: Request):
    """Fix data quality: dedup, summaries"""
    secret = request.headers.get("X-Seed-Secret","")
    if secret != SEED_SECRET:
        raise HTTPException(403, "Not authorized")
    
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not ready")
    
    fixed = 0
    async with pool.acquire() as conn:
        # Remove exact name duplicates
        dupes = await conn.fetch("""
            SELECT name, array_agg(rs_number ORDER BY min_wage_chf DESC NULLS LAST) as rss
            FROM cct GROUP BY name HAVING COUNT(*) > 1
        """)
        for d in dupes:
            rss = d["rss"]
            for rs in rss[1:]:
                await conn.execute("DELETE FROM cct WHERE rs_number=$1", rs)
                fixed += 1
        
        total = await conn.fetchval("SELECT COUNT(*) FROM cct")
        dfo = await conn.fetchval("SELECT COUNT(*) FROM cct WHERE is_dfo=true")
    
    return {"removed_dupes": fixed, "total_remaining": total, "dfo_count": dfo}
