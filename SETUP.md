# Post-Meeting Social Media Generator - Setup Guide

## 🚀 **Current Status**
The app is now working with **graceful fallbacks**! It will use real services when API keys are configured, and fall back to mock data when they're not.

## 🔧 **Setup Instructions**

### 1. **Google Calendar Integration**
To enable real Google Calendar integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized redirect URIs: `http://localhost:8000/auth/google/callback`
6. Create a `.env` file in the backend directory with:
   ```
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   ```

### 2. **Recall.ai Integration**
To enable meeting notetaking:

1. Sign up at [Recall.ai](https://recall.ai/)
2. Get your API key from the dashboard
3. Add to `.env` file:
   ```
   RECALL_API_KEY=your_recall_api_key_here
   RECALL_JOIN_BEFORE_MINUTES=5
   ```

### 3. **OpenAI Integration**
To enable AI content generation:

1. Get API key from [OpenAI](https://platform.openai.com/)
2. Add to `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## 🎯 **How It Works Now**

### **Without API Keys (Current State)**
- ✅ Google OAuth works with mock data
- ✅ Dashboard shows mock calendar events
- ✅ Past Meetings page works with mock data
- ✅ AI content generation works with mock responses
- ✅ All features work for testing

### **With API Keys (Full Integration)**
- ✅ Real Google Calendar integration
- ✅ Real Recall.ai bot scheduling
- ✅ Real AI content generation
- ✅ Real meeting transcript processing

## 🧪 **Testing the Integration**

1. **Test without API keys** (current state):
   - Everything works with mock data
   - Perfect for development and testing

2. **Test with API keys**:
   - Add your API keys to `.env` file
   - Restart the backend
   - Real services will be used automatically

## 📝 **Next Steps**

1. **Set up Google Calendar API** for real calendar integration
2. **Set up Recall.ai account** for meeting notetaking
3. **Set up OpenAI account** for AI content generation
4. **Test each integration** one by one

The app is designed to work with or without these services, so you can test everything immediately!
