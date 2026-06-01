import logging
from contextlib import contextmanager

# Need to ensure imports work from anywhere
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.engine import SessionLocal

logger = logging.getLogger(__name__)

@contextmanager
def get_session():
    """Provides a transactional database session scope.
    Services are responsible for calling session.commit() explicitly.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.exception("DB session error — rolled back: %s", e)
        raise
    finally:
        session.close()
