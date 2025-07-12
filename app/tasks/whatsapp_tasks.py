"""Celery tasks for asynchronous WhatsApp message processing."""

import time
import logging
from typing import List, Dict, Any, Optional
from celery import Celery, Task
from flask import current_app

# Remove the import of create_app, just keep db
from app import db
from app.models.whatsapp_session import WhatsAppSession
from app.models.message_queue import MessageQueue
from app.services.whatsapp.message import WhatsAppMessageService

logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery('blastify')

# Configure Celery with direct Redis URLs instead of loading from app config
celery.conf.update({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'enable_utc': True,
})


class WhatsAppTask(Task):
    """Base task for WhatsApp operations."""
    
    _whatsapp_services = {}
    
    def get_whatsapp_service(self, session_id: Optional[str] = None) -> WhatsAppMessageService:
        """Get or create a WhatsApp service instance.
        
        Args:
            session_id: The session ID to use (if None, will use first active session)
            
        Returns:
            WhatsAppMessageService instance
        """
        # If no session ID provided, use first active session
        if not session_id:
            active_sessions = WhatsAppSession.get_active_sessions()
            if active_sessions:
                session_id = active_sessions[0].session_id
        
        # Return existing service if available
        if session_id in self._whatsapp_services:
            return self._whatsapp_services[session_id]
        
        # Create new service
        service = WhatsAppMessageService(session_id=session_id)
        
        # Store for reuse
        self._whatsapp_services[session_id] = service
        
        return service


@celery.task(bind=True, base=WhatsAppTask, max_retries=3, default_retry_delay=60)
def send_bulk_messages_task(self, session_id: Optional[str], messages: List[Dict[str, Any]], 
                          rate_limit_ms: int = 200) -> Dict[str, Any]:
    """Send multiple WhatsApp messages asynchronously.
    
    Args:
        session_id: The WhatsApp session ID to use (if None, will use first active session)
        messages: List of message dictionaries with recipient, message text, and optional media_url
        rate_limit_ms: Milliseconds to wait between messages to avoid rate limiting
        
    Returns:
        Dictionary with results summary
    """
    logger.info(f"Starting WhatsApp bulk send task for {len(messages)} messages")
    
    results = {
        'total': len(messages),
        'successful': 0,
        'failed': 0,
        'details': []
    }
    
    try:
        # Get WhatsApp service
        whatsapp_service = self.get_whatsapp_service(session_id)
        
        # Process each message
        for msg_data in messages:
            try:
                # Get message details
                recipient = msg_data.get('recipient')
                message_text = msg_data.get('message')
                media_url = msg_data.get('media_url')
                
                if not recipient:
                    logger.warning(f"Skipping message with missing recipient: {msg_data}")
                    results['failed'] += 1
                    results['details'].append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': 'Missing recipient'
                    })
                    continue
                
                # At least one of message or media_url must be provided
                if not message_text and not media_url:
                    logger.warning(f"Skipping message with no content: {msg_data}")
                    results['failed'] += 1
                    results['details'].append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': 'Missing message content'
                    })
                    continue
                
                # Send message
                result = whatsapp_service.send_message(
                    recipient=recipient,
                    message=message_text,
                    media_url=media_url
                )
                
                # Update results
                if result.get('status') == 'success':
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    
                results['details'].append({
                    'recipient': recipient,
                    'status': result.get('status'),
                    'message_id': result.get('message_id'),
                    'error': result.get('error')
                })
                
                # Add a small delay to avoid rate limiting
                time.sleep(rate_limit_ms / 1000)
                
            except Exception as e:
                logger.error(f"Error processing message to {recipient}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'recipient': recipient,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
        
    except Exception as e:
        logger.error(f"WhatsApp bulk send task failed: {str(e)}")
        self.retry(exc=e)


@celery.task(bind=True, base=WhatsAppTask, max_retries=3, default_retry_delay=60)
def process_message_queue_task(self, session_id: Optional[str] = None, 
                             batch_size: int = 50) -> Dict[str, Any]:
    """Process the WhatsApp message queue.
    
    Args:
        session_id: The WhatsApp session ID to use (if None, will process all active sessions)
        batch_size: Maximum number of messages to process per session
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting WhatsApp message queue processing task")
    
    results = {
        'sessions_processed': 0,
        'total_processed': 0,
        'successful': 0,
        'failed': 0,
        'session_details': []
    }
    
    try:
        # Get sessions to process
        with app.app_context():
            if session_id:
                sessions = [WhatsAppSession.get_session_by_id(session_id)]
                if not sessions[0]:
                    logger.error(f"Session with ID {session_id} not found")
                    return {
                        'status': 'failed',
                        'error': f"Session with ID {session_id} not found"
                    }
            else:
                sessions = WhatsAppSession.get_active_sessions()
        
        # Process each session
        for session in sessions:
            try:
                # Get WhatsApp service for this session
                whatsapp_service = self.get_whatsapp_service(session.session_id)
                
                # Process queue
                result = whatsapp_service.process_queue(limit=batch_size)
                
                # Update results
                results['sessions_processed'] += 1
                results['total_processed'] += result.get('processed_count', 0)
                results['successful'] += result.get('success_count', 0)
                results['failed'] += result.get('failed_count', 0)
                
                results['session_details'].append({
                    'session_id': session.session_id,
                    'session_name': session.name,
                    'processed': result.get('processed_count', 0),
                    'successful': result.get('success_count', 0),
                    'failed': result.get('failed_count', 0),
                    'status': result.get('status'),
                    'error': result.get('error')
                })
                
            except Exception as e:
                logger.error(f"Error processing queue for session {session.session_id}: {str(e)}")
                results['session_details'].append({
                    'session_id': session.session_id,
                    'session_name': session.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
        
    except Exception as e:
        logger.error(f"WhatsApp message queue processing task failed: {str(e)}")
        self.retry(exc=e)