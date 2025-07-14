"""WhatsApp bulk messaging service."""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.models.message_queue import MessageQueue, MessageStatus
from app.services.whatsapp.client import WhatsAppClient
from app.services.whatsapp.message import WhatsAppMessageService
from app.utils.validators import validate_message_request_new
from app.utils.phone_formatter import format_phone_for_whatsapp

logger = logging.getLogger(__name__)

class WhatsAppBulkMessenger:
    """Service for sending bulk WhatsApp messages."""
    
    def __init__(self, session_id: str = None, max_workers: int = 5, rate_limit: int = 30):
        """Initialize the WhatsApp bulk messaging service.
        
        Args:
            session_id: ID of the session to use (if None, will use the first active session)
            max_workers: Maximum number of concurrent message sending threads
            rate_limit: Maximum number of messages to send per minute (to avoid blocking)
        """
        self.session_id = session_id
        self.max_workers = max_workers
        self.rate_limit = rate_limit
        self.message_service = WhatsAppMessageService(session_id=session_id)
        
        # If no session ID provided, use the first active session
        if not session_id:
            active_sessions = WhatsAppSession.get_active_sessions()
            if active_sessions and active_sessions[0].status == "connected":
                self.session_id = active_sessions[0].session_id
                self.message_service = WhatsAppMessageService(session_id=self.session_id)
    
    def connect(self) -> Dict[str, Any]:
        """Connect to WhatsApp Web.
        
        Returns:
            Dictionary with connection status
        """
        return self.message_service.connect()
    
    def queue_bulk_messages(self, recipients: List[str], message: str = None, media_url: str = None,
                          priority: int = 0, scheduled_at: datetime = None) -> Dict[str, Any]:
        """Queue multiple messages to be sent later.
        
        Args:
            recipients: List of phone numbers to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            priority: Message priority (higher number = higher priority)
            scheduled_at: When to send the message (if None, will be sent ASAP)
            
        Returns:
            Dictionary with queue status and count of queued messages
        """
        if not recipients:
            return {
                "status": "failed",
                "error": "No recipients provided"
            }
        
        if not message and not media_url:
            return {
                "status": "failed",
                "error": "Either message or media_url must be provided"
            }
        
        # Get session
        if not self.session_id:
            active_sessions = WhatsAppSession.get_active_sessions()
            if not active_sessions:
                return {
                    "status": "failed",
                    "error": "No active session available"
                }
            session = active_sessions[0]
        else:
            session = WhatsAppSession.get_session_by_id(self.session_id)
            if not session:
                return {
                    "status": "failed",
                    "error": f"Session with ID '{self.session_id}' not found"
                }
        
        success_count = 0
        failed_count = 0
        failed_recipients = []
        
        try:
            # Queue messages for each recipient
            for recipient in recipients:
                try:
                    # Format phone number
                    phone = format_phone_for_whatsapp(recipient)
                    if not phone:
                        failed_count += 1
                        failed_recipients.append({
                            "recipient": recipient,
                            "error": "Invalid phone number"
                        })
                        continue
                    
                    # Create queue item
                    queue_item = MessageQueue(
                        session_id=session.id,
                        recipient=phone,
                        message=message,
                        media_url=media_url,
                        priority=priority,
                        scheduled_at=scheduled_at,
                        status="pending"
                    )
                    
                    db.session.add(queue_item)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error queuing message for {recipient}: {str(e)}")
                    failed_count += 1
                    failed_recipients.append({
                        "recipient": recipient,
                        "error": str(e)
                    })
            
            db.session.commit()
            
            return {
                "status": "success",
                "message": f"Queued {success_count} messages successfully",
                "success_count": success_count,
                "failed_count": failed_count,
                "failed_recipients": failed_recipients
            }
            
        except Exception as e:
            logger.error(f"Error queuing bulk messages: {str(e)}")
            db.session.rollback()
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def send_bulk_messages(self, recipients: List[str], message: str = None, media_url: str = None) -> Dict[str, Any]:
        """Send messages to multiple recipients.
        
        Args:
            recipients: List of phone numbers to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            
        Returns:
            Dictionary with send status and counts of successful/failed messages
        """
        if not recipients:
            return {
                "status": "failed",
                "error": "No recipients provided"
            }
        
        if not message and not media_url:
            return {
                "status": "failed",
                "error": "Either message or media_url must be provided"
            }
        
        # Connect if not connected
        if not self.message_service.client or not self.message_service.client.is_connected:
            connect_result = self.connect()
            if connect_result.get("status") == "failed":
                return connect_result
        
        success_count = 0
        failed_count = 0
        results = []
        
        # Calculate delay between messages to respect rate limit
        delay = 60 / self.rate_limit if self.rate_limit > 0 else 0
        
        try:
            # Use ThreadPoolExecutor for concurrent sending
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit tasks
                future_to_recipient = {}
                for recipient in recipients:
                    future = executor.submit(
                        self._send_single_message, recipient, message, media_url
                    )
                    future_to_recipient[future] = recipient
                    
                    # Sleep to respect rate limit
                    if delay > 0:
                        time.sleep(delay)
                
                # Process results as they complete
                for future in as_completed(future_to_recipient):
                    recipient = future_to_recipient[future]
                    try:
                        result = future.result()
                        results.append({
                            "recipient": recipient,
                            "status": result.get("status"),
                            "message_id": result.get("message_id"),
                            "error": result.get("error")
                        })
                        
                        if result.get("status") == "success":
                            success_count += 1
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing result for {recipient}: {str(e)}")
                        results.append({
                            "recipient": recipient,
                            "status": "failed",
                            "error": str(e)
                        })
                        failed_count += 1
            
            return {
                "status": "success",
                "message": f"Sent {success_count} messages, {failed_count} failed",
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error sending bulk messages: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def process_queue(self, batch_size: int = 50) -> Dict[str, Any]:
        """Process the message queue in batches.
        
        Args:
            batch_size: Number of messages to process in each batch
            
        Returns:
            Dictionary with processing status and count of processed messages
        """
        return self.message_service.process_queue(limit=batch_size)
    
    def _send_single_message(self, recipient: str, message: str, media_url: str) -> Dict[str, Any]:
        """Send a message to a single recipient.
        
        Args:
            recipient: The phone number to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            
        Returns:
            Dictionary with send status
        """
        try:
            return self.message_service.send_message(recipient, message, media_url)
        except Exception as e:
            logger.error(f"Error sending message to {recipient}: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }