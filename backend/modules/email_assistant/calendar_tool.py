# Calendar Tool - Google Calendar API integration
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .auth_manager import auth_manager


class CalendarTool:
    """Tool for interacting with Google Calendar API."""
    
    def __init__(self):
        self.service = None
        self._build_service()
    
    def _build_service(self):
        """Build Calendar API service."""
        creds = auth_manager.get_credentials()
        if creds:
            try:
                self.service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            except Exception as e:
                print(f"Error building Calendar service: {e}")
                self.service = None
    
    def is_available(self) -> bool:
        """Check if Calendar service is available."""
        return self.service is not None and auth_manager.is_authenticated()
    
    def list_events(
        self,
        max_results: int = 20,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        List calendar events.
        
        Args:
            max_results: Maximum number of events
            time_min: Start time filter
            time_max: End time filter
            calendar_id: Calendar ID (default: primary)
        
        Returns:
            List of events
        """
        if not self.is_available():
            return []
        
        try:
            # Default to now if no time_min
            if not time_min:
                time_min = datetime.now()
            
            # Format for API: ISO 8601 with timezone
            time_min_str = time_min.isoformat() + 'Z'
            time_max_str = time_max.isoformat() + 'Z' if time_max else None
            
            kwargs = {
                'calendarId': calendar_id,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
                'timeMin': time_min_str
            }
            
            if time_max_str:
                kwargs['timeMax'] = time_max_str
            
            events_result = self.service.events().list(**kwargs).execute()
            events = events_result.get('items', [])
            
            return [self._format_event(e) for e in events]
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return []
        except Exception as e:
            print(f"Error listing events: {e}")
            return []
    
    def _format_event(self, event: Dict) -> Dict[str, Any]:
        """Format event data for consistent output."""
        formatted = {
            'id': event.get('id', ''),
            'summary': event.get('summary', 'Sin título'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'status': event.get('status', ''),
            'created': event.get('created', ''),
            'updated': event.get('updated', '')
        }
        
        # Handle start/end times
        start = event.get('start', {})
        end = event.get('end', {})
        
        # DateTime (with time) vs Date (all-day)
        if 'dateTime' in start:
            formatted['start'] = start['dateTime']
            formatted['end'] = end.get('dateTime', '')
            formatted['all_day'] = False
        elif 'date' in start:
            formatted['start'] = start['date']
            formatted['end'] = end.get('date', '')
            formatted['all_day'] = True
        
        # Attendees
        formatted['attendees'] = event.get('attendees', [])
        formatted['attendee_count'] = len(formatted['attendees'])
        
        # Reminders
        reminders = event.get('reminders', {})
        formatted['reminders_enabled'] = reminders.get('useDefault', False)
        if 'overrides' in reminders:
            formatted['reminder_overrides'] = reminders['overrides']
        
        return formatted
    
    def get_event(self, event_id: str, calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """
        Get a specific event.
        
        Args:
            event_id: Event ID
            calendar_id: Calendar ID
        
        Returns:
            Event data or None
        """
        if not self.is_available():
            return None
        
        try:
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return self._format_event(event)
            
        except HttpError as e:
            if e.resp.status == 404:
                return None
            print(f"Calendar API error: {e}")
            return None
        except Exception as e:
            print(f"Error getting event: {e}")
            return None
    
    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        reminder_minutes: Optional[int] = 30,
        timezone: str = 'America/Mexico_City'
    ) -> Dict[str, Any]:
        """
        Create a new calendar event.
        
        Args:
            summary: Event title
            start_time: Start datetime
            end_time: End datetime
            description: Event description
            location: Event location
            attendees: List of attendee emails
            reminder_minutes: Minutes before event to remind
            timezone: Timezone string
        
        Returns:
            Result with event ID if successful
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Google Calendar"
            }
        
        try:
            event = {
                'summary': summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
            }
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            if reminder_minutes:
                event['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': reminder_minutes},
                        {'method': 'popup', 'minutes': reminder_minutes},
                    ]
                }
            
            created_event = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all' if attendees else 'none'
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "html_link": created_event.get('htmlLink', ''),
                "message": "Evento creado correctamente"
            }
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return {
                "success": False,
                "error": f"Error al crear evento: {str(e)}"
            }
        except Exception as e:
            print(f"Error creating event: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update an existing event.
        
        Args:
            event_id: Event ID to update
            calendar_id: Calendar ID
            **kwargs: Fields to update (summary, description, start_time, end_time, etc.)
        
        Returns:
            Result status
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Google Calendar"
            }
        
        try:
            # Get current event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if 'summary' in kwargs:
                event['summary'] = kwargs['summary']
            if 'description' in kwargs:
                event['description'] = kwargs['description']
            if 'location' in kwargs:
                event['location'] = kwargs['location']
            if 'start_time' in kwargs:
                event['start']['dateTime'] = kwargs['start_time'].isoformat()
            if 'end_time' in kwargs:
                event['end']['dateTime'] = kwargs['end_time'].isoformat()
            
            updated = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "message": "Evento actualizado",
                "event_id": updated['id']
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> Dict[str, Any]:
        """
        Delete a calendar event.
        
        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID
        
        Returns:
            Result status
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "No autenticado con Google Calendar"
            }
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            
            return {
                "success": True,
                "message": "Evento eliminado"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def find_free_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        timezone: str = 'America/Mexico_City'
    ) -> List[Dict[str, Any]]:
        """
        Find available time slots in the given date range.
        
        Args:
            start_date: Start of search range
            end_date: End of search range
            duration_minutes: Required slot duration
            timezone: Timezone
        
        Returns:
            List of available time slots
        """
        if not self.is_available():
            return []
        
        try:
            # Get all events in range
            events = self.list_events(
                time_min=start_date,
                time_max=end_date
            )
            
            # Convert events to busy periods
            busy_periods = []
            for event in events:
                if event.get('start') and event['status'] != 'cancelled':
                    busy_periods.append({
                        'start': event['start'],
                        'end': event['end']
                    })
            
            # Find free slots
            free_slots = []
            current_time = start_date
            
            while current_time < end_date:
                slot_end = current_time + timedelta(minutes=duration_minutes)
                
                # Check if this slot overlaps with any busy period
                is_free = True
                for busy in busy_periods:
                    busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                    busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                    
                    if current_time < busy_end and slot_end > busy_start:
                        is_free = False
                        break
                
                if is_free:
                    # Check if slot is during reasonable hours (8am - 8pm)
                    if 8 <= current_time.hour <= 20:
                        free_slots.append({
                            'start': current_time,
                            'end': slot_end,
                            'formatted_start': current_time.strftime('%A %d, %H:%M'),
                            'formatted_end': slot_end.strftime('%H:%M')
                        })
                    
                    current_time += timedelta(minutes=duration_minutes)
                else:
                    # Move to end of busy period
                    if busy_periods:
                        latest_end = max(
                            datetime.fromisoformat(b['end'].replace('Z', '+00:00'))
                            for b in busy_periods
                        )
                        current_time = latest_end
            
            return free_slots
            
        except Exception as e:
            print(f"Error finding free slots: {e}")
            return []
    
    def check_conflicts(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_event_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check for conflicting events with the given time range.
        
        Args:
            start_time: Event start time
            end_time: Event end time
            exclude_event_id: Event ID to exclude (for updates)
        
        Returns:
            List of conflicting events
        """
        events = self.list_events(time_min=start_time, time_max=end_time)
        
        conflicts = []
        for event in events:
            if event.get('id') == exclude_event_id:
                continue
            
            if event.get('status') == 'cancelled':
                continue
            
            event_start = event.get('start', '')
            event_end = event.get('end', '')
            
            if event_start and event_end:
                conflicts.append({
                    'id': event['id'],
                    'summary': event['summary'],
                    'start': event_start,
                    'end': event_end
                })
        
        return conflicts


# Global instance
calendar_tool = CalendarTool()
