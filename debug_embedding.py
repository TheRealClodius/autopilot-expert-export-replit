"""
Debug script to test Gemini embedding generation.
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google import genai
from config import settings

async def test_embedding():
    """Test direct Gemini embedding generation."""
    try:
        print("1. Testing Gemini API key configuration...")
        if not settings.GEMINI_API_KEY:
            print("❌ GEMINI_API_KEY not configured")
            return
        print("✅ GEMINI_API_KEY is set")
        
        print("2. Initializing Gemini client...")
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        print("✅ Gemini client initialized")
        
        print("3. Testing embedding generation...")
        from google.genai import types
        
        test_text = "This is a test message for UiPath Autopilot integration."
        print(f"Test text: {test_text}")
        
        result = client.models.embed_content(
            model="text-embedding-004",
            contents=[types.Content(parts=[types.Part(text=test_text)])]
        )
        
        print(f"4. API Response type: {type(result)}")
        print(f"5. API Response attributes: {dir(result)}")
        
        if result and hasattr(result, 'embeddings'):
            print(f"6. Embeddings found: {len(result.embeddings)}")
            if result.embeddings:
                embedding = result.embeddings[0]
                print(f"7. First embedding type: {type(embedding)}")
                print(f"8. First embedding attributes: {dir(embedding)}")
                
                if hasattr(embedding, 'values'):
                    values = embedding.values
                    print(f"9. Values type: {type(values)}")
                    print(f"10. Values length: {len(values) if values else 'None'}")
                    if values:
                        print(f"11. First 5 values: {values[:5]}")
                        return values
                else:
                    print("❌ No 'values' attribute in embedding object")
            else:
                print("❌ No embeddings in result")
        else:
            print("❌ No 'embeddings' attribute in result")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_embedding())