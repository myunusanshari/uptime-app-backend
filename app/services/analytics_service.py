from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, date, timedelta
from ..models.domain import Domain
from ..models.downtime_log import DowntimeLog
from ..models.daily_stats import DailyStats

def get_today_stats(db: Session):
    today = date.today()
    logs = db.query(DowntimeLog).filter(
        extract("year", DowntimeLog.start_time) == today.year,
        extract("month", DowntimeLog.start_time) == today.month,
        extract("day", DowntimeLog.start_time) == today.day
    ).all()

    total_incidents = len(logs)
    total_downtime = sum((log.duration_seconds or 0) for log in logs)

    if logs:
        worst_log = max(logs, key=lambda x: x.duration_seconds or 0)
        worst_domain_obj = db.query(Domain).filter(Domain.id == worst_log.domain_id).first()
        worst_domain = worst_domain_obj.name if worst_domain_obj else None
    else:
        worst_domain = None

    # MTTR (Mean Time To Repair) - Only count resolved incidents
    resolved_logs = [l for l in logs if l.resolved and l.duration_seconds]
    mttr = int(sum(l.duration_seconds for l in resolved_logs) / len(resolved_logs)) if resolved_logs else 0

    return {
        "total_incidents": total_incidents,
        "total_downtime": total_downtime,
        "worst_domain": worst_domain,
        "mttr": mttr
    }


def get_domain_analytics(db: Session, domain_id: int, days: int = 7):
    """
    Get analytics for a domain over specified time range
    days: 1 (24 hours), 7 (week), 30 (month)
    """
    today = date.today()
    start_date = today - timedelta(days=days-1)  # Today + (days-1) back = total days
    tomorrow = today + timedelta(days=1)  # Include future dates in case of timezone issues

    # Fetch all logs for the period - use wider date range for timezone safety
    logs = db.query(DowntimeLog).filter(
        DowntimeLog.domain_id == domain_id,
        DowntimeLog.start_time >= start_date - timedelta(days=1),  # Extra buffer
        DowntimeLog.start_time <= tomorrow  # Include tomorrow for timezone issues
    ).order_by(DowntimeLog.start_time.asc()).all()
    
    # Calculate metrics
    total_incidents = len(logs)
    total_downtime = sum((l.duration_seconds or 0) for l in logs)
    worst_duration = max([l.duration_seconds or 0 for l in logs], default=0)
    
    # MTTR (Mean Time To Repair) - Average downtime per incident
    # Only count resolved incidents (those with duration)
    resolved_logs = [l for l in logs if l.resolved and l.duration_seconds]
    mttr = int(sum(l.duration_seconds for l in resolved_logs) / len(resolved_logs)) if resolved_logs else 0
    
    # MTBF (Mean Time Between Failures) - Average uptime between incidents
    # Calculate time between consecutive incidents (from end of one to start of next)
    mtbf = 0
    if len(resolved_logs) >= 2:
        time_between_failures = []
        for i in range(1, len(resolved_logs)):
            prev_log = resolved_logs[i-1]
            current_log = resolved_logs[i]
            
            # Time from end of previous incident to start of current incident
            if prev_log.end_time and current_log.start_time:
                # Convert to seconds
                delta = (current_log.start_time - prev_log.end_time).total_seconds()
                if delta > 0:  # Only count positive intervals (uptime)
                    time_between_failures.append(delta)
                    print(f"   MTBF interval {i}: {delta}s ({delta/3600:.2f} hours)")
        
        if time_between_failures:
            mtbf = int(sum(time_between_failures) / len(time_between_failures))
            print(f"   MTBF calculation: {len(time_between_failures)} intervals, avg: {mtbf}s")
        else:
            # Fallback: if no intervals, calculate as (total_period - total_downtime) / (incidents - 1)
            if total_incidents > 1:
                total_period_seconds = 7 * 24 * 60 * 60
                total_uptime = total_period_seconds - total_downtime
                mtbf = int(total_uptime / (total_incidents - 1))
                print(f"   MTBF fallback: total_uptime={total_uptime}s / {total_incidents-1} intervals = {mtbf}s")
    elif total_incidents == 1:
        # Only one incident: MTBF is the uptime before or after the incident
        total_period_seconds = 7 * 24 * 60 * 60
        mtbf = int((total_period_seconds - total_downtime))
        print(f"   MTBF (single incident): {mtbf}s")
    
    # Calculate uptime percentage for the period
    # Total period in seconds (days * 24 * 60 * 60)
    total_period_seconds = days * 24 * 60 * 60
    uptime_seconds = total_period_seconds - total_downtime
    uptime_percentage = (uptime_seconds / total_period_seconds) * 100 if total_period_seconds > 0 else 100
    
    # Build stats - hourly for 24h view, daily for others
    daily_stats = []
    
    if days == 1:
        # Hourly data for 24-hour view
        now = datetime.now()
        for i in range(24):
            hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23-i)
            hour_end = hour_start + timedelta(hours=1)
            
            # Find logs that overlap with this hour
            hour_logs = []
            for log in logs:
                log_start = log.start_time
                log_end = log.end_time if log.end_time else datetime.now()
                
                # Check if log overlaps with this hour
                if log_start < hour_end and log_end > hour_start:
                    # Calculate overlap duration
                    overlap_start = max(log_start, hour_start)
                    overlap_end = min(log_end, hour_end)
                    overlap_seconds = (overlap_end - overlap_start).total_seconds()
                    hour_logs.append((log, overlap_seconds))
            
            # Calculate downtime for this hour (in seconds)
            hour_downtime = sum(overlap_seconds for _, overlap_seconds in hour_logs)
            hour_total_seconds = 60 * 60  # 3600 seconds per hour
            hour_uptime = hour_total_seconds - hour_downtime
            
            daily_stats.append({
                "date": hour_start.strftime("%H:%M"),  # Format as "HH:MM"
                "incidents": len(set(log.id for log, _ in hour_logs)),
                "total_downtime": int(hour_downtime),
                "uptime_minutes": round(hour_uptime / 60, 2),
                "downtime_minutes": round(hour_downtime / 60, 2),
            })
    else:
        # Daily data for 7-day and 30-day views
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_logs = [l for l in logs if l.start_time.date() == day]
            
            # Calculate uptime for this day (1440 minutes per day)
            day_total_minutes = 24 * 60
            day_downtime_minutes = sum((l.duration_seconds or 0) for l in day_logs) / 60
            day_uptime_minutes = day_total_minutes - day_downtime_minutes
            
            daily_stats.append({
                "date": day.isoformat(),
                "incidents": len(day_logs),
                "total_downtime": sum((l.duration_seconds or 0) for l in day_logs),
                "uptime_minutes": round(day_uptime_minutes, 2),
                "downtime_minutes": round(day_downtime_minutes, 2),
            })
    
    # Log for debugging
    print(f"📊 Generated analytics for domain {domain_id} ({days} days)")
    print(f"   Range: {start_date} to {today}")
    print(f"   Total incidents: {total_incidents}")
    print(f"   Total downtime: {total_downtime}s")
    print(f"   MTTR: {mttr}s ({mttr/60:.1f} minutes)")
    print(f"   MTBF: {mtbf}s ({mtbf/60:.1f} minutes)")
    print(f"   Uptime: {uptime_percentage:.2f}%")
    for stat in daily_stats:
        if stat["total_downtime"] > 0:
            print(f"   {stat['date']}: {stat['incidents']} incidents, {stat['total_downtime']}s downtime")
    
    return {
        "domain_id": domain_id,
        "total_incidents": total_incidents,
        "total_downtime": total_downtime,
        "mttr": mttr,  # Mean Time To Repair (seconds)
        "mtbf": mtbf,  # Mean Time Between Failures (seconds)
        "worst_duration": worst_duration,
        "uptime_percentage": round(uptime_percentage, 2),
        "logs": [
            {
                "id": log.id,
                "start_time": log.start_time,
                "end_time": log.end_time,
                "duration_seconds": log.duration_seconds,
                "resolved": log.resolved
            }
            for log in logs
        ],
        "daily_stats": daily_stats
    }
