#!/usr/bin/env python3
"""
Debug webhook structure to understand why user/text is null
"""

import asyncio
import httpx
import json

async def debug_webhook_structure():
    """Debug the webhook structure to understand filtering issue"""
    
    print("🔍 DEBUGGING WEBHOOK STRUCTURE")
    print("=" * 50)
    
    try:
        # Get latest production traces
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:5000/admin/production-traces")
            
            if response.status_code == 200:
                traces = response.json()
                
                if traces:
                    latest_trace = traces[0]
                    trace_id = latest_trace.get("trace_id")
                    
                    print(f"Latest trace ID: {trace_id}")
                    
                    # Get detailed trace
                    detail_response = await client.get(f"http://localhost:5000/admin/production-trace/{trace_id}")
                    if detail_response.status_code == 200:
                        trace_detail = detail_response.json()
                        
                        print(f"\n📋 TRACE DETAILS:")
                        print(f"Start time: {trace_detail.get('start_time')}")
                        print(f"End time: {trace_detail.get('end_time')}")
                        print(f"Status: {trace_detail.get('status')}")
                        
                        steps = trace_detail.get("steps", [])
                        
                        # Look for slack_gateway step
                        slack_steps = [step for step in steps if step.get("component") == "slack_gateway"]
                        
                        if slack_steps:
                            slack_step = slack_steps[0]
                            data = slack_step.get("data", {})
                            
                            print(f"\n🔍 SLACK GATEWAY STEP:")
                            print(f"Message type: {data.get('message_type')}")
                            print(f"Channel: {data.get('channel')}")
                            print(f"User: {data.get('user')}")
                            print(f"Query preview: '{data.get('query_preview')}'")
                            
                            # Check if there's more detail in the step
                            if "raw_event" in data:
                                raw_event = data["raw_event"]
                                print(f"\n📄 RAW EVENT STRUCTURE:")
                                print(json.dumps(raw_event, indent=2)[:500] + "...")
                            
                        # Look for main event validation step
                        validation_steps = [step for step in steps if step.get("component") == "main" and step.get("action") == "event_validation"]
                        
                        if validation_steps:
                            validation_step = validation_steps[0]
                            validation_data = validation_step.get("data", {})
                            
                            print(f"\n✅ EVENT VALIDATION:")
                            print(f"Event type: {validation_data.get('event_type')}")
                            print(f"Validation time: {validation_data.get('validation_time_ms')}ms")
                        
                        return True
                    else:
                        print(f"❌ Failed to get trace detail: {detail_response.status_code}")
                        return False
                else:
                    print("❌ No traces found")
                    return False
            else:
                print(f"❌ Failed to get traces: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Error debugging webhook structure: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(debug_webhook_structure())