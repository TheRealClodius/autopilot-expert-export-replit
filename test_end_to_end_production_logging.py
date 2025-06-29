"""
End-to-End Production Logging Test
==================================

Test production logging integration through actual Slack webhook processing
to verify comprehensive execution tracing in deployment environment.
"""

import asyncio
import json
import time
import httpx
from datetime import datetime

async def test_end_to_end_production_logging():
    """Test production logging through complete Slack webhook flow"""
    print("🚀 END-TO-END PRODUCTION LOGGING TEST")
    print("🎯 Testing actual Slack webhook processing with production logging")
    print("=" * 70)
    
    try:
        base_url = "http://localhost:5000"
        
        # Step 1: Check initial production stats
        print("\n📊 STEP 1: Initial Production Statistics")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/admin/production-stats")
            if response.status_code == 200:
                initial_stats = response.json()['statistics']
                initial_traces = initial_stats.get('total_traces', initial_stats.get('active_traces', 0) + initial_stats.get('completed_traces', 0))
                print(f"✅ Initial traces: {initial_traces}")
            else:
                print(f"❌ Failed to get initial stats: {response.status_code}")
                return False
        
        # Step 2: Send simulated Slack webhook event
        print("\n🔗 STEP 2: Sending Simulated Slack Webhook")
        slack_event = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "text": "What are the latest features in the Autopilot for Everyone project?",
                "user": "U092YQL6HTN_TEST",  # Different from actual bot ID to avoid filtering
                "channel": "C123456789TEST",
                "ts": str(time.time())
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/slack/events",
                json=slack_event,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                webhook_response = response.json()
                print(f"✅ Webhook accepted: {webhook_response.get('status', 'unknown')}")
            else:
                print(f"❌ Webhook failed: {response.status_code} - {response.text}")
                return False
        
        # Step 3: Wait for processing and check updated stats
        print("\n⏱️  STEP 3: Waiting for Background Processing (10s)")
        await asyncio.sleep(10)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/admin/production-stats")
            if response.status_code == 200:
                updated_stats = response.json()['statistics']
                final_traces = updated_stats.get('total_traces', updated_stats.get('active_traces', 0) + updated_stats.get('completed_traces', 0))
                print(f"✅ Final traces: {final_traces}")
                
                if final_traces > initial_traces:
                    print(f"🎉 SUCCESS: New trace created! ({final_traces - initial_traces} new traces)")
                    new_trace_created = True
                else:
                    print(f"⚠️  No new traces detected (may indicate message filtering)")
                    new_trace_created = False
            else:
                print(f"❌ Failed to get updated stats: {response.status_code}")
                return False
        
        # Step 4: Get latest traces to find our test trace
        print("\n📋 STEP 4: Retrieving Latest Traces")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/admin/production-traces?limit=5")
            if response.status_code == 200:
                traces_response = response.json()
                traces = traces_response.get('traces', [])
                print(f"✅ Retrieved {len(traces)} latest traces")
                
                # Look for our test trace
                test_trace = None
                for trace in traces:
                    if 'Autopilot for Everyone' in trace.get('query', ''):
                        test_trace = trace
                        break
                
                if test_trace:
                    trace_id = test_trace['trace_id']
                    print(f"✅ Found our test trace: {trace_id}")
                    
                    # Step 5: Get detailed trace information
                    print(f"\n📄 STEP 5: Getting Detailed Trace Information")
                    response = await client.get(f"{base_url}/admin/production-trace/{trace_id}")
                    if response.status_code == 200:
                        detailed_trace = response.json()['trace']
                        steps = detailed_trace.get('steps', [])
                        print(f"✅ Trace has {len(steps)} execution steps")
                        
                        # Check for MCP calls
                        mcp_calls = [s for s in steps if s.get('step_type') == 'mcp_call']
                        api_calls = [s for s in steps if s.get('step_type') == 'api_call']
                        
                        print(f"   - MCP calls: {len(mcp_calls)}")
                        print(f"   - API calls: {len(api_calls)}")
                        print(f"   - Duration: {detailed_trace.get('total_duration_ms', 0):.1f}ms")
                    
                    # Step 6: Get execution transcript
                    print(f"\n📝 STEP 6: Getting Execution Transcript")
                    response = await client.get(f"{base_url}/admin/production-transcript/{trace_id}")
                    if response.status_code == 200:
                        transcript_response = response.json()
                        transcript = transcript_response.get('transcript', '')
                        print(f"✅ Generated transcript ({len(transcript)} characters)")
                        print("📄 Transcript preview:")
                        print("   " + transcript[:400].replace('\n', '\n   ') + "...")
                    
                    return True
                else:
                    print("⚠️  Test trace not found in latest traces")
                    if new_trace_created:
                        print("✅ But new traces were created, indicating system is working")
                        return True
                    else:
                        print("❌ No traces created, system may not be capturing properly")
                        return False
            else:
                print(f"❌ Failed to get traces: {response.status_code}")
                return False
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_admin_endpoints_comprehensive():
    """Test all admin endpoints for production logging"""
    print("\n🔧 COMPREHENSIVE ADMIN ENDPOINTS TEST")
    print("=" * 40)
    
    try:
        base_url = "http://localhost:5000"
        
        endpoints_tested = 0
        endpoints_passed = 0
        
        async with httpx.AsyncClient() as client:
            # Test 1: Production stats
            response = await client.get(f"{base_url}/admin/production-stats")
            endpoints_tested += 1
            if response.status_code == 200:
                stats = response.json()
                if 'statistics' in stats:
                    endpoints_passed += 1
                    print(f"✅ /admin/production-stats: Working")
                else:
                    print(f"❌ /admin/production-stats: Invalid format")
            else:
                print(f"❌ /admin/production-stats: {response.status_code}")
            
            # Test 2: Production traces
            response = await client.get(f"{base_url}/admin/production-traces?limit=3")
            endpoints_tested += 1
            if response.status_code == 200:
                traces = response.json()
                if 'traces' in traces:
                    endpoints_passed += 1
                    print(f"✅ /admin/production-traces: {traces['count']} traces")
                else:
                    print(f"❌ /admin/production-traces: Invalid format")
            else:
                print(f"❌ /admin/production-traces: {response.status_code}")
            
            # Test 3: Specific trace (if any exist)
            if 'traces' in traces and traces['traces']:
                trace_id = traces['traces'][0]['trace_id']
                
                response = await client.get(f"{base_url}/admin/production-trace/{trace_id}")
                endpoints_tested += 1
                if response.status_code == 200:
                    trace = response.json()
                    if 'trace' in trace:
                        endpoints_passed += 1
                        print(f"✅ /admin/production-trace/{trace_id}: Working")
                    else:
                        print(f"❌ /admin/production-trace/{trace_id}: Invalid format")
                else:
                    print(f"❌ /admin/production-trace/{trace_id}: {response.status_code}")
                
                # Test 4: Transcript
                response = await client.get(f"{base_url}/admin/production-transcript/{trace_id}")
                endpoints_tested += 1
                if response.status_code == 200:
                    transcript = response.json()
                    if 'transcript' in transcript:
                        endpoints_passed += 1
                        print(f"✅ /admin/production-transcript/{trace_id}: Working")
                    else:
                        print(f"❌ /admin/production-transcript/{trace_id}: Invalid format")
                else:
                    print(f"❌ /admin/production-transcript/{trace_id}: {response.status_code}")
        
        success_rate = (endpoints_passed / endpoints_tested * 100) if endpoints_tested > 0 else 0
        print(f"\n📊 ADMIN ENDPOINTS SUMMARY: {endpoints_passed}/{endpoints_tested} passed ({success_rate:.1f}%)")
        
        return endpoints_passed == endpoints_tested
        
    except Exception as e:
        print(f"❌ Admin endpoints test failed: {str(e)}")
        return False

async def main():
    """Run comprehensive end-to-end production logging verification"""
    print("🔬 COMPREHENSIVE END-TO-END PRODUCTION LOGGING VERIFICATION")
    print("🎯 Objective: Verify production logging captures complete Slack webhook execution")
    print("=" * 85)
    
    # Test end-to-end flow
    e2e_success = await test_end_to_end_production_logging()
    
    # Test admin endpoints
    admin_success = await test_admin_endpoints_comprehensive()
    
    print("\n📊 FINAL VERIFICATION SUMMARY")
    print("=" * 35)
    print(f"End-to-End Flow: {'✅ PASSED' if e2e_success else '❌ FAILED'}")
    print(f"Admin Endpoints: {'✅ PASSED' if admin_success else '❌ FAILED'}")
    
    if e2e_success and admin_success:
        print("\n🎉 PRODUCTION LOGGING SYSTEM FULLY OPERATIONAL")
        print("🔍 Ready to diagnose production vs local environment differences")
        print("📊 Complete execution tracing and admin endpoint access verified")
        print("🚀 System ready for deployment environment diagnosis")
    else:
        print("\n⚠️  PRODUCTION LOGGING SYSTEM NEEDS ATTENTION")
        print("🔧 Address remaining issues before deployment diagnosis")

if __name__ == "__main__":
    asyncio.run(main())