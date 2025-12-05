import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Firebase Admin SDK initialization
firebase_initialized = False
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    
    # Path to service account JSON
    service_account_path = Path(__file__).parent.parent.parent / "firebase-service-account.json"
    
    if not firebase_admin._apps:
        if service_account_path.exists():
            cred = credentials.Certificate(str(service_account_path))
            firebase_admin.initialize_app(cred)
            firebase_initialized = True
            print(f"✅ Firebase Admin SDK initialized successfully")
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            print(f"⚠️ Firebase service account file not found at {service_account_path}")
            logger.warning(f"Firebase service account file not found at {service_account_path}")
    else:
        firebase_initialized = True
        print("✅ Firebase Admin SDK already initialized")
    
except ImportError as e:
    print(f"⚠️ firebase-admin not installed: {e}")
    logger.warning("firebase-admin not installed. Run: pip install firebase-admin")
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
    logger.error(f"Error initializing Firebase: {e}")


def send_fcm(to: str, title: str, body: str, sound="default", data=None, channel_id="default"):
    """Send a notification via Firebase Cloud Messaging.

    Args:
        to: Topic (e.g., "/topics/all") or device token
        title: Notification title
        body: Notification body
        sound: Sound to play (default: "default")
        data: Additional data payload
        channel_id: Android notification channel ID (default: "default")
    """
    if not firebase_initialized:
        logger.warning("Firebase Admin SDK not initialized; skipping push send")
        return {"error": "Firebase Admin SDK not initialized"}

    try:
        # Ensure all data values are strings (FCM requirement)
        if data:
            data = {k: str(v) if v is not None else "" for k, v in data.items()}
        else:
            data = {}
        
        logger.info(f"📤 Preparing FCM notification:")
        logger.info(f"  → Title: {title}")
        logger.info(f"  → Sound: {sound}")
        logger.info(f"  → Channel ID: {channel_id}")
        logger.info(f"  → Data payload: {data}")
        
        # Determine if it's a topic or device token
        if to.startswith("/topics/"):
            topic = to.replace("/topics/", "")
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data,
                topic=topic,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound=sound,
                        priority='high',
                        channel_id=channel_id,  # Required for custom sounds
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                        )
                    )
                )
            )
        else:
            # Device token - Send as DATA-ONLY message for custom sounds
            # Android notification channels ignore FCM notification sound,
            # so we send data-only and let the app handle the notification
            data_with_notification = data.copy() if data else {}
            data_with_notification.update({
                'title': title,
                'body': body,
                'sound': sound,
                'channel_id': channel_id,
            })
            
            message = messaging.Message(
                # NO notification payload - data only
                data=data_with_notification,
                token=to,
                android=messaging.AndroidConfig(
                    priority='high',
                    # No AndroidNotification - data-only message
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound=sound,
                            badge=1,
                        )
                    )
                )
            )

        logger.info(f"Sending FCM notification to {to}: {title}")
        print(f"📤 Sending FCM: {title} -> {to}")
        print(f"📦 Data payload: {data}")
        response = messaging.send(message)
        logger.info(f"FCM notification sent successfully: {response}")
        print(f"✅ FCM sent successfully: {response}")
        return {"success": True, "message_id": response}
        
    except Exception as exc:
        logger.error(f"Failed sending FCM message to {to}: {exc}", exc_info=True)
        print(f"❌ FCM send failed: {exc}")
        return {"error": "failed_to_send", "details": str(exc)}


def send_to_all_devices(devices, title: str, body: str, sound="default", data=None, channel_id="default"):
    """Send notification to all registered device tokens.
    
    Args:
        devices: List of DeviceToken model instances
        title: Notification title
        body: Notification body
        sound: Notification sound (default: "default")
        data: Optional data payload dict
        channel_id: Android notification channel ID (default: "default")
        
    Returns:
        Dict with success/failure counts and results
    """
    if not devices:
        logger.info("No devices registered, skipping notifications")
        print("⚠️ No devices registered for notifications")
        return {"success": 0, "failed": 0, "total": 0}
    
    results = {"success": 0, "failed": 0, "total": len(devices), "details": []}
    
    for device in devices:
        try:
            result = send_fcm(
                to=device.token,
                title=title,
                body=body,
                sound=sound,
                data=data,
                channel_id=channel_id  # Pass channel_id to send_fcm
            )
            
            if result.get("error"):
                results["failed"] += 1
                results["details"].append({
                    "token": device.token[:20] + "...",
                    "platform": device.platform,
                    "status": "failed",
                    "error": result.get("error")
                })
            else:
                results["success"] += 1
                results["details"].append({
                    "token": device.token[:20] + "...",
                    "platform": device.platform,
                    "status": "success",
                    "message_id": result.get("message_id")
                })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "token": device.token[:20] + "...",
                "platform": device.platform,
                "status": "failed",
                "error": str(e)
            })
            logger.exception(f"Error sending to device {device.id}: {e}")
    
    logger.info(f"Notification batch complete: {results['success']}/{results['total']} successful")
    print(f"📊 Notification batch: {results['success']}/{results['total']} successful, {results['failed']} failed")
    return results

