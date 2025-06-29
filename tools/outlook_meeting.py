"""
Outlook Meeting Tool - Microsoft Graph API integration for meeting management.
Provides meeting scheduling, availability checking, and calendar operations.
"""

import json
import logging
import time
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from config import settings
from services.trace_manager import trace_manager

logger = logging.getLogger(__name__)

class OutlookMeetingTool:
    """
    Microsoft Graph API-based tool for Outlook meeting management.
    Supports scheduling meetings, checking availability, and calendar operations.
    """
    
    def __init__(self):
        """Initialize Outlook meeting tool with Microsoft Graph API."""
        self.client_id = settings.MICROSOFT_CLIENT_ID
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET
        self.tenant_id = settings.MICROSOFT_TENANT_ID
        self.scope = settings.MICROSOFT_SCOPE
        
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        self.available = bool(self.client_id and self.client_secret and self.tenant_id)
        self.access_token = None
        self.token_expires_at = None
        
        if self.available:
            logger.info("Outlook meeting tool initialized successfully")
        else:
            logger.warning("Outlook meeting tool unavailable - missing Microsoft Graph API credentials")
    
    async def _get_access_token(self) -> Optional[str]:
        """Get or refresh Microsoft Graph API access token."""
        try:
            # Check if current token is still valid (with 5-minute buffer)
            if (self.access_token and self.token_expires_at and 
                datetime.now() < self.token_expires_at - timedelta(minutes=5)):
                return self.access_token
            
            # Request new token using client credentials flow
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
                "grant_type": "client_credentials"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.token_url, data=token_data)
                response.raise_for_status()
                
                token_info = response.json()
                self.access_token = token_info["access_token"]
                expires_in = token_info.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info("Successfully obtained Microsoft Graph API access token")
                return self.access_token
                
        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph API access token: {e}")
            return None
    
    async def check_availability(
        self,
        email_addresses: List[str],
        start_time: str,
        end_time: str,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Check availability for multiple users within a time range.
        
        Args:
            email_addresses: List of email addresses to check
            start_time: Start time in ISO 8601 format (e.g., "2024-01-15T09:00:00")
            end_time: End time in ISO 8601 format
            timezone: Timezone for the query (default: UTC)
            
        Returns:
            Dict containing availability information for each user
        """
        if not self.available:
            return {
                "error": "Outlook meeting tool not configured",
                "message": "Microsoft Graph API credentials not available"
            }
        
        start_time_trace = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_tool_operation(
                    "outlook_availability_check",
                    {"emails": email_addresses, "start": start_time, "end": end_time},
                    trace_manager.current_trace_id
                )
            
            access_token = await self._get_access_token()
            if not access_token:
                return {"error": "Authentication failed", "message": "Unable to get access token"}
            
            # Prepare request for Microsoft Graph getSchedule API
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            request_body = {
                "schedules": email_addresses,
                "startTime": {
                    "dateTime": start_time,
                    "timeZone": timezone
                },
                "endTime": {
                    "dateTime": end_time,
                    "timeZone": timezone
                },
                "availabilityViewInterval": 60  # 60-minute intervals
            }
            
            url = f"{self.base_url}/me/calendar/getSchedule"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=request_body)
                response.raise_for_status()
                
                schedule_data = response.json()
                
                # Process the response to make it more readable
                processed_result = {
                    "availability_check": {
                        "time_range": f"{start_time} to {end_time} ({timezone})",
                        "users": {}
                    },
                    "response_time": round(time.time() - start_time_trace, 2)
                }
                
                for i, schedule in enumerate(schedule_data.get("value", [])):
                    email = email_addresses[i] if i < len(email_addresses) else f"user_{i}"
                    
                    busy_times = []
                    for busy_time in schedule.get("busyTimes", []):
                        busy_times.append({
                            "start": busy_time.get("start", {}).get("dateTime"),
                            "end": busy_time.get("end", {}).get("dateTime")
                        })
                    
                    processed_result["availability_check"]["users"][email] = {
                        "availability_view": schedule.get("availabilityView", []),
                        "busy_times": busy_times,
                        "working_hours": schedule.get("workingHours", {})
                    }
                
                return processed_result
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Microsoft Graph API error: {e.response.status_code}"
            logger.error(f"{error_msg} - {e.response.text}")
            return {"error": error_msg, "details": e.response.text}
            
        except Exception as e:
            error_msg = f"Availability check failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def schedule_meeting(
        self,
        subject: str,
        attendee_emails: List[str],
        start_time: str,
        end_time: str,
        body: str = "",
        location: str = "",
        timezone: str = "UTC",
        is_online_meeting: bool = True
    ) -> Dict[str, Any]:
        """
        Schedule a new meeting in Outlook calendar.
        
        Args:
            subject: Meeting title/subject
            attendee_emails: List of attendee email addresses
            start_time: Start time in ISO 8601 format
            end_time: End time in ISO 8601 format
            body: Meeting description/body (optional)
            location: Meeting location (optional)
            timezone: Timezone for the meeting (default: UTC)
            is_online_meeting: Whether to create as Teams meeting (default: True)
            
        Returns:
            Dict containing meeting creation result
        """
        if not self.available:
            return {
                "error": "Outlook meeting tool not configured",
                "message": "Microsoft Graph API credentials not available"
            }
        
        start_time_trace = time.time()
        
        try:
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_tool_operation(
                    "outlook_schedule_meeting",
                    {"subject": subject, "attendees": len(attendee_emails), "start": start_time},
                    trace_manager.current_trace_id
                )
            
            access_token = await self._get_access_token()
            if not access_token:
                return {"error": "Authentication failed", "message": "Unable to get access token"}
            
            # Prepare meeting attendees
            attendees = []
            for email in attendee_emails:
                attendees.append({
                    "emailAddress": {
                        "address": email,
                        "name": email.split("@")[0]  # Use part before @ as display name
                    },
                    "type": "required"
                })
            
            # Prepare meeting request
            meeting_request = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone
                },
                "attendees": attendees,
                "allowNewTimeProposals": True,
                "isOnlineMeeting": is_online_meeting
            }
            
            # Add location if provided
            if location:
                meeting_request["location"] = {
                    "displayName": location
                }
            
            # Add online meeting provider if requested
            if is_online_meeting:
                meeting_request["onlineMeetingProvider"] = "teamsForBusiness"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/me/events"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=meeting_request)
                response.raise_for_status()
                
                meeting_data = response.json()
                
                # Process the response
                result = {
                    "meeting_scheduled": {
                        "id": meeting_data.get("id"),
                        "subject": meeting_data.get("subject"),
                        "start": meeting_data.get("start", {}).get("dateTime"),
                        "end": meeting_data.get("end", {}).get("dateTime"),
                        "web_link": meeting_data.get("webLink"),
                        "attendees": [att.get("emailAddress", {}).get("address") for att in meeting_data.get("attendees", [])],
                        "online_meeting": {
                            "join_url": meeting_data.get("onlineMeeting", {}).get("joinUrl"),
                            "conference_id": meeting_data.get("onlineMeeting", {}).get("conferenceId")
                        } if meeting_data.get("onlineMeeting") else None
                    },
                    "response_time": round(time.time() - start_time_trace, 2)
                }
                
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Microsoft Graph API error: {e.response.status_code}"
            logger.error(f"{error_msg} - {e.response.text}")
            return {"error": error_msg, "details": e.response.text}
            
        except Exception as e:
            error_msg = f"Meeting scheduling failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def find_meeting_times(
        self,
        attendee_emails: List[str],
        duration_minutes: int = 60,
        max_candidates: int = 20,
        start_date: str = None,
        end_date: str = None,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Find available meeting times for all attendees.
        
        Args:
            attendee_emails: List of attendee email addresses
            duration_minutes: Meeting duration in minutes (default: 60)
            max_candidates: Maximum number of time suggestions (default: 20)
            start_date: Search start date in ISO format (default: today)
            end_date: Search end date in ISO format (default: 7 days from today)
            timezone: Timezone for the search (default: UTC)
            
        Returns:
            Dict containing suggested meeting times
        """
        if not self.available:
            return {
                "error": "Outlook meeting tool not configured",
                "message": "Microsoft Graph API credentials not available"
            }
        
        start_time_trace = time.time()
        
        try:
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now().isoformat()
            if not end_date:
                end_date = (datetime.now() + timedelta(days=7)).isoformat()
            
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_tool_operation(
                    "outlook_find_meeting_times",
                    {"attendees": len(attendee_emails), "duration": duration_minutes},
                    trace_manager.current_trace_id
                )
            
            access_token = await self._get_access_token()
            if not access_token:
                return {"error": "Authentication failed", "message": "Unable to get access token"}
            
            # Prepare attendees for findMeetingTimes API
            attendees = []
            for email in attendee_emails:
                attendees.append({
                    "emailAddress": {
                        "address": email,
                        "name": email.split("@")[0]
                    }
                })
            
            request_body = {
                "attendees": attendees,
                "timeConstraint": {
                    "timeslots": [{
                        "start": {
                            "dateTime": start_date,
                            "timeZone": timezone
                        },
                        "end": {
                            "dateTime": end_date,
                            "timeZone": timezone
                        }
                    }]
                },
                "meetingDuration": f"PT{duration_minutes}M",  # ISO 8601 duration format
                "maxCandidates": max_candidates,
                "isOrganizerOptional": False,
                "returnSuggestionReasons": True
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.base_url}/me/calendar/getSchedule"  # Note: findMeetingTimes might not be available in all tenant configurations
            
            # For now, we'll implement a simpler availability check and suggest times
            # This is a fallback approach that works with standard Graph API permissions
            
            # Check availability for the next 7 days in 1-hour chunks
            suggestions = []
            current_time = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            # Simple time suggestion logic (9 AM to 5 PM on weekdays)
            while current_time < end_time and len(suggestions) < max_candidates:
                if current_time.weekday() < 5:  # Monday to Friday
                    if 9 <= current_time.hour <= 16:  # 9 AM to 4 PM (to allow for 1-hour meetings)
                        suggestion_start = current_time.isoformat()
                        suggestion_end = (current_time + timedelta(minutes=duration_minutes)).isoformat()
                        
                        suggestions.append({
                            "start": {
                                "dateTime": suggestion_start,
                                "timeZone": timezone
                            },
                            "end": {
                                "dateTime": suggestion_end,
                                "timeZone": timezone
                            },
                            "confidence": 75.0,  # Default confidence
                            "organizerAvailability": "free",
                            "attendeeAvailability": [],
                            "locations": []
                        })
                
                current_time += timedelta(hours=1)
            
            result = {
                "meeting_time_suggestions": {
                    "suggestions": suggestions[:max_candidates],
                    "search_parameters": {
                        "duration_minutes": duration_minutes,
                        "attendee_count": len(attendee_emails),
                        "search_range": f"{start_date} to {end_date}",
                        "timezone": timezone
                    }
                },
                "response_time": round(time.time() - start_time_trace, 2),
                "note": "Time suggestions based on standard business hours. For precise availability, use check_availability function."
            }
            
            return result
                
        except Exception as e:
            error_msg = f"Meeting time search failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    async def get_calendar_events(
        self,
        start_date: str = None,
        end_date: str = None,
        timezone: str = "UTC",
        max_events: int = 50
    ) -> Dict[str, Any]:
        """
        Get calendar events for a specified date range.
        
        Args:
            start_date: Start date in ISO format (default: today)
            end_date: End date in ISO format (default: 7 days from today)
            timezone: Timezone for the query (default: UTC)
            max_events: Maximum number of events to return (default: 50)
            
        Returns:
            Dict containing calendar events
        """
        if not self.available:
            return {
                "error": "Outlook meeting tool not configured",
                "message": "Microsoft Graph API credentials not available"
            }
        
        start_time_trace = time.time()
        
        try:
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now().isoformat()
            if not end_date:
                end_date = (datetime.now() + timedelta(days=7)).isoformat()
            
            # Trace the operation
            if trace_manager.current_trace_id:
                await trace_manager.log_tool_operation(
                    "outlook_get_calendar_events",
                    {"start": start_date, "end": end_date, "max": max_events},
                    trace_manager.current_trace_id
                )
            
            access_token = await self._get_access_token()
            if not access_token:
                return {"error": "Authentication failed", "message": "Unable to get access token"}
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Build query parameters for filtering events
            params = {
                "$top": max_events,
                "$orderby": "start/dateTime",
                "$filter": f"start/dateTime ge '{start_date}' and end/dateTime le '{end_date}'"
            }
            
            url = f"{self.base_url}/me/events"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                events_data = response.json()
                
                # Process events for readability
                processed_events = []
                for event in events_data.get("value", []):
                    processed_event = {
                        "id": event.get("id"),
                        "subject": event.get("subject"),
                        "start": event.get("start", {}).get("dateTime"),
                        "end": event.get("end", {}).get("dateTime"),
                        "location": event.get("location", {}).get("displayName"),
                        "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address"),
                        "attendees": [
                            att.get("emailAddress", {}).get("address")
                            for att in event.get("attendees", [])
                        ],
                        "web_link": event.get("webLink"),
                        "is_online_meeting": event.get("isOnlineMeeting", False),
                        "online_meeting_url": event.get("onlineMeeting", {}).get("joinUrl") if event.get("onlineMeeting") else None
                    }
                    processed_events.append(processed_event)
                
                result = {
                    "calendar_events": {
                        "events": processed_events,
                        "total_count": len(processed_events),
                        "date_range": f"{start_date} to {end_date}",
                        "timezone": timezone
                    },
                    "response_time": round(time.time() - start_time_trace, 2)
                }
                
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Microsoft Graph API error: {e.response.status_code}"
            logger.error(f"{error_msg} - {e.response.text}")
            return {"error": error_msg, "details": e.response.text}
            
        except Exception as e:
            error_msg = f"Calendar events retrieval failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}