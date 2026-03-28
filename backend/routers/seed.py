"""CCTswiss — Seed & Admin endpoints"""
import json, os, re
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import date as date_type

router = APIRouter()
SEED_SECRET = os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")

# Full CCT dataset - 29 DFO + horlogerie + MEM
CCT_DATA = [
    {"rs_number":"Gastgewerbe","name":"CCNT hôtellerie-restauration (L-GAV)","branch":"restauration","emoji":"🍽️","is_dfo":True,"min_wage_chf":3880,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":True,"dfo_until":"2027-12-31","source_url":"https://l-gav.ch/fr/","scope_description_fr":"Tous hôtels, restaurants, cafés, traiteurs et take-away en Suisse"},
    {"rs_number":"Bauhauptgewerbe","name":"CN secteur principal construction","branch":"construction","emoji":"🏗️","is_dfo":True,"min_wage_chf":5200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2025-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Bauhauptgewerbe.html","scope_description_fr":"Maçonnerie, génie civil, terrassement, gros œuvre"},
    {"rs_number":"Reinigungssektor_Romandie","name":"CCT nettoyage Suisse romande","branch":"nettoyage","emoji":"🧹","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Reinigungssektor_Westschweiz.html","scope_cantons":["GE","VD","VS","NE","FR","JU"],"scope_description_fr":"Nettoyage bâtiments Suisse romande"},
    {"rs_number":"Reinigung_Deutschschweiz","name":"CCT nettoyage Suisse alémanique","branch":"nettoyage","emoji":"🧹","is_dfo":True,"min_wage_chf":3700,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2029-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Reinigung_Deutschschweiz.html","scope_description_fr":"Nettoyage bâtiments Suisse alémanique"},
    {"rs_number":"Coiffeurgewerbe","name":"CCT nationale coiffure","branch":"coiffure","emoji":"💈","is_dfo":True,"min_wage_chf":3500,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Coiffeurgewerbe.html","scope_description_fr":"Salons de coiffure, barbiers en Suisse"},
    {"rs_number":"Personalverleih","name":"CCT location de services","branch":"location_services","emoji":"👔","is_dfo":True,"min_wage_chf":3500,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Personalverleih.html","scope_description_fr":"Agences de placement temporaire, travail intérimaire"},
    {"rs_number":"Sicherheitsbranche","name":"CCT services de sécurité privés","branch":"securite","emoji":"🔒","is_dfo":True,"min_wage_chf":3800,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Private_Sicherheitsdienstleistungsbranche.html","scope_description_fr":"Surveillance, gardiennage, sécurité privée"},
    {"rs_number":"Ausbaugewerbe_Romandie","name":"CCT second œuvre romand","branch":"second_oeuvre","emoji":"🔨","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Ausbaugewerbe_Westschweiz.html","scope_cantons":["GE","VD","VS","NE","FR","JU","BE"],"scope_description_fr":"Peinture, plâtrerie, revêtements en Suisse romande"},
    {"rs_number":"Boulangerie_Suisse","name":"CCT boulangerie-pâtisserie-confiserie","branch":"alimentation","emoji":"🥖","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Schweizerische_Baecker_Konditoren_Confiseurgewerbe.html","scope_description_fr":"Boulangeries, pâtisseries et confiseries"},
    {"rs_number":"Carrosseriegewerbe","name":"CCT industrie carrosserie","branch":"automobile","emoji":"🚗","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Carrosseriegewerbe.html","scope_description_fr":"Carrosserie, peinture auto, débosselage"},
    {"rs_number":"Callcenter_Branche","name":"CCT centres de contact et d'appel","branch":"services","emoji":"📞","is_dfo":True,"min_wage_chf":3600,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Contact-Callcenter-Branche.html","scope_description_fr":"Call centers, centres de contact en Suisse"},
    {"rs_number":"Elektrogewerbe","name":"CCT branche suisse de l'électricité","branch":"electricite","emoji":"⚡","is_dfo":True,"min_wage_chf":4500,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2029-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Elektro_Telekommunikations_Installationsgewerbes.html","scope_description_fr":"Électriciens, télécommunications, installations électriques"},
    {"rs_number":"Gebaeudehuelle","name":"CCT branche enveloppe des édifices","branch":"construction","emoji":"🏠","is_dfo":True,"min_wage_chf":4300,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Gebaeudehuellegewerbe.html","scope_description_fr":"Toitures, façades, bardages, étanchéité"},
    {"rs_number":"Gebaeudetechnik","name":"CCT techniques du bâtiment","branch":"construction","emoji":"🔧","is_dfo":True,"min_wage_chf":4400,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2029-12-30","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Gebaeudetechnikbranche.html","scope_description_fr":"Chauffage, ventilation, climatisation, sanitaire, plomberie"},
    {"rs_number":"Geruestbau","name":"CCT échafaudeurs","branch":"construction","emoji":"🦺","is_dfo":True,"min_wage_chf":4100,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2029-03-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Geruestbau.html","scope_description_fr":"Montage et démontage d'échafaudages"},
    {"rs_number":"Maler_Gipser","name":"CCT peinture et plâtrerie","branch":"artisanat","emoji":"🖌️","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-03-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Maler_Gipsergewerbe.html","scope_description_fr":"Peintres et plâtriers en Suisse"},
    {"rs_number":"Metallgewerbe","name":"CCT artisanat du métal","branch":"industrie","emoji":"⚙️","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-06-30","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Metallgewerbe.html","scope_description_fr":"Serrurerie, métallerie, construction métallique"},
    {"rs_number":"Metzgereigewerbe","name":"CCT boucherie-charcuterie","branch":"alimentation","emoji":"🥩","is_dfo":True,"min_wage_chf":3700,"vacation_weeks":4,"weekly_hours":43,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Metzgereigewerbe.html","scope_description_fr":"Bouchers et charcutiers en Suisse"},
    {"rs_number":"Moebelindustrie","name":"CCT industrie du meuble","branch":"industrie","emoji":"🪑","is_dfo":True,"min_wage_chf":3900,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Moebelindustrie.html","scope_description_fr":"Fabrication de meubles, ébénisterie industrielle"},
    {"rs_number":"Isoliergewerbe","name":"CCT isolation bâtiment","branch":"construction","emoji":"🏡","is_dfo":True,"min_wage_chf":4100,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Isoliergewerbe.html","scope_description_fr":"Isolation thermique, acoustique et étanchéité"},
    {"rs_number":"Tankstellenshops","name":"CCT shops stations-service","branch":"commerce","emoji":"⛽","is_dfo":True,"min_wage_chf":3400,"vacation_weeks":4,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2028-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Tankstellenshops_Schweiz.html","scope_description_fr":"Shops de stations-service"},
    {"rs_number":"Zahntechnik","name":"CCT laboratoires de prothèse dentaire","branch":"sante","emoji":"🦷","is_dfo":True,"min_wage_chf":3900,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Zahntechnische-Laboratorien.html","scope_description_fr":"Laboratoires de prothèse dentaire en Suisse"},
    {"rs_number":"Schreinergewerbe","name":"CCT menuiserie et ébénisterie","branch":"artisanat","emoji":"🪵","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":41.5,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Schreinergewerbe.html","scope_description_fr":"Menuiserie, ébénisterie, charpenterie intérieure"},
    {"rs_number":"Holzbaugewerbe","name":"CCT construction en bois","branch":"construction","emoji":"🌲","is_dfo":True,"min_wage_chf":4200,"vacation_weeks":5,"weekly_hours":41,"has_13th_salary":False,"dfo_until":"2027-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Holzbaugewerbe.html","scope_description_fr":"Charpente, ossature bois, construction en bois"},
    {"rs_number":"Plattenleger","name":"CCT carreleurs (cantons alémaniques)","branch":"artisanat","emoji":"🏺","is_dfo":True,"min_wage_chf":4000,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Plattenlegergewerbe_AG_BE_GL_LU_NW_OW_SZ_SO_UR_ZG_ZH.html","scope_cantons":["AG","BE","GL","LU","NW","OW","SZ","SO","UR","ZG","ZH"],"scope_description_fr":"Carreleurs et poseurs de revêtements"},
    {"rs_number":"Netzinfrastruktur","name":"CCT infrastructure réseau","branch":"construction","emoji":"🌐","is_dfo":True,"min_wage_chf":4300,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":"2026-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/GAV_Netzinfrastruktur.html","scope_description_fr":"Fibre optique, câbles, conduites souterraines"},
    {"rs_number":"FAR_Construction","name":"CCT retraite anticipée construction (FAR)","branch":"construction","emoji":"🏗️","is_dfo":True,"min_wage_chf":None,"vacation_weeks":None,"weekly_hours":None,"has_13th_salary":False,"dfo_until":"2034-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/FAR_Bauhauptgewerbe.html","scope_description_fr":"Fonds de retraite anticipée secteur construction"},
    {"rs_number":"Betonwaren","name":"CCT industrie béton préfabriqué","branch":"construction","emoji":"🏭","is_dfo":True,"min_wage_chf":4100,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2025-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Betonwarenindustrie.html","scope_description_fr":"Produits en béton préfabriqués"},
    {"rs_number":"Gleisbau","name":"CCT construction des voies ferrées","branch":"construction","emoji":"🚂","is_dfo":True,"min_wage_chf":4400,"vacation_weeks":5,"weekly_hours":42,"has_13th_salary":False,"dfo_until":"2025-12-31","source_url":"https://www.seco.admin.ch/seco/fr/home/Arbeit/Personenfreizugigkeit_Arbeitsbeziehungen/Gesamtarbeitsvertraege_Normalarbeitsvertraege/Gesamtarbeitsvertraege_Bund/Allgemeinverbindlich_erklaerte_Gesamtarbeitsvertraege/Gleisbau.html","scope_description_fr":"Construction et entretien des voies ferrées"},
    # Non-DFO but important
    {"rs_number":"CCT_Horlogerie","name":"CCT industrie horlogère","branch":"horlogerie","emoji":"⌚","is_dfo":False,"min_wage_chf":3800,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":True,"dfo_until":None,"source_url":"https://www.cpih.ch/convention-collective-de-travail/","scope_cantons":["JU","NE","BE","SO","GE","VD"],"scope_description_fr":"Arc jurassien — montres, bijouterie, microtechnique"},
    {"rs_number":"CCT_MEM","name":"CCT industries MEM (machines, électronique, métallurgie)","branch":"industrie","emoji":"🔩","is_dfo":False,"min_wage_chf":4500,"vacation_weeks":5,"weekly_hours":40,"has_13th_salary":False,"dfo_until":None,"source_url":"https://www.swissmem.ch/fr/themes/la-cct.html","scope_description_fr":"Industrie des machines, appareils électriques et métaux"},
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
    async with pool.acquire() as conn:
        # Clear existing data for clean reseed
        await conn.execute("TRUNCATE TABLE cct RESTART IDENTITY CASCADE")
        
        for cct in CCT_DATA:
            try:
                dfu = None
                if cct.get("dfo_until"):
                    p = cct["dfo_until"].split("-")
                    dfu = date_type(int(p[0]),int(p[1]),int(p[2]))
                await conn.execute("""
                    INSERT INTO cct (rs_number,name,branch,emoji,is_dfo,dfo_until,
                        min_wage_chf,vacation_weeks,weekly_hours,has_13th_salary,
                        source_url,scope_cantons,scope_description_fr,content_hash)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'seeded-v2')
                    ON CONFLICT (rs_number) DO UPDATE SET
                        name=EXCLUDED.name,branch=EXCLUDED.branch,emoji=EXCLUDED.emoji,
                        is_dfo=EXCLUDED.is_dfo,dfo_until=EXCLUDED.dfo_until,
                        min_wage_chf=EXCLUDED.min_wage_chf,vacation_weeks=EXCLUDED.vacation_weeks,
                        weekly_hours=EXCLUDED.weekly_hours,has_13th_salary=EXCLUDED.has_13th_salary,
                        source_url=EXCLUDED.source_url,scope_cantons=EXCLUDED.scope_cantons,
                        scope_description_fr=EXCLUDED.scope_description_fr,updated_at=NOW()
                """,
                    cct["rs_number"],cct["name"],cct["branch"],cct["emoji"],
                    cct.get("is_dfo",True),dfu,cct.get("min_wage_chf"),
                    cct.get("vacation_weeks"),cct.get("weekly_hours"),
                    cct.get("has_13th_salary",False),cct.get("source_url",""),
                    cct.get("scope_cantons"),cct.get("scope_description_fr",""))
                inserted += 1
            except Exception as e:
                pass
    return {"inserted": inserted, "total_in_db": len(CCT_DATA)}

@router.post("/translate")
async def translate_ccts(request: Request):
    secret = request.headers.get("X-Seed-Secret","")
    if secret != SEED_SECRET:
        raise HTTPException(403, "Not authorized")
    pool = getattr(request.app.state, "pool", None)
    if not pool:
        raise HTTPException(503, "DB not ready")
    
    import httpx
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY","")
    if not ANTHROPIC_KEY:
        return {"error": "ANTHROPIC_API_KEY not set", "translated": 0}
    
    async with pool.acquire() as conn:
        ccts = await conn.fetch("SELECT rs_number, name FROM cct ORDER BY name")
    
    translated = 0
    errors = []
    
    for i in range(0, len(ccts), 8):
        batch = ccts[i:i+8]
        names = [{"rs": r["rs_number"], "n": r["name"]} for r in batch]
        prompt = f"""Translate these Swiss labor convention abbreviated names into 9 languages.
Return ONLY a JSON array.
Format: [{{"rs":"id","de":"...","it":"...","en":"...","pt":"...","es":"...","sq":"...","bs":"...","tr":"...","uk":"..."}}]
- SQ=Albanian, BS=BCMS Latin, TR=Turkish, UK=Ukrainian Cyrillic
Input: {json.dumps(names, ensure_ascii=False)}"""
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post("https://api.anthropic.com/v1/messages",
                    headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
                    json={"model":"claude-haiku-4-5-20251001","max_tokens":2000,
                          "messages":[{"role":"user","content":prompt}]})
                data = resp.json()
                text = re.sub(r'```[a-z]*\n?','',data["content"][0]["text"]).strip()
                t_list = json.loads(text)
                async with pool.acquire() as conn:
                    for t in t_list:
                        rs = t.get("rs")
                        for lang in ["de","it","en","pt","es","sq","bs","tr","uk"]:
                            val = t.get(lang)
                            if val:
                                try:
                                    await conn.execute(f"UPDATE cct SET name_{lang}=$1 WHERE rs_number=$2", val, rs)
                                except: pass
                translated += len(t_list)
        except Exception as e:
            errors.append(f"batch {i}: {str(e)[:80]}")
    
    return {"translated": translated, "errors": errors}


@router.post("/clear")
async def clear_ccts(request: Request):
    """Clear all CCT data for fresh reseed"""
    secret = request.headers.get("X-Seed-Secret","")
    if secret != SEED_SECRET:
        raise HTTPException(403, "Not authorized")
    pool = getattr(request.app.state, "pool", None)
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE cct_views, cct_changelog, cct_wages_cache RESTART IDENTITY")
        await conn.execute("TRUNCATE TABLE cct RESTART IDENTITY CASCADE")
    return {"cleared": True}
