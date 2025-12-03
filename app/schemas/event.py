from pydantic import BaseModel
from datetime import datetime

class DownEvent(BaseModel):
    domain_id: int
    detected_at: datetime

class UpEvent(BaseModel):
    domain_id: int
    detected_at: datetime
