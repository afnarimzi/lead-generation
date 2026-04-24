"""Database connection manager with connection pooling."""

import logging
from typing import Any, Optional
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool, extras

from lead_scraper.models.lead import Lead


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages PostgreSQL database connections with connection pooling."""
    
    def __init__(self, database_url: str, pool_size: int = 10):
        """Initialize connection manager with connection pool.
        
        Args:
            database_url: PostgreSQL connection URL
            pool_size: Maximum number of connections in the pool
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self._pool: Optional[pool.SimpleConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.database_url
            )
            logger.info(f"Database connection pool initialized with size {self.pool_size}")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for getting a connection from the pool.
        
        Yields:
            Database connection from the pool
        """
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)
    
    def execute(self, query: str, params: tuple = None) -> list[tuple]:
        """Execute a SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            
        Returns:
            List of result tuples
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                
                # Check if query returns results
                if cursor.description:
                    results = cursor.fetchall()
                else:
                    results = []
                
                conn.commit()
                return results
    
    def bulk_insert(self, leads: list[Lead]) -> int:
        """Bulk insert leads into the database.
        
        Args:
            leads: List of Lead objects to insert
            
        Returns:
            Number of leads successfully inserted
        """
        if not leads:
            logger.warning("No leads provided for bulk insert")
            return 0
        
        logger.info(f"💾 BULK INSERT: Attempting to insert {len(leads)} leads")
        
        insert_query = """
            INSERT INTO leads (
                job_title, job_description, platform_name, budget_amount,
                payment_type, client_info, job_url, posted_datetime,
                skills_tags, quality_score, is_potential_duplicate, created_at
            ) VALUES %s
            ON CONFLICT (job_url) DO NOTHING
        """
        
        # Prepare data tuples
        data = []
        for i, lead in enumerate(leads):
            try:
                # Convert numpy types to Python types to avoid PostgreSQL errors
                budget_amount = lead.budget_amount
                if budget_amount is not None:
                    # Handle numpy types
                    if hasattr(budget_amount, 'item'):  # numpy scalar
                        budget_amount = float(budget_amount.item())
                    else:
                        budget_amount = float(budget_amount)
                
                quality_score = lead.quality_score
                if quality_score is not None:
                    # Handle numpy types
                    if hasattr(quality_score, 'item'):  # numpy scalar
                        quality_score = float(quality_score.item())
                    else:
                        quality_score = float(quality_score)
                
                data_tuple = (
                    lead.job_title,
                    lead.job_description,
                    lead.platform_name,
                    budget_amount,
                    lead.payment_type,
                    psycopg2.extras.Json(lead.client_info) if lead.client_info else None,
                    lead.job_url,
                    lead.posted_datetime,
                    lead.skills_tags,
                    quality_score,
                    lead.is_potential_duplicate,
                    lead.created_at
                )
                data.append(data_tuple)
            except Exception as e:
                logger.error(f"Error preparing lead {i} for insert: {e}")
                logger.error(f"Lead data: title={lead.job_title[:50]}, budget={type(lead.budget_amount)}, quality={type(lead.quality_score)}")
                continue
        
        if not data:
            logger.error("No valid lead data prepared for insert")
            return 0
        
        logger.info(f"💾 BULK INSERT: Prepared {len(data)} valid lead records")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"💾 EXECUTING BULK INSERT with {len(data)} records...")
                    psycopg2.extras.execute_values(
                        cursor,
                        insert_query,
                        data,
                        template=None,
                        page_size=100
                    )
                    inserted_count = cursor.rowcount
                    logger.info(f"💾 BULK INSERT EXECUTED: {inserted_count} rows affected")
                    
                    # Explicit commit
                    conn.commit()
                    logger.info(f"💾 TRANSACTION COMMITTED")
                    
                    logger.info(f"💾 BULK INSERT SUCCESS: Inserted {inserted_count} leads into database")
                    
                    # Verify the insert by counting total leads
                    cursor.execute("SELECT COUNT(*) FROM leads")
                    total_count = cursor.fetchone()[0]
                    logger.info(f"💾 DATABASE STATUS: Total leads in database: {total_count}")
                    
                    return inserted_count
        except Exception as e:
            logger.error(f"💾 BULK INSERT FAILED: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if database connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            result = self.execute("SELECT 1")
            return len(result) > 0 and result[0][0] == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")
