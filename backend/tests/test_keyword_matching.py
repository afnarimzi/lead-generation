#!/usr/bin/env python3
"""
Simple test script to verify smart keyword matching functionality.
Tests the core word boundary matching behavior.
"""

from datetime import datetime
from lead_scraper.engines.filter_engine import FilterEngine
from lead_scraper.models.lead import Lead
from lead_scraper.models.filter_criteria import FilterCriteria


def create_test_lead(title, description):
    """Helper to create a test lead."""
    return Lead(
        job_title=title,
        job_description=description,
        platform_name="Test",
        job_url="https://test.com/job",
        posted_datetime=datetime.now(),
        budget_amount=100.0,
        payment_type="fixed",
        skills_tags=[],
        quality_score=50.0
    )


def test_ai_word_boundary():
    """Test that 'AI' matches 'AI engineer' but not 'Adobe Illustrator'."""
    print("\n🧪 Test 1: AI Word Boundary Matching")
    print("=" * 60)
    
    engine = FilterEngine()
    
    # Should match: "AI" as a standalone word
    lead1 = create_test_lead("AI Engineer", "Looking for AI expertise")
    lead2 = create_test_lead("Senior AI Developer", "Work with AI models")
    lead3 = create_test_lead("Machine Learning Expert", "Experience with AI required")
    
    # Should NOT match: "AI" within other words
    lead4 = create_test_lead("Adobe Illustrator Expert", "Need Illustrator skills")
    lead5 = create_test_lead("Email Marketing Specialist", "Email campaigns")
    lead6 = create_test_lead("API Developer", "REST API development")
    
    filters = FilterCriteria(keywords=["AI"])
    
    # Test matches
    assert engine._matches_keywords(lead1, ["AI"]), "❌ Failed: Should match 'AI Engineer'"
    print("✅ Matched: 'AI Engineer'")
    
    assert engine._matches_keywords(lead2, ["AI"]), "❌ Failed: Should match 'Senior AI Developer'"
    print("✅ Matched: 'Senior AI Developer'")
    
    assert engine._matches_keywords(lead3, ["AI"]), "❌ Failed: Should match 'Experience with AI required'"
    print("✅ Matched: 'Experience with AI required'")
    
    # Test non-matches
    assert not engine._matches_keywords(lead4, ["AI"]), "❌ Failed: Should NOT match 'Adobe Illustrator'"
    print("✅ Correctly rejected: 'Adobe Illustrator Expert'")
    
    assert not engine._matches_keywords(lead5, ["AI"]), "❌ Failed: Should NOT match 'Email'"
    print("✅ Correctly rejected: 'Email Marketing Specialist'")
    
    assert not engine._matches_keywords(lead6, ["AI"]), "❌ Failed: Should NOT match 'API'"
    print("✅ Correctly rejected: 'API Developer'")
    
    print("\n✨ Test 1 PASSED: AI word boundary matching works correctly!")


def test_phrase_matching():
    """Test that phrases are matched as complete units."""
    print("\n🧪 Test 2: Phrase Matching")
    print("=" * 60)
    
    engine = FilterEngine()
    
    # Should match: complete phrase
    lead1 = create_test_lead("Machine Learning Engineer", "Expert in machine learning")
    lead2 = create_test_lead("Data Scientist", "Experience with machine learning algorithms")
    
    # Should NOT match: words not consecutive
    lead3 = create_test_lead("Machine Operator", "Learning new skills")
    lead4 = create_test_lead("Learning Management System", "Machine setup required")
    
    # Test matches
    assert engine._matches_keywords(lead1, ["machine learning"]), "❌ Failed: Should match 'machine learning' in title"
    print("✅ Matched: 'Machine Learning Engineer'")
    
    assert engine._matches_keywords(lead2, ["machine learning"]), "❌ Failed: Should match 'machine learning' in description"
    print("✅ Matched: 'Experience with machine learning algorithms'")
    
    # Test non-matches
    assert not engine._matches_keywords(lead3, ["machine learning"]), "❌ Failed: Should NOT match separated words"
    print("✅ Correctly rejected: 'Machine Operator' + 'Learning new skills'")
    
    assert not engine._matches_keywords(lead4, ["machine learning"]), "❌ Failed: Should NOT match reversed words"
    print("✅ Correctly rejected: 'Learning Management System' + 'Machine setup'")
    
    print("\n✨ Test 2 PASSED: Phrase matching works correctly!")


def test_case_insensitive():
    """Test that matching is case-insensitive."""
    print("\n🧪 Test 3: Case-Insensitive Matching")
    print("=" * 60)
    
    engine = FilterEngine()
    
    lead1 = create_test_lead("ai engineer", "looking for ai expertise")
    lead2 = create_test_lead("AI ENGINEER", "LOOKING FOR AI EXPERTISE")
    lead3 = create_test_lead("Ai Engineer", "Looking for Ai expertise")
    lead4 = create_test_lead("aI eNgInEeR", "lOoKiNg FoR aI eXpErTiSe")
    
    # All should match regardless of case
    for i, lead in enumerate([lead1, lead2, lead3, lead4], 1):
        assert engine._matches_keywords(lead, ["AI"]), f"❌ Failed: Should match case variation {i}"
        print(f"✅ Matched case variation {i}: '{lead.job_title}'")
    
    print("\n✨ Test 3 PASSED: Case-insensitive matching works correctly!")


def test_special_characters():
    """Test that special characters are matched literally."""
    print("\n🧪 Test 4: Special Character Matching")
    print("=" * 60)
    
    engine = FilterEngine()
    
    # Should match: exact special characters
    lead1 = create_test_lead("C++ Developer", "Expert in C++ programming")
    lead2 = create_test_lead("C# Programmer", "Looking for C# expertise")
    lead3 = create_test_lead(".NET Developer", "Experience with .NET framework")
    
    # Should NOT match: different characters
    lead4 = create_test_lead("C Developer", "C programming only")
    lead5 = create_test_lead("Network Engineer", "Networking skills")
    
    # Test C++
    assert engine._matches_keywords(lead1, ["C++"]), "❌ Failed: Should match 'C++'"
    print("✅ Matched: 'C++ Developer'")
    
    # Test C#
    assert engine._matches_keywords(lead2, ["C#"]), "❌ Failed: Should match 'C#'"
    print("✅ Matched: 'C# Programmer'")
    
    # Test .NET
    assert engine._matches_keywords(lead3, [".NET"]), "❌ Failed: Should match '.NET'"
    print("✅ Matched: '.NET Developer'")
    
    # Test non-matches
    assert not engine._matches_keywords(lead4, ["C++"]), "❌ Failed: Should NOT match 'C' for 'C++'"
    print("✅ Correctly rejected: 'C Developer' for 'C++' keyword")
    
    assert not engine._matches_keywords(lead5, [".NET"]), "❌ Failed: Should NOT match 'Network' for '.NET'"
    print("✅ Correctly rejected: 'Network Engineer' for '.NET' keyword")
    
    print("\n✨ Test 4 PASSED: Special character matching works correctly!")


def test_multiple_keywords():
    """Test that any matching keyword returns True (OR logic)."""
    print("\n🧪 Test 5: Multiple Keyword OR Logic")
    print("=" * 60)
    
    engine = FilterEngine()
    
    lead1 = create_test_lead("Python Developer", "Django and Flask experience")
    lead2 = create_test_lead("JavaScript Developer", "React and Node.js")
    lead3 = create_test_lead("Java Developer", "Spring Boot experience")
    
    keywords = ["Python", "JavaScript", "Ruby"]
    
    # Should match: has Python
    assert engine._matches_keywords(lead1, keywords), "❌ Failed: Should match Python"
    print("✅ Matched: 'Python Developer' (has Python)")
    
    # Should match: has JavaScript
    assert engine._matches_keywords(lead2, keywords), "❌ Failed: Should match JavaScript"
    print("✅ Matched: 'JavaScript Developer' (has JavaScript)")
    
    # Should NOT match: has none of the keywords
    assert not engine._matches_keywords(lead3, keywords), "❌ Failed: Should NOT match Java"
    print("✅ Correctly rejected: 'Java Developer' (no matching keywords)")
    
    print("\n✨ Test 5 PASSED: Multiple keyword OR logic works correctly!")


def test_edge_cases():
    """Test edge cases like empty keywords, text boundaries, etc."""
    print("\n🧪 Test 6: Edge Cases")
    print("=" * 60)
    
    engine = FilterEngine()
    
    lead = create_test_lead("AI Engineer", "Looking for AI expertise")
    
    # Empty keyword list
    assert not engine._matches_keywords(lead, []), "❌ Failed: Empty list should return False"
    print("✅ Empty keyword list returns False")
    
    # Whitespace-only keywords
    assert not engine._matches_keywords(lead, ["  ", "\t", "\n"]), "❌ Failed: Whitespace keywords should be skipped"
    print("✅ Whitespace-only keywords are skipped")
    
    # Keyword at text start
    lead_start = create_test_lead("AI is the future", "Description here")
    assert engine._matches_keywords(lead_start, ["AI"]), "❌ Failed: Should match at text start"
    print("✅ Matched keyword at text start")
    
    # Keyword at text end
    lead_end = create_test_lead("Expert in AI", "Description here")
    assert engine._matches_keywords(lead_end, ["AI"]), "❌ Failed: Should match at text end"
    print("✅ Matched keyword at text end")
    
    # Empty lead fields
    lead_empty = create_test_lead("", "")
    assert not engine._matches_keywords(lead_empty, ["AI"]), "❌ Failed: Empty lead should not match"
    print("✅ Empty lead fields handled correctly")
    
    print("\n✨ Test 6 PASSED: Edge cases handled correctly!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 Smart Keyword Matching - Core Functionality Tests")
    print("=" * 60)
    
    try:
        test_ai_word_boundary()
        test_phrase_matching()
        test_case_insensitive()
        test_special_characters()
        test_multiple_keywords()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\n✅ Core functionality verified:")
        print("   • Word boundary matching works correctly")
        print("   • 'AI' matches 'AI engineer' but not 'Adobe Illustrator'")
        print("   • Phrase matching works as expected")
        print("   • Case-insensitive matching works")
        print("   • Special characters are handled correctly")
        print("   • Multiple keyword OR logic works")
        print("   • Edge cases are handled gracefully")
        print("\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
