#!/usr/bin/env python3
"""
Quick test for Liz Holz calendar availability
"""
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.outlook_meeting import OutlookMeetingTool
from datetime import datetime, timedelta

async def test_liz_holz():
    """Test calendar access for Liz Holz"""
    print("🔍 Testing Outlook integration for Liz Holz...")
    
    # Initialize the tool
    outlook_tool = OutlookMeetingTool()
    
    if not outlook_tool.available:
        print("❌ Outlook tool not available - missing credentials")
        return
    
    print("✅ Outlook tool initialized successfully")
    
    # Test 1: Check availability for Liz Holz
    print("\n📅 Test 1: Checking availability for Liz Holz tomorrow 2-3 PM")
    
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()
    end_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
    
    try:
        result = await outlook_tool.check_availability(
            attendee_emails=["liz.holz@company.com"],
            start_time=start_time,
            end_time=end_time
        )
        print(f"📊 Availability result: {result}")
        
    except Exception as e:
        print(f"⚠️ Availability check error: {str(e)}")
        print(f"📝 This is expected if calendar permissions aren't granted yet")
    
    # Test 2: Try to get calendar info
    print("\n📋 Test 2: Getting calendar information for Liz Holz")
    
    try:
        result = await outlook_tool.get_calendar(
            attendee_emails=["liz.holz@company.com"],
            start_time=start_time,
            end_time=end_time
        )
        print(f"📅 Calendar result: {result}")
        
    except Exception as e:
        print(f"⚠️ Calendar access error: {str(e)}")
        print(f"📝 This is expected if calendar permissions aren't granted yet")
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_liz_holz())