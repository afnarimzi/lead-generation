#!/usr/bin/env python3
"""
Debug script to test database operations and identify the lead disappearing issue.
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from lead_scraper.database.connection_manager import ConnectionManager
from lead_scraper.models.lead import Lead

def main():
    print("🔍 DATABASE DEBUG SCRIPT")
    print("=" * 50)
    
    # Initialize database connection
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    print(f"📊 Connecting to database...")
    db = ConnectionManager(db_url)
    
    # Test 1: Check database health
    print("\n1️⃣ Testing database health...")
    if db.health_check():
        print("✅ Database connection healthy")
    else:
        print("❌ Database connection failed")
        return
    
    # Test 2: Count existing leads
    print("\n2️⃣ Counting existing leads...")
    try:
        total_result = db.execute("SELECT COUNT(*) FROM leads", ())
        total_count = total_result[0][0] if total_result else 0
        print(f"📊 Total leads in database: {total_count}")
        
        fav_result = db.execute("SELECT COUNT(*) FROM leads WHERE is_favorited = TRUE", ())
        fav_count = fav_result[0][0] if fav_result else 0
        print(f"⭐ Favorited leads: {fav_count}")
        
        recent_result = db.execute(
            "SELECT COUNT(*) FROM leads WHERE created_at >= NOW() - INTERVAL '1 hour'", 
            ()
        )
        recent_count = recent_result[0][0] if recent_result else 0
        print(f"🕐 Recent leads (last hour): {recent_count}")
        
    except Exception as e:
        print(f"❌ Failed to count leads: {e}")
        return
    
    # Test 3: Show recent leads
    print("\n3️⃣ Showing recent leads...")
    try:
        recent_leads = db.execute(
            """
            SELECT id, job_title, platform_name, created_at, is_favorited 
            FROM leads 
            ORDER BY created_at DESC 
            LIMIT 10
            """, 
            ()
        )
        
        if recent_leads:
            print("Recent leads:")
            for lead in recent_leads:
                fav_icon = "⭐" if lead[4] else "☆"
                print(f"  {fav_icon} ID:{lead[0]} | {lead[2]} | {lead[1][:50]}... | {lead[3]}")
        else:
            print("No leads found")
            
    except Exception as e:
        print(f"❌ Failed to fetch recent leads: {e}")
    
    # Test 4: Create a test lead
    print("\n4️⃣ Testing lead insertion...")
    try:
        test_lead = Lead(
            job_title="Test Lead - Debug Script",
            job_description="This is a test lead created by the debug script to verify database operations.",
            platform_name="Debug",
            budget_amount=100.0,
            payment_type="fixed",
            client_info={"test": True},
            job_url=f"https://debug.test/job/{datetime.now().timestamp()}",
            posted_datetime=datetime.now(timezone.utc),
            skills_tags=["debug", "test"],
            quality_score=50.0,
            is_potential_duplicate=False,
            created_at=datetime.now(timezone.utc)
        )
        
        inserted_count = db.bulk_insert([test_lead])
        print(f"✅ Inserted {inserted_count} test lead")
        
        # Verify insertion
        new_total_result = db.execute("SELECT COUNT(*) FROM leads", ())
        new_total_count = new_total_result[0][0] if new_total_result else 0
        print(f"📊 New total leads: {new_total_count}")
        
    except Exception as e:
        print(f"❌ Failed to insert test lead: {e}")
    
    # Test 5: Test cleanup logic
    print("\n5️⃣ Testing cleanup safety logic...")
    try:
        from datetime import timedelta
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        recent_check_query = """
            SELECT COUNT(*) FROM leads 
            WHERE created_at >= %s OR posted_datetime >= %s
        """
        recent_result = db.execute(recent_check_query, (recent_cutoff, recent_cutoff))
        recent_count = recent_result[0][0] if recent_result else 0
        
        print(f"🛡️ Recent leads (last 10 min): {recent_count}")
        if recent_count > 3:
            print("⚠️ Cleanup would be SKIPPED due to safety check")
        else:
            print("✅ Cleanup would proceed")
            
    except Exception as e:
        print(f"❌ Failed to test cleanup logic: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Debug script completed")

if __name__ == "__main__":
    main()