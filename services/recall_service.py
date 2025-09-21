"""
Recall.ai service for meeting notetaking integration
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RecallService:
    def __init__(self):
        self.api_key = os.getenv('RECALL_API_KEY', 'your_recall_api_key_here')
        self.base_url = 'https://us-west-2.recall.ai/api/v1'
        self.headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Track bot IDs to avoid conflicts with shared account
        self.managed_bot_ids = set()
        self.managed_bot_ids.add('27308843-5c22-451d-9299-1e6152c93f41')

    def create_bot(self, meeting_url: str, meeting_start_time: datetime,
                   meeting_duration_minutes: int = 60, join_before_minutes: int = 5) -> Optional[Dict]:
        """
        Create a Recall bot for a meeting
        """
        try:
            logger.info(f"Creating Recall bot for meeting URL: {meeting_url}")
            logger.info(f"Meeting start time: {meeting_start_time}")
            logger.info(f"Meeting duration: {meeting_duration_minutes} minutes")
            logger.info(f"Join before minutes: {join_before_minutes}")

            # Calculate bot join time
            bot_join_time = meeting_start_time - timedelta(minutes=join_before_minutes)
            logger.info(f"Bot will join at: {bot_join_time}")

            # Check if meeting is in the future
            now = datetime.now(bot_join_time.tzinfo) if bot_join_time.tzinfo else datetime.now()
            logger.info(f"Current time: {now}")
            logger.info(f"Bot join time is in future: {bot_join_time > now}")

            if bot_join_time <= now:
                logger.warning(f"Meeting start time {meeting_start_time} is too soon, skipping bot creation")
                return None

            payload = {
                'bot_name': f'PostMeeting Bot - {meeting_start_time.strftime("%Y-%m-%d %H:%M")}',
                'meeting_url': meeting_url,

                "recording_config": {
                    "transcript": {
                        "provider": {
                            "meeting_captions": {}
                        }
                    }
                }
            }

            logger.info(f"Recall.ai API payload: {payload}")
            logger.info(f"API URL: {self.base_url}/bot")
            logger.info(f"Headers: {self.headers}")

            response = requests.post(
                f'{self.base_url}/bot',
                headers=self.headers,
                json=payload,
                timeout=30
            )

            logger.info(f"Recall.ai API response status: {response.status_code}")
            logger.info(f"Recall.ai API response text: {response.text}")

            if response.status_code == 201:
                bot_data = response.json()
                bot_id = bot_data.get('id')
                if bot_id:
                    self.managed_bot_ids.add(bot_id)
                    logger.info(f"Created Recall bot {bot_id} for meeting at {meeting_url} (joins at {bot_join_time})")
                else:
                    logger.warning("Bot created but no ID returned in response")
                return bot_data
            else:
                logger.error(f"Failed to create Recall bot: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error creating Recall bot: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_bot_status(self, bot_id: str) -> Optional[Dict]:
        """
        Get the status of a specific bot
        """
        try:
            response = requests.get(
                f'{self.base_url}/bot/{bot_id}',
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get bot status: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting bot status: {str(e)}")
            return None

    def get_bot_media(self, bot_id: str) -> Optional[Dict]:
        """
        Get media files from a completed bot session
        """
        try:
            response = requests.get(
                f'{self.base_url}/bot/{bot_id}/media',
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get bot media: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting bot media: {str(e)}")
            return None

    def get_bot_transcript(self, bot_id: str) -> Optional[str]:
        """
        Get transcript from a completed bot session
        """
        try:
            response = requests.get(
                f'{self.base_url}/bot/{bot_id}',
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                bot_data = response.json()
                recordings = bot_data.get("recordings", [])
                if not recordings:
                    raise Exception("No recordings found for this bot")

                recording = recordings[0]  # Get first recording
                media_shortcuts = recording.get("media_shortcuts", {})

                if "transcript" not in media_shortcuts:
                    raise Exception("No transcript available for this bot")

                transcript_data = media_shortcuts["transcript"].get("data", {})
                transcript_url = transcript_data.get("download_url")

                if not transcript_url:
                    raise Exception("Transcript download URL not available")

                # Download the transcript JSON
                response = requests.get(transcript_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download transcript: {response.status_code}")

                transcript_json = response.json()
                
                # Parse the transcript based on format
                if isinstance(transcript_json, list):
                    return self._parse_meeting_captions_format(transcript_json)
                elif isinstance(transcript_json, dict) and "segments" in transcript_json:
                    return self._parse_segments_format(transcript_json.get("segments", []))
                else:
                    logger.error(f"Unknown transcript format: {type(transcript_json)}")
                    return None
            else:
                logger.error(f"Failed to get bot transcript: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting bot transcript: {str(e)}")
            return None

    def _parse_meeting_captions_format(self, transcript_data: list) -> str:
        """
        Parse meeting captions transcript format

        Format:
        [
            {
                "participant": {"name": "Speaker Name", ...},
                "words": [{"text": "Hello", "start_timestamp": {...}, ...}]
            }
        ]
        """
        transcript_text = ""

        for segment in transcript_data:
            participant = segment.get("participant", {})
            speaker_name = participant.get("name", "Unknown Speaker")
            words = segment.get("words", [])

            if not words:
                continue

            # Combine all words from this participant segment
            segment_text = " ".join(word.get("text", "") for word in words).strip()

            if segment_text:
                if transcript_text:  # Add spacing between speakers
                    transcript_text += "\n\n"
                transcript_text += f"{speaker_name}: {segment_text}"

        return transcript_text.strip()

    def _parse_segments_format(self, segments: list) -> str:
        """
        Parse AI transcript format with segments

        Format:
        {"segments": [{"speaker": "Speaker 1", "text": "Hello", ...}]}
        """
        transcript_text = ""
        current_speaker = None

        for segment in segments:
            speaker = segment.get("speaker", "Unknown")
            text = segment.get("text", "").strip()

            if not text:
                continue

            # Add speaker label if speaker changes
            if speaker != current_speaker:
                if current_speaker is not None:
                    transcript_text += "\n\n"
                transcript_text += f"{speaker}: "
                current_speaker = speaker
            else:
                transcript_text += " "

            transcript_text += text

        return transcript_text.strip()

    def poll_managed_bots(self) -> List[Dict]:
        """
        Poll all managed bots to check their status and get completed media
        """
        completed_bots = []

        for bot_id in list(self.managed_bot_ids):
            try:
                status = self.get_bot_status(bot_id)
                if status:
                    recordings = status.get('recordings', [])
                    if recordings:
                        bot_status = recordings[0]

                        if bot_status:
                            transcript = self.get_bot_transcript(bot_id)

                            completed_bot = {
                                'bot_id': bot_id,
                                'status': bot_status,
                                'meeting_url': status.get('meeting_url'),
                                'start_time': status.get('start_time'),
                                'end_time': status.get('end_time'),
                                'transcript': transcript
                            }
                            completed_bots.append(completed_bot)

                            # Remove from managed bots since it's completed
                            self.managed_bot_ids.discard(bot_id)

                        elif bot_status in ['failed', 'error']:
                            # Bot failed, remove from managed bots
                            logger.warning(f"Bot {bot_id} failed with status: {bot_status}")
                            self.managed_bot_ids.discard(bot_id)

            except Exception as e:
                logger.error(f"Error polling bot {bot_id}: {str(e)}")

        return completed_bots

    def detect_meeting_platform(self, meeting_url: str) -> str:
        """
        Detect the meeting platform from URL
        """
        url_lower = meeting_url.lower()

        if 'zoom.us' in url_lower or 'zoom.com' in url_lower:
            return 'zoom'
        elif 'teams.microsoft.com' in url_lower or 'teams.live.com' in url_lower:
            return 'teams'
        elif 'meet.google.com' in url_lower:
            return 'google_meet'
        elif 'webex.com' in url_lower:
            return 'webex'
        else:
            return 'unknown'

    def extract_meeting_info(self, calendar_event: Dict) -> Optional[Dict]:
        """
        Extract meeting information from calendar event
        """
        try:
            logger.info(f"Extracting meeting info from event: {calendar_event.get('title', 'Untitled')}")

            # Look for meeting URL in description or location
            description = calendar_event.get('description', '') or ''
            location = calendar_event.get('location', '') or ''

            logger.info(f"Event description: '{description}'")
            logger.info(f"Event location: '{location}'")

            # Common patterns for meeting URLs
            meeting_url = None
            for text in [description, location]:
                logger.info(f"Checking text for meeting URLs: '{text}'")
                if 'zoom.us' in text or 'teams.microsoft.com' in text or 'meet.google.com' in text:
                    logger.info(f"Found meeting platform in text: '{text}'")
                    # Extract URL from text
                    import re
                    url_pattern = r'https?://[^\s]+'
                    urls = re.findall(url_pattern, text)
                    logger.info(f"Found URLs in text: {urls}")
                    if urls:
                        meeting_url = urls[0]
                        logger.info(f"Selected meeting URL: {meeting_url}")
                        break

            if not meeting_url:
                logger.warning("No meeting URL found in event description or location")
                return None

            logger.info(f"Parsing start time: {calendar_event.get('start_time')}")
            logger.info(f"Parsing end time: {calendar_event.get('end_time')}")

            start_time = datetime.fromisoformat(calendar_event['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(calendar_event['end_time'].replace('Z', '+00:00'))
            duration = int((end_time - start_time).total_seconds() / 60)

            logger.info(f"Parsed start time: {start_time}")
            logger.info(f"Parsed end time: {end_time}")
            logger.info(f"Calculated duration: {duration} minutes")

            result = {
                'meeting_url': meeting_url,
                'start_time': start_time,
                'duration_minutes': duration,
                'platform': self.detect_meeting_platform(meeting_url),
                'title': calendar_event.get('title', 'Untitled Meeting'),
                'attendees': calendar_event.get('attendees', [])
            }

            print('calendar_event')
            print(calendar_event)

            logger.info(f"Extracted meeting info: {result}")
            return result

        except Exception as e:
            logger.error(f"Error extracting meeting info: {str(e)}")
            logger.error(f"Calendar event that caused error: {calendar_event}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def schedule_bot_for_event(self, calendar_event: Dict, join_before_minutes: int = 5) -> Optional[Dict]:
        """
        Schedule a Recall bot for a calendar event if it has a meeting URL
        """
        try:
            logger.info(f"Starting bot scheduling for event: {calendar_event.get('title', 'Untitled')}")
            logger.info(f"Event details: {calendar_event}")

            # Extract meeting information
            logger.info("Extracting meeting information...")
            meeting_info = self.extract_meeting_info(calendar_event)
            if not meeting_info:
                logger.warning(f"No meeting URL found in event: {calendar_event.get('title', 'Untitled')}")
                logger.info(f"Event description: {calendar_event.get('description', 'No description')}")
                logger.info(f"Event location: {calendar_event.get('location', 'No location')}")
                return None

            logger.info(f"Meeting info extracted: {meeting_info}")

            # Check if notetaker is enabled for this event
            notetaker_enabled = calendar_event.get('notetaker_enabled', False)
            logger.info(f"Notetaker enabled for event: {notetaker_enabled}")
            if not notetaker_enabled:
                logger.info(f"Notetaker disabled for event: {calendar_event.get('title', 'Untitled')}")
                return None

            # Check if meeting is in the future
            meeting_start = meeting_info['start_time']
            now = datetime.now(meeting_start.tzinfo) if meeting_start.tzinfo else datetime.now()
            logger.info(f"Meeting start time: {meeting_start}")
            logger.info(f"Current time: {now}")
            logger.info(f"Meeting is in future: {meeting_start > now}")

            if meeting_start <= now:
                logger.warning(f"Meeting start time {meeting_start} is in the past, skipping bot creation")
                return None

            # Create bot for the meeting
            logger.info(f"Creating bot for meeting URL: {meeting_info['meeting_url']}")
            logger.info(f"Meeting platform: {meeting_info.get('platform', 'unknown')}")
            logger.info(f"Meeting duration: {meeting_info['duration_minutes']} minutes")
            logger.info(f"Join before minutes: {join_before_minutes}")

            bot_data = self.create_bot(
                meeting_url=meeting_info['meeting_url'],
                meeting_start_time=meeting_info['start_time'],
                meeting_duration_minutes=meeting_info['duration_minutes'],
                join_before_minutes=join_before_minutes
            )

            if bot_data:
                logger.info(f"Bot created successfully: {bot_data}")
                result = {
                    'bot_id': bot_data.get('id'),
                    'meeting_info': meeting_info,
                    'scheduled_for': meeting_info['start_time'] - timedelta(minutes=join_before_minutes),
                    'status': 'scheduled'
                }
                logger.info(f"Bot scheduling result: {result}")
                return result
            else:
                logger.error("Failed to create bot - bot_data is None")
                return None

        except Exception as e:
            logger.error(f"Error scheduling bot for event: {str(e)}")
            logger.error(f"Event that caused error: {calendar_event}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def get_managed_bot_ids(self) -> List[str]:
        """
        Get list of currently managed bot IDs
        """
        return list(self.managed_bot_ids)

    def remove_managed_bot(self, bot_id: str):
        """
        Remove a bot from managed bots (when completed or failed)
        """
        self.managed_bot_ids.discard(bot_id)
        logger.info(f"Removed bot {bot_id} from managed bots")
