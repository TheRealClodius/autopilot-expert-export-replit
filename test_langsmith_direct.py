#!/usr/bin/env python3
"""
Direct LangSmith test to identify the exact issue
"""

import os
from datetime import datetime
from langsmith import Client
from config import Settings

def test_langsmith_direct():
    """Test LangSmith directly to identify the exact issue"""
    settings = Settings()
    
    print(f"Testing LangSmith directly...")
    print(f"API Key configured: {bool(settings.LANGSMITH_API_KEY)}")
    print(f"Project: {settings.LANGSMITH_PROJECT}")
    print(f"Endpoint: {settings.LANGSMITH_ENDPOINT}")
    
    if not settings.LANGSMITH_API_KEY:
        print("❌ No API key configured")
        return
    
    try:
        # Initialize client
        client = Client(
            api_key=settings.LANGSMITH_API_KEY,
            api_url=settings.LANGSMITH_ENDPOINT
        )
        print("✅ Client initialized")
        
        # Test project existence by trying to list runs
        try:
            # This should fail gracefully if project doesn't exist
            runs_response = client.list_runs(project_name=settings.LANGSMITH_PROJECT, limit=1)
            runs_list = list(runs_response)
            print(f"✅ Project exists, found {len(runs_list)} existing runs")
        except Exception as e:
            print(f"⚠️  Project may not exist or access issue: {e}")
            print("Creating project...")
            
            # Try to create a run (this should auto-create the project)
            test_run = client.create_run(
                name="project_creation_test",
                run_type="chain",
                inputs={"test": "creating project"},
                project_name=settings.LANGSMITH_PROJECT
            )
            
            if test_run:
                print(f"✅ Project created via run creation: {test_run.id}")
                client.update_run(
                    run_id=test_run.id,
                    outputs={"result": "project created"},
                    end_time=datetime.now()
                )
            else:
                print("❌ create_run returned None - authentication or configuration issue")
                return
        
        # Test normal run creation
        print("\nTesting normal run creation...")
        run = client.create_run(
            name="connectivity_test",
            run_type="chain", 
            inputs={"test": "normal operation"},
            project_name=settings.LANGSMITH_PROJECT
        )
        
        if run:
            print(f"✅ Run created successfully: {run.id}")
            print(f"Run type: {type(run)}")
            
            # Complete the run
            client.update_run(
                run_id=run.id,
                outputs={"result": "success"},
                end_time=datetime.now()
            )
            print("✅ Run completed successfully")
            
            # Test child run creation
            print("\nTesting child run creation...")
            child_run = client.create_run(
                name="child_test",
                run_type="chain",
                parent_run_id=run.id,
                inputs={"test": "child run"},
                project_name=settings.LANGSMITH_PROJECT
            )
            
            if child_run:
                print(f"✅ Child run created: {child_run.id}")
                client.update_run(
                    run_id=child_run.id,
                    outputs={"result": "child success"},
                    end_time=datetime.now()
                )
            else:
                print("❌ Child run creation returned None")
                
        else:
            print("❌ Run creation returned None")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_langsmith_direct()