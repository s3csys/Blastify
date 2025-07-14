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
    """Service for sending WhatsApp messages using WhatsApp Web.
    
    This service handles authentication, QR code generation, and message sending
    for WhatsApp using the WhatsApp Web client.
    """
    
    def __init__(self, session_name=None):
        """Initialize WhatsApp service.
        
        Args:
            session_name: Optional name of WhatsApp session to use
        """
        try:
            # Create application-specific directories
            self.app_data_dir = os.path.join(os.getcwd(), 'app_data')
            os.makedirs(self.app_data_dir, exist_ok=True)
            
            # Store session data path within app_data
            self.session_path = os.path.join(self.app_data_dir, 'whatsapp_session')
            os.makedirs(self.session_path, exist_ok=True)
            
            self.is_logged_in = False
            self.qr_code_base64 = None
            self.session_name = None
            
            # Initialize with WhatsApp Web client
            from app.services.whatsapp.client import WhatsAppClient
            from app.services.whatsapp.message import WhatsAppMessageService
            
            self.message_service = None
            
            # Load session if provided
            if session_name:
                self.session = self.get_session_by_name(session_name)
                if self.session:
                    self.session_name = session_name
            else:
                # Try to get first active session
                self.session = self._get_session()
            
        except ImportError as e:
            logger.error(f"Required package not installed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error initializing WhatsApp service: {str(e)}")
            raise
    
    def _get_session(self, session_name=None):
        """Get or create a WhatsApp Web session.
        
        Args:
            session_name: Optional name of the session to use
            
        Returns:
            WhatsApp session object or None if not found
        """
        try:
            from app.models.whatsapp_session import WhatsAppSession
            
            # If session name provided, try to get that specific session
            if session_name:
                session = WhatsAppSession.get_session_by_name(session_name)
                if session:
                    logger.info(f"Found WhatsApp session: {session_name}")
                    return session
            
            # Otherwise, get the first active session
            active_sessions = WhatsAppSession.get_active_sessions()
            if active_sessions:
                logger.info(f"Using active WhatsApp session: {active_sessions[0].name}")
                return active_sessions[0]
            
            logger.warning("No active WhatsApp sessions found")
            return None
                
        except Exception as e:
            logger.error(f"Error getting WhatsApp session: {str(e)}")
            return None
    
    def create_session(self, session_name):
        """Create a new WhatsApp Web session.
        
        Args:
            session_name: Name for the new session
            
        Returns:
            Dictionary with session creation status and session ID if successful
        """
        try:
            from app.services.whatsapp.auth import WhatsAppAuth
            
            # Create a new session
            result = WhatsAppAuth.create_session(session_name)
            
            if result.get("status") == "success":
                logger.info(f"Created new WhatsApp session: {session_name}")
                return True
            else:
                logger.error(f"Failed to create WhatsApp session: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Error creating WhatsApp session: {str(e)}")
            return False
    
    def generate_qr_code(self, session_id=None):
        """Generate QR code for WhatsApp Web authentication.
        
        Args:
            session_id: Optional session ID to use
            
        Returns:
            Base64 encoded string of the QR code image or None if failed
        """
        try:
            from app.services.whatsapp.auth import WhatsAppAuth
            
            # If no session ID provided, try to get one
            if not session_id:
                session = self._get_session()
                if session:
                    session_id = session.session_id
                else:
                    logger.error("No active session found for QR code generation")
                    return None
            
            # Connect to WhatsApp Web and get QR code
            result = WhatsAppAuth.connect_session(session_id)
            
            if result.get("status") == "success" and "qr_code" in result:
                qr_base64 = result.get("qr_code")
                self.qr_code_base64 = qr_base64
                logger.info("Generated WhatsApp QR code")
                return qr_base64
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Error generating QR code: {error_msg}")
                return None
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return None
    
    # Keep the existing _get_qr_code method for backward compatibility
    def _get_qr_code(self, session_id=None):
        """Get the QR code for WhatsApp Web authentication.
        
        Args:
            session_id: Optional session ID to use
            
        Returns:
            Base64 encoded string of the QR code image
        """
        return self.generate_qr_code(session_id)
    
    def is_connected(self, session_id=None):
        """Check if WhatsApp is connected.
        
        Args:
            session_id: Optional session ID to check
            
        Returns:
            Boolean indicating if WhatsApp is connected
        """
        try:
            from app.models.whatsapp_session import WhatsAppSession
            
            # If no session ID provided, try to get one
            if not session_id:
                session = self._get_session()
                if not session:
                    return False
                session_id = session.session_id
            
            # Get session from database
            session = WhatsAppSession.get_session_by_id(session_id)
            if not session:
                return False
            
            # Check if session is connected
            return session.status == "connected"
        except Exception as e:
            logger.error(f"Error checking WhatsApp connection: {str(e)}")
            return False

    def send_message(self, recipient, message, media_url=None):
        """Send a WhatsApp message using WhatsApp Web.
        
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
            
            # Get session
            session = self._get_session()
            if not session:
                return {'status': 'failed', 'error': 'No active WhatsApp session found'}
            
            # Initialize WhatsApp message service
            from app.services.whatsapp.message import WhatsAppMessageService
            message_service = WhatsAppMessageService(session_id=session.session_id)
            
            # Determine media type if provided
            media_type = None
            if media_url:
                media_ext = media_url.split('.')[-1].lower()
                if media_ext in ['jpg', 'jpeg', 'png']:
                    media_type = 'image'
                elif media_ext in ['mp4', 'avi', 'mov']:
                    media_type = 'video'
                elif media_ext in ['mp3', 'wav', 'ogg']:
                    media_type = 'audio'
                else:
                    media_type = 'document'
            
            # Send message
            result = message_service.send_message(
                phone=phone,
                message=message,
                media_url=media_url,
                media_type=media_type
            )
            
            if result.get('status') == 'success':
                return {
                    'status': 'sent',
                    'message_id': result.get('message_id', f"wa_{int(time.time())}")
                }
            else:
                return {
                    'status': 'failed',
                    'error': result.get('message', 'Unknown error')
                }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _determine_media_type(self, url):
        """Determine media type from URL.
        
        Args:
            url: URL to media file
            
        Returns:
            Media type string (image, video, document, audio)
        """
        # Get file extension
        ext = url.split('.')[-1].lower()
        
        # Determine media type based on extension
        if ext in ['jpg', 'jpeg', 'png', 'gif']:
            return "image"
        elif ext in ['mp4', 'avi', 'mov', 'webm']:
            return "video"
        elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
            return "audio"
        elif ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt']:
            return "document"
        else:
            return "document"  # Default to document
    
    def get_session_by_name(self, session_name):
        """Get WhatsApp session by name.
        
        Args:
            session_name: Name of the session
            
        Returns:
            WhatsAppSession object or None if not found
        """
        try:
            from app.models.whatsapp_session import WhatsAppSession
            
            # Get session from database
            session = WhatsAppSession.get_session_by_name(session_name)
            return session
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None
    
    def delete_session(self, session_name):
        """Delete WhatsApp session by name.
        
        Args:
            session_name: Name of the session to delete
            
        Returns:
            Boolean indicating if session was deleted successfully
        """
        try:
            from app.models.whatsapp_session import WhatsAppSession
            
            # Get session from database
            session = WhatsAppSession.get_session_by_name(session_name)
            if not session:
                logger.error(f"No session found with name: {session_name}")
                return False
            
            # Delete session
            result = session.delete()
            
            if result:
                logger.info(f"Deleted WhatsApp session: {session_name}")
                return True
            else:
                logger.error(f"Failed to delete session: {session_name}")
                return False
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False
    
    def get_all_sessions(self):
        """Get all WhatsApp sessions.
        
        Returns:
            List of WhatsAppSession objects
        """
        try:
            from app.models.whatsapp_session import WhatsAppSession
            
            # Get all sessions from database
            sessions = WhatsAppSession.get_all_active_sessions()
            return sessions
        except Exception as e:
            logger.error(f"Error getting sessions: {str(e)}")
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