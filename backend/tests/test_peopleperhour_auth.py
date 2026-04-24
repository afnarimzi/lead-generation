#!/usr/bin/env python3
"""
Test PeoplePerHour authentication and scraping.
This script tests ONLY PeoplePerHour to verify credentials work.

Usage:
    python test_peopleperhour_auth.py
"""

import asyncio
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

from lead_scraper.adapters.peopleperhour_adapter import PeoplePerHourAdapter
from lead_scraper.models.filter_criteria import FilterCriteria
from lead_scraper.models.auth_config import AuthConfig


async def test_peopleperhour():
    """Test PeoplePerHour scraping with authentication."""
    
    # Load environment variables
    load_dotenv()
    
    print("\n" + "=" * 70)
    print("🧪 PEOPLEPERHOUR AUTHENTICATION TEST")
    print("=" * 70)
    
    # Check if credentials are configured
    username = os.getenv("PEOPLEPERHOUR_USERNAME")
    password = os.getenv("PEOPLEPERHOUR_PASSWORD")
    
    print("\n📋 Configuration Check:")
    print(f"   APIFY_TOKEN: {'✓ Set' if os.getenv('APIFY_TOKEN') else '✗ Missing'}")
    print(f"   APIFY_PEOPLEPERHOUR_ACTOR_ID: {os.getenv('APIFY_PEOPLEPERHOUR_ACTOR_ID', 'getdataforme~peopleperhour-job-scraper')}")
    print(f"   PEOPLEPERHOUR_USERNAME: {'✓ Set' if username else '✗ Missing'}")
    print(f"   PEOPLEPERHOUR_PASSWORD: {'✓ Set' if password else '✗ Missing'}")
    
    # Create auth config if credentials are provided
    auth_config = None
    if username and password:
        print("\n🔐 Authentication: ENABLED")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password)}")
        
        auth_config = AuthConfig(
            platform="peopleperhour",
            username=username,
            password=password
        )
        
        if not auth_config.is_valid():
            print("\n❌ Invalid authentication configuration!")
            print("   Both username and password are required.")
            return
    else:
        print("\n⚠️  Authentication: DISABLED (no credentials found)")
        print("   Add PEOPLEPERHOUR_USERNAME and PEOPLEPERHOUR_PASSWORD to .env file")
        print("   Scraping will proceed without authentication...")
    
    # Initialize adapter
    print("\n⚙️  Initializing PeoplePerHour adapter...")
    
    try:
        adapter = PeoplePerHourAdapter(
            apify_token=os.getenv("APIFY_TOKEN"),
            actor_id=os.getenv("APIFY_PEOPLEPERHOUR_ACTOR_ID", "getdataforme~peopleperhour-job-scraper"),
            auth_config=auth_config
        )
        print("✓ Adapter initialized")
    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return
    
    # Create filter criteria for test search
    print("\n🔍 Test Search Parameters:")
    print("   Keywords: AI, machine learning")
    print("   Max results: 10")
    print("   Platform: PeoplePerHour only")
    
    filters = FilterCriteria(
        keywords=["AI", "machine learning"],
        max_results_per_platform=10
    )
    
    # Estimate credits
    estimated_credits = adapter.estimate_credits(filters)
    print(f"\n💰 Estimated credits: {estimated_credits:.2f}")
    
    # Run scrape
    print("\n⏳ Scraping PeoplePerHour... (this may take 30-60 seconds)")
    
    try:
        raw_results = await adapter.scrape(filters)
        
        print(f"\n✓ Scrape complete!")
        print(f"   Raw results: {len(raw_results)} jobs")
        
        if len(raw_results) == 0:
            print("\n⚠️  No results found. This could mean:")
            print("   - No jobs match the search criteria")
            print("   - The Apify actor is not working correctly")
            print("   - Authentication failed (if credentials were provided)")
            return
        
        # Normalize results
        print("\n📊 Normalizing results...")
        leads = []
        for raw_lead in raw_results:
            try:
                lead = adapter.normalize(raw_lead)
                leads.append(lead)
            except Exception as e:
                print(f"   ⚠️  Failed to normalize one lead: {e}")
        
        print(f"✓ Normalized {len(leads)} leads")
        
        # Display results
        print("\n" + "=" * 70)
        print("📋 RESULTS")
        print("=" * 70)
        
        for i, lead in enumerate(leads[:5], 1):  # Show first 5
            print(f"\n{i}. {lead.job_title}")
            
            if lead.budget_amount:
                print(f"   💰 Budget: ${lead.budget_amount:,.2f}")
            else:
                print(f"   💰 Budget: Not specified")
            
            print(f"   📅 Posted: {lead.posted_datetime}")
            
            if lead.skills_tags:
                skills = ', '.join(lead.skills_tags[:5])
                print(f"   🔧 Skills: {skills}")
            
            if lead.metadata and 'auth_used' in lead.metadata:
                auth_status = "✓ Authenticated" if lead.metadata['auth_used'] else "○ Anonymous"
                print(f"   🔐 Auth Status: {auth_status}")
            
            print(f"   🔗 {lead.job_url}")
        
        if len(leads) > 5:
            print(f"\n   ... and {len(leads) - 5} more jobs")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ TEST SUMMARY")
        print("=" * 70)
        print(f"   Total jobs scraped: {len(leads)}")
        print(f"   Authentication: {'ENABLED' if auth_config else 'DISABLED'}")
        
        if auth_config:
            auth_working = any(
                lead.metadata and lead.metadata.get('auth_used', False) 
                for lead in leads
            )
            if auth_working:
                print(f"   Auth status: ✓ WORKING")
            else:
                print(f"   Auth status: ⚠️  UNKNOWN (metadata not set)")
        
        # Budget statistics
        with_budget = sum(1 for lead in leads if lead.budget_amount)
        print(f"   Jobs with budget: {with_budget}/{len(leads)} ({with_budget/len(leads)*100:.1f}%)")
        
        if with_budget > 0:
            avg_budget = sum(lead.budget_amount for lead in leads if lead.budget_amount) / with_budget
            print(f"   Average budget: ${avg_budget:,.2f}")
        
        print("\n✅ PeoplePerHour test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("This script tests PeoplePerHour authentication and scraping.")
    print("It will NOT save results to the database.")
    print("=" * 70)
    
    try:
        asyncio.run(test_peopleperhour())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
