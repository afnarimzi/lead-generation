#!/usr/bin/env python3
"""
Database initialization script for Vercel deployment.
Creates the leads table with all required fields and indexes.
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from lead_scraper.database.connection_manager import ConnectionManager

def init_database():
    """Initialize the database with required tables and indexes."""
    
    print("🔍 Initializing database...")
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"📊 Connecting to database...")
    
    try:
        db = ConnectionManager(db_url)
        
        # Test connection
        if not db.health_check():
            print("❌ Database health check failed")
            return False
        
        print("✅ Database connection successful")
        
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
        
        print("🏗️ Creating tables and indexes...")
        db.execute(create_table_sql, ())
        
        print("✅ Database initialization completed successfully!")
        
        # Verify table creation
        result = db.execute("SELECT COUNT(*) FROM leads", ())
        count = result[0][0] if result else 0
        print(f"📊 Leads table created with {count} existing records")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)