"""
Database connection and session management.
"""
from typing import Generator, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from backend.api.core.config import settings
from backend.api.core.logging import get_logger

logger = get_logger(__name__)

# Create engine with connection pooling
engine = None
SessionLocal = None


def init_database():
    """Initialize database engine and session factory."""
    global engine, SessionLocal

    try:
        engine = create_engine(
            settings.database_url_computed,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_pre_ping=True,
            poolclass=QueuePool,
        )

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

        logger.info("Database engine initialized")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Usage:
        @router.get("/example")
        async def example(db: Session = Depends(get_db)):
            ...
    """
    global SessionLocal

    if SessionLocal is None:
        init_database()

    if SessionLocal is None:
        # Return a mock session for demo mode
        logger.warning("Database not available, running in demo mode")
        yield MockSession()
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def check_db_health(db: Session) -> bool:
    """Check database health by executing a simple query."""
    try:
        if isinstance(db, MockSession):
            return False
        db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


class MockSession:
    """
    Mock database session for demo mode when database is unavailable.
    Returns empty results for all queries.
    """

    def execute(self, query, params=None):
        """Execute a query (returns mock result)."""
        return MockResult()

    def query(self, *args, **kwargs):
        """Query (returns mock query)."""
        return MockQuery()

    def add(self, obj):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def refresh(self, obj):
        pass


class MockResult:
    """Mock query result."""

    def fetchall(self):
        return []

    def fetchone(self):
        return None

    def scalar(self):
        return 0


class MockQuery:
    """Mock query builder."""

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def offset(self, n):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def count(self):
        return 0

    def join(self, *args, **kwargs):
        return self

    def outerjoin(self, *args, **kwargs):
        return self

    def group_by(self, *args):
        return self

    def having(self, *args):
        return self
