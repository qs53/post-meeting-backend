import os
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from models import User, GoogleAccount
from config import settings

class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        self.scopes = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self):
        """Generate Google OAuth authorization URL"""
        flow = Flow.from_client_config(
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
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url, state
    
    def exchange_code_for_token(self, code: str):
        """Exchange authorization code for access token"""
        flow = Flow.from_client_config(
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
        flow.redirect_uri = self.redirect_uri
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return credentials
    
    def get_user_info(self, credentials: Credentials):
        """Get user information from Google"""
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        return user_info
    
    def save_google_account(self, db: Session, user: User, credentials: Credentials, user_info: dict):
        """Save or update Google account information"""
        google_user_id = user_info['id']
        email = user_info['email']
        
        # Check if Google account already exists
        google_account = db.query(GoogleAccount).filter(
            GoogleAccount.google_user_id == google_user_id
        ).first()
        
        if google_account:
            # Update existing account
            google_account.access_token = credentials.token
            google_account.refresh_token = credentials.refresh_token
            google_account.token_expires_at = credentials.expiry
            google_account.is_active = True
        else:
            # Create new account
            google_account = GoogleAccount(
                user_id=user.id,
                google_user_id=google_user_id,
                email=email,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expires_at=credentials.expiry
            )
            db.add(google_account)
        
        db.commit()
        db.refresh(google_account)
        return google_account
    
    def get_valid_credentials(self, db: Session, google_account: GoogleAccount):
        """Get valid credentials for a Google account, refreshing if necessary"""
        credentials = Credentials(
            token=google_account.access_token,
            refresh_token=google_account.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Check if token needs refresh
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # Update stored token
            google_account.access_token = credentials.token
            google_account.token_expires_at = credentials.expiry
            db.commit()
        
        return credentials
    
    def get_calendar_events(self, db: Session, google_account: GoogleAccount, max_results=10):
        """Get calendar events for a Google account"""
        credentials = self.get_valid_credentials(db, google_account)
        
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
        return events
