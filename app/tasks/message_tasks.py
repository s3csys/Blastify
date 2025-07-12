"""Celery tasks for asynchronous message processing."""

import time
import logging
from celery import Celery
from app.services.message_service import MessageService
from app.models.message import Message
from app import create_app, db

logger = logging.getLogger(__name__)

# Initialize Celery
celery = Celery('blastify')

# Load Celery config from Flask config
app = create_app()
celery.conf.update(app.config)

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def send_bulk_messages_task(self, platform, messages):
    """Send multiple messages asynchronously.
    
    Args:
        platform: The messaging platform to use
        messages: List of message dictionaries with recipient and message text
        
    Returns:
        Dictionary with results summary
    """
    logger.info(f"Starting bulk send task for {len(messages)} messages on {platform}")
    
    results = {
        'total': len(messages),
        'successful': 0,
        'failed': 0,
        'details': []
    }
    
    try:
        # Create message service
        message_service = MessageService.create(platform)
        
        # Process each message
        for msg_data in messages:
            try:
                # Get message details
                recipient = msg_data.get('recipient')
                message_text = msg_data.get('message')
                media_url = msg_data.get('media_url')
                
                if not recipient or not message_text:
                    logger.warning(f"Skipping message with missing data: {msg_data}")
                    results['failed'] += 1
                    results['details'].append({
                        'recipient': recipient,
                        'status': 'failed',
                        'error': 'Missing required data'
                    })
                    continue
                
                # Send message
                result = message_service.send_message(
                    recipient=recipient,
                    message=message_text,
                    media_url=media_url
                )
                
                # Create app context for database operations
                with app.app_context():
                    # Save to database
                    message = Message(
                        platform=platform,
                        recipient=recipient,
                        message_text=message_text,
                        media_url=media_url,
                        status=result.get('status', 'unknown'),
                        external_id=result.get('message_sid') or result.get('message_id')
                    )
                    db.session.add(message)
                    db.session.commit()
                
                # Update results
                if result.get('status') in ['queued', 'sent']:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                    
                results['details'].append({
                    'recipient': recipient,
                    'status': result.get('status', 'unknown'),
                    'message_id': message.id,
                    'external_id': result.get('message_sid') or result.get('message_id')
                })
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.2)
                
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
        logger.error(f"Bulk send task failed: {str(e)}")
        self.retry(exc=e)