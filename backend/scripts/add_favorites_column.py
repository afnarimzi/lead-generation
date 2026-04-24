#!/usr/bin/env python3
"""
Migration script to add is_favorited column to leads table.
Run this to update existing database.
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lead_scraper.database.connection_manager import ConnectionManager

load_dotenv()

def migrate():
    """Add is_favorited column and index to leads table."""
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        print("🔄 Adding is_favorited column to leads table...")
        
        # Add column if it doesn't exist
        db.execute("""
            ALTER TABLE leads 
            ADD COLUMN IF NOT EXISTS is_favorited BOOLEAN DEFAULT FALSE;
        """, ())
        
        print("✅ Column added successfully")
        
        print("🔄 Creating index on is_favorited...")
        
        # Create index
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_leads_favorited 
            ON leads(is_favorited) 
            WHERE is_favorited = TRUE;
        """, ())
        
        print("✅ Index created successfully")
        print("🎉 Migration completed!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
