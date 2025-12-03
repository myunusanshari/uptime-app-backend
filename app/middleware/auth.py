"""
Middleware for API endpoints - Authentication, Logging, Rate Limiting
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable
import logging
import time
from datetime import datetime, timedelta
from collections import defaultdict
import secrets
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Load API keys from environment variables
VALID_API_KEYS = {}

# Load primary API key
api_key = os.getenv("API_KEY")
if api_key:
    VALID_API_KEYS[api_key] = "Primary Client"

# Load additional API keys (API_KEY_1, API_KEY_2, etc.)
for i in range(1, 10):
    key = os.getenv(f"API_KEY_{i}")
    name = os.getenv(f"API_KEY_{i}_NAME", f"Client {i}")
    if key:
        VALID_API_KEYS[key] = name

# Fallback for development (if no keys in .env)
if not VALID_API_KEYS:
    logger.warning("⚠️ No API keys found in .env file! Using default key for development.")
    VALID_API_KEYS["your-api-key-here"] = "Development Client"

# Rate limiting storage (domain_id -> list of timestamps)
rate_limit_storage = defaultdict(list)
RATE_LIMIT_REQUESTS = 400  # requests
RATE_LIMIT_WINDOW = 60  # seconds


def verify_api_key(api_key: str) -> bool:
    """Verify if API key is valid"""
    return api_key in VALID_API_KEYS


def get_client_name(api_key: str) -> str:
    """Get client name from API key"""
    return VALID_API_KEYS.get(api_key, "Unknown")


def check_rate_limit(domain_id: int) -> tuple[bool, int]:
    """
    Check if domain has exceeded rate limit.
    Returns: (is_allowed, requests_remaining)
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    # Clean old requests
    rate_limit_storage[domain_id] = [
        ts for ts in rate_limit_storage[domain_id] 
        if ts > window_start
    ]
    
    current_requests = len(rate_limit_storage[domain_id])
    
    if current_requests >= RATE_LIMIT_REQUESTS:
        return False, 0
    
    # Add current request
    rate_limit_storage[domain_id].append(now)
    
    return True, RATE_LIMIT_REQUESTS - current_requests - 1


async def api_key_middleware(request: Request, call_next: Callable):
    """
    Middleware to verify API key in request headers.
    Only applies to /events routes.
    """
    # Skip middleware for non-events routes
    if not request.url.path.startswith("/events"):
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key.replace("Bearer ", "")
    
    # Verify API key
    if not api_key or not verify_api_key(api_key):
        logger.warning(f"❌ Invalid API key attempt from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Invalid or missing API key",
                "message": "Please provide a valid API key in X-API-Key header"
            }
        )
    
    # Add client info to request state
    request.state.client_name = get_client_name(api_key)
    request.state.api_key = api_key
    
    logger.info(f"✅ Authenticated: {request.state.client_name}")
    
    # Continue to next middleware/endpoint
    response = await call_next(request)
    return response


async def rate_limit_middleware(request: Request, call_next: Callable):
    """
    Middleware to enforce rate limiting per domain.
    Only applies to /events routes.
    """
    # Skip middleware for non-events routes
    if not request.url.path.startswith("/events"):
        return await call_next(request)
    
    # Try to get domain_id from request body (for POST requests)
    if request.method == "POST":
        try:
            # Read body
            body = await request.body()
            
            # Parse JSON to get domain_id
            import json
            data = json.loads(body) if body else {}
            domain_id = data.get("domain_id")
            
            if domain_id:
                # Check rate limit
                is_allowed, remaining = check_rate_limit(domain_id)
                
                if not is_allowed:
                    logger.warning(f"⚠️ Rate limit exceeded for domain {domain_id}")
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests for domain {domain_id}. Try again later.",
                            "retry_after": RATE_LIMIT_WINDOW
                        }
                    )
                
                # Add remaining requests to response header
                request.state.rate_limit_remaining = remaining
            
            # Restore body for endpoint to read
            async def receive():
                return {"type": "http.request", "body": body}
            
            request._receive = receive
            
        except Exception as e:
            logger.error(f"Error in rate limit middleware: {e}")
            # Continue anyway if parsing fails
    
    response = await call_next(request)
    
    # Add rate limit headers to response
    if hasattr(request.state, "rate_limit_remaining"):
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW)
    
    return response


async def logging_middleware(request: Request, call_next: Callable):
    """
    Middleware to log all requests and responses.
    Logs timing, status, and details.
    """
    start_time = time.time()
    
    # Log request
    client_ip = request.client.host if request.client else "unknown"
    client_name = getattr(request.state, "client_name", "Anonymous")
    
    logger.info(f"📥 {request.method} {request.url.path} from {client_ip} ({client_name})")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # ms
        
        # Log response
        status_emoji = "✅" if response.status_code < 400 else "❌"
        logger.info(
            f"{status_emoji} {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration:.0f}ms)"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{duration:.2f}ms"
        
        return response
        
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"❌ {request.method} {request.url.path} → ERROR ({duration:.0f}ms): {str(e)}")
        raise


def generate_api_key() -> str:
    """Generate a new secure API key"""
    return secrets.token_urlsafe(32)


def add_api_key(key: str, client_name: str):
    """Add a new API key"""
    VALID_API_KEYS[key] = client_name
    logger.info(f"✅ Added API key for: {client_name}")


def remove_api_key(key: str):
    """Remove an API key"""
    if key in VALID_API_KEYS:
        client_name = VALID_API_KEYS[key]
        del VALID_API_KEYS[key]
        logger.info(f"🗑️ Removed API key for: {client_name}")
        return True
    return False
