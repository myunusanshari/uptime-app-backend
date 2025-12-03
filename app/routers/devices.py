from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.orm import Session
from ..models.device_token import DeviceToken
from ..schemas.device import DeviceRegister
from ..dependencies import get_db
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_device(payload: DeviceRegister, request: Request, db: Session = Depends(get_db)):
    """Register a device token for push notifications"""
    # Try to get token from payload
    token = payload.token
    platform = payload.platform

    # Fallback to request body if not in payload
    if not token:
        try:
            body = await request.json()
            token = body.get("deviceToken") or body.get("token")
            platform = platform or body.get("platform")
        except Exception as e:
            logger.warning(f"Failed to parse request body: {e}")
            token = None

    # Validate token
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    # Validate platform
    if platform and platform not in ["android", "ios", "web"]:
        raise HTTPException(status_code=400, detail="Invalid platform")

    # Check if device already registered
    existing = db.query(DeviceToken).filter(DeviceToken.token == token).first()
    if existing:
        logger.info(f"Device token already registered: {token}")
        return {"message": "Already registered"}

    # Register new device
    try:
        device = DeviceToken(token=token, platform=platform or "unknown")
        db.add(device)
        db.commit()
        logger.info(f"New device registered: {token} ({platform})")
    except IntegrityError:
        db.rollback()
        logger.warning(f"Failed to register device (integrity error): {token}")

    return {"message": "Registered", "token": token}
