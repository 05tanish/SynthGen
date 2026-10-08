from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

def _sanitise_db_url(url: str) -> str:
    """Strip query params unsupported by psycopg2 (e.g. channel_binding from Neon URLs)."""
    _UNSUPPORTED = {"channel_binding"}
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    filtered = {k: v for k, v in qs.items() if k not in _UNSUPPORTED}
    clean = parsed._replace(query=urlencode(filtered, doseq=True))
    return urlunparse(clean)

_db_url = _sanitise_db_url(settings.DATABASE_URL)
connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
engine = create_engine(
    _db_url,
    connect_args=connect_args,
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=300,    # Recycle connections every 5 minutes (prevents Neon timeout)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
