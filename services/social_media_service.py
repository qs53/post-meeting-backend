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
        """Post content to Facebook using Graph API"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting Facebook post process")
        logger.info(f"Content length: {len(content)} characters")
        logger.info(f"Content preview: {content[:100]}...")
        logger.info(f"Access token present: {bool(access_token)}")
        
        try:
            # First, get user info to verify the token and get user ID
            user_info_url = "https://graph.facebook.com/v22.0/me"
            user_headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            logger.info(f"Fetching user info from: {user_info_url}")
            user_response = requests.get(user_info_url, headers=user_headers)
            
            logger.info(f"User info response status: {user_response.status_code}")
            logger.info(f"User info response: {user_response.text}")
            
            if user_response.status_code != 200:
                error_msg = f"Failed to get user info: {user_response.text}"
                logger.error(error_msg)
                return {
                    "success": False, 
                    "error": error_msg
                }
            
            user_data = user_response.json()
            user_id = user_data.get('id')
            user_name = user_data.get('name', 'User')
            
            logger.info(f"User authenticated - ID: {user_id}, Name: {user_name}")
            
            # Try to post to user's feed
            post_url = f"https://graph.facebook.com/v22.0/{user_id}/feed"
            post_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            post_data = {"message": content}
            
            logger.info(f"Attempting to post to Facebook feed: {post_url}")
            logger.info(f"Post data: {post_data}")
            
            response = requests.post(post_url, headers=post_headers, json=post_data)
            
            logger.info(f"Facebook post response status: {response.status_code}")
            logger.info(f"Facebook post response: {response.text}")
            
            if response.status_code == 200:
                post_result = response.json()
                post_id = post_result.get("id")
                
                logger.info(f"Successfully posted to Facebook - Post ID: {post_id}")
                logger.info(f"Post result: {post_result}")
                
                return {
                    "success": True,
                    "post_id": post_id,
                    "message": f"Successfully posted to Facebook as {user_name}"
                }
            else:
                # If direct posting fails, try alternative approaches
                error_data = response.json() if response.text else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                
                logger.warning(f"Direct posting failed with status {response.status_code}")
                logger.warning(f"Error message: {error_message}")
                logger.warning(f"Full error data: {error_data}")
                
                # Check if it's a permissions error or posting restriction
                if ('permission' in error_message.lower() or 
                    'scope' in error_message.lower() or 
                    'publish_to_groups' in error_message.lower() or
                    'pages_read_engagement' in error_message.lower() or
                    'pages_manage_posts' in error_message.lower() or
                    'requires app being installed' in error_message.lower()):
                    
                    logger.info("Facebook posting permission error detected, generating share URL as fallback")
                    logger.info(f"Specific error: {error_message}")
                    
                    # Generate a share URL as fallback
                    encoded_content = requests.utils.quote(content)
                    facebook_share_url = f"https://www.facebook.com/sharer/sharer.php?u=&quote={encoded_content}"
                    
                    logger.info(f"Generated share URL: {facebook_share_url}")
                    
                    return {
                        "success": True,
                        "post_id": f"share_url_{hash(content) % 10000}",
                        "message": "Facebook share URL generated (direct posting requires additional permissions)",
                        "share_url": facebook_share_url,
                        "user_name": user_name,
                        "note": "Due to Facebook's API restrictions, this opens a share dialog for you to manually post the content. To enable direct posting, the app would need to be submitted for Facebook review with publish_to_groups or pages_manage_posts permissions."
                    }
                else:
                    error_msg = f"Facebook API error: {error_message}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Exception in post_to_facebook: {error_msg}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"success": False, "error": error_msg}
    
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
                return "https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=mock_client_id&redirect_uri=http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/linkedin/callback&state=state&scope=w_member_social,openid,profile,email"
            return f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={self.linkedin_client_id}&redirect_uri=http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/linkedin/callback&state=state&scope=w_member_social,openid,profile,email"
        elif platform == "facebook":
            if not self.facebook_app_id:
                return "https://www.facebook.com/v22.0/dialog/oauth?client_id=mock_app_id&redirect_uri=http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/facebook/callback&scope=public_profile,pages_show_list&response_type=code&state=state"
            return f"https://www.facebook.com/v22.0/dialog/oauth?client_id={self.facebook_app_id}&redirect_uri=http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/facebook/callback&scope=public_profile,pages_show_list&response_type=code&state=state"
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
                "redirect_uri": "http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/linkedin/callback"
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
            token_url = "https://graph.facebook.com/v22.0/oauth/access_token"
            data = {
                "client_id": self.facebook_app_id or "mock_app_id",
                "client_secret": self.facebook_app_secret or "mock_app_secret",
                "redirect_uri": "http://ec2-34-221-10-72.us-west-2.compute.amazonaws.com/auth/facebook/callback",
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
    
