import requests
from typing import Optional, Dict, Any
import os

class SocialMediaService:
    def __init__(self):
        self.linkedin_client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.linkedin_client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.facebook_app_id = os.getenv('FACEBOOK_APP_ID')
        self.facebook_app_secret = os.getenv('FACEBOOK_APP_SECRET')
    
    def post_to_linkedin(self, access_token: str, content: str) -> Dict[str, Any]:
        """Post content to LinkedIn"""
        try:
            # LinkedIn API v2 endpoint for posting
            url = "https://api.linkedin.com/v2/ugcPosts"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # For LinkedIn API v2, we need to get the user's URN differently
            # First, let's try to get the user info from the token
            profile_url = "https://api.linkedin.com/v2/userinfo"
            profile_response = requests.get(profile_url, headers=headers)
            
            if profile_response.status_code != 200:
                # If that fails, try the legacy endpoint
                profile_url = "https://api.linkedin.com/v2/people/~"
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code != 200:
                    return {"success": False, "error": f"Failed to get LinkedIn profile: {profile_response.text}"}
                
                profile_data = profile_response.json()
                author_id = f"urn:li:person:{profile_data['id']}"
            else:
                profile_data = profile_response.json()
                # For OpenID Connect, the user ID is in the 'sub' field
                user_id = profile_data.get('sub', '').split('/')[-1]  # Extract ID from the sub field
                author_id = f"urn:li:person:{user_id}"
            
            # Create the post data
            post_data = {
                "author": author_id,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = requests.post(url, headers=headers, json=post_data)
            
            # Debug logging
            print(f"LinkedIn post response status: {response.status_code}")
            print(f"LinkedIn post response: {response.text}")
            
            if response.status_code == 201:
                return {"success": True, "post_id": response.json().get("id")}
            else:
                return {"success": False, "error": f"LinkedIn API error: {response.text}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def post_to_facebook(self, access_token: str, content: str) -> Dict[str, Any]:
        """Post content to Facebook"""
        try:
            # For now, we'll simulate posting since Facebook requires app review for posting permissions
            # In a real implementation, you would need to:
            # 1. Submit your app for Facebook review
            # 2. Get approved for publishing permissions
            # 3. Use the proper Facebook Graph API endpoints
            
            print(f"Facebook post simulation - Content: {content}")
            print(f"Facebook post simulation - Access Token: {access_token[:20]}...")
            
            # Simulate successful posting
            return {
                "success": True, 
                "post_id": f"simulated_facebook_post_{hash(content) % 10000}",
                "message": "Post simulated successfully (Facebook posting requires app review)"
            }
            
            # Uncomment this when you have proper Facebook posting permissions:
            # url = "https://graph.facebook.com/v18.0/me/feed"
            # headers = {
            #     "Authorization": f"Bearer {access_token}",
            #     "Content-Type": "application/json"
            # }
            # post_data = {"message": content}
            # response = requests.post(url, headers=headers, json=post_data)
            # 
            # if response.status_code == 200:
            #     post_data = response.json()
            #     return {"success": True, "post_id": post_data.get("id")}
            # else:
            #     return {"success": False, "error": f"Facebook API error: {response.text}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def post_to_platform(self, platform: str, access_token: str, content: str) -> Dict[str, Any]:
        """Post content to the specified platform"""
        if platform == "linkedin":
            return self.post_to_linkedin(access_token, content)
        elif platform == "facebook":
            return self.post_to_facebook(access_token, content)
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}
    
    def get_platform_auth_url(self, platform: str) -> str:
        """Get authorization URL for social media platform"""
        if platform == "linkedin":
            if not self.linkedin_client_id:
                return "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=mock_client_id&redirect_uri=http://localhost:8000/auth/linkedin/callback&state=state&scope=w_member_social,openid,profile,email"
            return f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={self.linkedin_client_id}&redirect_uri=http://localhost:8000/auth/linkedin/callback&state=state&scope=w_member_social,openid,profile,email"
        elif platform == "facebook":
            if not self.facebook_app_id:
                return "https://www.facebook.com/v18.0/dialog/oauth?client_id=mock_app_id&redirect_uri=http://localhost:8000/auth/facebook/callback&scope=email,public_profile,pages_manage_posts,pages_read_engagement&response_type=code&state=state"
            return f"https://www.facebook.com/v18.0/dialog/oauth?client_id={self.facebook_app_id}&redirect_uri=http://localhost:8000/auth/facebook/callback&scope=public_profile,pages_show_list&response_type=code&state=state"
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    def handle_platform_callback(self, platform: str, code: str) -> Dict[str, Any]:
        """Handle OAuth callback for social media platform"""
        if platform == "linkedin":
            return self._handle_linkedin_callback(code)
        elif platform == "facebook":
            return self._handle_facebook_callback(code)
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}
    
    def _handle_linkedin_callback(self, code: str) -> Dict[str, Any]:
        """Handle LinkedIn OAuth callback"""
        try:
            # Exchange code for access token
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.linkedin_client_id or "mock_client_id",
                "client_secret": self.linkedin_client_secret or "mock_client_secret",
                "redirect_uri": "http://localhost:8000/auth/linkedin/callback"
            }
            
            response = requests.post(token_url, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    "success": True,
                    "access_token": token_data["access_token"],
                    "expires_in": token_data.get("expires_in")
                }
            else:
                return {"success": False, "error": f"LinkedIn token exchange failed: {response.text}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _handle_facebook_callback(self, code: str) -> Dict[str, Any]:
        """Handle Facebook OAuth callback"""
        try:
            # Exchange code for access token
            token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
            data = {
                "client_id": self.facebook_app_id or "mock_app_id",
                "client_secret": self.facebook_app_secret or "mock_app_secret",
                "redirect_uri": "http://localhost:8000/auth/facebook/callback",
                "code": code
            }
            
            response = requests.get(token_url, params=data)
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    "success": True,
                    "access_token": token_data["access_token"],
                    "expires_in": token_data.get("expires_in")
                }
            else:
                return {"success": False, "error": f"Facebook token exchange failed: {response.text}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
