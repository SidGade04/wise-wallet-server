from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Literal

# --- Profile ---
class ProfileOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None

class ProfileUpdate(BaseModel):
    full_name: str
    email: EmailStr

# --- Notifications / Preferences ---
class NotificationSettingsUpdate(BaseModel):
    emailWeekly: bool = Field(..., description="Weekly email summary")
    inAppAlerts: bool = Field(..., description="In-app notifications")

class PreferencesUpdate(BaseModel):
    theme: Literal["light", "dark", "system"]
    currency: str = Field(min_length=1)
    timezone: str = Field(min_length=1)

# --- Billing ---
class PortalSessionResponse(BaseModel):
    url: HttpUrl

# --- Generic ---
class SuccessMessage(BaseModel):
    ok: bool = True
    message: str = "ok"
