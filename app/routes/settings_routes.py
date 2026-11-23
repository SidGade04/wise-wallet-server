# settings_routes.py - Updated with additional endpoints
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from ..core.auth import get_current_user

from ..models.settings_models import (
    ProfileOut, ProfileUpdate,
    NotificationSettingsUpdate, PreferencesUpdate,
    PortalSessionResponse, SuccessMessage,
)
from ..services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["settings"])

# Lazy service initialization to prevent import-time errors
_settings_service = None

def get_settings_service():
    global _settings_service
    if _settings_service is None:
        try:
            _settings_service = SettingsService()
        except Exception as e:
            logger.error(f"Failed to initialize SettingsService: {e}")
            raise HTTPException(status_code=500, detail="Settings service not available")
    return _settings_service

# ---------- Profile ----------
@router.get("/profile", response_model=ProfileOut)
async def get_profile(current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        data = await svc.get_profile(current_user["user_id"])
        return ProfileOut(id=str(data["id"]), email=data["email"], full_name=data.get("full_name"))
    except Exception as e:
        logger.error(f"Failed to get profile for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/profile", response_model=ProfileOut)
async def update_profile(body: ProfileUpdate, current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        data = await svc.update_profile(current_user["user_id"], body.full_name, body.email)
        return ProfileOut(**data)
    except Exception as e:
        logger.error(f"Failed to update profile for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Notifications ----------
@router.get("/settings/notifications")
async def get_notifications(current_user=Depends(get_current_user)):
    """Get current notification settings"""
    try:
        svc = get_settings_service()
        data = await svc.get_notifications(current_user["user_id"])
        return data
    except Exception as e:
        logger.error(f"Failed to get notifications for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/settings/notifications", response_model=SuccessMessage)
async def update_notifications(body: NotificationSettingsUpdate, current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        await svc.update_notifications(current_user["user_id"], body.emailWeekly, body.inAppAlerts)
        return SuccessMessage(message="Notification settings updated")
    except Exception as e:
        logger.error(f"Failed to update notifications for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Preferences ----------
@router.get("/settings/preferences")
async def get_preferences(current_user=Depends(get_current_user)):
    """Get current preferences"""
    try:
        svc = get_settings_service()
        data = await svc.get_preferences(current_user["user_id"])
        return data
    except Exception as e:
        logger.error(f"Failed to get preferences for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/settings/preferences", response_model=PreferencesUpdate)
async def update_preferences(body: PreferencesUpdate, current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        updated = await svc.update_preferences(
            user_id=current_user["user_id"],
            email=current_user.get("email"),  # <-- pass email
            theme=body.theme,
            currency=body.currency,
            timezone=body.timezone,
        )
        return {
            "theme": updated.get("pref_theme"),
            "currency": updated.get("pref_currency"),
            "timezone": updated.get("pref_timezone"),
        }
    except Exception as e:
        logger.error(f"Failed to update preferences for user {current_user.get('user_id')}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Billing Portal ----------
@router.post("/billing/portal", response_model=PortalSessionResponse)
async def create_billing_portal(http_request: Request, current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        url = await svc.create_billing_portal(
            current_user["user_id"], origin=http_request.headers.get("origin")
        )
        return PortalSessionResponse(url=url)
    except Exception as e:
        logger.error(f"Failed to create billing portal for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Data Export ----------
@router.post("/data/export")
async def export_data(current_user=Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        logger.info(f"Starting data export for user: {user_id}")
        
        svc = get_settings_service()
        content = await svc.export_user_zip(user_id)
        
        headers = {"Content-Disposition": 'attachment; filename="wise-wallet-export.zip"'}
        return StreamingResponse(iter([content]), media_type="application/zip", headers=headers)
        
    except Exception as e:
        logger.error(f"Failed to export data for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data export failed: {str(e)}")

# ---------- Account Deletion ----------
@router.delete("/account", response_model=SuccessMessage)
async def delete_account(current_user=Depends(get_current_user)):
    try:
        svc = get_settings_service()
        await svc.delete_account(current_user["user_id"])
        return SuccessMessage(message="Account deleted successfully")
    except Exception as e:
        logger.error(f"Failed to delete account for user {current_user.get('user_id')}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Add these GET endpoints to your settings_routes.py
