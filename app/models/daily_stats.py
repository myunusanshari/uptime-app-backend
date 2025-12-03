from sqlalchemy import Column, Integer, Date, ForeignKey
from app.database import Base

class DailyStats(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey("domains.id"))
    date = Column(Date)
    total_incidents = Column(Integer, default=0)
    total_downtime = Column(Integer, default=0)
