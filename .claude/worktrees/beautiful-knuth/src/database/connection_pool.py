"""
MARTA Platform - Optimized Database Connection Pool Configuration
High-performance database connections with connection pooling, async support, and monitoring
"""
import os
import asyncio
import logging
import time
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
import threading
from functools import wraps

import psycopg2
from psycopg2 import pool as psycopg2_pool
from psycopg2.extras import RealDictCursor, execute_values
import asyncpg
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool
import pandas as pd
import structlog

from config.settings import settings

# Configure logging
logger = structlog.get_logger(__name__)

class DatabaseConnectionPool:
    """
    High-performance database connection pool with monitoring and optimization features
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._sync_engine: Optional[Engine] = None
        self._async_pool: Optional[asyncpg.Pool] = None
        self._session_factory: Optional[sessionmaker] = None
        self._psycopg2_pool: Optional[psycopg2_pool.ThreadedConnectionPool] = None
        
        # Connection statistics
        self._connection_stats = {
            'total_connections_created': 0,
            'active_connections': 0,
            'connection_errors': 0,
            'query_count': 0,
            'total_query_time': 0.0,
            'last_reset': datetime.now()
        }
        self._stats_lock = threading.Lock()
        
        # Initialize connection pools
        self._initialize_pools()
    
    def _initialize_pools(self):
        """Initialize all database connection pools"""
        try:
            self._initialize_sqlalchemy_pool()
            self._initialize_psycopg2_pool()
            logger.info("Database connection pools initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database pools", error=str(e))
            raise
    
    def _initialize_sqlalchemy_pool(self):
        """Initialize SQLAlchemy connection pool with optimizations"""
        # Construct database URL with optimized parameters
        db_url = (
            f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@"
            f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
            f"?sslmode=prefer&connect_timeout=10&application_name=marta_platform"
        )
        
        # Create engine with optimized pool settings
        self._sync_engine = create_engine(
            db_url,
            # Connection Pool Settings
            poolclass=QueuePool,
            pool_size=20,  # Number of connections to maintain
            max_overflow=30,  # Additional connections when pool is full
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections every hour
            pool_pre_ping=True,  # Validate connections before use
            pool_reset_on_return='commit',  # Reset connections on return
            
            # Engine Settings
            echo=settings.LOG_LEVEL == 'DEBUG',  # Log SQL queries in debug mode
            future=True,  # Use SQLAlchemy 2.0 style
            connect_args={
                'options': '-c default_transaction_isolation=read_committed',
                'connect_timeout': 10,
                'server_settings': {
                    'application_name': 'marta_platform',
                    'timezone': 'UTC',
                    'statement_timeout': '300000',  # 5 minutes
                    'idle_in_transaction_session_timeout': '60000',  # 1 minute
                }
            }
        )
        
        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._sync_engine,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        # Add event listeners for monitoring
        self._add_sqlalchemy_listeners()
    
    def _initialize_psycopg2_pool(self):
        """Initialize psycopg2 connection pool for high-performance operations"""
        self._psycopg2_pool = psycopg2_pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=25,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            cursor_factory=RealDictCursor,
            options='-c default_transaction_isolation=read_committed',
            application_name='marta_platform_pool'
        )
    
    async def _initialize_async_pool(self):
        """Initialize asyncpg connection pool"""
        if self._async_pool is None:
            self._async_pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                min_size=10,
                max_size=30,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60,
                server_settings={
                    'application_name': 'marta_platform_async',
                    'timezone': 'UTC'
                }
            )
        return self._async_pool
    
    def _add_sqlalchemy_listeners(self):
        """Add SQLAlchemy event listeners for monitoring"""
        
        @event.listens_for(self._sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            with self._stats_lock:
                self._connection_stats['total_connections_created'] += 1
        
        @event.listens_for(self._sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(self._sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info['query_start_time'].pop(-1)
            with self._stats_lock:
                self._connection_stats['query_count'] += 1
                self._connection_stats['total_query_time'] += total_time
    
    @contextmanager
    def get_session(self):
        """Get SQLAlchemy session with automatic cleanup"""
        session = self._session_factory()
        try:
            with self._stats_lock:
                self._connection_stats['active_connections'] += 1
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("Database session error", error=str(e))
            with self._stats_lock:
                self._connection_stats['connection_errors'] += 1
            raise
        finally:
            session.close()
            with self._stats_lock:
                self._connection_stats['active_connections'] -= 1
    
    @contextmanager
    def get_raw_connection(self):
        """Get raw psycopg2 connection for high-performance operations"""
        conn = self._psycopg2_pool.getconn()
        try:
            with self._stats_lock:
                self._connection_stats['active_connections'] += 1
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error("Raw connection error", error=str(e))
            with self._stats_lock:
                self._connection_stats['connection_errors'] += 1
            raise
        finally:
            self._psycopg2_pool.putconn(conn)
            with self._stats_lock:
                self._connection_stats['active_connections'] -= 1
    
    @asynccontextmanager
    async def get_async_connection(self):
        """Get async connection for high-performance async operations"""
        pool = await self._initialize_async_pool()
        async with pool.acquire() as conn:
            try:
                with self._stats_lock:
                    self._connection_stats['active_connections'] += 1
                yield conn
            except Exception as e:
                logger.error("Async connection error", error=str(e))
                with self._stats_lock:
                    self._connection_stats['connection_errors'] += 1
                raise
            finally:
                with self._stats_lock:
                    self._connection_stats['active_connections'] -= 1
    
    def execute_query(self, query: str, params: Optional[Dict] = None, fetch: str = 'all') -> Any:
        """Execute query with connection pooling and error handling"""
        start_time = time.time()
        
        with self.get_session() as session:
            try:
                result = session.execute(text(query), params or {})
                
                if fetch == 'all':
                    data = result.fetchall()
                elif fetch == 'one':
                    data = result.fetchone()
                elif fetch == 'many':
                    data = result.fetchmany()
                else:
                    data = result
                
                execution_time = time.time() - start_time
                logger.debug("Query executed successfully", 
                           query=query[:100], execution_time=execution_time)
                
                return data
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error("Query execution failed", 
                           query=query[:100], error=str(e), execution_time=execution_time)
                raise
    
    def execute_to_dataframe(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """Execute query and return results as pandas DataFrame"""
        start_time = time.time()
        
        try:
            df = pd.read_sql_query(
                query, 
                self._sync_engine,
                params=params
            )
            
            execution_time = time.time() - start_time
            logger.debug("DataFrame query executed successfully", 
                       query=query[:100], rows=len(df), execution_time=execution_time)
            
            return df
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("DataFrame query execution failed", 
                       query=query[:100], error=str(e), execution_time=execution_time)
            raise
    
    def bulk_insert(self, table: str, data: list, columns: list, page_size: int = 1000):
        """High-performance bulk insert using execute_values"""
        with self.get_raw_connection() as conn:
            with conn.cursor() as cursor:
                # Create INSERT query with placeholders
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES %s"
                
                try:
                    # Execute in batches
                    for i in range(0, len(data), page_size):
                        batch = data[i:i + page_size]
                        execute_values(
                            cursor,
                            insert_query,
                            batch,
                            template=f"({placeholders})",
                            page_size=page_size
                        )
                    
                    conn.commit()
                    logger.info("Bulk insert completed", 
                              table=table, rows=len(data), batches=(len(data) + page_size - 1) // page_size)
                    
                except Exception as e:
                    conn.rollback()
                    logger.error("Bulk insert failed", table=table, error=str(e))
                    raise
    
    async def async_execute_query(self, query: str, params: Optional[list] = None) -> list:
        """Execute query asynchronously"""
        async with self.get_async_connection() as conn:
            try:
                start_time = time.time()
                result = await conn.fetch(query, *(params or []))
                execution_time = time.time() - start_time
                
                logger.debug("Async query executed successfully", 
                           query=query[:100], rows=len(result), execution_time=execution_time)
                
                return result
                
            except Exception as e:
                logger.error("Async query execution failed", 
                           query=query[:100], error=str(e))
                raise
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self._stats_lock:
            stats = self._connection_stats.copy()
        
        # Add pool-specific stats
        if self._sync_engine:
            pool = self._sync_engine.pool
            stats.update({
                'pool_size': pool.size(),
                'pool_checked_in': pool.checkedin(),
                'pool_checked_out': pool.checkedout(),
                'pool_overflow': pool.overflow(),
                'pool_invalid': pool.invalid(),
            })
        
        # Calculate derived metrics
        if stats['query_count'] > 0:
            stats['avg_query_time'] = stats['total_query_time'] / stats['query_count']
        else:
            stats['avg_query_time'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset connection statistics"""
        with self._stats_lock:
            self._connection_stats.update({
                'total_connections_created': 0,
                'active_connections': 0,
                'connection_errors': 0,
                'query_count': 0,
                'total_query_time': 0.0,
                'last_reset': datetime.now()
            })
        logger.info("Connection statistics reset")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.get_session() as session:
                result = session.execute(text("SELECT 1 as health_check, CURRENT_TIMESTAMP as timestamp"))
                row = result.fetchone()
                
                return {
                    'status': 'healthy',
                    'timestamp': row.timestamp if row else None,
                    'response_time_ms': 0,  # Will be filled by timing decorator
                    'connection_stats': self.get_connection_stats()
                }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now(),
                'connection_stats': self.get_connection_stats()
            }
    
    def optimize_queries(self):
        """Run query optimization analysis"""
        optimization_query = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            stddev_time,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements 
        WHERE query LIKE '%gtfs_%' OR query LIKE '%unified_%' OR query LIKE '%feature_%'
        ORDER BY total_time DESC
        LIMIT 10
        """
        
        try:
            df = self.execute_to_dataframe(optimization_query)
            logger.info("Query optimization analysis completed", slow_queries=len(df))
            return df
        except Exception as e:
            logger.error("Query optimization analysis failed", error=str(e))
            return pd.DataFrame()
    
    def cleanup(self):
        """Clean up connection pools"""
        try:
            if self._sync_engine:
                self._sync_engine.dispose()
            if self._psycopg2_pool:
                self._psycopg2_pool.closeall()
            if self._async_pool:
                asyncio.create_task(self._async_pool.close())
            
            logger.info("Database connection pools cleaned up")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

# Global connection pool instance
_connection_pool: Optional[DatabaseConnectionPool] = None

def get_db_pool() -> DatabaseConnectionPool:
    """Get or create global database connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = DatabaseConnectionPool()
    return _connection_pool

def timing_decorator(func):
    """Decorator to add timing information to database operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if isinstance(result, dict) and 'response_time_ms' in result:
            result['response_time_ms'] = execution_time
        
        return result
    return wrapper

# Convenience functions
@timing_decorator
def execute_query(query: str, params: Optional[Dict] = None, fetch: str = 'all') -> Any:
    """Execute query using global connection pool"""
    return get_db_pool().execute_query(query, params, fetch)

@timing_decorator
def execute_to_dataframe(query: str, params: Optional[Dict] = None) -> pd.DataFrame:
    """Execute query to DataFrame using global connection pool"""
    return get_db_pool().execute_to_dataframe(query, params)

def bulk_insert(table: str, data: list, columns: list, page_size: int = 1000):
    """Bulk insert using global connection pool"""
    return get_db_pool().bulk_insert(table, data, columns, page_size)

async def async_execute_query(query: str, params: Optional[list] = None) -> list:
    """Execute async query using global connection pool"""
    return await get_db_pool().async_execute_query(query, params)

@timing_decorator
def health_check() -> Dict[str, Any]:
    """Perform database health check"""
    return get_db_pool().health_check()

def get_connection_stats() -> Dict[str, Any]:
    """Get connection pool statistics"""
    return get_db_pool().get_connection_stats()

def optimize_queries() -> pd.DataFrame:
    """Run query optimization analysis"""
    return get_db_pool().optimize_queries()

# Context managers for direct access
def get_session():
    """Get SQLAlchemy session"""
    return get_db_pool().get_session()

def get_raw_connection():
    """Get raw psycopg2 connection"""
    return get_db_pool().get_raw_connection()

def get_async_connection():
    """Get async connection"""
    return get_db_pool().get_async_connection()