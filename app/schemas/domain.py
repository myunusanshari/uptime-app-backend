from pydantic import BaseModel
from datetime import datetime

class DomainBase(BaseModel):
    name: str
    label: str | None = None
    custom_sound: str | None = None  # Deprecated - kept for backward compatibility
    custom_sound_down: str | None = None  # Custom sound filename for downtime alerts
    custom_sound_up: str | None = None  # Custom sound filename for recovery alerts
    sensitivity: int = 0
    ssl_enabled: bool = True

class DomainCreate(DomainBase):
    pass

class DomainUpdate(BaseModel):
    """Schema for updating a domain - all fields optional"""
    name: str | None = None
    label: str | None = None
    custom_sound: str | None = None  # Deprecated
    custom_sound_down: str | None = None
    custom_sound_up: str | None = None
    sensitivity: int | None = None
    ssl_enabled: bool | None = None



class DomainOut(DomainBase):
    id: int
    is_active: bool
    status: str = "up"
    
    # SSL Certificate fields
    ssl_expiry_date: datetime | None = None
    ssl_issuer: str | None = None
    ssl_subject: str | None = None
    ssl_days_until_expiry: int | None = None
    ssl_last_checked: datetime | None = None
    
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    class Config:
        orm_mode = True
