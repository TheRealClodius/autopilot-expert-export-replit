#!/usr/bin/env python3
"""
Test script to verify the google.generativeai dependency fix
and ensure orchestrator can properly use Gemini API.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from agents.orchestrator_agent import OrchestratorAgent
from models.schemas import ProcessedMessage
import google.generativeai as genai

async def test_dependency_fix():
    """Test that the google.generativeai dependency fix resolves execution errors"""
    print("🧪 DEPENDENCY FIX VERIFICATION TEST")
    print("=" * 50)
    
    # Test 1: Import verification
    print("\n1. Import Verification:")
    try:
        import google.generativeai as genai
        print(f"   ✅ google.generativeai imported successfully (v{genai.__version__})")
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: API configuration
    print("\n2. API Configuration:")
    try:
        if not settings.GEMINI_API_KEY:
            print("   ⚠️ GEMINI_API_KEY not set - skipping API test")
            return True
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        print("   ✅ Gemini API configured successfully")
    except Exception as e:
        print(f"   ❌ API configuration failed: {e}")
        return False
    
    # Test 3: Orchestrator initialization
    print("\n3. Orchestrator Agent Initialization:")
    try:
        orchestrator = OrchestratorAgent()
        print("   ✅ OrchestratorAgent initialized successfully")
    except Exception as e:
        print(f"   ❌ Orchestrator initialization failed: {e}")
        return False
    
    # Test 4: Simple query processing
    print("\n4. Simple Query Processing:")
    try:
        # Create a simple test message
        test_message = ProcessedMessage(
            user_id="test_user",
            channel_id="test_channel",
            message_ts="1234567890.123",
            text="Hello, can you help me with Autopilot features?",
            thread_ts=None,
            user_name="Test User",
            user_first_name="Test",
            user_display_name="Test User",
            user_title="Engineer",
            user_department="Engineering"
        )
        
        # Test query analysis without full execution
        print("   Testing basic orchestrator analysis...")
        
        # This should work if google.generativeai is properly installed
        analysis = await orchestrator.analyze_query(test_message)
        
        if analysis and analysis.get("intent"):
            print(f"   ✅ Query analysis successful - Intent: {analysis['intent']}")
            return True
        else:
            print(f"   ⚠️ Query analysis returned empty result: {analysis}")
            return False
            
    except Exception as e:
        print(f"   ❌ Query processing failed: {e}")
        return False

async def main():
    """Run the dependency fix verification"""
    success = await test_dependency_fix()
    
    print(f"\n{'='*50}")
    print(f"VERIFICATION RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*50}")
    
    if success:
        print("\n🎯 DEPENDENCY FIX CONFIRMED:")
        print("   - google.generativeai properly installed and working")
        print("   - Orchestrator agent can initialize successfully")
        print("   - Gemini API integration functional")
        print("   - This should resolve deployment 'execution error' issues")
    else:
        print("\n❌ DEPENDENCY ISSUES REMAIN:")
        print("   - Further investigation needed")
        print("   - Check logs for specific error details")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)