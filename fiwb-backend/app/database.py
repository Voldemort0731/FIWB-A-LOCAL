from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite — single-process only (Railway free tier without PostgreSQL addon)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        # Single connection pool for SQLite — prevents "database is locked"
        pool_size=1,
        max_overflow=0,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")      # Allows concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")    # Faster writes
        cursor.execute("PRAGMA busy_timeout=10000")    # Wait 10s before "locked" error
        cursor.execute("PRAGMA cache_size=-64000")     # 64MB cache
        cursor.close()

else:
    # PostgreSQL (production)
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=3,
        max_overflow=5,
        pool_timeout=60,        # Wait up to 60s for a connection
        pool_recycle=300,       # Recycle connections every 5 min (Railway drops idle ones)
        pool_pre_ping=True,     # Test connection before using it (handles dropped connections)
        connect_args={
            "connect_timeout": 30,          # 30s to establish connection
            "keepalives": 1,                # Enable TCP keepalives
            "keepalives_idle": 30,          # Send keepalive after 30s idle
            "keepalives_interval": 10,      # Retry keepalive every 10s
            "keepalives_count": 5,          # Give up after 5 failed keepalives
        }
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
