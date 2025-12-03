from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

# Support sqlite fallback when DB_URL is not set (useful for local/dev runs).
db_url = settings.DB_URL

# If using sqlite, we need to pass connect_args to allow multi-threaded access
# from FastAPI/uvicorn worker threads.
connect_args = {}
if db_url.startswith("sqlite"):
	connect_args = {"check_same_thread": False}

engine = create_engine(db_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()
