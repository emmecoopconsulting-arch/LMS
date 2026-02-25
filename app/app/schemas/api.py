from datetime import date
from pydantic import BaseModel, Field


class CertificationCreate(BaseModel):
    cert_type: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=255)
    provider: str | None = None
    issued_date: date | None = None
    expiry_date: date
    notes: str | None = None


class SettingsUpdate(BaseModel):
    factorial_base_url: str = ""
    factorial_api_token: str = ""
    factorial_company_id: str = ""
    thresholds_csv: str = "90,60,30,14,7,1"
    recipient_emails: str = ""
    email_enabled: bool = True
    webhook_enabled: bool = False
