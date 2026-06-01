# Thread-safe SQLite setup
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import sys
from pathlib import Path

# Need to ensure config can be imported if this is run from anywhere
sys.path.append(str(Path(__file__).parent.parent))
from config import DB_URL

engine = create_engine(
    DB_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    poolclass=NullPool,
    echo=False,
)

# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Safe for desktop
)

def init_db():
    from database.models import Base
    Base.metadata.create_all(bind=engine)