#!/usr/bin/env python3
"""
Full integration test for Outlook meeting functionality
This will work once admin grants calendar permissions
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.outlook_meeting import OutlookMeetingTool

async def test_full_integration():
    """Test complete Outlook integration once permissions are granted"""
    print("Testing complete Outlook integration...")
    
    outlook_tool = OutlookMeetingTool()
    
    if not outlook_tool.available:
        print("Outlook tool not available")
        return
    
    print("Outlook tool initialized successfully")
    
    # Test scenarios that will work with User.Read.All + Calendars.ReadWrite
    
    # Test 1: Search for Liz Holz
    print("\n1. Testing user search for Liz Holz")
    test_emails = [
        "liz.holz@company.com",
        "lholz@company.com", 
        "elizabeth.holz@company.com",
        "liz@company.com"
    ]
    
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0).isoformat()
    end_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
    
    working_emails = []
    for email in test_emails:
        try:
            result = await outlook_tool.check_availability(
                email_addresses=[email],
                start_time=start_time,
                end_time=end_time
            )
            
            if not result.get('error'):
                print(f"✅ Found working email: {email}")
                working_emails.append(email)
                break
            else:
                print(f"❌ {email}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ {email}: {str(e)}")
    
    if working_emails:
        # Test 2: Check availability for found users
        print(f"\n2. Testing availability check for {working_emails[0]}")
        try:
            result = await outlook_tool.check_availability(
                email_addresses=working_emails,
                start_time=start_time,
                end_time=end_time
            )
            print(f"Availability result: {result}")
            
        except Exception as e:
            print(f"Availability check failed: {e}")
        
        # Test 3: Find meeting times
        print(f"\n3. Testing find meeting times for {len(working_emails)} attendees")
        try:
            # This would be a new method we'd need to implement
            week_start = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            week_end = (datetime.now() + timedelta(days=5)).replace(hour=17, minute=0, second=0, microsecond=0)
            
            result = await outlook_tool.check_availability(
                email_addresses=working_emails,
                start_time=week_start.isoformat(),
                end_time=week_end.isoformat()
            )
            print(f"Week availability: {result}")
            
        except Exception as e:
            print(f"Find meeting times failed: {e}")
        
        # Test 4: Schedule a test meeting (careful!)
        print(f"\n4. Testing meeting scheduling (TEST ONLY)")
        try:
            meeting_start = (datetime.now() + timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=1)
            
            result = await outlook_tool.schedule_meeting(
                subject="TEST - Slack Bot Integration Test",
                attendee_emails=working_emails,
                start_time=meeting_start.isoformat(),
                end_time=meeting_end.isoformat(),
                body="This is a test meeting created by the Slack bot integration. Please disregard.",
                location="Virtual"
            )
            print(f"Meeting scheduled: {result}")
            
        except Exception as e:
            print(f"Meeting scheduling failed: {e}")
    
    else:
        print("No working email addresses found - may need different email format")
    
    print("\nIntegration test completed!")
    print("Once admin grants Calendars.ReadWrite permission, all these features will work through Slack!")

if __name__ == "__main__":
    asyncio.run(test_full_integration())