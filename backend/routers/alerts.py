"""
CCTswiss — Système d'alertes email
Abonnement aux changements de CCT via double opt-in.

Flow:
  1. POST /api/alerts/subscribe  → crée abonné non confirmé + envoie email confirmation
  2. GET  /api/alerts/confirm    → confirme l'abonné (lien depuis email)
  3. GET  /api/alerts/unsubscribe → désabonne (lien 1-clic depuis chaque email)
  4. POST /api/alerts/send       → (admin) déclenche manuellement les alertes
  5. GET  /api/alerts/stats      → stats abonnés (admin)

Email provider: Resend (RESEND_API_KEY Railway var)
From: alertes@cctswiss.ch
"""
import os, secrets, logging, json, httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Header, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse
import asyncpg

log = logging.getLogger("cctswiss.alerts")
router = APIRouter()

RESEND_API_KEY   = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL       = "alertes@cctswiss.ch"
FROM_NAME        = "CCTswiss.ch"
BASE_URL         = os.environ.get("BASE_URL", "https://cctswiss.ch")
SEED_SECRET      = os.environ.get("SEED_SECRET", "cctswiss-neo-seed-2025")

def get_pool(r: Request): return r.app.state.pool


# ── Helpers ──────────────────────────────────────────────────────────
def _token() -> str:
    return secrets.token_urlsafe(32)

async def _send_email(to: str, subject: str, html: str) -> bool:
    """Envoie via Resend API. Retourne True si succès."""
    if not RESEND_API_KEY:
        log.warning(f"[Alerts] RESEND_API_KEY non défini — email non envoyé à {to}")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                         "Content-Type":  "application/json"},
                json={"from": f"{FROM_NAME} <{FROM_EMAIL}>",
                      "to":   [to],
                      "subject": subject,
                      "html":    html}
            )
        if resp.status_code in (200, 201):
            log.info(f"[Alerts] Email envoyé → {to}")
            return True
        log.error(f"[Alerts] Resend {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        log.error(f"[Alerts] Erreur envoi: {e}")
        return False

def _email_confirm_html(email: str, company: str, token: str, lang: str, rs_names: list[str]) -> str:
    url = f"{BASE_URL}/api/alerts/confirm?token={token}"
    ccts_list = "".join(f"<li>{n}</li>" for n in rs_names[:5])
    labels = {
        "fr": ("Confirmez vos alertes CCT", "Vous avez demandé à recevoir des alertes pour", "Confirmer mon abonnement", "Ce lien est valable 48h.", "Si vous n'avez pas fait cette demande, ignorez cet email."),
        "de": ("GAV-Alerts bestätigen", "Sie haben Benachrichtigungen beantragt für", "Abonnement bestätigen", "Dieser Link ist 48 Stunden gültig.", "Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail."),
        "it": ("Conferma avvisi CCL", "Hai richiesto avvisi per", "Conferma abbonamento", "Questo link è valido per 48 ore.", "Se non hai effettuato questa richiesta, ignora questa email."),
        "en": ("Confirm your CCT alerts", "You've requested alerts for", "Confirm subscription", "This link is valid for 48 hours.", "If you didn't make this request, ignore this email."),
    }
    l = labels.get(lang, labels["fr"])
    return f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f3ef;margin:0;padding:20px}}
  .card{{background:#fff;border-radius:8px;max-width:560px;margin:0 auto;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
  .top{{background:#0A0A0A;padding:24px 28px;display:flex;align-items:center;gap:12px}}
  .logo-box{{background:#C8102E;border-radius:6px;width:34px;height:34px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:10px;color:#fff;font-family:monospace;letter-spacing:.5px}}
  .logo-name{{color:#fff;font-weight:700;font-size:18px;letter-spacing:-.2px}}
  .body{{padding:28px}}
  h2{{margin:0 0 16px;font-size:20px;font-weight:700;color:#0A0A0A}}
  p{{margin:0 0 14px;color:#555;font-size:14px;line-height:1.6}}
  ul{{margin:0 0 20px;padding-left:18px;color:#333;font-size:14px;line-height:1.8}}
  .btn{{display:block;background:#C8102E;color:#fff!important;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:700;font-size:15px;text-align:center;margin:22px 0}}
  .btn:hover{{background:#9B0B22}}
  .muted{{font-size:11px;color:#999;border-top:1px solid #eee;padding-top:14px;margin-top:20px;line-height:1.7}}
  .muted a{{color:#1a6eb5;text-decoration:none}}
</style></head><body>
<div class="card">
  <div class="top">
    <div class="logo-box">CCT</div>
    <span class="logo-name">swiss.ch</span>
  </div>
  <div class="body">
    <h2>🔔 {l[0]}</h2>
    <p>{l[1]} :</p>
    <ul>{ccts_list}</ul>
    <p>Email : <strong>{email}</strong>{f'<br>Entreprise : <strong>{company}</strong>' if company else ''}</p>
    <a href="{url}" class="btn">✓ {l[2]}</a>
    <p class="muted">
      {l[3]}<br>
      {l[4]}<br><br>
      <strong>Vos données sont utilisées uniquement pour envoyer ces alertes.</strong><br>
      Elles ne sont jamais vendues, ni partagées avec des tiers.<br>
      Vous pouvez vous désinscrire en 1 clic depuis chaque email.<br><br>
      © CCTswiss.ch · Groupe NEO · <a href="https://cctswiss.ch">cctswiss.ch</a>
    </p>
  </div>
</div>
</body></html>"""

def _email_alert_html(email: str, changes: list[dict], unsub_token: str, lang: str) -> str:
    url_unsub = f"{BASE_URL}/api/alerts/unsubscribe?token={unsub_token}"
    labels = {
        "fr": ("Mise à jour CCT", "Les conventions collectives suivantes ont été modifiées", "Voir la CCT →", "Source officielle : Fedlex"),
        "de": ("GAV-Aktualisierung", "Folgende Gesamtarbeitsverträge wurden aktualisiert", "GAV anzeigen →", "Offizielle Quelle: Fedlex"),
        "it": ("Aggiornamento CCL", "I seguenti contratti collettivi sono stati aggiornati", "Vedi CCL →", "Fonte ufficiale: Fedlex"),
        "en": ("CCT Update", "The following collective agreements have been updated", "View CCA →", "Official source: Fedlex"),
    }
    l = labels.get(lang, labels["fr"])
    changes_html = ""
    for c in changes:
        changes_html += f"""
        <div style="border-left:3px solid #C8102E;padding:12px 16px;margin:10px 0;background:#fafaf8;border-radius:0 4px 4px 0">
          <div style="font-size:13px;font-weight:700;color:#0A0A0A">{c.get('emoji','📄')} {c.get('name','')}</div>
          <div style="font-size:11px;color:#999;font-family:monospace;margin:3px 0">{c.get('rs_number','')}</div>
          {f'<div style="font-size:12px;color:#555;margin-top:5px">{c.get("description","")}</div>' if c.get('description') else ''}
          <a href="{BASE_URL}/#cct-{c.get('rs_number','')}" style="display:inline-block;margin-top:8px;background:#0A0A0A;color:#fff;padding:6px 14px;border-radius:4px;font-size:11px;font-weight:600;text-decoration:none;font-family:monospace;letter-spacing:.06em">{l[2]}</a>
        </div>"""
    today = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    return f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f3ef;margin:0;padding:20px}}
  .card{{background:#fff;border-radius:8px;max-width:560px;margin:0 auto;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
  .top{{background:#0A0A0A;padding:20px 28px;display:flex;align-items:center;justify-content:space-between}}
  .logo{{display:flex;align-items:center;gap:10px}}
  .logo-box{{background:#C8102E;border-radius:6px;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:9px;color:#fff;font-family:monospace}}
  .logo-name{{color:#fff;font-weight:700;font-size:16px}}
  .date{{color:rgba(255,255,255,.4);font-size:11px;font-family:monospace}}
  .red-band{{background:#C8102E;padding:12px 28px}}
  .red-band h2{{margin:0;color:#fff;font-size:16px;font-weight:800;letter-spacing:.04em}}
  .body{{padding:24px 28px}}
  p{{margin:0 0 14px;color:#555;font-size:14px;line-height:1.6}}
  .muted{{font-size:11px;color:#999;border-top:1px solid #eee;padding-top:14px;margin-top:20px;line-height:1.8}}
  .muted a{{color:#1a6eb5;text-decoration:none}}
</style></head><body>
<div class="card">
  <div class="top">
    <div class="logo"><div class="logo-box">CCT</div><span class="logo-name">swiss.ch</span></div>
    <span class="date">{today}</span>
  </div>
  <div class="red-band"><h2>🔔 {l[0]}</h2></div>
  <div class="body">
    <p>{l[1]} :</p>
    {changes_html}
    <p style="font-size:12px;color:#999;margin-top:16px">
      📜 {l[3]} · <a href="https://fedlex.data.admin.ch" style="color:#1a6eb5">fedlex.data.admin.ch</a>
    </p>
    <div class="muted">
      Vous recevez cet email car vous êtes abonné aux alertes CCTswiss.ch.<br>
      <strong>Vos données ne sont jamais vendues ni partagées avec des tiers.</strong><br><br>
      <a href="{url_unsub}" style="color:#C8102E;font-weight:700">🚫 Se désinscrire en 1 clic</a><br><br>
      © CCTswiss.ch · Groupe NEO · <a href="https://cctswiss.ch">cctswiss.ch</a>
    </div>
  </div>
</div>
</body></html>"""


# ── POST /api/alerts/subscribe ────────────────────────────────────────
@router.post("/subscribe")
async def subscribe(request: Request, pool: asyncpg.Pool = Depends(get_pool)):
    """
    Abonnement aux alertes CCT.
    Envoie un email de confirmation (double opt-in).
    """
    body = await request.json()
    email   = (body.get("email") or "").strip().lower()
    company = (body.get("company") or "").strip()[:120]
    lang    = (body.get("lang") or "fr").strip()[:5]
    rs_list = body.get("rs_numbers") or []

    # Validation
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(422, "Email invalide")
    if not rs_list:
        raise HTTPException(422, "Sélectionnez au moins une CCT à suivre")
    if len(rs_list) > 50:
        raise HTTPException(422, "Maximum 50 CCTs par abonnement")

    # Get CCT names for email
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT rs_number, name FROM cct WHERE rs_number = ANY($1)", rs_list
        )
        rs_names = [r["name"] for r in rows]

        # Check existing
        existing = await conn.fetchrow(
            "SELECT id, confirmed, confirm_token FROM cct_subscribers WHERE lower(email) = $1",
            email
        )

        if existing and existing["confirmed"]:
            # Déjà confirmé → mettre à jour les CCTs suivies silencieusement
            await conn.execute("""
                UPDATE cct_subscribers
                SET rs_numbers = $2, company = $3, lang = $4, updated_at = NOW()
                WHERE lower(email) = $1
            """, email, rs_list, company or None, lang)
            return JSONResponse({"status": "updated",
                                 "message": "Abonnement mis à jour."})

        # Créer ou recréer token
        confirm_token = _token()
        unsub_token   = _token()

        if existing:
            await conn.execute("""
                UPDATE cct_subscribers
                SET rs_numbers=$2, company=$3, lang=$4,
                    confirm_token=$5, unsub_token=$6, updated_at=NOW()
                WHERE lower(email)=$1
            """, email, rs_list, company or None, lang, confirm_token, unsub_token)
        else:
            await conn.execute("""
                INSERT INTO cct_subscribers
                  (email, company, lang, rs_numbers, confirm_token, unsub_token)
                VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (lower(email)) DO UPDATE SET
                  rs_numbers=$4, company=$2, lang=$3,
                  confirm_token=$5, unsub_token=$6, updated_at=NOW()
            """, email, company or None, lang, rs_list, confirm_token, unsub_token)

    # Envoyer email de confirmation
    html = _email_confirm_html(email, company, confirm_token, lang, rs_names)
    sent = await _send_email(
        email,
        {"fr":"✓ Confirmez vos alertes CCTswiss","de":"✓ Bestätigen Sie Ihre GAV-Alerts",
         "it":"✓ Conferma avvisi CCTswiss","en":"✓ Confirm your CCT alerts"}.get(lang,"✓ Confirmez vos alertes CCTswiss"),
        html
    )

    return JSONResponse({
        "status":  "pending_confirmation",
        "message": "Email de confirmation envoyé. Vérifiez votre boîte mail.",
        "email_sent": sent,
    })


# ── GET /api/alerts/confirm ───────────────────────────────────────────
@router.get("/confirm")
async def confirm(token: str = Query(...), pool: asyncpg.Pool = Depends(get_pool)):
    """
    Confirme l'abonnement (lien depuis l'email).
    Retourne une page HTML de confirmation.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, lang FROM cct_subscribers WHERE confirm_token = $1 AND confirmed = FALSE",
            token
        )
        if not row:
            return HTMLResponse(_page_html("error", "fr"), status_code=400)

        await conn.execute("""
            UPDATE cct_subscribers
            SET confirmed=TRUE, confirmed_at=NOW(), confirm_token=NULL, updated_at=NOW()
            WHERE id=$1
        """, row["id"])

    return HTMLResponse(_page_html("confirmed", row["lang"]))


# ── GET /api/alerts/unsubscribe ───────────────────────────────────────
@router.get("/unsubscribe")
async def unsubscribe(token: str = Query(...), pool: asyncpg.Pool = Depends(get_pool)):
    """Désinscription 1-clic depuis les emails."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, lang FROM cct_subscribers WHERE unsub_token = $1",
            token
        )
        if not row:
            return HTMLResponse(_page_html("unsub_notfound", "fr"), status_code=404)

        await conn.execute("DELETE FROM cct_subscribers WHERE id=$1", row["id"])

    return HTMLResponse(_page_html("unsubscribed", row["lang"]))


# ── GET /api/alerts/stats (admin) ─────────────────────────────────────
@router.get("/stats")
async def stats(x_seed_secret: str = Header(None), pool: asyncpg.Pool = Depends(get_pool)):
    if x_seed_secret != SEED_SECRET:
        raise HTTPException(403, "Forbidden")
    async with pool.acquire() as conn:
        total      = await conn.fetchval("SELECT COUNT(*) FROM cct_subscribers")
        confirmed  = await conn.fetchval("SELECT COUNT(*) FROM cct_subscribers WHERE confirmed=TRUE")
        pending    = total - confirmed
        top_ccts   = await conn.fetch("""
            SELECT unnest(rs_numbers) as rs, COUNT(*) as n
            FROM cct_subscribers WHERE confirmed=TRUE
            GROUP BY 1 ORDER BY 2 DESC LIMIT 10
        """)
        langs = await conn.fetch("""
            SELECT lang, COUNT(*) as n FROM cct_subscribers
            WHERE confirmed=TRUE GROUP BY 1 ORDER BY 2 DESC
        """)
    return JSONResponse({
        "total":      total,
        "confirmed":  confirmed,
        "pending":    pending,
        "top_ccts":   [dict(r) for r in top_ccts],
        "by_lang":    [dict(r) for r in langs],
    })


# ── POST /api/alerts/send (admin — déclenche manuellement) ────────────
@router.post("/send")
async def send_alerts(request: Request, x_seed_secret: str = Header(None),
                      pool: asyncpg.Pool = Depends(get_pool)):
    """
    Déclenche les alertes pour les rs_numbers modifiés depuis la dernière alerte.
    Normalement appelé par l'auto-updater — peut aussi être déclenché manuellement.
    """
    if x_seed_secret != SEED_SECRET:
        raise HTTPException(403, "Forbidden")

    body = await request.json()
    changed_rs: list[str] = body.get("changed_rs_numbers", [])
    if not changed_rs:
        return JSONResponse({"sent": 0, "message": "Aucune CCT modifiée transmise"})

    # Récupérer les détails des CCTs modifiées
    async with pool.acquire() as conn:
        cct_rows = await conn.fetch(
            "SELECT rs_number, name, emoji, scope_description_fr FROM cct WHERE rs_number = ANY($1)",
            changed_rs
        )
        ccts_info = {r["rs_number"]: dict(r) for r in cct_rows}

        # Trouver les abonnés concernés
        subscribers = await conn.fetch("""
            SELECT id, email, lang, rs_numbers, unsub_token
            FROM cct_subscribers
            WHERE confirmed = TRUE
              AND rs_numbers && $1::text[]
        """, changed_rs)

    sent = 0
    errors = []

    for sub in subscribers:
        try:
            # Filtrer les CCTs modifiées que cet abonné suit vraiment
            sub_changes = [
                ccts_info[rs] for rs in changed_rs
                if rs in (sub["rs_numbers"] or []) and rs in ccts_info
            ]
            if not sub_changes:
                continue

            html = _email_alert_html(
                sub["email"], sub_changes, sub["unsub_token"], sub["lang"]
            )
            nb = len(sub_changes)
            subjects = {
                "fr": f"🔔 {nb} CCT{'s' if nb>1 else ''} mise{'s' if nb>1 else ''} à jour — CCTswiss.ch",
                "de": f"🔔 {nb} GAV aktualisiert — CCTswiss.ch",
                "it": f"🔔 {nb} CCL aggiornati — CCTswiss.ch",
                "en": f"🔔 {nb} CLA updated — CCTswiss.ch",
            }
            ok = await _send_email(sub["email"], subjects.get(sub["lang"], subjects["fr"]), html)
            if ok:
                sent += 1
                async with pool.acquire() as conn2:
                    await conn2.execute("""
                        UPDATE cct_subscribers
                        SET last_alerted_at=NOW(), alert_count=alert_count+1, updated_at=NOW()
                        WHERE id=$1
                    """, sub["id"])
        except Exception as e:
            errors.append(f"{sub['email']}: {str(e)[:80]}")

    log.info(f"[Alerts] Envoyé {sent} alertes pour {len(changed_rs)} CCTs modifiées")
    return JSONResponse({"sent": sent, "errors": errors, "subscribers_matched": len(subscribers)})


# ── Pages HTML de retour (confirm / unsub / error) ────────────────────
def _page_html(state: str, lang: str) -> str:
    messages = {
        "confirmed": {
            "fr": ("✅ Abonnement confirmé !", "Vous recevrez désormais un email dès qu'une convention collective que vous suivez est mise à jour sur Fedlex.", "#0A0A0A"),
            "de": ("✅ Abonnement bestätigt!", "Sie erhalten eine E-Mail, sobald ein von Ihnen verfolgter GAV auf Fedlex aktualisiert wird.", "#0A0A0A"),
            "en": ("✅ Subscription confirmed!", "You'll receive an email whenever a tracked CLA is updated on Fedlex.", "#0A0A0A"),
        },
        "unsubscribed": {
            "fr": ("Désinscription effectuée", "Vous ne recevrez plus d'alertes de CCTswiss.ch. Vos données ont été supprimées.", "#555"),
            "de": ("Abmeldung erfolgreich", "Sie erhalten keine Benachrichtigungen mehr von CCTswiss.ch. Ihre Daten wurden gelöscht.", "#555"),
            "en": ("Unsubscribed", "You'll no longer receive alerts from CCTswiss.ch. Your data has been deleted.", "#555"),
        },
        "error": {
            "fr": ("Lien invalide ou expiré", "Ce lien de confirmation n'est plus valide (déjà utilisé ou expiré). Réabonnez-vous sur CCTswiss.ch.", "#C8102E"),
            "de": ("Ungültiger Link", "Dieser Bestätigungslink ist nicht mehr gültig. Bitte melden Sie sich erneut auf CCTswiss.ch an.", "#C8102E"),
            "en": ("Invalid link", "This confirmation link is no longer valid. Please subscribe again on CCTswiss.ch.", "#C8102E"),
        },
        "unsub_notfound": {
            "fr": ("Déjà désinscrit", "Cet abonnement n'existe pas ou a déjà été supprimé.", "#555"),
            "de": ("Bereits abgemeldet", "Dieses Abonnement existiert nicht oder wurde bereits gelöscht.", "#555"),
            "en": ("Already unsubscribed", "This subscription doesn't exist or was already deleted.", "#555"),
        },
    }
    m = messages.get(state, messages["error"])
    title, body, color = m.get(lang, m.get("fr", m.get("en")))
    icons = {"confirmed":"✅","unsubscribed":"👋","error":"❌","unsub_notfound":"👋"}
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>CCTswiss.ch</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f3ef;
     min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;padding:20px}}
.card{{background:#fff;border-radius:10px;max-width:460px;width:100%;
       box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden}}
.top{{background:#0A0A0A;padding:20px 24px;display:flex;align-items:center;gap:10px}}
.logo-box{{background:#C8102E;border-radius:6px;width:30px;height:30px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:900;color:#fff;font-family:monospace}}
.logo-name{{color:#fff;font-weight:700;font-size:16px}}
.body{{padding:32px 24px;text-align:center}}
.icon{{font-size:48px;margin-bottom:16px}}
h2{{color:#0A0A0A;font-size:20px;margin:0 0 12px}}
p{{color:#666;font-size:14px;line-height:1.6;margin:0 0 24px}}
a.btn{{display:inline-block;background:#C8102E;color:#fff;padding:12px 28px;
       border-radius:6px;text-decoration:none;font-weight:700;font-size:14px}}
.small{{font-size:11px;color:#999;margin-top:16px}}
</style></head><body>
<div class="card">
  <div class="top">
    <div class="logo-box">CCT</div>
    <span class="logo-name">swiss.ch</span>
  </div>
  <div class="body">
    <div class="icon">{icons.get(state,'ℹ️')}</div>
    <h2>{title}</h2>
    <p>{body}</p>
    <a href="{BASE_URL}" class="btn">← cctswiss.ch</a>
    <p class="small">© CCTswiss.ch · Groupe NEO · Vos données ne sont jamais vendues ni partagées.</p>
  </div>
</div>
</body></html>"""
