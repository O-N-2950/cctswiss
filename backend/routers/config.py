"""
CCTswiss — /api/config
Sert la configuration publique côté client (GA4 ID, feature flags).
Les secrets restent dans les variables Railway — jamais exposés ici.
"""
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/config", tags=["config"])
async def get_config():
    """
    Configuration publique pour le frontend SPA.
    N'expose JAMAIS de secrets — uniquement les IDs publics (GA4, etc.)
    """
    return JSONResponse({
        # GA4 Measurement ID (format G-XXXXXXXXXX) — public par nature
        "ga_measurement_id": os.environ.get("GA_MEASUREMENT_ID", ""),
        # Feature flags (optionnel)
        "sentry_enabled":    bool(os.environ.get("SENTRY_DSN")),
        "env":               os.environ.get("RAILWAY_ENVIRONMENT", "production"),
    }, headers={
        # Cache 1h — rarement change en prod
        "Cache-Control": "public, max-age=3600",
    })
