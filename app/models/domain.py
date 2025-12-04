from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..database import Base

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    label = Column(String, nullable=True)
    custom_sound = Column(String, nullable=True)  # Deprecated - kept for backward compatibility
    custom_sound_down = Column(String, nullable=True)  # Custom sound for downtime notifications
    custom_sound_up = Column(String, nullable=True)  # Custom sound for recovery notifications
    is_active = Column(Boolean, default=True)
    sensitivity = Column(Integer, default=0)  # minimum downtime (seconds) before notify
    
    # SSL Certificate fields
    ssl_enabled = Column(Boolean, default=True)  # Check SSL certificate
    ssl_expiry_date = Column(DateTime(timezone=True), nullable=True)  # When cert expires
    ssl_issuer = Column(String, nullable=True)  # Certificate issuer
    ssl_subject = Column(String, nullable=True)  # Certificate subject
    ssl_days_until_expiry = Column(Integer, nullable=True)  # Days remaining
    ssl_last_checked = Column(DateTime(timezone=True), nullable=True)  # Last SSL check time
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
