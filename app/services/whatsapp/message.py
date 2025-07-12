"""WhatsApp messaging service."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.models.message_queue import MessageQueue, MessageStatus
from app.services.whatsapp.client import WhatsAppClient
from app.utils.validators import validate_message_request_new
from app.utils.phone_formatter import format_phone_for_whatsapp

logger = logging.getLogger(__name__)

class WhatsAppMessageService:
    """Service for sending WhatsApp messages."""
    
    def __init__(self, session_id: str = None):
        """Initialize the WhatsApp message service.
        
        Args:
            session_id: ID of the session to use (if None, will use the first active session)
        """
        self.session_id = session_id
        self.client = None
        
        # If no session ID provided, use the first active session
        if not session_id:
            active_sessions = WhatsAppSession.get_active_sessions()
            if active_sessions and active_sessions[0].status == "connected":
                self.session_id = active_sessions[0].session_id
    
    def connect(self) -> Dict[str, Any]:
        """Connect to WhatsApp Web.
        
        Returns:
            Dictionary with connection status
        """
        if not self.session_id:
            return {
                "status": "failed",
                "error": "No active session available"
            }
        
        try:
            # Create client
            self.client = WhatsAppClient(session_id=self.session_id)
            
            # Check if already connected
            session = WhatsAppSession.get_session_by_id(self.session_id)
            if session and session.status == "connected":
                self.client.is_connected = True
                return {
                    "status": "success",
                    "message": "Already connected"
                }
            
            # Connect to WhatsApp Web
            result = self.client.connect()
            
            return result
            
        except Exception as e:
            logger.error(f"Error connecting to WhatsApp: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def send_message(self, recipient: str, message: str = None, media_url: str = None) -> Dict[str, Any]:
        """Send a message to a WhatsApp contact.
        
        Args:
            recipient: The phone number to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            
        Returns:
            Dictionary with send status and message ID if successful
        """
        # Validate request
        validation = validate_message_request_new({
            "_use_new_format": True,
            "recipient": recipient,
            "message": message,
            "media_url": media_url
        })
        
        if validation.get("status") == "failed":
            return validation
        
        # Format phone number
        phone = format_phone_for_whatsapp(recipient)
        if not phone:
            return {
                "status": "failed",
                "error": "Invalid phone number"
            }
        
        # Connect if not connected
        if not self.client or not self.client.is_connected:
            connect_result = self.connect()
            if connect_result.get("status") == "failed":
                return connect_result
        
        # Send message
        result = self.client.send_message(phone, message, media_url)
        
        # Save message status
        if result.get("status") == "success":
            self._save_message_status(phone, message, media_url, result)
        
        return result
    
    def queue_message(self, recipient: str, message: str = None, media_url: str = None, 
                     priority: int = 0, scheduled_at: datetime = None) -> Dict[str, Any]:
        """Queue a message to be sent later.
        
        Args:
            recipient: The phone number to send the message to
            message: The message text to send
            media_url: Optional URL to media to send
            priority: Message priority (higher number = higher priority)
            scheduled_at: When to send the message (if None, will be sent ASAP)
            
        Returns:
            Dictionary with queue status and message ID if successful
        """
        # Validate request
        validation = validate_message_request_new({
            "_use_new_format": True,
            "recipient": recipient,
            "message": message,
            "media_url": media_url
        })
        
        if validation.get("status") == "failed":
            return validation
        
        # Format phone number
        phone = format_phone_for_whatsapp(recipient)
        if not phone:
            return {
                "status": "failed",
                "error": "Invalid phone number"
            }
        
        try:
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
            db.session.commit()
            
            return {
                "status": "success",
                "message": "Message queued successfully",
                "queue_id": queue_item.id
            }
            
        except Exception as e:
            logger.error(f"Error queuing message: {str(e)}")
            db.session.rollback()
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def process_queue(self, limit: int = 50) -> Dict[str, Any]:
        """Process the message queue.
        
        Args:
            limit: Maximum number of messages to process
            
        Returns:
            Dictionary with processing status and count of processed messages
        """
        if not self.session_id:
            return {
                "status": "failed",
                "error": "No active session available"
            }
        
        try:
            # Get session
            session = WhatsAppSession.get_session_by_id(self.session_id)
            if not session:
                return {
                    "status": "failed",
                    "error": f"Session with ID '{self.session_id}' not found"
                }
            
            # Connect if not connected
            if not self.client or not self.client.is_connected:
                connect_result = self.connect()
                if connect_result.get("status") == "failed":
                    return connect_result
            
            # Get pending messages
            pending_messages = MessageQueue.get_pending_messages(session.id, limit)
            
            processed_count = 0
            success_count = 0
            failed_count = 0
            
            # Process each message
            for queue_item in pending_messages:
                # Update status to processing
                queue_item.status = "processing"
                db.session.commit()
                
                try:
                    # Send message
                    result = self.client.send_message(
                        queue_item.recipient,
                        queue_item.message,
                        queue_item.media_url
                    )
                    
                    processed_count += 1
                    
                    if result.get("status") == "success":
                        # Update status to sent
                        queue_item.status = "sent"
                        success_count += 1
                        
                        # Save message status
                        message_status = MessageStatus(
                            message_id=queue_item.id,
                            status="sent",
                            external_id=result.get("message_id")
                        )
                        db.session.add(message_status)
                        
                    else:
                        # Update status to failed
                        queue_item.status = "failed"
                        queue_item.retry_count += 1
                        failed_count += 1
                        
                        # If retry limit not reached, set back to pending
                        if queue_item.retry_count < queue_item.max_retries:
                            queue_item.status = "pending"
                        
                        # Save error message
                        message_status = MessageStatus(
                            message_id=queue_item.id,
                            status="failed",
                            error_message=result.get("error")
                        )
                        db.session.add(message_status)
                    
                    db.session.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing queue item {queue_item.id}: {str(e)}")
                    
                    # Update status to failed
                    queue_item.status = "failed"
                    queue_item.retry_count += 1
                    failed_count += 1
                    
                    # If retry limit not reached, set back to pending
                    if queue_item.retry_count < queue_item.max_retries:
                        queue_item.status = "pending"
                    
                    # Save error message
                    message_status = MessageStatus(
                        message_id=queue_item.id,
                        status="failed",
                        error_message=str(e)
                    )
                    db.session.add(message_status)
                    
                    db.session.commit()
            
            return {
                "status": "success",
                "message": f"Processed {processed_count} messages",
                "processed_count": processed_count,
                "success_count": success_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"Error processing queue: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _save_message_status(self, recipient: str, message: str, media_url: str, result: Dict[str, Any]) -> None:
        """Save message status to database.
        
        Args:
            recipient: The phone number the message was sent to
            message: The message text that was sent
            media_url: The media URL that was sent (if any)
            result: The result of sending the message
        """
        try:
            # Get session
            session = WhatsAppSession.get_session_by_id(self.session_id)
            if not session:
                logger.error(f"Session with ID '{self.session_id}' not found")
                return
            
            # Create queue item (for record keeping)
            queue_item = MessageQueue(
                session_id=session.id,
                recipient=recipient,
                message=message,
                media_url=media_url,
                status="sent"
            )
            
            db.session.add(queue_item)
            db.session.commit()
            
            # Create status record
            message_status = MessageStatus(
                message_id=queue_item.id,
                status="sent",
                external_id=result.get("message_id")
            )
            
            db.session.add(message_status)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error saving message status: {str(e)}")
            db.session.rollback()