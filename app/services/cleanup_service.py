from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.downtime_log import DowntimeLog
from app.models.daily_stats import DailyStats

def cleanup_old_logs(db: Session):
    limit_date = datetime.utcnow() - timedelta(days=90)

    old_logs = db.query(DowntimeLog).filter(
        DowntimeLog.start_time < limit_date
    ).all()

    for log in old_logs:
        date = log.start_time.date()

        stats = db.query(DailyStats).filter_by(
            domain_id=log.domain_id,
            date=date
        ).first()

        if not stats:
            stats = DailyStats(
                domain_id=log.domain_id,
                date=date,
                total_incidents=1,
                total_downtime=log.duration_seconds or 0
            )
            db.add(stats)
        else:
            stats.total_incidents += 1
            stats.total_downtime += log.duration_seconds or 0

        db.delete(log)

    db.commit()
