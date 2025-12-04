from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..services.analytics_service import (
    get_today_stats,
    get_domain_analytics
)

router = APIRouter()

@router.get("/today")
def today_stats(db: Session = Depends(get_db)):
    return get_today_stats(db)


@router.get("/domain/{domain_id}")
def analytics_domain(domain_id: int, days: int = 7, db: Session = Depends(get_db)):
    """
    Get domain analytics for specified time range
    days: 1 (24h), 7 (week), 30 (month)
    """
    return get_domain_analytics(db, domain_id, days=days)
