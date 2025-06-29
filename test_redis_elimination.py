#!/usr/bin/env python3
"""
Redis Elimination Verification Test

This test verifies that the deployment can run completely without Redis,
using memory-based fallbacks for all Redis-dependent services.
"""

import asyncio
import aiohttp
import subprocess
import time
import os
import sys
from datetime import datetime


async def test_redis_free_deployment():
    """Test that deployment starts and runs without any Redis dependencies"""
    
    print("=" * 80)
    print("🔧 REDIS ELIMINATION VERIFICATION")
    print("=" * 80)
    
    # Force Redis-free environment
    os.environ["CELERY_BROKER_URL"] = "memory://"
    os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
    os.environ["REDIS_URL"] = ""
    os.environ["REDIS_PASSWORD"] = ""
    
    print("\n1️⃣ TESTING REDIS-FREE STARTUP")
    print("-" * 60)
    
    try:
        print("🚀 Starting Redis-free deployment...")
        
        # Start the deployment script
        process = subprocess.Popen(
            [sys.executable, "start_deployment.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=os.environ  # Pass Redis-free environment
        )
        
        print(f"Deployment script started with PID: {process.pid}")
        
        # Monitor for Redis connection attempts in output
        print("⏳ Monitoring startup for Redis connection attempts...")
        
        startup_lines = []
        redis_errors = []
        
        # Collect first 30 seconds of output
        start_time = time.time()
        while time.time() - start_time < 30:
            if process.poll() is not None:
                break
                
            try:
                line = process.stdout.readline()
                if line:
                    startup_lines.append(line.strip())
                    print(f"   {line.strip()}")
                    
                    # Check for Redis connection attempts
                    if any(redis_indicator in line.lower() for redis_indicator in [
                        "redis://", "6379", "connection refused", "redis.exceptions",
                        "dial tcp 127.0.0.1:6379", "redis connection"
                    ]):
                        redis_errors.append(line.strip())
                else:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"   Error reading output: {e}")
                break
        
        # Check results
        if redis_errors:
            print("\n❌ REDIS CONNECTION ATTEMPTS DETECTED:")
            for error in redis_errors:
                print(f"   {error}")
            redis_free = False
        else:
            print("\n✅ NO REDIS CONNECTION ATTEMPTS DETECTED")
            redis_free = True
        
        # Test server availability
        print("\n2️⃣ TESTING SERVER AVAILABILITY")
        print("-" * 60)
        
        servers_ready = False
        
        # Wait a bit more for servers to fully start
        await asyncio.sleep(15)
        
        async with aiohttp.ClientSession() as session:
            # Test MCP server
            try:
                async with session.get("http://localhost:8001/healthz", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        print("✅ MCP server is running")
                        mcp_ready = True
                    else:
                        print(f"❌ MCP server returned status: {response.status}")
                        mcp_ready = False
            except Exception as e:
                print(f"❌ MCP server not reachable: {e}")
                mcp_ready = False
            
            # Test FastAPI server
            try:
                async with session.get("http://localhost:5000/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ FastAPI server is running")
                        print(f"   Status: {result.get('status', 'unknown')}")
                        fastapi_ready = True
                    else:
                        print(f"❌ FastAPI server returned status: {response.status}")
                        fastapi_ready = False
            except Exception as e:
                print(f"❌ FastAPI server not reachable: {e}")
                fastapi_ready = False
        
        servers_ready = mcp_ready and fastapi_ready
        
        # Test memory service functionality
        if servers_ready:
            print("\n3️⃣ TESTING MEMORY SERVICE WITHOUT REDIS")
            print("-" * 60)
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Test memory service endpoints
                    url = "http://localhost:5000/admin/short-term-memory-test"
                    
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get("test_passed"):
                                print("✅ Memory service working with in-memory cache")
                                print(f"   Cached messages: {result.get('message_count', 0)}")
                                memory_working = True
                            else:
                                print(f"❌ Memory service test failed: {result}")
                                memory_working = False
                        else:
                            print(f"❌ Memory service test returned: {response.status}")
                            memory_working = False
            except Exception as e:
                print(f"❌ Memory service test exception: {e}")
                memory_working = False
        else:
            print("\n⏸️ Skipping memory service test - servers not ready")
            memory_working = False
        
        # Test webhook processing without Redis
        if servers_ready and memory_working:
            print("\n4️⃣ TESTING WEBHOOK PROCESSING WITHOUT REDIS")
            print("-" * 60)
            
            # Test a simple webhook
            slack_payload = {
                "type": "event_callback",
                "event": {
                    "type": "message",
                    "text": "Test Redis-free deployment",
                    "user": "U123TEST",
                    "channel": "C123TEST",
                    "ts": str(datetime.now().timestamp()),
                    "event_ts": str(datetime.now().timestamp()),
                    "channel_type": "channel"
                },
                "team_id": "T123TEST",
                "event_id": f"Ev{int(datetime.now().timestamp())}REDIS",
                "event_time": int(datetime.now().timestamp())
            }
            
            try:
                async with aiohttp.ClientSession() as session:
                    url = "http://localhost:5000/slack/events"
                    
                    print("🔍 Testing webhook processing...")
                    
                    start_time = datetime.now()
                    
                    async with session.post(
                        url,
                        json=slack_payload,
                        timeout=aiohttp.ClientTimeout(total=90)
                    ) as response:
                        duration = (datetime.now() - start_time).total_seconds()
                        
                        print(f"⏱️ Processing time: {duration:.2f}s")
                        
                        if response.status == 200:
                            print("✅ WEBHOOK PROCESSING SUCCESSFUL WITHOUT REDIS!")
                            webhook_success = True
                        else:
                            result = await response.text()
                            print(f"❌ Webhook processing failed: {response.status}")
                            print(f"   Response: {result}")
                            webhook_success = False
                            
            except Exception as e:
                print(f"❌ Webhook processing exception: {e}")
                webhook_success = False
        else:
            print("\n⏸️ Skipping webhook test - prerequisites not met")
            webhook_success = False
        
        # Cleanup
        print("\n5️⃣ CLEANUP")
        print("-" * 60)
        
        print("Terminating deployment process...")
        process.terminate()
        
        try:
            process.wait(timeout=10)
            print("✅ Deployment process terminated cleanly")
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing deployment process")
            process.kill()
        
        # Final assessment
        print("\n" + "=" * 80)
        print("📊 REDIS ELIMINATION VERIFICATION RESULTS")
        print("=" * 80)
        
        if redis_free:
            print("✅ NO REDIS CONNECTION ATTEMPTS - Clean deployment")
        else:
            print("❌ REDIS CONNECTION ATTEMPTS DETECTED - Further fixes needed")
        
        if servers_ready:
            print("✅ Both servers start successfully without Redis")
        else:
            print("❌ Server startup issues remain")
        
        if memory_working:
            print("✅ Memory service works with in-memory cache fallback")
        else:
            print("❌ Memory service issues remain")
        
        if webhook_success:
            print("✅ WEBHOOK PROCESSING WORKS WITHOUT REDIS!")
            print("   Ready for Redis-free deployment")
            return True
        else:
            print("❌ Webhook processing still has issues")
            return False
            
    except Exception as e:
        print(f"❌ Redis elimination test failed: {e}")
        return False


async def main():
    """Run Redis elimination verification"""
    
    print("🔧 REDIS ELIMINATION VERIFICATION")
    print("Testing deployment without any Redis dependencies")
    print("=" * 80)
    
    success = await test_redis_free_deployment()
    
    if success:
        print("\n🎉 REDIS ELIMINATION SUCCESSFUL!")
        print("The deployment can run completely without Redis")
        print("Ready for deployment with memory-only configuration")
    else:
        print("\n❌ REDIS ELIMINATION INCOMPLETE")
        print("Additional fixes needed to remove all Redis dependencies")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)