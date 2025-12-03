from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..database import Base

class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True)
    platform = Column(String)  # ios / android
    created_at = Column(DateTime(timezone=True), server_default=func.now())
