import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # If DB_URL is not provided, fall back to a local sqlite file for ease of local
    # development (this makes it easier for React Native developers to run locally
    # without a Postgres instance).
    DB_URL: str = os.getenv("DB_URL") or "sqlite:///./dev.db"

    # FCM server key should come from environment for security. If missing, the
    # notification code will behave gracefully (no hardcoded secrets).
    FCM_SERVER_KEY: Optional[str] = os.getenv("FCM_SERVER_KEY") or None

    PROJECT_NAME: str = os.getenv("PROJECT_NAME") or "Uptime Monitor API"


settings = Settings()
