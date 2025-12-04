from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.domain import Domain
from ..models.downtime_log import DowntimeLog
from ..models.device_token import DeviceToken
from ..schemas.event import DownEvent, UpEvent
from ..dependencies import get_db
from ..services.notification_service import send_to_all_devices
from ..utils.sound_utils import normalize_sound_name
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/down")
def domain_down(payload: DownEvent, db: Session = Depends(get_db)):
    """
    Handle domain DOWN event.
    Only sends notifications if domain status changes from UP to DOWN.
    Prevents duplicate notifications when domain is already down.
    Does not create duplicate downtime logs if already down.
    """
    # Get domain details
    domain = db.query(Domain).filter(Domain.id == payload.domain_id).first()
    domain_name = domain.name if domain else f"Domain #{payload.domain_id}"
    domain_label = domain.label if domain and domain.label else domain_name
    
    # Check current status BEFORE updating
    was_up = domain.is_active if domain else True  # If no domain record, assume it was up
    
    # Only create downtime log if domain was UP (status is changing)
    if was_up:
        # Create new downtime log
        log = DowntimeLog(
            domain_id=payload.domain_id,
            start_time=payload.detected_at,
            resolved=False
        )
        db.add(log)
        
        # Update domain status to DOWN
        if domain:
            domain.is_active = False
        
        db.commit()

        # Send notification to all devices
        devices = db.query(DeviceToken).all()
        
        # Use custom_sound_down if set, otherwise default
        # Ignore the deprecated custom_sound field
        raw_sound = domain.custom_sound_down if domain.custom_sound_down else "default_down"
        sound_name = normalize_sound_name(raw_sound)
        logger.info(f"🔊 DOWN notification sound: {sound_name} (custom_sound_down={domain.custom_sound_down})")
        
        notification_results = send_to_all_devices(
            devices=devices,
            title=f"🔴 {domain_name} DOWN",
            body=f"{domain_label} ({domain_name}) is currently unreachable",
            sound=sound_name,  # Use domain's custom sound or default
            channel_id="downtime_v3",  # Use downtime channel
            data={
                "type": "down",
                "domain_name": domain_name,
                "domain_label": domain_label,
                "sound": sound_name,  # Add sound to data payload for frontend
                "timestamp": payload.detected_at.isoformat()
            }
        )
        logger.info(f"✅ DOWN event for {domain_name}: log created, notification sent to {notification_results['success']}/{notification_results['total']} devices")
        
        return {
            "message": "Down recorded",
            "notifications": notification_results,
            "status_changed": True
        }
    else:
        # Domain was already DOWN, skip everything
        logger.info(f"⏭️ Skipped DOWN event for {domain_name} (already down, no log created)")
        
        return {
            "message": "Domain already down, no action taken",
            "notifications": {"total": 0, "success": 0, "failed": 0},
            "status_changed": False
        }

@router.post("/up")
def domain_up(payload: UpEvent, db: Session = Depends(get_db)):
    """
    Handle domain UP event (recovery).
    Only sends notifications if domain status changes from DOWN to UP.
    Prevents duplicate notifications when domain is already up.
    """
    # Get domain details
    domain = db.query(Domain).filter(Domain.id == payload.domain_id).first()
    domain_name = domain.name if domain else f"Domain #{payload.domain_id}"
    domain_label = domain.label if domain and domain.label else domain_name
    
    # Check current status BEFORE updating
    was_down = not domain.is_active if domain else False  # If no domain record, assume it wasn't down
    
    # Find active downtime log
    log = db.query(DowntimeLog)\
        .filter(DowntimeLog.domain_id == payload.domain_id, DowntimeLog.resolved == False)\
        .first()

    if not log:
        # No active downtime log found
        logger.info(f"⏭️ No active downtime log for {domain_name}, updating status only")
        if domain and not domain.is_active:
            domain.is_active = True
            db.commit()
        raise HTTPException(status_code=404, detail="No active downtime log")

    # Update downtime log
    log.end_time = payload.detected_at
    log.duration_seconds = int((log.end_time - log.start_time).total_seconds())
    log.resolved = True
    
    # Update domain status to UP
    if domain:
        domain.is_active = True
    
    db.commit()

    # Send notification ONLY if status changed from DOWN to UP
    notification_results = {"total": 0, "success": 0, "failed": 0}
    
    if was_down and log.duration_seconds > 0:
        # Status changed: DOWN -> UP, send notification to all devices
        
        # Format duration
        duration_seconds = log.duration_seconds
        if duration_seconds < 60:
            duration_text = f"{duration_seconds} seconds"
        elif duration_seconds < 3600:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_text = f"{minutes}m {seconds}s"
        else:
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            duration_text = f"{hours}h {minutes}m"
        
        devices = db.query(DeviceToken).all()
        
        # Use custom_sound_up if set, otherwise default
        # Ignore the deprecated custom_sound field
        raw_sound = domain.custom_sound_up if domain.custom_sound_up else "default_up"
        sound_name = normalize_sound_name(raw_sound)
        logger.info(f"🔊 UP notification sound: {sound_name} (custom_sound_up={domain.custom_sound_up})")
        
        notification_results = send_to_all_devices(
            devices=devices,
            title=f"✅ {domain_name} RECOVERED",
            body=f"{domain_label} ({domain_name}) is back online after {duration_text}",
            sound=sound_name,  # Use domain's custom sound or default
            channel_id="uptime_v3",  # Use uptime channel
            data={
                "type": "up",
                "domain_name": domain_name,
                "domain_label": domain_label,
                "duration": str(duration_seconds),
                "duration_formatted": duration_text,
                "sound": sound_name,  # Add sound to data payload for frontend
                "timestamp": payload.detected_at.isoformat()
            }
        )
        logger.info(f"✅ UP notification sent for {domain_name}: {notification_results['success']}/{notification_results['total']} devices")
    else:
        # Domain was already UP, skip notification
        logger.info(f"⏭️ Skipped UP notification for {domain_name} (already up or instant recovery)")

    return {
        "message": "Up updated",
        "duration": log.duration_seconds,
        "notifications": notification_results,
        "status_changed": was_down
    }
