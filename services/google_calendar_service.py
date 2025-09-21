"""
Google Calendar service for real calendar integration
"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/google/callback')
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/calendar.readonly'
        ]
        
        # OAuth flow configuration
        self.flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        self.flow.redirect_uri = self.redirect_uri
    
    def get_auth_url(self, state: str = None) -> str:
        """
        Get Google OAuth authorization URL
        """
        auth_url, _ = self.flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        return auth_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens
        """
        try:
            self.flow.fetch_token(code=code)
            credentials = self.flow.credentials
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise
    
    def get_user_info(self, credentials_dict: Dict) -> Dict:
        """
        Get user information from Google
        """
        try:
            # Create credentials with all required fields
            credentials = Credentials(
                token=credentials_dict.get('access_token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_dict.get('client_id', self.client_id),
                client_secret=credentials_dict.get('client_secret', self.client_secret),
                scopes=credentials_dict.get('scopes', self.scopes)
            )
            
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            return {
                'id': user_info.get('id'),
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'verified_email': user_info.get('verified_email', False)
            }
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise
    
    def get_calendar_events(self, credentials_dict: Dict, max_results: int = 50) -> List[Dict]:
        """
        Get calendar events from Google Calendar
        """
        try:
            # Create credentials with all required fields
            credentials = Credentials(
                token=credentials_dict.get('access_token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_dict.get('client_id', self.client_id),
                client_secret=credentials_dict.get('client_secret', self.client_secret),
                scopes=credentials_dict.get('scopes', self.scopes)
            )
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get current time and 30 days from now
            now = datetime.utcnow()
            time_max = now + timedelta(days=30)
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Transform events to our format
            transformed_events = []
            for event in events:
                try:
                    # Parse start and end times
                    start = event.get('start', {})
                    end = event.get('end', {})
                    
                    start_time = None
                    end_time = None
                    
                    if 'dateTime' in start:
                        start_time = start['dateTime']
                    elif 'date' in start:
                        start_time = start['date'] + 'T00:00:00Z'
                    
                    if 'dateTime' in end:
                        end_time = end['dateTime']
                    elif 'date' in end:
                        end_time = end['date'] + 'T23:59:59Z'
                    
                    if not start_time or not end_time:
                        continue
                    
                    # Extract attendees
                    attendees = []
                    for attendee in event.get('attendees', []):
                        attendees.append({
                            'email': attendee.get('email'),
                            'name': attendee.get('displayName'),
                            'response_status': attendee.get('responseStatus', 'needsAction')
                        })
                    
                    # Check if event has meeting link
                    meeting_url = None
                    description = event.get('description', '') or ''
                    location = event.get('location', '') or ''
                    
                    # Look for meeting URLs in description or location
                    import re
                    url_pattern = r'https?://[^\s]+'
                    for text in [description, location]:
                        urls = re.findall(url_pattern, text)
                        for url in urls:
                            if any(platform in url.lower() for platform in ['zoom.us', 'teams.microsoft.com', 'meet.google.com', 'webex.com']):
                                meeting_url = url
                                break
                        if meeting_url:
                            break
                    
                    transformed_event = {
                        'id': event.get('id'),
                        'title': event.get('summary', 'No Title'),
                        'description': description,
                        'start_time': start_time,
                        'end_time': end_time,
                        'location': location,
                        'attendees': attendees,
                        'meeting_url': meeting_url,
                        'creator': event.get('creator', {}).get('email'),
                        'organizer': event.get('organizer', {}).get('email'),
                        'status': event.get('status'),
                        'html_link': event.get('htmlLink'),
                        'notetaker_enabled': False,  # Default to False, will be updated by user
                        'google_event_id': event.get('id'),
                        'google_account_email': credentials_dict.get('email', 'unknown')
                    }
                    
                    transformed_events.append(transformed_event)
                    
                except Exception as e:
                    logger.error(f"Error processing event {event.get('id', 'unknown')}: {str(e)}")
                    continue
            
            return transformed_events
            
        except Exception as e:
            logger.error(f"Error getting calendar events: {str(e)}")
            raise
    
    def refresh_credentials(self, credentials_dict: Dict) -> Dict:
        """
        Refresh expired credentials
        """
        try:
            # Create credentials with all required fields
            credentials = Credentials(
                token=credentials_dict.get('access_token'),
                refresh_token=credentials_dict.get('refresh_token'),
                token_uri=credentials_dict.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=credentials_dict.get('client_id', self.client_id),
                client_secret=credentials_dict.get('client_secret', self.client_secret),
                scopes=credentials_dict.get('scopes', self.scopes)
            )
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                return {
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes
                }
            else:
                return credentials_dict
                
        except Exception as e:
            logger.error(f"Error refreshing credentials: {str(e)}")
            raise
