#!/usr/bin/env python3
"""
Script to clear all non-favorited leads from database.
Keeps your favorited jobs safe.
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lead_scraper.database.connection_manager import ConnectionManager

load_dotenv()

def clear_non_favorites():
    """Clear all non-favorited leads from database."""
    db = ConnectionManager(os.getenv('DATABASE_URL'))
    
    try:
        # Count total leads
        count_query = "SELECT COUNT(*) FROM leads"
        total_result = db.execute(count_query, ())
        total_leads = total_result[0][0] if total_result else 0
        
        # Count favorited leads
        fav_query = "SELECT COUNT(*) FROM leads WHERE is_favorited = TRUE"
        fav_result = db.execute(fav_query, ())
        fav_leads = fav_result[0][0] if fav_result else 0
        
        print(f"📊 Current database status:")
        print(f"   Total leads: {total_leads}")
        print(f"   Favorited leads: {fav_leads}")
        print(f"   Non-favorited leads: {total_leads - fav_leads}")
        
        if total_leads == fav_leads:
            print("\n✅ All leads are favorited. Nothing to clear!")
            return
        
        # Confirm deletion
        print(f"\n⚠️  This will delete {total_leads - fav_leads} non-favorited leads.")
        print(f"   Your {fav_leads} favorited leads will be kept safe.")
        response = input("\nContinue? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Cancelled.")
            return
        
        # Delete non-favorited leads
        print("\n🗑️  Deleting non-favorited leads...")
        delete_query = "DELETE FROM leads WHERE is_favorited = FALSE OR is_favorited IS NULL"
        db.execute(delete_query, ())
        
        # Verify deletion
        remaining_query = "SELECT COUNT(*) FROM leads"
        remaining_result = db.execute(remaining_query, ())
        remaining = remaining_result[0][0] if remaining_result else 0
        
        print(f"✅ Done! Deleted {total_leads - remaining} leads.")
        print(f"   Remaining leads: {remaining} (all favorited)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    clear_non_favorites()
