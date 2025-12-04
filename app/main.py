from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from .routers import domains, events, devices, sounds
from .routers import analytics
from .middleware import api_key_middleware, rate_limit_middleware, logging_middleware
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.cleanup_service import cleanup_old_logs
from app.services.ssl_service import get_ssl_certificate, should_alert_ssl_expiry, format_ssl_alert_message
from app.services.notification_service import send_to_all_devices
from app.models.domain import Domain
from app.models.device_token import DeviceToken
from datetime import datetime, timezone

# Scheduler is created here but started on application startup to avoid
# duplicate jobs when Uvicorn's auto-reload restarts the process.
scheduler = BackgroundScheduler()


def run_cleanup():
    db = SessionLocal()
    cleanup_old_logs(db)
    db.close()


def run_ssl_check():
    """Check SSL certificates for all domains and send notifications if expiring soon"""
    db = SessionLocal()
    try:
        # Get all domains with SSL checking enabled
        domains = db.query(Domain).filter(Domain.ssl_enabled == True).all()
        
        # Get all registered devices for notifications
        devices = db.query(DeviceToken).all()
        
        for domain in domains:
            print(f"🔒 Checking SSL for {domain.name}...")
            ssl_info = get_ssl_certificate(domain.name)
            
            if ssl_info and ssl_info.get('valid'):
                # Update domain with SSL info
                domain.ssl_expiry_date = ssl_info['expiry_date']
                domain.ssl_days_until_expiry = ssl_info['days_until_expiry']
                domain.ssl_issuer = ssl_info['issuer']
                domain.ssl_subject = ssl_info['subject']
                domain.ssl_last_checked = ssl_info['checked_at']
                
                days = ssl_info['days_until_expiry']
                print(f"✅ SSL OK for {domain.name}: expires in {days} days")
                
                # Check if we should send notification (less than 31 days)
                should_alert, severity = should_alert_ssl_expiry(days)
                
                if should_alert and days <= 30:  # Alert when 30 days or less
                    # Format notification message
                    title = "🔐 SSL Certificate Expiring Soon"
                    if days <= 0:
                        title = "🔴 SSL Certificate EXPIRED"
                    elif days <= 7:
                        title = "🚨 SSL Certificate Expiring SOON"
                    
                    body = format_ssl_alert_message(domain.name, days, ssl_info['expiry_date'])
                    
                    # Additional info for notification
                    expiry_formatted = ssl_info['expiry_date'].strftime('%Y-%m-%d %H:%M UTC')
                    body += f"\nExpires: {expiry_formatted}"
                    body += f"\nIssuer: {ssl_info['issuer']}"
                    
                    # Send notification to all devices
                    print(f"📢 Sending SSL expiry notification for {domain.name}")
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
                    print(f"✅ SSL notification sent: {result['success']}/{result['total']} successful")
                
            else:
                # SSL check failed
                domain.ssl_last_checked = ssl_info['checked_at'] if ssl_info else datetime.now(timezone.utc)
                domain.ssl_days_until_expiry = None
                print(f"❌ SSL check failed for {domain.name}: {ssl_info.get('error', 'Unknown error')}")
            
            db.commit()
            
    except Exception as e:
        print(f"❌ Error in SSL check job: {str(e)}")
        db.rollback()
    finally:
        db.close()


scheduler.add_job(run_cleanup, "cron", hour=3)  # run daily at 03:00
scheduler.add_job(run_ssl_check, "interval", hours=6)  # check SSL every 6 hours



# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Uptime Monitor API")

# Allow requests from React Native dev clients and other origins. For production,
# set a stricter allow_origins list via env if desired.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - they run in reverse order)
# 1. Logging (outermost - logs everything)
app.middleware("http")(logging_middleware)

# 2. Rate limiting (before API key check)
app.middleware("http")(rate_limit_middleware)

# 3. API key authentication (innermost - checks auth)
app.middleware("http")(api_key_middleware)

app.include_router(domains.router, prefix="/domains", tags=["Domains"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(sounds.router, prefix="/sounds", tags=["Sounds"])

@app.get("/")
def root():
    return {"message": "Uptime Monitor API running"}


@app.on_event("startup")
def start_scheduler():
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass
