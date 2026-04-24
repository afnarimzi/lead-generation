#!/usr/bin/env python3
"""Script to clear all leads from the database."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from lead_scraper.database.connection_manager import ConnectionManager

def main():
    """Clear all leads from database."""
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return 1
    
    print("⚠️  WARNING: This will delete ALL leads from the database!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return 0
    
    try:
        db = ConnectionManager(database_url)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count before
            cursor.execute("SELECT COUNT(*) FROM leads")
            count_before = cursor.fetchone()[0]
            print(f"\n📊 Current leads in database: {count_before}")
            
            # Delete all
            cursor.execute("TRUNCATE TABLE leads RESTART IDENTITY CASCADE")
            conn.commit()
            
            # Count after
            cursor.execute("SELECT COUNT(*) FROM leads")
            count_after = cursor.fetchone()[0]
            
            print(f"✅ Database cleared! Deleted {count_before} leads")
            print(f"📊 Remaining leads: {count_after}")
            print("\n🚀 Now you can do a fresh search from the UI!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
