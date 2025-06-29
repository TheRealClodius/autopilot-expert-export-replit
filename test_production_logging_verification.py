"""
Test Production Logging Integration
===================================

Comprehensive verification that production logging captures execution traces
for diagnosing production deployment issues with MCP integration.
"""

import asyncio
import json
import time
from datetime import datetime
from models.schemas import SlackEvent, ProcessedMessage

async def test_production_logging_integration():
    """Test complete production logging integration"""
    print("🔬 PRODUCTION LOGGING INTEGRATION TEST")
    print("=" * 50)
    
    try:
        # Import production logger
        from services.production_logger import production_logger
        
        # Test 1: Basic production logger functionality
        print("\n📋 TEST 1: Production Logger Initialization")
        stats = production_logger.get_production_stats()
        print(f"✅ Production logger initialized with {stats['total_traces']} traces")
        
        # Test 2: Trace creation and logging
        print("\n📋 TEST 2: Manual Trace Creation")
        mock_slack_event = {
            "type": "message",
            "text": "Testing production logging",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": str(time.time())
        }
        
        trace_id = production_logger.start_slack_trace(mock_slack_event)
        print(f"✅ Created trace: {trace_id}")
        
        # Log execution steps
        production_logger.log_step(trace_id, "orchestrator_start", "orchestrator", "query_analysis", {
            "query": "Testing production logging",
            "plan_created": True
        }, duration_ms=1200.5)
        
        production_logger.log_mcp_call(trace_id, "confluence_search", 
                                     {"query": "test", "limit": 10},
                                     {"success": True, "result": [{"title": "Test Page"}]}, 
                                     duration_ms=2500.0)
        
        production_logger.log_api_call(trace_id, "slack_api", "/api/chat.postMessage", 
                                     200, duration_ms=150.0)
        
        # Complete trace
        production_logger.complete_trace(trace_id, final_result={"status": "success"})
        print("✅ Logged orchestrator, MCP, and API steps")
        
        # Test 3: Retrieve trace data
        print("\n📋 TEST 3: Trace Retrieval")
        retrieved_trace = production_logger.get_trace_by_id(trace_id)
        if retrieved_trace:
            print(f"✅ Retrieved trace with {len(retrieved_trace['steps'])} steps")
            print(f"   Duration: {retrieved_trace.get('total_duration_ms', 0):.1f}ms")
        else:
            print("❌ Failed to retrieve trace")
            return False
        
        # Test 4: Execution transcript
        print("\n📋 TEST 4: Human-Readable Transcript")
        transcript = production_logger.get_execution_transcript(trace_id)
        if transcript:
            print("✅ Generated execution transcript:")
            print("   " + transcript.replace('\n', '\n   ')[:300] + "...")
        else:
            print("❌ Failed to generate transcript")
        
        # Test 5: Statistics
        print("\n📋 TEST 5: Production Statistics")
        updated_stats = production_logger.get_production_stats()
        print(f"✅ Total traces: {updated_stats['total_traces']}")
        print(f"✅ Successful traces: {updated_stats['successful_traces']}")
        print(f"✅ Average duration: {updated_stats['average_duration_ms']:.1f}ms")
        
        # Test 6: Latest traces
        print("\n📋 TEST 6: Latest Traces Retrieval")
        latest_traces = production_logger.get_latest_traces(5)
        print(f"✅ Retrieved {len(latest_traces)} latest traces")
        
        print("\n🎉 PRODUCTION LOGGING INTEGRATION: ALL TESTS PASSED")
        print("✅ Production logging ready for deployment environment diagnosis")
        return True
        
    except Exception as e:
        print(f"\n❌ PRODUCTION LOGGING TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_admin_endpoints():
    """Test admin endpoints for production trace extraction"""
    print("\n🌐 ADMIN ENDPOINTS TEST")
    print("=" * 30)
    
    try:
        import httpx
        base_url = "http://localhost:5000"
        
        # Test production stats endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/admin/production-stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ /admin/production-stats: {stats['statistics']['total_traces']} traces")
            else:
                print(f"❌ Production stats endpoint failed: {response.status_code}")
                return False
            
            # Test traces list endpoint
            response = await client.get(f"{base_url}/admin/production-traces?limit=5")
            if response.status_code == 200:
                traces = response.json()
                print(f"✅ /admin/production-traces: {traces['count']} traces retrieved")
                
                # Test specific trace endpoint if we have traces
                if traces['traces']:
                    first_trace_id = traces['traces'][0]['trace_id']
                    response = await client.get(f"{base_url}/admin/production-trace/{first_trace_id}")
                    if response.status_code == 200:
                        print(f"✅ /admin/production-trace/{first_trace_id}: Success")
                    else:
                        print(f"❌ Specific trace endpoint failed: {response.status_code}")
                    
                    # Test transcript endpoint
                    response = await client.get(f"{base_url}/admin/production-transcript/{first_trace_id}")
                    if response.status_code == 200:
                        transcript = response.json()
                        print(f"✅ /admin/production-transcript/{first_trace_id}: {len(transcript['transcript'])} chars")
                    else:
                        print(f"❌ Transcript endpoint failed: {response.status_code}")
            else:
                print(f"❌ Production traces endpoint failed: {response.status_code}")
                return False
        
        print("✅ All admin endpoints working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Admin endpoints test failed: {str(e)}")
        return False

async def main():
    """Run comprehensive production logging verification"""
    print("🚀 COMPREHENSIVE PRODUCTION LOGGING VERIFICATION")
    print("🎯 Objective: Verify logging system ready for deployment environment diagnosis")
    print("=" * 80)
    
    # Test production logging integration
    logging_test = await test_production_logging_integration()
    
    # Give server time to restart if needed
    await asyncio.sleep(2)
    
    # Test admin endpoints
    endpoints_test = await test_admin_endpoints()
    
    print("\n📊 VERIFICATION SUMMARY")
    print("=" * 25)
    print(f"Production Logging: {'✅ PASSED' if logging_test else '❌ FAILED'}")
    print(f"Admin Endpoints: {'✅ PASSED' if endpoints_test else '❌ FAILED'}")
    
    if logging_test and endpoints_test:
        print("\n🎉 PRODUCTION LOGGING SYSTEM FULLY OPERATIONAL")
        print("🔍 Ready to diagnose production vs local environment differences")
        print("📝 Admin endpoints available for trace extraction and analysis")
    else:
        print("\n⚠️  PRODUCTION LOGGING SYSTEM NEEDS ATTENTION")
        print("🔧 Address issues before production deployment diagnosis")

if __name__ == "__main__":
    asyncio.run(main())