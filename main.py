import logging
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Try to import Google Calendar service, fallback to mock if not available
try:
    from services.google_calendar_service import GoogleCalendarService
    google_calendar_service = GoogleCalendarService()
    logger.info("Google Calendar service initialized")
except Exception as e:
    logger.warning(f"Google Calendar service not available: {e}")
    google_calendar_service = None

# Try to import Recall.ai service, fallback to mock if not available
try:
    from services.recall_service import RecallService
    recall_service = RecallService()
    logger.info("Recall.ai service initialized")
except Exception as e:
    logger.warning(f"Recall.ai service not available: {e}")
    recall_service = None

# Try to import AI service, fallback to mock if not available
try:
    from services.ai_service import AIService
    ai_service = AIService()
    logger.info("AI service initialized")
except Exception as e:
    logger.warning(f"AI service not available: {e}")
    ai_service = None

# Try to import Social Media service, fallback to mock if not available
try:
    from services.social_media_service import SocialMediaService
    social_media_service = SocialMediaService()
    logger.info("Social Media service initialized")
except Exception as e:
    logger.warning(f"Social Media service not available: {e}")
    social_media_service = None

# Create Flask app
app = Flask(__name__)
CORS(app)

# In-memory storage for demo (replace with database in production)
user_credentials = {}
meeting_data = {}
notetaker_settings = {}  # Store notetaker settings for events
scheduled_bots = {}  # Store scheduled bot information
completed_meetings = {}  # Store completed meetings with transcripts
user_settings = {  # Store user settings in memory
    "recallJoinBeforeMinutes": 5,
    "enableNotifications": True,
    "autoGenerateContent": True,
    "defaultPlatform": "zoom",
    "linkedinPrompt": "Draft a LinkedIn post (120-180 words) that summarizes the meeting value in first person. Use a warm, conversational tone consistent with an experienced financial advisor. End with up to three hashtags. Return only the post text.",
    "facebookPrompt": "Write a Facebook post (100-150 words) that summarizes the meeting value in first person. Use a friendly, conversational tone that's engaging for Facebook. Include 2-3 relevant hashtags at the end. Make it shareable and engaging for Facebook audience. Return only the post text."
}

def poll_recall_bots_background():
    """Background function to poll Recall bots for completed meetings"""
    logger.info("Background polling thread started")
    poll_count = 0
    
    while True:
        try:
            poll_count += 1
            logger.info(f"Polling cycle #{poll_count} - Checking for completed bots...")
            logger.info(f"Total scheduled bots: {scheduled_bots}")
            logger.info(f"Total scheduled bots: {len(scheduled_bots)}")
            logger.info(f"Total completed meetings: {len(completed_meetings)}")
            
            if recall_service:
                completed_bots = recall_service.poll_managed_bots()
                logger.info(f"Found {len(completed_bots)} completed bots")
                
                for completed_bot in completed_bots:
                    bot_id = completed_bot['bot_id']
                    logger.info(f"Processing completed bot: {bot_id}")
                    
                    # Find the corresponding meeting event
                    meeting_id = None
                    for event_id, bot_info in scheduled_bots.items():
                        if bot_info.get('bot_id') == bot_id:
                            meeting_id = event_id
                            break

                    
                    if meeting_id:
                        # Get meeting info from scheduled bots
                        meeting_info = scheduled_bots.get(meeting_id, {}).get('meeting_info', {})
                        logger.info(f"Meeting info for {meeting_id}: {meeting_info}")
                        logger.info(f"Attendees from meeting_info: {meeting_info.get('attendees', [])}")
                        logger.info(f"scheduled bots: {scheduled_bots}")
                        
                        # Store completed meeting data
                        completed_meetings[meeting_id] = {
                            'meeting_id': meeting_id,
                            'bot_id': bot_id,
                            'transcript': completed_bot.get('transcript', ''),
                            'media_url': completed_bot.get('media_url', ''),
                            'status': 'completed',
                            'completed_at': completed_bot.get('completed_at', ''),
                            'duration': completed_bot.get('duration', 0),
                            'attendees': meeting_info.get('attendees', []),
                            'platform': meeting_info.get('platform', 'unknown'),
                            'meeting_url': meeting_info.get('meeting_url', ''),
                            'title': meeting_info.get('title', 'Untitled Meeting')
                        }
                        logger.info(f"Stored attendees in completed_meetings: {completed_meetings[meeting_id]['attendees']}")
                        
                        # Update scheduled bot status
                        scheduled_bots[meeting_id]['status'] = 'completed'
                        scheduled_bots[meeting_id]['completed_data'] = completed_bot
                        
                        transcript_length = len(completed_bot.get('transcript', ''))
                        logger.info(f"Stored completed meeting {meeting_id} with transcript ({transcript_length} chars)")
                    else:
                        logger.warning(f"Could not find meeting for completed bot {bot_id}")
                        logger.warning(f"Available scheduled bots: {list(scheduled_bots.keys())}")
                
                if completed_bots:
                    logger.info(f"Successfully processed {len(completed_bots)} completed meetings")
                else:
                    logger.info("No completed meetings found in this cycle")
            else:
                logger.warning("Recall service not available, skipping polling")

            logger.info(f"Polling cycle #{poll_count} completed, sleeping for 120 seconds...")
            time.sleep(120)
            
        except Exception as e:
            logger.error(f"Error in background polling cycle #{poll_count}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error("Sleeping for 60 seconds before retry...")
            time.sleep(60)  # Wait 1 minute on error

# Start background polling thread
if recall_service:
    polling_thread = threading.Thread(target=poll_recall_bots_background, daemon=True)
    polling_thread.start()
    logger.info("Started background polling for Recall bots")

# Routes
@app.route('/')
def root():
    return jsonify({
        "message": "Post-Meeting Social Media Generator API",
        "status": "running"
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Backend is running successfully"
    })

@app.route('/auth/google')
def google_auth():
    """Get Google OAuth URL"""
    if google_calendar_service:
        try:
            auth_url = google_calendar_service.get_auth_url("test_state")
            return jsonify({
                "auth_url": auth_url,
                "state": "test_state"
            })
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            # Fallback to mock URL
            pass
    
    # Fallback to mock URL if service not available
    return jsonify({
        "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=871559871580-9j8c3hi70u9pobf0u4mu6qg0ofue32ek.apps.googleusercontent.com&redirect_uri=http://localhost:8000/auth/google/callback&response_type=code&scope=openid email profile https://www.googleapis.com/auth/calendar.readonly",
        "state": "test_state"
    })

@app.route('/auth/linkedin/callback')
def linkedin_auth_callback():
    """Handle LinkedIn OAuth callback"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400
    
    try:
        if social_media_service:
            result = social_media_service.handle_platform_callback('linkedin', code)
            if result["success"]:
                # Redirect to frontend with success
                from urllib.parse import urlencode
                auth_data = {
                    "access_token": result["access_token"],
                    "platform": "linkedin",
                    "status": "success"
                }
                frontend_url = f"http://localhost:3000/auth/success?{urlencode(auth_data)}"
                return redirect(frontend_url)
            else:
                return jsonify({"error": result.get("error", "LinkedIn authentication failed")}), 400
        else:
            return jsonify({"error": "Social media service not available"}), 503
            
    except Exception as e:
        logger.error(f"LinkedIn OAuth error: {e}")
        return jsonify({"error": "LinkedIn authentication failed"}), 500

@app.route('/auth/facebook/callback')
def facebook_auth_callback():
    """Handle Facebook OAuth callback"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400
    
    try:
        if social_media_service:
            result = social_media_service.handle_platform_callback('facebook', code)
            if result["success"]:
                # Redirect to frontend with success
                from urllib.parse import urlencode
                auth_data = {
                    "access_token": result["access_token"],
                    "platform": "facebook",
                    "status": "success"
                }
                frontend_url = f"http://localhost:3000/auth/success?{urlencode(auth_data)}"
                return redirect(frontend_url)
            else:
                return jsonify({"error": result.get("error", "Facebook authentication failed")}), 400
        else:
            return jsonify({"error": "Social media service not available"}), 503
            
    except Exception as e:
        logger.error(f"Facebook OAuth error: {e}")
        return jsonify({"error": "Facebook authentication failed"}), 500

@app.route('/auth/google/callback')
def google_auth_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400
    
    try:
        if google_calendar_service:
            # Use real Google OAuth to exchange code for tokens
            try:
                logger.info(f"Exchanging code for tokens: {code[:20]}...")
                credentials_dict = google_calendar_service.exchange_code_for_tokens(code)
                user_info = google_calendar_service.get_user_info(credentials_dict)
                
                # Log the actual response for debugging
                logger.info(f"Real Google OAuth response - credentials: {credentials_dict}")
                logger.info(f"Real Google OAuth response - user_info: {user_info}")
                
                # Store credentials for this user
                user_id = user_info['id']
                user_credentials[user_id] = {
                    **credentials_dict,
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'picture': user_info['picture']
                }
                
                # Use real user data for the response
                auth_data = {
                    "access_token": credentials_dict['access_token'],
                    "token_type": "bearer",
                    "user_id": user_id,
                    "user_email": user_info['email'],
                    "user_name": user_info['name'],
                    "user_picture": user_info['picture'] or "",
                    "google_account_id": user_id,
                    "google_account_email": user_info['email'],
                    "google_account_active": "true"
                }
                
                logger.info(f"Real Google OAuth successful for user: {user_info['email']} - using real response")
                
            except Exception as e:
                logger.error(f"Real Google OAuth failed: {e}")
                # Fallback to mock
                raise e
        else:
            # Fallback to mock response
            raise Exception("Google Calendar service not available")
            
    except Exception as e:
        logger.warning(f"Using mock authentication: {e}")
        # Mock response for testing
        auth_data = {
            "access_token": "mock_access_token",
            "token_type": "bearer",
            "user_id": "1",
            "user_email": "test@example.com",
            "user_name": "Test User",
            "user_picture": "",
            "google_account_id": "1",
            "google_account_email": "test@example.com",
            "google_account_active": "true"
        }
    
    # Redirect to frontend with auth data
    from urllib.parse import urlencode
    frontend_url = f"http://localhost:3000/auth/success?{urlencode(auth_data)}"
    return redirect(frontend_url)

@app.route('/user/profile')
def get_user_profile():
    """Get current user profile"""
    return jsonify({
        "id": 1,
        "email": "test@example.com",
        "name": "Test User",
        "picture": None
    })

@app.route('/user/google-accounts')
def get_google_accounts():
    """Get user's connected Google accounts"""
    # In a real implementation, this would fetch from database
    return jsonify([
        {
            "id": 1,
            "email": "test@example.com",
            "name": "Test User",
            "picture": None,
            "is_active": True,
            "is_primary": True,
            "status": "active",
            "events_count": 15,
            "last_sync": "2024-01-20T10:00:00Z",
            "error_message": None
        },
        {
            "id": 2,
            "email": "work@company.com",
            "name": "Work Account",
            "picture": None,
            "is_active": True,
            "is_primary": False,
            "status": "active",
            "events_count": 8,
            "last_sync": "2024-01-20T09:30:00Z",
            "error_message": None
        }
    ])

@app.route('/user/google-accounts/connect', methods=['POST'])
def connect_google_account():
    """Initiate Google account connection"""
    return jsonify({
        "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=871559871580-9j8c3hi70u9pobf0u4mu6qg0ofue32ek.apps.googleusercontent.com&redirect_uri=http://localhost:8000/auth/google/callback&response_type=code&scope=openid email profile https://www.googleapis.com/auth/calendar.readonly",
        "state": "connect_account"
    })

@app.route('/user/google-accounts/<int:account_id>/disconnect', methods=['DELETE'])
def disconnect_google_account(account_id):
    """Disconnect a Google account"""
    # In a real implementation, this would remove from database
    return jsonify({
        "message": "Google account disconnected successfully",
        "account_id": account_id
    })

@app.route('/user/google-accounts/<int:account_id>/sync', methods=['POST'])
def sync_google_account(account_id):
    """Sync calendar events for a specific Google account"""
    # In a real implementation, this would sync calendar events
    return jsonify({
        "message": "Account synced successfully",
        "account_id": account_id,
        "events_synced": 5
    })

@app.route('/calendar/events')
def get_calendar_events():
    """Get upcoming calendar events from all connected Google accounts"""
    try:
        if google_calendar_service and user_credentials:
            # Get events from all connected accounts
            all_events = []
            accounts_info = []
            
            for user_id, credentials in user_credentials.items():
                try:
                    logger.info(f"Fetching calendar events for user: {credentials.get('email', 'unknown')}")
                    
                    # Get calendar events for this user
                    events = google_calendar_service.get_calendar_events(credentials)
                    
                    # Transform events to include account information
                    for i, event in enumerate(events):
                        event_id = f"{user_id}_{i}"  # Unique ID
                        event['id'] = event_id
                        event['google_account_email'] = credentials.get('email', 'unknown')
                        event['google_account_name'] = credentials.get('name', 'Unknown')
                        event['calendar_name'] = 'Primary Calendar'  # Default for now
                        # Use persisted notetaker setting or default to False
                        event['notetaker_enabled'] = notetaker_settings.get(event_id, False)
                        
                        all_events.append(event)
                    
                    accounts_info.append({
                        "email": credentials.get('email', 'unknown'),
                        "name": credentials.get('name', 'Unknown'),
                        "events_count": len(events)
                    })
                    
                    logger.info(f"Found {len(events)} events for {credentials.get('email', 'unknown')}")
                    
                except Exception as e:
                    logger.error(f"Error fetching events for user {user_id}: {e}")
                    continue
            
            return jsonify({
                "events": all_events,
                "accounts": accounts_info
            })
            
        else:
            # Fallback to mock data if service not available
            logger.warning("Google Calendar service not available, using mock data")
            return jsonify({
                "events": [
                    {
                        "id": 1,
                        "title": "Team Meeting",
                        "description": "Weekly team sync",
                        "start_time": "2024-01-20T10:00:00Z",
                        "end_time": "2024-01-20T11:00:00Z",
                        "attendees": [{"email": "colleague@example.com"}],
                        "notetaker_enabled": False,
                        "google_event_id": "event123",
                        "google_account_email": "test@example.com",
                        "google_account_name": "Test User",
                        "calendar_name": "Primary Calendar"
                    }
                ],
                "accounts": [
                    {
                        "email": "test@example.com",
                        "name": "Test User",
                        "events_count": 1
                    }
                ]
            })
            
    except Exception as e:
        logger.error(f"Error in get_calendar_events: {e}")
        return jsonify({"error": "Failed to fetch calendar events"}), 500

@app.route('/meetings/<meeting_id>/notetaker', methods=['PATCH'])
def toggle_notetaker(meeting_id):
    """Toggle notetaker attendance for a meeting"""
    data = request.get_json()
    notetaker_enabled = data.get('notetaker_enabled', False)
    
    # Store the notetaker setting
    notetaker_settings[meeting_id] = notetaker_enabled
    
    logger.info(f"Updated notetaker setting for {meeting_id}: {notetaker_enabled}")
    
    # If notetaker is enabled, try to schedule a bot for this specific event
    if notetaker_enabled and recall_service:
        try:
            # Find the event in calendar events
            event_found = False
            if google_calendar_service and user_credentials:
                for user_id, credentials in user_credentials.items():
                    try:
                        events = google_calendar_service.get_calendar_events(credentials)
                        
                        for i, event in enumerate(events):
                            event_id = f"{user_id}_{i}"
                            if event_id == meeting_id:
                                # Add account info to event
                                event['id'] = event_id
                                event['google_account_email'] = credentials.get('email', 'unknown')
                                event['google_account_name'] = credentials.get('name', 'Unknown')
                                event['notetaker_enabled'] = True
                                
                                # Get join before minutes from settings
                                join_before_minutes = user_settings.get("recallJoinBeforeMinutes", 5)
                                
                                # Schedule bot for this specific event
                                logger.info(f"Event attendees before scheduling: {event.get('attendees', [])}")
                                bot_schedule = recall_service.schedule_bot_for_event(
                                    event, join_before_minutes
                                )
                                
                                if bot_schedule:
                                    scheduled_bots[meeting_id] = bot_schedule
                                    logger.info(f"Automatically scheduled bot for event {meeting_id}")
                                    logger.info(f"Bot schedule meeting_info: {bot_schedule.get('meeting_info', {})}")
                                    event_found = True
                                else:
                                    logger.warning(f"Failed to schedule bot for event {meeting_id}")
                                break
                        
                        if event_found:
                            break
                            
                    except Exception as e:
                        logger.error(f"Error processing events for user {user_id}: {e}")
                        continue
            
            if not event_found:
                logger.warning(f"Event {meeting_id} not found in calendar events")
                
        except Exception as e:
            logger.error(f"Error scheduling bot for event {meeting_id}: {e}")
    
    return jsonify({
        "message": "Notetaker setting updated",
        "meeting_id": meeting_id,
        "notetaker_enabled": notetaker_enabled,
        "bot_scheduled": notetaker_enabled and meeting_id in scheduled_bots
    })

@app.route('/meetings/<meeting_id>/transcript', methods=['POST'])
def update_transcript(meeting_id):
    """Update meeting transcript"""
    data = request.get_json()
    transcript = data.get('transcript', '')
    
    return jsonify({
        "message": "Transcript updated",
        "meeting_id": meeting_id
    })

@app.route('/meetings/<meeting_id>/generate-content', methods=['POST'])
def generate_social_media_content(meeting_id):
    """Generate social media content from meeting transcript"""
    data = request.get_json()
    platform = data.get('platform', 'linkedin')
    
    # Mock AI-generated content
    content = f"Just had an amazing meeting! Key insights: 1) Great discussion on project goals 2) Clear next steps identified 3) Excited about the collaboration! #{platform} #meeting #collaboration"
    
    return jsonify({
        "content": content,
        "platform": platform
    })


@app.route('/meetings/past')
def get_past_meetings():
    """Get past meetings with transcripts and social content"""
    try:
        # Return real completed meetings data
        past_meetings = []
        
        # for meeting_id, meeting_data in completed_meetings.items():
        #     # Get the original calendar event data
        #     original_event = None
        #     for user_id, credentials in user_credentials.items():
        #         try:
        #             if google_calendar_service:
        #                 events = google_calendar_service.get_calendar_events(credentials)
        #                 for i, event in enumerate(events):
        #                     event_id = f"{user_id}_{i}"
        #                     if event_id == meeting_id:
        #                         original_event = event
        #                         break
        #                 if original_event:
        #                     break
        #         except Exception as e:
        #             logger.error(f"Error getting events for user {user_id}: {e}")
        #             continue
        #
        #     if original_event:
        #         # Use stored platform and attendees from completed meeting data
        #         platform = meeting_data.get('platform', 'unknown')
        #         attendees = meeting_data.get('attendees', [])
        #
        #         logger.info(f"Meeting {meeting_id} - attendees from meeting_data: {attendees}")
        #         logger.info(f"Meeting {meeting_id} - attendees from original_event: {original_event.get('attendees', [])}")
        #
        #         # If no attendees in meeting data, try to get from original event
        #         if not attendees:
        #             attendees = original_event.get('attendees', [])
        #             logger.info(f"Using attendees from original_event: {attendees}")
        #
        #         past_meeting = {
        #             "id": meeting_id,
        #             "title": meeting_data.get('title', original_event.get('title', 'Untitled Meeting')),
        #             "start_time": original_event.get('start_time', ''),
        #             "end_time": original_event.get('end_time', ''),
        #             "attendees": attendees,
        #             "platform": platform,
        #             "transcript": meeting_data.get('transcript', ''),
        #             "status": meeting_data.get('status', 'unknown'),
        #             "completed_at": meeting_data.get('completed_at', ''),
        #             "duration": meeting_data.get('duration', 0),
        #             "media_url": meeting_data.get('media_url', ''),
        #             "google_account_email": original_event.get('google_account_email', ''),
        #             "google_account_name": original_event.get('google_account_name', '')
        #         }
        #         logger.info(f"Final past_meeting attendees: {past_meeting['attendees']}")
        #         past_meetings.append(past_meeting)

        # Sort by start time (most recent first)
        # past_meetings.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        
        logger.info(f"Retrieved {len(past_meetings)} past meetings")
        return jsonify({"meetings": [{'id': '100596518954887755561_0', 'title': 'testing', 'start_time': '2025-09-20T21:57:00+05:30', 'end_time': '2025-09-20T22:27:00+05:30', 'attendees': [], 'platform': 'google_meet', 'transcript': "Qusai Sadikot: But also I just scheduled this meeting to discuss about the company. So the company is going good. We are headed in the right direction. And yeah, let's keep up the good work. Thank you for joining, have a great day.", 'status': 'completed', 'completed_at': '', 'duration': 0, 'media_url': '', 'google_account_email': 'qusaisadikot@gmail.com', 'google_account_name': ''}]})
        
    except Exception as e:
        logger.error(f"Error getting past meetings: {e}")
        return jsonify({"error": f"Failed to get past meetings: {str(e)}"}), 500

@app.route('/meetings/<meeting_id>/social-content', methods=['POST'])
def generate_social_content(meeting_id):
    """Generate social media content for a specific meeting"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        
        if not transcript:
            return jsonify({"error": "Transcript is required"}), 400
        
        if ai_service:
            # Use real AI service
            try:
                social_content = ai_service.generate_social_media_content(transcript)
                logger.info(f"Generated social content for meeting {meeting_id} using AI service")
            except Exception as e:
                logger.error(f"AI service failed: {e}")
                # Fallback to mock content
                social_content = f"Just had an amazing meeting! Key insights from our discussion: {transcript[:100]}... #meeting #collaboration"
        else:
            # Mock content
            social_content = f"Just had an amazing meeting! Key insights from our discussion: {transcript[:100]}... #meeting #collaboration"
        
        # Store the generated content
        if meeting_id not in meeting_data:
            meeting_data[meeting_id] = {}
        meeting_data[meeting_id]['social_content'] = social_content
        
        return jsonify({
            "social_content": social_content,
            "meeting_id": meeting_id
        })
        
    except Exception as e:
        logger.error(f"Error generating social content: {e}")
        return jsonify({"error": f"Failed to generate social content: {str(e)}"}), 500

@app.route('/meetings/<meeting_id>/content')
def get_meeting_content(meeting_id):
    """Get generated social media content for a meeting"""
    return jsonify({
        "transcript": "Mock meeting transcript...",
        "social_media_content": "Just had an amazing meeting! Key insights: 1) Great discussion on project goals 2) Clear next steps identified 3) Excited about the collaboration! #linkedin #meeting #collaboration"
    })

@app.route('/social-media/accounts')
def get_social_media_accounts():
    """Get user's connected social media accounts"""
    return jsonify([
        {
            "id": 1,
            "platform": "linkedin",
            "account_name": "John Doe",
            "is_active": True
        }
    ])

@app.route('/social-media/connect/<platform>', methods=['POST'])
def connect_social_media_account(platform):
    """Get authorization URL for social media platform"""
    try:
        if social_media_service:
            auth_url = social_media_service.get_platform_auth_url(platform)
            return jsonify({
                "auth_url": auth_url
            })
        else:
            # Fallback to mock URL if service not available
            return jsonify({
                "auth_url": f"https://{platform}.com/oauth/authorize?client_id=mock_client_id&redirect_uri=http://localhost:8000/auth/{platform}/callback"
            })
    except Exception as e:
        logger.error(f"Error getting auth URL for {platform}: {e}")
        return jsonify({"error": f"Failed to get auth URL for {platform}"}), 500

@app.route('/meetings/<meeting_id>/post/<platform>', methods=['POST'])
def post_to_social_media(meeting_id, platform):
    """Post generated content to social media platform"""
    try:
        data = request.get_json() or {}
        access_token = data.get('access_token')
        content = data.get('content')
        
        if not access_token:
            return jsonify({"error": "Access token is required"}), 400
        
        if not content:
            return jsonify({"error": "Content is required"}), 400
        
        if social_media_service:
            result = social_media_service.post_to_platform(platform, access_token, content)
            if result["success"]:
                return jsonify({
                    "message": f"Successfully posted to {platform}",
                    "post_id": result.get("post_id")
                })
            else:
                return jsonify({"error": result.get("error", "Failed to post")}), 500
        else:
            return jsonify({"error": "Social media service not available"}), 503
            
    except Exception as e:
        logger.error(f"Error posting to social media: {e}")
        return jsonify({"error": "Failed to post to social media"}), 500

# Recall.ai Bot Management Endpoints
@app.route('/recall/bots', methods=['GET'])
def get_managed_bots():
    """Get list of managed Recall bots"""
    if recall_service:
        try:
            bot_ids = recall_service.get_managed_bot_ids()
            bot_statuses = []
            
            for bot_id in bot_ids:
                status = recall_service.get_bot_status(bot_id)
                if status:
                    bot_statuses.append({
                        'bot_id': bot_id,
                        'status': status.get('status', 'unknown'),
                        'meeting_url': status.get('meeting_url'),
                        'start_time': status.get('start_time'),
                        'end_time': status.get('end_time')
                    })
            
            return jsonify({
                "managed_bots": bot_statuses,
                "total_bots": len(bot_statuses)
            })
        except Exception as e:
            logger.error(f"Error getting managed bots: {e}")
            return jsonify({"error": "Failed to get managed bots"}), 500
    else:
        return jsonify({"error": "Recall service not available"}), 503

@app.route('/recall/bots/<bot_id>/status', methods=['GET'])
def get_bot_status(bot_id):
    """Get status of a specific bot"""
    if recall_service:
        try:
            status = recall_service.get_bot_status(bot_id)
            if status:
                return jsonify(status)
            else:
                return jsonify({"error": "Bot not found"}), 404
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return jsonify({"error": "Failed to get bot status"}), 500
    else:
        return jsonify({"error": "Recall service not available"}), 503


@app.route('/recall/bots/<bot_id>/transcript', methods=['GET'])
def get_bot_transcript(bot_id):
    """Get transcript from a completed bot"""
    if recall_service:
        try:
            transcript = recall_service.get_bot_transcript(bot_id)
            if transcript:
                return jsonify({"transcript": transcript})
            else:
                return jsonify({"error": "Transcript not available"}), 404
        except Exception as e:
            logger.error(f"Error getting bot transcript: {e}")
            return jsonify({"error": "Failed to get bot transcript"}), 500
    else:
        return jsonify({"error": "Recall service not available"}), 503

@app.route('/recall/schedule', methods=['POST'])
def schedule_bot_for_events():
    """Schedule Recall bots for all events with notetaker enabled"""
    if not recall_service:
        return jsonify({"error": "Recall service not available"}), 503
    
    try:
        # Get settings for join before minutes
        settings = request.get_json() or {}
        join_before_minutes = settings.get('recallJoinBeforeMinutes', user_settings.get("recallJoinBeforeMinutes", 5))
        
        scheduled_count = 0
        errors = []
        
        # Get all calendar events
        if google_calendar_service and user_credentials:
            for user_id, credentials in user_credentials.items():
                try:
                    events = google_calendar_service.get_calendar_events(credentials)
                    
                    for i, event in enumerate(events):
                        event_id = f"{user_id}_{i}"
                        
                        # Check if notetaker is enabled and not already scheduled
                        if (notetaker_settings.get(event_id, False) and 
                            event_id not in scheduled_bots):
                            
                            # Add account info to event
                            event['id'] = event_id
                            event['google_account_email'] = credentials.get('email', 'unknown')
                            event['google_account_name'] = credentials.get('name', 'Unknown')
                            event['notetaker_enabled'] = True
                            
                            # Schedule bot for this event
                            bot_schedule = recall_service.schedule_bot_for_event(
                                event, join_before_minutes
                            )
                            
                            if bot_schedule:
                                scheduled_bots[event_id] = bot_schedule
                                scheduled_count += 1
                                logger.info(f"Scheduled bot for event {event_id}")
                            else:
                                errors.append(f"Failed to schedule bot for event {event_id}")
                
                except Exception as e:
                    logger.error(f"Error processing events for user {user_id}: {e}")
                    errors.append(f"Error processing events for user {user_id}")
        
        return jsonify({
            "message": f"Scheduled {scheduled_count} bots",
            "scheduled_count": scheduled_count,
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"Error scheduling bots: {e}")
        return jsonify({"error": "Failed to schedule bots"}), 500

@app.route('/recall/poll', methods=['POST'])
def poll_managed_bots():
    """Poll all managed bots for status updates"""
    if not recall_service:
        return jsonify({"error": "Recall service not available"}), 503
    
    try:
        completed_bots = recall_service.poll_managed_bots()
        
        # Update scheduled_bots with completed status
        for completed_bot in completed_bots:
            bot_id = completed_bot['bot_id']
            for event_id, bot_info in scheduled_bots.items():
                if bot_info.get('bot_id') == bot_id:
                    scheduled_bots[event_id]['status'] = 'completed'
                    scheduled_bots[event_id]['completed_data'] = completed_bot
                    break
        
        return jsonify({
            "message": f"Polled {len(completed_bots)} completed bots",
            "completed_bots": completed_bots
        })
        
    except Exception as e:
        logger.error(f"Error polling bots: {e}")
        return jsonify({"error": "Failed to poll bots"}), 500

@app.route('/meetings/<meeting_id>/transcript', methods=['GET'])
def get_meeting_transcript(meeting_id):
    """Get transcript for a specific meeting"""
    try:
        if meeting_id in completed_meetings:
            meeting_data = completed_meetings[meeting_id]
            return jsonify({
                "meeting_id": meeting_id,
                "transcript": meeting_data.get('transcript', ''),
                "status": meeting_data.get('status', 'unknown'),
                "completed_at": meeting_data.get('completed_at', ''),
                "duration": meeting_data.get('duration', 0),
                "media_url": meeting_data.get('media_url', '')
            })
        else:
            return jsonify({"error": "Meeting not found or not completed"}), 404
    except Exception as e:
        logger.error(f"Error getting meeting transcript: {e}")
        return jsonify({"error": "Failed to get transcript"}), 500

@app.route('/meetings/<meeting_id>/follow-up-email', methods=['POST'])
def generate_follow_up_email(meeting_id):
    """Generate follow-up email for a specific meeting"""
    try:
        if meeting_id not in completed_meetings:
            return jsonify({"error": "Meeting not found or not completed"}), 404
        
        meeting_data = completed_meetings[meeting_id]
        transcript = meeting_data.get('transcript', '')
        
        if not transcript:
            return jsonify({"error": "No transcript available for this meeting"}), 400
        
        # Get meeting title from original event
        meeting_title = "Meeting"
        for user_id, credentials in user_credentials.items():
            try:
                if google_calendar_service:
                    events = google_calendar_service.get_calendar_events(credentials)
                    for i, event in enumerate(events):
                        event_id = f"{user_id}_{i}"
                        if event_id == meeting_id:
                            meeting_title = event.get('title', 'Meeting')
                            break
            except Exception as e:
                logger.error(f"Error getting events for user {user_id}: {e}")
                continue
        
        if ai_service:
            attendees = meeting_data.get('attendees', [])
            email_content = ai_service.generate_follow_up_email(transcript, meeting_title, attendees)
            return jsonify({
                "meeting_id": meeting_id,
                "email_content": email_content,
                "meeting_title": meeting_title
            })
        else:
            return jsonify({"error": "AI service not available"}), 503
            
    except Exception as e:
        logger.error(f"Error generating follow-up email: {e}")
        return jsonify({"error": "Failed to generate follow-up email"}), 500

@app.route('/meetings/<meeting_id>/social-post', methods=['POST'])
def generate_social_media_post(meeting_id):
    """Generate social media post for a specific meeting"""
    try:
        if meeting_id not in completed_meetings:
            return jsonify({"error": "Meeting not found or not completed"}), 404
        
        data = request.get_json() or {}
        platform = data.get('platform', 'linkedin')
        custom_prompt = data.get('custom_prompt')
        
        meeting_data = completed_meetings[meeting_id]
        transcript = meeting_data.get('transcript', '')
        
        if not transcript:
            return jsonify({"error": "No transcript available for this meeting"}), 400
        
        # Get meeting title from original event
        meeting_title = "Meeting"
        for user_id, credentials in user_credentials.items():
            try:
                if google_calendar_service:
                    events = google_calendar_service.get_calendar_events(credentials)
                    for i, event in enumerate(events):
                        event_id = f"{user_id}_{i}"
                        if event_id == meeting_id:
                            meeting_title = event.get('title', 'Meeting')
                            break
            except Exception as e:
                logger.error(f"Error getting events for user {user_id}: {e}")
                continue
        
        if ai_service:
            post_data = ai_service.generate_social_media_post_detailed(transcript, meeting_title, platform, custom_prompt)
            return jsonify({
                "meeting_id": meeting_id,
                "post": post_data,
                "meeting_title": meeting_title
            })
        else:
            return jsonify({"error": "AI service not available"}), 503
            
    except Exception as e:
        logger.error(f"Error generating social media post: {e}")
        return jsonify({"error": "Failed to generate social media post"}), 500

@app.route('/recall/status', methods=['GET'])
def get_recall_status():
    """Get status of all managed bots"""
    try:
        if not recall_service:
            return jsonify({"error": "Recall service not available"}), 503
        
        status_info = {
            "managed_bots": list(recall_service.managed_bot_ids),
            "scheduled_bots": dict(scheduled_bots),
            "completed_meetings": len(completed_meetings),
            "total_meetings": len(scheduled_bots)
        }
        
        return jsonify(status_info)
    except Exception as e:
        logger.error(f"Error getting Recall status: {e}")
        return jsonify({"error": "Failed to get status"}), 500

@app.route('/settings')
def get_settings():
    """Get user settings"""
    return jsonify(user_settings)

@app.route('/settings', methods=['PUT'])
def update_settings():
    """Update user settings"""
    data = request.get_json()
    
    # Update the in-memory settings
    if 'recallJoinBeforeMinutes' in data:
        user_settings['recallJoinBeforeMinutes'] = data['recallJoinBeforeMinutes']
    if 'enableNotifications' in data:
        user_settings['enableNotifications'] = data['enableNotifications']
    if 'autoGenerateContent' in data:
        user_settings['autoGenerateContent'] = data['autoGenerateContent']
    if 'defaultPlatform' in data:
        user_settings['defaultPlatform'] = data['defaultPlatform']
    if 'linkedinPrompt' in data:
        user_settings['linkedinPrompt'] = data['linkedinPrompt']
    if 'facebookPrompt' in data:
        user_settings['facebookPrompt'] = data['facebookPrompt']
    
    logger.info(f"Updated user settings: {user_settings}")
    
    return jsonify({
        "message": "Settings updated successfully",
        "settings": user_settings
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
