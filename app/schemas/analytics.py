from pydantic import BaseModel
from typing import List, Optional

class DailyStats(BaseModel):
    date: str
    incidents: int
    total_downtime: int
    uptime_minutes: Optional[float] = None
    downtime_minutes: Optional[float] = None

class DomainAnalytics(BaseModel):
    domain_id: int
    total_incidents: int
    total_downtime: int
    mttr: int  # Mean Time To Repair (seconds)
    mtbf: Optional[int] = 0  # Mean Time Between Failures (seconds)
    worst_duration: int
    uptime_percentage: Optional[float] = None
    logs: List[dict]
    daily_stats: List[DailyStats]

class SummaryAnalytics(BaseModel):
    total_incidents: int
    total_downtime: int
    worst_domain: Optional[str]
    mttr: int
    today_incidents: int
    today_downtime: int
