from pydantic import BaseModel
from typing import Optional

class DeviceRegister(BaseModel):
    token: Optional[str] = None
    platform: Optional[str] = None
    deviceToken: Optional[str] = None  # Fallback for Firebase Web SDK
    class Config:
        allow_population_by_field_name = True
