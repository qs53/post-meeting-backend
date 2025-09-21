# Post-Meeting Social Media Generator - Backend

A Flask backend for generating social media content from meeting transcripts.

## Features

- Google OAuth authentication (mock implementation)
- Google Calendar integration (mock data)
- AI-powered social media content generation (mock)
- Social media posting (LinkedIn, Twitter) (mock)
- Meeting transcript management
- Notetaker toggle functionality

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/google/callback

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Social Media API Keys
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret

# Test User Email
TEST_USER_EMAIL=your_email@example.com
```

### 3. Run the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /` - API status
- `GET /health` - Health check

### Authentication (Mock)
- `GET /auth/google` - Get Google OAuth URL
- `GET /auth/google/callback` - Handle Google OAuth callback

### User (Mock)
- `GET /user/profile` - Get user profile
- `GET /user/google-accounts` - Get connected Google accounts

### Calendar (Mock Data)
- `GET /calendar/events` - Get upcoming calendar events

### Meetings (Mock)
- `PATCH /meetings/{id}/notetaker` - Toggle notetaker for meeting
- `POST /meetings/{id}/transcript` - Update meeting transcript
- `POST /meetings/{id}/generate-content` - Generate social media content
- `GET /meetings/{id}/content` - Get meeting content

### Social Media (Mock)
- `GET /social-media/accounts` - Get connected social media accounts
- `POST /social-media/connect/{platform}` - Get auth URL for platform
- `POST /meetings/{id}/post/{platform}` - Post content to social media

## Current Status

This is a **mock implementation** that provides all the necessary API endpoints with sample data. This allows you to:

1. Test the frontend interface
2. See how the application flow works
3. Develop the UI without needing real API integrations

## Next Steps

To make this production-ready, you'll need to:

1. **Replace mock Google OAuth** with real Google OAuth implementation
2. **Add real Google Calendar API** integration
3. **Integrate OpenAI API** for actual content generation
4. **Add real social media APIs** (LinkedIn, Twitter)
5. **Add database** for persistent data storage
6. **Add authentication middleware** for protected routes

## Development

The Flask app runs in debug mode by default, so it will auto-reload when you make changes to the code.
