from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.domain import Domain
from ..models.device_token import DeviceToken
from ..schemas.domain import DomainCreate, DomainOut
from ..dependencies import get_db
from ..services.ssl_service import get_ssl_certificate, should_alert_ssl_expiry, format_ssl_alert_message
from ..services.notification_service import send_to_all_devices

router = APIRouter()

@router.post("/", response_model=DomainOut)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    domain = Domain(**payload.dict())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    
    # Check SSL immediately after creation if enabled
    if domain.ssl_enabled:
        ssl_info = get_ssl_certificate(domain.name)
        if ssl_info and ssl_info.get('valid'):
            domain.ssl_expiry_date = ssl_info['expiry_date']
            domain.ssl_days_until_expiry = ssl_info['days_until_expiry']
            domain.ssl_issuer = ssl_info['issuer']
            domain.ssl_subject = ssl_info['subject']
            domain.ssl_last_checked = ssl_info['checked_at']
            db.commit()
            db.refresh(domain)
    
    return domain

@router.get("/", response_model=list[DomainOut])
def list_domains(db: Session = Depends(get_db)):
    domains = db.query(Domain).all()
    for d in domains:
        d.status = "up" if d.is_active else "down"
    return domains

# Get single domain by ID
@router.get("/{domain_id}", response_model=DomainOut)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    domain.status = "up" if domain.is_active else "down"
    return domain

# Update domain
@router.put("/{domain_id}", response_model=DomainOut)
def update_domain(domain_id: int, payload: DomainCreate, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(domain, key, value)
    db.commit()
    db.refresh(domain)
    return domain

# Delete domain
@router.delete("/{domain_id}")
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    db.delete(domain)
    db.commit()
    return {"message": "Domain deleted"}

# Check SSL certificate for a domain
@router.post("/{domain_id}/check-ssl")
def check_ssl(domain_id: int, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    ssl_info = get_ssl_certificate(domain.name)
    
    if ssl_info and ssl_info.get('valid'):
        domain.ssl_expiry_date = ssl_info['expiry_date']
        domain.ssl_days_until_expiry = ssl_info['days_until_expiry']
        domain.ssl_issuer = ssl_info['issuer']
        domain.ssl_subject = ssl_info['subject']
        domain.ssl_last_checked = ssl_info['checked_at']
        db.commit()
        
        # Check if notification should be sent (less than 31 days)
        days = ssl_info['days_until_expiry']
        should_alert, severity = should_alert_ssl_expiry(days)
        notification_sent = False
        
        if should_alert and days <= 30:
            # Get all devices
            devices = db.query(DeviceToken).all()
            
            if devices:
                # Format notification
                title = "🔐 SSL Certificate Expiring Soon"
                if days <= 0:
                    title = "🔴 SSL Certificate EXPIRED"
                elif days <= 7:
                    title = "🚨 SSL Certificate Expiring SOON"
                
                body = format_ssl_alert_message(domain.name, days, ssl_info['expiry_date'])
                expiry_formatted = ssl_info['expiry_date'].strftime('%Y-%m-%d %H:%M UTC')
                body += f"\nExpires: {expiry_formatted}"
                body += f"\nIssuer: {ssl_info['issuer']}"
                
                # Send notification
                result = send_to_all_devices(
                    devices=devices,
                    title=title,
                    body=body,
                    sound=domain.custom_sound or "default_down.mp3",
                    data={
                        "type": "ssl_expiry",
                        "domain_id": str(domain.id),
                        "domain_name": domain.name,
                        "days_until_expiry": str(days),
                        "severity": severity,
                        "expiry_date": ssl_info['expiry_date'].isoformat()
                    }
                )
                notification_sent = result['success'] > 0
        
        return {
            "success": True,
            "message": "SSL certificate checked successfully",
            "notification_sent": notification_sent,
            "ssl_info": {
                "expiry_date": ssl_info['expiry_date'].isoformat(),
                "days_until_expiry": ssl_info['days_until_expiry'],
                "issuer": ssl_info['issuer'],
                "subject": ssl_info['subject'],
                "severity": severity if should_alert else "normal"
            }
        }
    else:
        domain.ssl_last_checked = ssl_info['checked_at'] if ssl_info else None
        db.commit()
        
        return {
            "success": False,
            "message": "SSL certificate check failed",
            "error": ssl_info.get('error', 'Unknown error') if ssl_info else 'Failed to check SSL'
        }
