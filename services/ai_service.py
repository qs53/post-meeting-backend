import openai
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        logger.info("Initializing AI Service")
        self.api_key = os.getenv('OPENAI_API_KEY')
        logger.info(f"OpenAI API key found: {bool(self.api_key)}")
        
        if self.api_key:
            try:
                openai.api_key = self.api_key
                logger.info("OpenAI API key set successfully")
                # Test the API key with a simple call
                logger.info("Testing OpenAI API connection...")
                # We'll test the connection in the first actual API call
                logger.info("AI Service initialized successfully")
            except Exception as e:
                logger.error(f"Error setting OpenAI API key: {e}")
                raise e
        else:
            logger.warning("OpenAI API key not found in environment variables")
            logger.warning("AI Service will not be able to make API calls")
    
    def is_available(self) -> bool:
        """Check if AI service is properly configured and available"""
        return self.api_key is not None and self.api_key.strip() != ""
    
    def generate_social_media_content(self, meeting_transcript: str, meeting_title: str, platform: str = "linkedin") -> str:
        """Generate social media content from meeting transcript"""
        
        if platform == "linkedin":
            prompt = f"""
            Based on the following meeting transcript, create a professional LinkedIn post that:
            1. Highlights key insights or outcomes from the meeting
            2. Is engaging and valuable to the professional network
            3. Is between 100-300 characters
            4. Uses appropriate hashtags
            5. Maintains a professional tone
            
            Meeting Title: {meeting_title}
            Transcript: {meeting_transcript}
            
            Generate a LinkedIn post:
            """
        else:
            prompt = f"""
            Based on the following meeting transcript, create a social media post that:
            1. Highlights key insights or outcomes
            2. Is engaging and professional
            3. Is appropriate for {platform}
            4. Uses relevant hashtags
            
            Meeting Title: {meeting_title}
            Transcript: {meeting_transcript}
            
            Generate a {platform} post:
            """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional social media content creator who specializes in creating engaging posts from meeting transcripts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error generating content: {str(e)}"
    
    def generate_meeting_summary(self, meeting_transcript: str) -> str:
        """Generate a summary of the meeting transcript"""
        prompt = f"""
        Please provide a concise summary of the following meeting transcript:
        
        {meeting_transcript}
        
        The summary should:
        1. Highlight the main topics discussed
        2. Note any key decisions or action items
        3. Be 2-3 paragraphs long
        4. Be professional and clear
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional meeting assistant who creates clear, concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def extract_key_insights(self, meeting_transcript: str) -> list:
        """Extract key insights from meeting transcript"""
        prompt = f"""
        Extract 3-5 key insights or takeaways from this meeting transcript:
        
        {meeting_transcript}
        
        Return them as a bulleted list, each insight being 1-2 sentences.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional meeting analyst who extracts key insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            # Split by bullet points and clean up
            insights = [line.strip() for line in content.split('\n') if line.strip() and (line.strip().startswith('•') or line.strip().startswith('-'))]
            return insights
        
        except Exception as e:
            return [f"Error extracting insights: {str(e)}"]
    
    def generate_follow_up_email(self, meeting_transcript: str, meeting_title: str, attendees: list = None) -> str:
        """Generate a follow-up email from meeting transcript"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting follow-up email generation in AI service")
        logger.info(f"Meeting title: {meeting_title}")
        logger.info(f"Transcript length: {len(meeting_transcript)} characters")
        logger.info(f"Number of attendees: {len(attendees) if attendees else 0}")
        logger.info(f"Attendees: {attendees}")
        
        attendees_text = ""
        if attendees:
            attendees_text = f"Attendees: {', '.join(attendees)}"
            logger.info(f"Formatted attendees text: {attendees_text}")
        else:
            logger.info("No attendees provided")
        
        prompt = f"""
        Based on the following meeting transcript, create a professional follow-up email that:
        1. Summarizes what was discussed in the meeting
        2. Highlights key decisions and action items
        3. Thanks participants for their time
        4. Suggests next steps or follow-up actions
        5. Is professional and concise (2-3 paragraphs)
        
        Meeting Title: {meeting_title}
        {attendees_text}
        Transcript: {meeting_transcript}
        
        Generate a follow-up email:
        """
        
        logger.info(f"Generated prompt length: {len(prompt)} characters")
        logger.info(f"Prompt preview: {prompt[:200]}...")
        
        try:
            logger.info("Calling OpenAI API for follow-up email generation")
            logger.info(f"Model: gpt-3.5-turbo, max_tokens: 500, temperature: 0.3")
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional assistant who creates clear, concise follow-up emails from meeting transcripts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            logger.info("OpenAI API call successful")
            logger.info(f"Response choices count: {len(response.choices)}")
            
            email_content = response.choices[0].message.content.strip()
            logger.info(f"Generated email content length: {len(email_content)} characters")
            logger.info(f"Email content preview: {email_content[:200]}...")
            
            return email_content
        
        except Exception as e:
            logger.error(f"Error in OpenAI API call for follow-up email: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error generating follow-up email: {str(e)}"
    
    def generate_social_media_post_detailed(self, meeting_transcript: str, meeting_title: str, platform: str = "linkedin", custom_prompt: str = None) -> dict:
        """Generate detailed social media post with hashtags and disclaimer"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Starting social media post generation in AI service")
        logger.info(f"Platform: {platform}")
        logger.info(f"Meeting title: {meeting_title}")
        logger.info(f"Transcript length: {len(meeting_transcript)} characters")
        logger.info(f"Custom prompt provided: {bool(custom_prompt)}")
        if custom_prompt:
            logger.info(f"Custom prompt length: {len(custom_prompt)} characters")
            logger.info(f"Custom prompt preview: {custom_prompt[:100]}...")
        
        if platform == "linkedin":
            if custom_prompt:
                prompt = f"""
                {custom_prompt}
                
                Meeting Title: {meeting_title}
                Transcript: {meeting_transcript}
                """
            else:
                # Default prompt if none provided
                prompt = f"""
                Based on the following meeting transcript, create a LinkedIn post that:
                1. Draft a LinkedIn post (120-180 words) that summarizes the meeting value in first person.
                2. Use a warm, conversational tone consistent with an experienced financial advisor.
                3. End with up to three hashtags.
                Return only the post text.
                
                Meeting Title: {meeting_title}
                Transcript: {meeting_transcript}
                """
        elif platform == "facebook":
            if custom_prompt:
                prompt = f"""
                {custom_prompt}
                
                Meeting Title: {meeting_title}
                Transcript: {meeting_transcript}
                """
            else:
                # Default prompt if none provided
                prompt = f"""
                Based on the following meeting transcript, create a Facebook post that:
                1. Write a Facebook post (100-150 words) that summarizes the meeting value in first person.
                2. Use a friendly, conversational tone that's engaging for Facebook.
                3. Include 2-3 relevant hashtags at the end.
                4. Make it shareable and engaging for Facebook audience.
                Return only the post text.
                
                Meeting Title: {meeting_title}
                Transcript: {meeting_transcript}
                """
        else:
            prompt = f"""
            Based on the following meeting transcript, create a {platform} post that:
            1. Highlights key insights in a personal, engaging way
            2. Is appropriate for {platform} character limits
            3. Includes relevant hashtags
            4. Maintains an appropriate tone for {platform}
            
            Meeting Title: {meeting_title}
            Transcript: {meeting_transcript}
            
            Return the response in this exact format:
            POST: [the main post content]
            HASHTAGS: [hashtags separated by spaces]
            DISCLAIMER: [if applicable]
            """
        
        logger.info(f"Generated prompt length: {len(prompt)} characters")
        logger.info(f"Prompt preview: {prompt[:200]}...")
        
        try:
            logger.info("Calling OpenAI API for social media post generation")
            logger.info(f"Model: gpt-3.5-turbo, max_tokens: 600, temperature: 0.7")
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional social media content creator who specializes in creating engaging posts from meeting transcripts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            logger.info("OpenAI API call successful")
            logger.info(f"Response choices count: {len(response.choices)}")
            
            content = response.choices[0].message.content.strip()
            logger.info(f"Generated content length: {len(content)} characters")
            logger.info(f"Content preview: {content[:200]}...")
            
            # For LinkedIn and Facebook, we expect the content to be returned directly with hashtags at the end
            if platform in ["linkedin", "facebook"]:
                logger.info(f"Parsing content for {platform} platform")
                # Split content and hashtags
                lines = content.split('\n')
                logger.info(f"Content split into {len(lines)} lines")
                
                post_content = ""
                hashtags = ""
                
                for line in lines:
                    if line.strip().startswith('#'):
                        hashtags += line.strip() + " "
                    else:
                        post_content += line + "\n"
                
                post_content = post_content.strip()
                hashtags = hashtags.strip()
                
                logger.info(f"Parsed post content length: {len(post_content)} characters")
                logger.info(f"Parsed hashtags: {hashtags}")
                logger.info(f"Post content preview: {post_content[:100]}...")
                
                result = {
                    "content": post_content,
                    "hashtags": hashtags,
                    "disclaimer": "",
                    "platform": platform
                }
                logger.info(f"Returning {platform} social media post result")
                return result
            else:
                logger.info(f"Parsing content for {platform} platform using structured format")
                # For other platforms, use the old parsing logic
                lines = content.split('\n')
                logger.info(f"Content split into {len(lines)} lines")
                
                post_content = ""
                hashtags = ""
                disclaimer = ""
                
                for line in lines:
                    if line.startswith('POST:'):
                        post_content = line.replace('POST:', '').strip()
                    elif line.startswith('HASHTAGS:'):
                        hashtags = line.replace('HASHTAGS:', '').strip()
                    elif line.startswith('DISCLAIMER:'):
                        disclaimer = line.replace('DISCLAIMER:', '').strip()
                
                logger.info(f"Parsed post content length: {len(post_content)} characters")
                logger.info(f"Parsed hashtags: {hashtags}")
                logger.info(f"Parsed disclaimer: {disclaimer}")
                
                result = {
                    "content": post_content,
                    "hashtags": hashtags,
                    "disclaimer": disclaimer,
                    "platform": platform
                }
                logger.info(f"Returning {platform} social media post result")
                return result
        
        except Exception as e:
            logger.error(f"Error in OpenAI API call for social media post: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            error_result = {
                "content": f"Error generating content: {str(e)}",
                "hashtags": "",
                "disclaimer": "",
                "platform": platform
            }
            logger.error(f"Returning error result for {platform}")
            return error_result
