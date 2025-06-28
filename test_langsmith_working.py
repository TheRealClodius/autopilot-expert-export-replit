#!/usr/bin/env python3
"""
Working LangSmith integration test to identify the exact issue
"""

import os
import asyncio
from datetime import datetime
from langsmith import Client
from config import Settings

async def test_working_langsmith():
    """Test LangSmith integration to identify the exact issue"""
    settings = Settings()
    
    print(f"Testing LangSmith integration...")
    print(f"API Key: {'*' * (len(settings.LANGSMITH_API_KEY) - 4) + settings.LANGSMITH_API_KEY[-4:]}")
    print(f"Project: {settings.LANGSMITH_PROJECT}")
    print(f"Endpoint: {settings.LANGSMITH_ENDPOINT}")
    
    try:
        # Initialize client
        client = Client(
            api_key=settings.LANGSMITH_API_KEY,
            api_url=settings.LANGSMITH_ENDPOINT
        )
        print("✓ Client initialized")
        
        # Test 1: Simple run creation
        print("\n--- Test 1: Simple Run Creation ---")
        run = client.create_run(
            name="test_simple",
            run_type="chain",
            inputs={"test": "hello"},
            project_name=settings.LANGSMITH_PROJECT
        )
        
        if run:
            print(f"✓ Run created: {run.id}")
            print(f"Run type: {type(run)}")
            print(f"Run dict: {run.__dict__ if hasattr(run, '__dict__') else 'No __dict__'}")
            
            # Test completion
            client.update_run(
                run_id=run.id,
                outputs={"result": "success"},
                end_time=datetime.now()
            )
            print("✓ Run completed successfully")
            
        else:
            print("✗ Run creation returned None")
            
        # Test 2: List existing runs to verify project access
        print("\n--- Test 2: Project Access ---")
        try:
            runs = list(client.list_runs(project_name=settings.LANGSMITH_PROJECT, limit=1))
            print(f"✓ Project accessible, found {len(runs)} recent runs")
        except Exception as list_error:
            print(f"✗ Project access error: {list_error}")
        
        # Test 3: Create run with conversation structure
        print("\n--- Test 3: Conversation Structure ---")
        conv_run = client.create_run(
            name="conversation_test_session",
            run_type="chain",
            inputs={
                "initial_message": "Hello",
                "user_id": "test_user",
                "channel_context": "test_channel"
            },
            project_name=settings.LANGSMITH_PROJECT
        )
        
        if conv_run:
            print(f"✓ Conversation run created: {conv_run.id}")
            
            # Add child runs (message turns)
            user_turn = client.create_run(
                name="user_new_message", 
                run_type="chain",
                inputs={"message": "Hello", "user": "test_user"},
                parent_run_id=conv_run.id,
                project_name=settings.LANGSMITH_PROJECT
            )
            
            if user_turn:
                print(f"✓ User turn created: {user_turn.id}")
                
                # Complete user turn
                client.update_run(
                    run_id=user_turn.id,
                    outputs={"processed": True},
                    end_time=datetime.now()
                )
                
                # Add assistant response
                assistant_turn = client.create_run(
                    name="assistant_response_complete",
                    run_type="chain", 
                    inputs={"processing_time_ms": 1500},
                    outputs={"final_response": "Hello! How can I help you?", "success": True},
                    parent_run_id=conv_run.id,
                    project_name=settings.LANGSMITH_PROJECT
                )
                
                if assistant_turn:
                    print(f"✓ Assistant turn created: {assistant_turn.id}")
                    client.update_run(
                        run_id=assistant_turn.id,
                        end_time=datetime.now()
                    )
                    print("✓ Full conversation structure tested successfully")
                else:
                    print("✗ Assistant turn creation failed")
            else:
                print("✗ User turn creation failed")
        else:
            print("✗ Conversation run creation failed")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_working_langsmith())