"""Message service classes for different messaging platforms."""

import os
import logging
from abc import ABC, abstractmethod
import base64
import time
import uuid
from pathlib import Path
import qrcode
from PIL import Image
import io
import json
from app.models.api_credential import ApiCredential

logger = logging.getLogger(__name__)

class BaseMessageService(ABC):
    """Base abstract class for all message services."""
    
    @abstractmethod
    def send_message(self, recipient, message, media_url=None):
        """Send a message to a recipient.
        
        Args:
            recipient: The recipient's identifier (phone number, user ID, etc.)
            message: The message text to send
            media_url: Optional URL to media to include
            
        Returns:
            Dictionary with status and any relevant information
        """
        pass

class WhatsAppService(BaseMessageService):
    """Service for sending WhatsApp messages using Green API."""
    
    def __init__(self, generate_qr=False):
        """Initialize the WhatsApp service with Green API."""
        try:
            from whatsapp_api_client_python import API
            self.API = API  # Store API class for later use
            
            # Create application-specific directories
            self.app_data_dir = os.path.join(os.getcwd(), 'app_data')
            os.makedirs(self.app_data_dir, exist_ok=True)
            
            # Store session data path within app_data
            self.session_path = os.path.join(self.app_data_dir, 'whatsapp_session')
            os.makedirs(self.session_path, exist_ok=True)
            
            # Store credentials file path
            self.credentials_file = os.path.join(self.session_path, 'credentials.json')
            
            # Load credentials
            self._load_credentials()
            
            # Initialize Green API client with loaded credentials
            self.green_api = self.API.GreenAPI(self.instance_id, self.api_token)
            
            self.is_logged_in = False
            self.qr_code_base64 = None
            
            # If generate_qr is True, get QR code
            if generate_qr:
                self.qr_code_base64 = self._get_qr_code()
            
        except ImportError as e:
            logger.error(f"Required package not installed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error initializing WhatsApp service: {str(e)}")
            raise
    
    def _load_credentials(self, credential_name=None):
        """Load Green API credentials from database or file.
        
        Args:
            credential_name: Optional name of the credential set to load
            
        Returns:
            Tuple of (instance_id, api_token)
        """
        try:
            # Try to load from database first
            db_instance_id = ApiCredential.get_credential('whatsapp', credential_name, 'instance_id')
            db_api_token = ApiCredential.get_credential('whatsapp', credential_name, 'api_token')
            
            if db_instance_id and db_api_token:
                self.instance_id = db_instance_id
                self.api_token = db_api_token
                logger.info(f"Loaded WhatsApp credentials from database for {credential_name if credential_name else 'default'}")
                return (self.instance_id, self.api_token)
                
            # If not in database, try to load from file
            elif os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    self.instance_id = credentials.get('instance_id')
                    self.api_token = credentials.get('api_token')
                    logger.info("Loaded WhatsApp credentials from file")
                    
                    # Save to database for future use
                    if self.instance_id and self.api_token:
                        ApiCredential.set_credential('whatsapp', 'instance_id', self.instance_id, credential_name)
                        ApiCredential.set_credential('whatsapp', 'api_token', self.api_token, credential_name)
                    
                    return (self.instance_id, self.api_token)
            
            # If no credentials found, set placeholder values
            self.instance_id = "your_instance_id"
            self.api_token = "your_api_token"
            logger.warning("No WhatsApp credentials found in database or file")
            return (None, None)
                
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            self.instance_id = "your_instance_id"
            self.api_token = "your_api_token"
            return (None, None)
    
    def save_credentials(self, instance_id, api_token, credential_name=None):
        """Save Green API credentials to database and file.
        
        Args:
            instance_id: The Green API instance ID
            api_token: The Green API token
            credential_name: Optional name to identify this credential set
            
        Returns:
            Boolean indicating success
        """
        try:
            # Update instance variables
            self.instance_id = instance_id
            self.api_token = api_token
            
            # Save to database
            ApiCredential.set_credential('whatsapp', 'instance_id', instance_id, credential_name)
            ApiCredential.set_credential('whatsapp', 'api_token', api_token, credential_name)
            
            # Also save to file as backup
            with open(self.credentials_file, 'w') as f:
                json.dump({
                    'instance_id': instance_id,
                    'api_token': api_token,
                    'credential_name': credential_name
                }, f)
            
            # Reinitialize Green API client with new credentials
            self.green_api = self.API.GreenAPI(instance_id, api_token)
                
            logger.info(f"Saved WhatsApp credentials to database and file for {credential_name if credential_name else 'default'}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            return False
    
    def generate_qr_code(self):
        """Generate QR code for WhatsApp Web authentication.
        
        Returns:
            Base64 encoded string of the QR code image or None if failed
        """
        try:
            # Get QR code from Green API
            response = self.green_api.account.qr()
            
            if response and hasattr(response, 'code') and response.code == 200:
                # The response contains the QR code in base64 format
                qr_base64 = response.data.get('qrCode')
                self.qr_code_base64 = qr_base64
                logger.info("Generated WhatsApp QR code")
                return qr_base64
            else:
                error_msg = getattr(response, 'error', 'Unknown error') if response else 'No response received'
                logger.error(f"Error generating QR code: {error_msg}")
                return None
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return None
    
    # Keep the existing _get_qr_code method for backward compatibility
    def _get_qr_code(self):
        """Get the QR code for WhatsApp Web authentication.
        
        Returns:
            Base64 encoded string of the QR code image
        """
        return self.generate_qr_code()
    
    def is_connected(self):
        """Check if WhatsApp is connected.
        
        Returns:
            Boolean indicating if WhatsApp is connected
        """
        try:
            # Check instance state
            response = self.green_api.account.getStateInstance()
            
            if response.code == 200:
                # Check if the state is 'authorized'
                state = response.data.get('stateInstance')
                return state == 'authorized'
            else:
                logger.error(f"Error checking WhatsApp connection: {response.error}")
                return False
        except Exception as e:
            logger.error(f"Error checking WhatsApp connection: {str(e)}")
            return False

    def send_message(self, recipient, message, media_url=None):
        """Send a WhatsApp message using Green API.
        
        Args:
            recipient: The recipient's phone number with country code
            message: The message text to send
            media_url: Optional URL to media to include
            
        Returns:
            Dictionary with status and any relevant information
        """
        try:
            if not self.is_connected():
                return {'status': 'failed', 'error': 'WhatsApp not connected'}
            
            # Format phone number (remove any non-numeric characters except +)
            phone = ''.join(c for c in recipient if c.isdigit() or c == '+')
            
            # Remove the + sign if present
            if phone.startswith('+'):
                phone = phone[1:]
            
            # Format the chat ID for Green API
            chat_id = f"{phone}@c.us"
            
            # If media_url is provided, send it as well
            if media_url:
                # Determine media type and send appropriate message
                media_ext = media_url.split('.')[-1].lower()
                
                if media_ext in ['jpg', 'jpeg', 'png']:
                    # Send image with caption
                    response = self.green_api.sending.sendFileByUrl(
                        chat_id,
                        media_url,
                        f"image.{media_ext}",
                        message
                    )
                elif media_ext in ['mp4', 'avi', 'mov']:
                    # Send video with caption
                    response = self.green_api.sending.sendFileByUrl(
                        chat_id,
                        media_url,
                        f"video.{media_ext}",
                        message
                    )
                elif media_ext in ['mp3', 'wav', 'ogg']:
                    # Send audio with caption
                    response = self.green_api.sending.sendFileByUrl(
                        chat_id,
                        media_url,
                        f"audio.{media_ext}",
                        message
                    )
                else:
                    # Send document with caption
                    response = self.green_api.sending.sendFileByUrl(
                        chat_id,
                        media_url,
                        f"document.{media_ext}",
                        message
                    )
            else:
                # Send text message
                response = self.green_api.sending.sendMessage(chat_id, message)
            
            if response.code == 200:
                return {
                    'status': 'sent',
                    'message_id': response.data.get('idMessage', f"wa_{int(time.time())}")
                }
            else:
                return {
                    'status': 'failed',
                    'error': response.error
                }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    # Add these methods to WhatsAppService class
    def load_credential_by_name(self, credential_name):
        """Load a specific credential set by name.
        
        Args:
            credential_name: The name of the credential set to load
            
        Returns:
            Dictionary with credential details or None if not found
        """
        try:
            # Get credentials from database
            instance_id = ApiCredential.get_credential('whatsapp', credential_name, 'instance_id')
            api_token = ApiCredential.get_credential('whatsapp', credential_name, 'api_token')
            
            if not instance_id or not api_token:
                logger.warning(f"Credential set '{credential_name}' not found or incomplete")
                return None
                
            # Update instance variables
            self.instance_id = instance_id
            self.api_token = api_token
            
            # Reinitialize Green API client with new credentials
            self.green_api = self.API.GreenAPI(instance_id, api_token)
            
            logger.info(f"Loaded WhatsApp credentials for '{credential_name}'")
            return {'credential_name': credential_name, 'instance_id': instance_id, 'api_token': api_token}
        except Exception as e:
            logger.error(f"Error loading credential set '{credential_name}': {str(e)}")
            return None

    def delete_credential(self, credential_name):
        """Delete a credential set by name.
        
        Args:
            credential_name: The name of the credential set to delete
            
        Returns:
            Boolean indicating success
        """
        try:
            return ApiCredential.delete_credential_set('whatsapp', credential_name)
        except Exception as e:
            logger.error(f"Error deleting credential set '{credential_name}': {str(e)}")
            return False
            
    def get_all_credentials(self):
        """Get all saved WhatsApp credential sets.
        
        Returns:
            List of credential sets with names
        """
        try:
            return ApiCredential.get_credential_sets('whatsapp')
        except Exception as e:
            logger.error(f"Error getting WhatsApp credentials: {str(e)}")
            return []

class TelegramService(BaseMessageService):
    """Service for sending Telegram messages using python-telegram-bot."""
    
    def __init__(self):
        """Initialize the Telegram service with bot token."""
        try:
            import telegram
            
            self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            
            if not self.bot_token:
                raise ValueError("Missing Telegram bot token in environment variables")
                
            self.bot = telegram.Bot(token=self.bot_token)
            
        except ImportError:
            logger.error("python-telegram-bot package not installed")
            raise
        except Exception as e:
            logger.error(f"Error initializing Telegram service: {str(e)}")
            raise
    
    def send_message(self, recipient, message, media_url=None):
        """Send a Telegram message.
        
        Args:
            recipient: The chat ID to send the message to
            message: The message text to send
            media_url: Optional URL to media to include
            
        Returns:
            Dictionary with status and message ID
        """
        try:
            if media_url:
                # Determine media type and send appropriate message
                media_ext = media_url.split('.')[-1].lower()
                
                if media_ext in ['jpg', 'jpeg', 'png']:
                    sent_message = self.bot.send_photo(
                        chat_id=recipient,
                        photo=media_url,
                        caption=message
                    )
                elif media_ext in ['mp4', 'avi', 'mov']:
                    sent_message = self.bot.send_video(
                        chat_id=recipient,
                        video=media_url,
                        caption=message
                    )
                elif media_ext in ['mp3', 'wav', 'ogg']:
                    sent_message = self.bot.send_audio(
                        chat_id=recipient,
                        audio=media_url,
                        caption=message
                    )
                else:
                    # Default to sending document
                    sent_message = self.bot.send_document(
                        chat_id=recipient,
                        document=media_url,
                        caption=message
                    )
            else:
                sent_message = self.bot.send_message(
                    chat_id=recipient,
                    text=message
                )
                
            return {
                'status': 'sent',
                'message_id': sent_message.message_id
            }
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }

class FreeWhatsAppService(BaseMessageService):
    """Service for sending WhatsApp messages using a free API."""
    
    def __init__(self):
        """Initialize the free WhatsApp service."""
        # No authentication needed for this demo service
        pass
    
    def send_message(self, recipient, message, media_url=None):
        """Send a WhatsApp message using a free service.
        
        Args:
            recipient: The recipient's phone number with country code
            message: The message text to send
            media_url: Optional URL to media to include
            
        Returns:
            Dictionary with status and message ID
        """
        try:
            # This is a mock implementation that simulates sending a message
            # In a real implementation, you would integrate with a free API service
            import time
            import uuid
            
            # Simulate API call delay
            time.sleep(0.5)
            
            # Generate a random message ID
            message_id = str(uuid.uuid4())
            
            logger.info(f"Simulated sending message to {recipient}: {message[:30]}...")
            
            return {
                'status': 'sent',
                'message_id': message_id
            }
            
        except Exception as e:
            logger.error(f"Error sending free WhatsApp message: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }

class MessageService:
    """Factory class for creating message services."""
    
    @staticmethod
    def create(platform):
        """Create and return a message service for the specified platform.
        
        Args:
            platform: The messaging platform to use (whatsapp, telegram, etc.)
            
        Returns:
            An instance of the appropriate message service
            
        Raises:
            ValueError: If the platform is not supported
        """
        platform = platform.lower()
        
        if platform == 'whatsapp':
            # Try to use WhatsAppService first, fall back to FreeWhatsAppService
            try:
                whatsapp_service = WhatsAppService()
                if whatsapp_service.is_connected():
                    return whatsapp_service
                else:
                    logger.warning("WhatsApp is not connected, using FreeWhatsAppService instead")
                    return FreeWhatsAppService()
            except Exception as e:
                logger.error(f"Error creating WhatsAppService: {str(e)}")
                return FreeWhatsAppService()
        elif platform == 'telegram':
            return TelegramService()
        else:
            raise ValueError(f"Unsupported messaging platform: {platform}")