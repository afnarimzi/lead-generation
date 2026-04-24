"""
Admin endpoints for database management.
"""
import os
from fastapi import APIRouter, HTTPException
from lead_scraper.database.connection_manager import ConnectionManager

router = APIRouter()

@router.post("/init-db")
async def initialize_database():
    """Initialize the database with required tables and indexes."""
    
    try:
        # Get database URL
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
        
        db = ConnectionManager(db_url)
        
        # Test connection
        if not db.health_check():
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # Create leads table
        create_table_sql = """
        -- Enable pg_trgm extension for similarity searches
        CREATE EXTENSION IF NOT EXISTS pg_trgm;

        -- Create leads table
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            job_title VARCHAR(500) NOT NULL,
            job_description TEXT NOT NULL,
            platform_name VARCHAR(50) NOT NULL,
            budget_amount DECIMAL(10, 2),
            payment_type VARCHAR(20),
            client_info JSONB,
            job_url VARCHAR(1000) UNIQUE NOT NULL,
            posted_datetime TIMESTAMP NOT NULL,
            skills_tags TEXT[],
            quality_score DECIMAL(5, 2) DEFAULT 0.0,
            is_potential_duplicate BOOLEAN DEFAULT FALSE,
            is_favorited BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_leads_platform ON leads(platform_name);
        CREATE INDEX IF NOT EXISTS idx_leads_posted_datetime ON leads(posted_datetime DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_budget ON leads(budget_amount);
        CREATE INDEX IF NOT EXISTS idx_leads_quality_score ON leads(quality_score DESC);
        CREATE INDEX IF NOT EXISTS idx_leads_job_url ON leads(job_url);
        CREATE INDEX IF NOT EXISTS idx_leads_fulltext ON leads 
            USING GIN(to_tsvector('english', job_title || ' ' || job_description));
        CREATE INDEX IF NOT EXISTS idx_leads_title_similarity ON leads 
            USING GIN(job_title gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_leads_is_favorited ON leads(is_favorited) WHERE is_favorited = TRUE;
        """
        
        db.execute(create_table_sql, ())
        
        # Verify table creation
        result = db.execute("SELECT COUNT(*) FROM leads", ())
        count = result[0][0] if result else 0
        
        return {
            "status": "success",
            "message": f"Database initialized successfully with {count} existing records",
            "tables_created": ["leads"],
            "indexes_created": 8
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Check database health."""
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            return {"status": "error", "message": "DATABASE_URL not configured"}
        
        db = ConnectionManager(db_url)
        if db.health_check():
            return {"status": "healthy", "message": "Database connection successful"}
        else:
            return {"status": "unhealthy", "message": "Database connection failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}