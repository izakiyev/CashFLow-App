import logging
import os
from alembic.config import Config
from alembic import command
from database.engine import init_db
from config import ALEMBIC_INI

logger = logging.getLogger(__name__)

def run_migrations():
    """Run database setup and migrations using Alembic."""
    logger.info("Checking database schema...")
    try:
        # 1. Ensure tables exist (for a fresh DB)
        init_db()
        
        # 2. Run Alembic migrations to handle schema updates/drift
        logger.info("Running Alembic migrations...")
        alembic_cfg = Config(str(ALEMBIC_INI))
        
        # Use the DB_URL from our config
        from config import DB_URL
        alembic_cfg.set_main_option("sqlalchemy.url", DB_URL)
        
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database is up to date.")
    except Exception as e:
        logger.error(f"Migration error: {e}")

if __name__ == "__main__":
    run_migrations()
