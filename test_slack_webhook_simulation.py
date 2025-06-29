#!/usr/bin/env python3
"""
Test Slack Webhook Simulation

Simulate a real Slack webhook to identify where the technical difficulties error is coming from.
"""

import asyncio
import httpx
import json
import time

async def test_slack_webhook():
    """Simulate a Slack webhook to test the processing pipeline"""
    
    print("\n" + "="*60)
    print("SLACK WEBHOOK SIMULATION TEST")
    print("="*60)
    
    # Simulate a real Slack message event
    slack_event = {
        "token": "verification_token",
        "team_id": "T123456",
        "api_app_id": "A123456",
        "event": {
            "type": "message",
            "channel": "C123456",
            "user": "U123456",
            "text": "<@U092YQL6HTN> Help me retrieve the roadmap for Autopilot for Everyone?",
            "ts": str(time.time()),
            "event_ts": str(time.time())
        },
        "type": "event_callback",
        "event_id": "Ev123456",
        "event_time": int(time.time())
    }
    
    try:
        print("🔄 Sending webhook to FastAPI server...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:5000/slack/events",
                json=slack_event,
                headers={
                    "Content-Type": "application/json",
                    "X-Slack-Signature": "test_signature",
                    "X-Slack-Request-Timestamp": str(int(time.time()))
                }
            )
            
            print(f"📊 Response status: {response.status_code}")
            print(f"📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"📊 Response body: {json.dumps(response_data, indent=2)}")
                except:
                    print(f"📊 Response text: {response.text}")
                
                print("✅ Webhook processed successfully")
                return True
            else:
                print(f"❌ Webhook failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_health_endpoints():
    """Test basic health endpoints first"""
    
    print("\n" + "="*60)
    print("HEALTH ENDPOINTS TEST")
    print("="*60)
    
    endpoints = [
        ("FastAPI Root", "http://localhost:5000/"),
        ("FastAPI Health", "http://localhost:5000/health"),
        ("MCP Health", "http://localhost:8001/healthz")
    ]
    
    results = []
    
    for name, url in endpoints:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    print(f"✅ {name}: OK ({response.status_code})")
                    results.append(True)
                else:
                    print(f"❌ {name}: FAILED ({response.status_code})")
                    results.append(False)
                    
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
            results.append(False)
    
    return all(results)

async def main():
    """Run the webhook simulation test"""
    
    print("Testing Slack webhook processing...")
    
    # Test 1: Health endpoints
    health_ok = await test_health_endpoints()
    
    if not health_ok:
        print("\n⚠️  Health checks failed, skipping webhook test")
        return False
    
    # Test 2: Slack webhook simulation
    webhook_ok = await test_slack_webhook()
    
    if webhook_ok:
        print("\n🎉 Webhook processing working!")
        print("If you're still seeing technical difficulties, it might be a Slack-specific issue.")
    else:
        print("\n⚠️  Webhook processing failed.")
        print("This explains the technical difficulties error.")
    
    return webhook_ok

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)