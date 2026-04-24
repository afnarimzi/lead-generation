#!/usr/bin/env python3
"""
Test script to verify Gemini API is working properly.
Run this to check if your GEMINI_API_KEY is valid.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test Gemini API connection and embedding generation."""
    
    # Check if API key exists
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("Please add your Gemini API key to .env file")
        return False
    
    print(f"🔑 Found Gemini API key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Import and test Gemini
        import google.generativeai as genai
        
        print("📦 Configuring Gemini API...")
        genai.configure(api_key=api_key)
        
        print("🧪 Testing embedding generation...")
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content="This is a test for AI and machine learning jobs",
            task_type="retrieval_document"
        )
        
        embedding = result['embedding']
        print(f"✅ Success! Generated embedding with {len(embedding)} dimensions")
        print(f"📊 First 5 values: {embedding[:5]}")
        
        # Test similarity calculation
        result2 = genai.embed_content(
            model="models/gemini-embedding-001", 
            content="Python developer needed for artificial intelligence project",
            task_type="retrieval_document"
        )
        
        embedding2 = result2['embedding']
        
        # Calculate cosine similarity
        import numpy as np
        e1 = np.array(embedding)
        e2 = np.array(embedding2)
        similarity = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        
        print(f"🎯 Similarity between related texts: {similarity:.3f}")
        
        if similarity > 0.5:
            print("✅ Gemini API is working perfectly for semantic matching!")
            return True
        else:
            print("⚠️ Similarity seems low, but API is functional")
            return True
            
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install google-generativeai")
        return False
        
    except Exception as e:
        print(f"❌ Gemini API test failed: {type(e).__name__}: {e}")
        
        # Provide specific error guidance
        error_str = str(e).upper()
        if "API_KEY" in error_str or "AUTHENTICATION" in error_str:
            print("🔑 Issue: Invalid API key")
            print("Solution: Get a new API key from https://makersuite.google.com/app/apikey")
        elif "QUOTA" in error_str or "LIMIT" in error_str:
            print("📊 Issue: API quota exceeded")
            print("Solution: Wait for quota reset or upgrade your plan")
        elif "NETWORK" in error_str or "CONNECTION" in error_str:
            print("🌐 Issue: Network connection problem")
            print("Solution: Check your internet connection")
        else:
            print("🔧 Issue: Unknown error")
            print("Solution: Check Gemini API status and try again")
        
        return False

if __name__ == "__main__":
    print("🚀 Testing Gemini API Connection...")
    print("=" * 50)
    
    success = test_gemini_api()
    
    print("=" * 50)
    if success:
        print("🎉 Gemini API is ready for semantic lead filtering!")
    else:
        print("💡 Fix the issues above to enable AI-powered lead filtering")
        print("   The system will use basic keyword filtering as fallback")
    
    sys.exit(0 if success else 1)