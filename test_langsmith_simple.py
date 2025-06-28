#!/usr/bin/env python3
"""
Simple LangSmith integration test to validate basic connectivity
"""

import os
from datetime import datetime
from langsmith import Client
from config import Settings

def test_langsmith_basic():
    """Test basic LangSmith connectivity and trace creation"""
    settings = Settings()
    
    print(f"API Key present: {bool(settings.LANGSMITH_API_KEY)}")
    print(f"API Key length: {len(settings.LANGSMITH_API_KEY)}")
    print(f"Project: {settings.LANGSMITH_PROJECT}")
    print(f"Endpoint: {settings.LANGSMITH_ENDPOINT}")
    
    try:
        # Initialize client
        client = Client(
            api_key=settings.LANGSMITH_API_KEY,
            api_url=settings.LANGSMITH_ENDPOINT
        )
        print("✓ Client initialized successfully")
        
        # Test simple trace creation
        trace_data = {
            "name": "test_trace_simple",
            "run_type": "chain",
            "inputs": {"test": "hello world"},
            "project_name": settings.LANGSMITH_PROJECT,
            "start_time": datetime.now()
        }
        
        print(f"Creating trace with data: {trace_data}")
        run = client.create_run(**trace_data)
        
        if run:
            print(f"✓ Trace created successfully: {run.id}")
            print(f"Run object type: {type(run)}")
            print(f"Run attributes: {dir(run)}")
            
            # Complete the trace
            client.update_run(
                run_id=run.id,
                outputs={"result": "test successful"},
                end_time=datetime.now()
            )
            print("✓ Trace completed successfully")
            
        else:
            print("✗ create_run returned None")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_langsmith_basic()